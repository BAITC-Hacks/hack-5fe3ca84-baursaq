"""Small persistent store. Original hackathon data is never modified."""
import csv
import io
import json
import os
import sqlite3
from pathlib import Path
from threading import RLock

from .schemas import Employee, HistoryRecord

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'career_quest_dataset' / 'case_1' / 'career_quest_dataset'


def decode_employees(text: str) -> list[dict]:
    data = json.loads(text.lstrip('\ufeff'))
    if isinstance(data, dict):
        data = data.get('employees', [data] if 'employee_id' in data else None)
    if not isinstance(data, list) or not data or len(data) > 1000:
        raise ValueError('JSON должен содержать от 1 до 1000 профилей: массив или объект employees')
    return data


def decode_history(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required = {'record_id', 'employee_id', 'event_id', 'date', 'status', 'completion_pct'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('CSV должен содержать столбцы record_id, employee_id, event_id, date, status, completion_pct')
    rows = list(reader)
    if len(rows) > 20000:
        raise ValueError('Максимум 20000 строк истории за один импорт')
    return [{k: (None if v == '' else v) for k, v in row.items()} for row in rows]


class Store:
    def __init__(self, db_path=None, data_dir=DATA_DIR):
        self.lock = RLock()
        self.data_dir = Path(data_dir)
        self.catalog = json.loads((self.data_dir / 'skills.json').read_text(encoding='utf-8'))
        self.as_of_date = self.catalog['meta']['as_of_date']
        event_data = json.loads((self.data_dir / 'events.json').read_text(encoding='utf-8'))
        self.events = {e['event_id']: e for e in event_data['events']}
        db_path = Path(db_path or os.getenv('DATABASE_PATH', ROOT / '.state' / 'career_quest.sqlite3'))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS employees (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        if not self.db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]:
            employees = decode_employees((self.data_dir / 'employees.json').read_text(encoding='utf-8'))
            history = decode_history((self.data_dir / 'activity_history.csv').read_text(encoding='utf-8'))
            with self.db:
                self.db.executemany('INSERT INTO employees VALUES (?, ?)', [(e['employee_id'], json.dumps(e)) for e in employees])
                self.db.executemany('INSERT INTO history VALUES (?, ?)', [(r['record_id'], json.dumps(r)) for r in history])
        self.reload()

    def reload(self):
        self.employees = {key: json.loads(payload) for key, payload in self.db.execute('SELECT id, payload FROM employees')}
        self.history = [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM history')]
        self.history_by_employee = {key: [] for key in self.employees}
        for record in self.history:
            self.history_by_employee.setdefault(record['employee_id'], []).append(record)
        for history in self.history_by_employee.values():
            history.sort(key=lambda r: (r['date'], r['record_id']))

    def import_data(self, employees, history):
        """Validate entire batch before transactional upsert. Existing runtime progress is reset for replaced profiles."""
        with self.lock:
            profiles = [Employee.model_validate(e).model_dump(mode='json') for e in employees]
            records = [HistoryRecord.model_validate(r).model_dump(mode='json') for r in history]
            ids = [p['employee_id'] for p in profiles]
            record_ids = [r['record_id'] for r in records]
            if len(set(ids)) != len(ids) or len(set(record_ids)) != len(record_ids):
                raise ValueError('В одном импорте ID не должны повторяться')
            known_people = set(self.employees) | set(ids)
            known_skills = {s['skill_id'] for s in self.catalog['skills']}
            role_grades = {(p['role'], p['grade']) for p in self.catalog['role_profiles']}
            for person in profiles:
                if (person['role'], person['grade']) not in role_grades:
                    raise ValueError(f"Неизвестная роль/грейд: {person['employee_id']}")
                goal = person.get('career_goal')
                if goal and (goal['target_role'], goal['target_grade']) not in role_grades:
                    raise ValueError('Неизвестная целевая роль/грейд')
                if set(person['skills']) - known_skills:
                    raise ValueError('Профиль содержит неизвестные skill_id')
                if person['last_review_date'] > self.as_of_date:
                    raise ValueError('Дата оценки позже даты среза 2026-10-01')
            for record in records:
                if record['employee_id'] not in known_people or record['event_id'] not in self.events:
                    raise ValueError('История содержит неизвестный employee_id/event_id')
                if record['date'] > self.as_of_date:
                    raise ValueError('Дата истории позже даты среза')
                if record['status'] == 'completed' and record['completion_pct'] != 100:
                    raise ValueError('completed требует completion_pct=100')
            previous = {r['record_id']: r for r in self.history}
            for record in records:
                old = previous.get(record['record_id'])
                if old and (old['employee_id'] != record['employee_id'] or old['event_id'] != record['event_id']):
                    raise ValueError('record_id уже принадлежит другой записи')
            with self.db:
                for old in self.history:
                    if old.get('runtime') and old['employee_id'] in ids:
                        self.db.execute('DELETE FROM history WHERE id=?', (old['record_id'],))
                self.db.executemany('INSERT OR REPLACE INTO employees VALUES (?, ?)', [(p['employee_id'], json.dumps(p)) for p in profiles])
                self.db.executemany('INSERT OR REPLACE INTO history VALUES (?, ?)', [(r['record_id'], json.dumps(r)) for r in records])
            self.reload()
            return {'employees_imported': len(profiles), 'history_imported': len(records)}

    def add_completion(self, employee_id, event_id):
        record = {
            'record_id': f'demo:{employee_id}:{event_id}:{self.as_of_date}',
            'employee_id': employee_id, 'event_id': event_id, 'date': self.as_of_date,
            'due_date': None, 'status': 'completed', 'completion_pct': 100,
            'score': None, 'feedback_rating': None, 'assigned_by': 'self', 'runtime': True,
        }
        with self.lock, self.db:
            cursor = self.db.execute('INSERT OR IGNORE INTO history VALUES (?, ?)', (record['record_id'], json.dumps(record)))
            changed = bool(cursor.rowcount)
            self.reload()
        return changed
