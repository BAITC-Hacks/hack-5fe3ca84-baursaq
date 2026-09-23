"""Deterministic facts shared by API and agent tools."""
from collections import Counter
from copy import deepcopy

GRADES = ['Junior', 'Middle', 'Senior', 'Lead']


def apply_gain(levels, event):
    result = dict(levels)
    for development in event['develops_skills']:
        key = development['skill_id']
        current = result.get(key, 0)
        result[key] = max(current, min(5, development['max_level'], current + development['gain']))
    return result


class Engine:
    def __init__(self, store):
        self.store = store
        self.skills = {s['skill_id']: s for s in store.catalog['skills']}
        self.role_profiles = {(p['role'], p['grade']): p for p in store.catalog['role_profiles']}

    def history(self, employee_id):
        return [r for r in self.store.history_by_employee.get(employee_id, []) if r['date'] <= self.store.as_of_date]

    def levels(self, employee_id):
        employee = self.store.employees[employee_id]
        levels = dict(employee['skills'])
        for record in self.history(employee_id):
            if record['status'] == 'completed' and (record.get('runtime') or record['date'] > employee['last_review_date']):
                levels = apply_gain(levels, self.store.events[record['event_id']])
        return levels

    def target(self, employee):
        goal = employee.get('career_goal')
        if goal:
            role, grade = goal['target_role'], goal['target_grade']
        else:
            role = employee['role']
            grade = GRADES[min(GRADES.index(employee['grade']) + 1, 3)]
        return self.role_profiles[(role, grade)]

    @staticmethod
    def progress(levels, target):
        required = target['required_skills']
        total = sum(required.values())
        matched = sum(min(levels.get(key, 0), value) for key, value in required.items())
        return round(100 * matched / total, 1) if total else 100.0

    def profile(self, employee_id):
        employee = deepcopy(self.store.employees[employee_id])
        levels = self.levels(employee_id)
        target = self.target(employee)
        rows = []
        for key in sorted(set(levels) | set(target['required_skills'])):
            current, required = levels.get(key, 0), target['required_skills'].get(key, 0)
            rows.append({'skill_id': key, 'name': self.skills[key]['name'], 'current': current,
                         'required': required, 'gap': max(0, required-current), 'critical': key in target['critical_skills']})
        rows.sort(key=lambda s: (not (s['critical'] and s['gap']), -s['gap'], s['name']))
        history = [dict(r, title=self.store.events[r['event_id']]['title']) for r in self.history(employee_id)]
        counts = Counter(r['status'] for r in history)
        return {'employee': employee, 'effective_skills': levels, 'skills': rows,
                'target': {'role': target['role'], 'grade': target['grade'], 'critical_skills': target['critical_skills']},
                'progress_pct': self.progress(levels, target), 'history': list(reversed(history)),
                'history_summary': dict(counts), 'as_of_date': self.store.as_of_date}

    def exclusion(self, employee_id, event):
        employee = self.store.employees[employee_id]
        levels = self.levels(employee_id)
        history = self.history(employee_id)
        if event['mandatory']:
            return 'Обязательная активность не является рекомендацией развития'
        if employee['role'] not in event['target_roles'] or employee['grade'] not in event['target_grades']:
            return 'Не соответствует текущей роли или грейду'
        if any(levels.get(key, 0) < value for key, value in event['prerequisites'].items()):
            return 'Не выполнены prerequisites'
        completed = [r for r in history if r['event_id'] == event['event_id'] and r['status'] == 'completed']
        if completed and (event['event_id'] != 'EV_036' or any(r['date'] == self.store.as_of_date for r in completed)):
            return 'Уже завершено'
        if event['format'] != 'self_paced' and not any(d >= self.store.as_of_date for d in event['upcoming_sessions']):
            return 'Нет предстоящей сессии'
        return None

    def simulate(self, employee_id, event_id):
        if event_id not in self.store.events:
            raise ValueError('Неизвестная активность')
        event = self.store.events[event_id]
        if reason := self.exclusion(employee_id, event):
            raise ValueError(reason)
        levels = self.levels(employee_id)
        after = apply_gain(levels, event)
        target = self.target(self.store.employees[employee_id])
        changes = [{'skill_id': key, 'name': self.skills[key]['name'], 'before': levels.get(key, 0), 'after': value}
                   for key, value in after.items() if value > levels.get(key, 0)]
        return {'event_id': event_id, 'changes': changes,
                'progress_before': self.progress(levels, target), 'progress_after': self.progress(after, target)}

    def candidates(self, employee_id):
        employee = self.store.employees[employee_id]
        levels = self.levels(employee_id)
        target = self.target(employee)
        history = self.history(employee_id)
        candidates = []
        for event in self.store.events.values():
            if self.exclusion(employee_id, event):
                continue
            projection = self.simulate(employee_id, event['event_id'])
            if not projection['changes']:
                continue
            benefit = 0.0
            gaps = []
            for change in projection['changes']:
                key = change['skill_id']
                gap = max(0, target['required_skills'].get(key, 0) - levels.get(key, 0))
                if gap:
                    closed = min(gap, change['after']-change['before'])
                    benefit += closed * (3 if key in target['critical_skills'] else 1)
                    gaps.append({'skill_id': key, 'current': change['before'], 'required': target['required_skills'][key],
                                 'critical': key in target['critical_skills'], 'gap_closed': closed})
            if not gaps:
                continue
            negatives = []
            for record in history:
                past = self.store.events[record['event_id']]
                shared = {s['skill_id'] for s in past['develops_skills']} & {s['skill_id'] for s in event['develops_skills']}
                if record['status'] in ('no_show', 'declined', 'dropped') and (record['event_id'] == event['event_id'] or shared):
                    negatives.append(record)
            remote_penalty = 0.5 if employee['work_format'] == 'remote' and event['format'] == 'offline' else 1.0
            score = round(benefit * remote_penalty / (1 + 0.3*len(negatives)), 3)
            evidence = [
                {'factor': 'career_goal', 'source': f'employees:{employee_id}',
                 'text': f"{employee['role']} / {employee['grade']} → {target['role']} / {target['grade']}"},
                {'factor': 'skill_gap', 'source': f"role_profiles:{target['role']}:{target['grade']}",
                 'text': '; '.join(f"{self.skills[g['skill_id']]['name']}: {g['current']}/{g['required']}" + (' (критичный)' if g['critical'] else '') for g in gaps)},
                {'factor': 'participation_history', 'source': f'activity_history:{employee_id}',
                 'text': f"Завершено: {sum(r['status']=='completed' for r in history)}; отказов/пропусков/прерываний сходных активностей: {len(negatives)}"},
            ]
            candidates.append({'event_id': event['event_id'], 'title': event['title'], 'description': event['description'],
                               'format': event['format'], 'type': event['type'], 'duration_hours': event['duration_hours'],
                               'next_session': min((d for d in event['upcoming_sessions'] if d >= self.store.as_of_date), default=None),
                               'score': score, 'gaps': gaps, 'history_risk_count': len(negatives),
                               'evidence': evidence, 'projection': projection})
        return sorted(candidates, key=lambda e: (-e['score'], e['duration_hours'], e['event_id']))

    def complete(self, employee_id, event_id):
        with self.store.lock:
            if event_id not in self.store.events:
                raise ValueError('Неизвестная активность')
            if self.store.events[event_id]['mandatory']:
                raise ValueError('Обязательная активность не является рекомендацией развития')
            existing = [r for r in self.history(employee_id) if r['event_id'] == event_id and r['status'] == 'completed']
            if existing and (event_id != 'EV_036' or any(r['date'] == self.store.as_of_date for r in existing)):
                return {'changed': False, 'profile': self.profile(employee_id)}
            self.simulate(employee_id, event_id)
            changed = self.store.add_completion(employee_id, event_id)
            return {'changed': changed, 'profile': self.profile(employee_id)}

    def hr_summary(self):
        gaps = Counter()
        no_step = []
        for employee_id, employee in self.store.employees.items():
            profile = self.profile(employee_id)
            gaps.update(s['skill_id'] for s in profile['skills'] if s['gap'] > 0)
            if not self.candidates(employee_id):
                no_step.append({'employee_id': employee_id, 'full_name': employee['full_name'],
                                'reason': 'Цель покрыта или нет доступных активностей, закрывающих разрыв'})
        by_event = {}
        for row in self.store.history:
            if row['date'] <= self.store.as_of_date:
                by_event.setdefault(row['event_id'], Counter())[row['status']] += 1
        return {'employee_count': len(self.store.employees), 'as_of_date': self.store.as_of_date,
                'skill_gaps': [{'skill_id': key, 'name': self.skills[key]['name'], 'employee_count': count} for key, count in gaps.most_common()],
                'no_next_step': no_step,
                'participation': [{'event_id': key, 'title': event['title'], 'statuses': dict(by_event.get(key, {}))}
                                  for key, event in self.store.events.items()]}
