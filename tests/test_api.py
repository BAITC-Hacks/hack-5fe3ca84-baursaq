from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from backend.app.main import create_app
from backend.app.store import Store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('HR_PASSWORD', 'hr-demo')
    monkeypatch.setenv('EMPLOYEE_PASSWORD', 'employee-demo')
    return TestClient(create_app(Store(tmp_path / 'api.sqlite3')))


def auth(client, role='employee'):
    response = client.post('/api/auth/login', json={'role': role, 'employee_id': 'E0001',
                                                 'password': 'hr-demo' if role == 'hr' else 'employee-demo'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_permissions_enforced_on_server(client):
    assert client.get('/api/hr/summary').status_code == 401
    employee = auth(client)
    assert client.get('/api/employees/E0001', headers=employee).status_code == 200
    assert client.get('/api/employees/E0002', headers=employee).status_code == 403
    assert client.get('/api/hr/summary', headers=employee).status_code == 403
    assert len(client.get('/api/employees', headers=employee).json()) == 1
    assert client.get('/api/hr/summary', headers=auth(client, 'hr')).status_code == 200


def test_completion_flow_and_errors(client):
    headers = auth(client)
    candidates = client.get('/api/employees/E0001/candidates', headers=headers).json()
    event_id = candidates[0]['event_id']
    result = client.post('/api/employees/E0001/complete', headers=headers, json={'event_id': event_id})
    assert result.status_code == 200 and result.json()['changed']
    repeated = client.post('/api/employees/E0001/complete', headers=headers, json={'event_id': event_id})
    assert not repeated.json()['changed']
    assert client.post('/api/employees/E0001/complete', headers=headers, json={'event_id': 'UNKNOWN'}).status_code == 400


def test_jury_profile_upload(client):
    profile = deepcopy(client.app.state.store.employees['E0001'])
    profile.update(employee_id='JURY002', full_name='Additional profile')
    files = {'employees': ('employees.json', json.dumps({'employees': [profile]}), 'application/json')}
    assert client.post('/api/import', files=files, headers=auth(client)).status_code == 403
    headers = auth(client, 'hr')
    imported = client.post('/api/import', files=files, headers=headers)
    assert imported.status_code == 200
    assert client.get('/api/employees/JURY002', headers=headers).status_code == 200
    assert client.get('/api/employees/JURY002/candidates', headers=headers).json()


def test_invalid_upload_and_login(client):
    assert client.post('/api/auth/login', json={'role': 'hr', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/import', headers=auth(client, 'hr'), files={'employees': ('bad.json', '{broken', 'application/json')}).status_code == 400


def test_logout_revokes_session(client):
    headers = auth(client)
    client.post('/api/auth/logout', headers=headers)
    assert client.get('/api/employees', headers=headers).status_code == 401


def test_invalid_history_does_not_partially_import_profile(client):
    profile = deepcopy(client.app.state.store.employees['E0001'])
    profile.update(employee_id='JURY_BAD_CSV', full_name='Bad CSV test')
    files = {'employees': ('profiles.json', json.dumps([profile]), 'application/json'),
             'history': ('history.csv', 'unrelated,column\n1,2', 'text/csv')}
    response = client.post('/api/import', headers=auth(client, 'hr'), files=files)
    assert response.status_code == 400
    assert 'JURY_BAD_CSV' not in client.app.state.store.employees
