from copy import deepcopy

import pytest

from backend.app.domain import Engine, apply_gain
from backend.app.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'test.sqlite3')


def test_gain_never_reduces_skill_and_respects_cap():
    event = {'develops_skills': [{'skill_id': 'x', 'gain': 2, 'max_level': 3}]}
    assert apply_gain({'x': 4}, event)['x'] == 4
    assert apply_gain({'x': 2}, event)['x'] == 3
    assert apply_gain({}, event)['x'] == 2


def test_post_review_completions_are_applied_once(store):
    engine = Engine(store)
    employee = store.employees['E0001']
    employee['skills']['SK_SYSTEM_DESIGN'] = 0
    employee['last_review_date'] = '2026-09-01'
    store.history_by_employee['E0001'] = [
        {'record_id': 'old', 'date': '2026-08-01', 'event_id': 'EV_005', 'status': 'completed'},
        {'record_id': 'new', 'date': '2026-09-20', 'event_id': 'EV_005', 'status': 'completed'},
        {'record_id': 'future', 'date': '2026-12-20', 'event_id': 'EV_005', 'status': 'completed'},
    ]
    assert engine.levels('E0001')['SK_SYSTEM_DESIGN'] == 1
    assert engine.levels('E0001')['SK_SYSTEM_DESIGN'] == 1


def test_completion_is_persistent_and_idempotent(store):
    engine = Engine(store)
    event = engine.candidates('E0001')[0]
    before = engine.profile('E0001')['progress_pct']
    first = engine.complete('E0001', event['event_id'])
    second = engine.complete('E0001', event['event_id'])
    assert first['changed'] and not second['changed']
    assert first['profile']['progress_pct'] > before
    assert first['profile']['effective_skills'] == second['profile']['effective_skills']
    reopened = Store(store.db.execute('PRAGMA database_list').fetchone()[2])
    assert Engine(reopened).profile('E0001')['progress_pct'] == first['profile']['progress_pct']


def test_all_candidates_obey_catalog_constraints(store):
    engine = Engine(store)
    for employee_id in store.employees:
        for candidate in engine.candidates(employee_id):
            event = store.events[candidate['event_id']]
            assert not event['mandatory']
            assert engine.exclusion(employee_id, event) is None
            assert candidate['projection']['progress_after'] > candidate['projection']['progress_before']
            assert {e['factor'] for e in candidate['evidence']} == {'career_goal', 'skill_gap', 'participation_history'}


def test_history_affects_ranking(store):
    engine = Engine(store)
    before = next(e for e in engine.candidates('E0001') if e['event_id'] == 'EV_005')
    for index in range(3):
        store.history_by_employee['E0001'].append({'record_id': f'negative-{index}', 'date': '2026-09-01',
                                                  'event_id': 'EV_005', 'status': 'no_show'})
    after = next(e for e in engine.candidates('E0001') if e['event_id'] == 'EV_005')
    assert after['score'] < before['score']
    assert after['history_risk_count'] == before['history_risk_count'] + 3


def test_import_is_atomic_and_new_person_can_be_recommended(store):
    profile = deepcopy(store.employees['E0001'])
    profile.update(employee_id='JURY001', full_name='Jury Test')
    invalid = deepcopy(profile)
    invalid.update(employee_id='INVALID', role='Unknown role')
    with pytest.raises(ValueError):
        store.import_data([profile, invalid], [])
    assert 'JURY001' not in store.employees
    result = store.import_data([profile], [])
    assert result['employees_imported'] == 1
    assert Engine(store).candidates('JURY001')


def test_mandatory_and_prerequisite_failure_cannot_be_completed(store):
    engine = Engine(store)
    with pytest.raises(ValueError, match='Обязательная'):
        engine.complete('E0001', 'EV_001')
    event = store.events['EV_005']
    event['prerequisites'] = {'SK_SYSTEM_DESIGN': 5}
    with pytest.raises(ValueError, match='prerequisites'):
        engine.complete('E0001', 'EV_005')


def test_hr_covers_dataset_without_public_rankings(store):
    summary = Engine(store).hr_summary()
    assert summary['employee_count'] == 200
    assert len(summary['participation']) == 40
    assert summary['skill_gaps']
    assert summary['no_next_step']
