"""In-memory dataset: loaded from data/career_quest at startup, extended by uploads, reset on demand.

Uploads accept the dataset format as-is (the jury uploads test profiles at the defense):
employees.json ({"employees": [...]}, a bare list, or a single profile), activity_history.csv
(comma or semicolon separated), events.json, skills.json.
"""

import csv
import datetime as dt
import io
import json
import re
import threading
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from app.models.api import UploadResult
from app.models.dataset import Employee, Event, HistoryRecord, RoleProfile, Skill

DEFAULT_AS_OF = dt.date(2026, 10, 1)


class DataStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.lock = threading.RLock()
        self.version = 0
        self.reset()

    # ---------- loading ----------
    def reset(self) -> None:
        with self.lock:
            self.as_of = DEFAULT_AS_OF
            self.proficiency_scale: dict[str, str] = {}
            self.skills: dict[str, Skill] = {}
            self.role_profiles: dict[tuple[str, str], RoleProfile] = {}
            self.employees: dict[str, Employee] = {}
            self.events: dict[str, Event] = {}
            self.history: dict[str, HistoryRecord] = {}
            result = _empty_result()
            for name in ("skills.json", "events.json", "employees.json"):
                self._ingest_json(json.loads((self.data_dir / name).read_text("utf-8-sig")), result)
            self._ingest_csv((self.data_dir / "activity_history.csv").read_text("utf-8-sig"), result)
            self._touch()

    def ingest_files(self, files: list[tuple[str, bytes]]) -> UploadResult:
        """Upsert uploaded dataset files. Employees in an uploaded history file get their history replaced."""
        result = _empty_result()
        with self.lock:
            pre_existing = set(self.employees)
            # catalogue first, then people, then history (CSV) — so references resolve in one upload
            order = {"skill": 0, "event": 1, "employ": 2}

            def rank(f: tuple[str, bytes]) -> tuple[int, int]:
                name = f[0].lower()
                return name.endswith(".csv"), next((v for k, v in order.items() if k in name), 3)

            for filename, raw in sorted(files, key=rank):
                text = raw.decode("utf-8-sig", errors="replace")
                try:
                    if filename.lower().endswith(".csv"):
                        self._ingest_csv(text, result, replace_history=True)
                    else:
                        self._ingest_json(json.loads(text), result)
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    result.warnings.append(f"{filename}: не удалось разобрать ({e})")
            self._touch()
        # newly added employees first — the UI links to them
        added = [e for e in result.employee_ids if e not in pre_existing]
        rest = [e for e in result.employee_ids if e in pre_existing]
        result.employee_ids = list(dict.fromkeys(added + rest))[:100]
        return result

    def _ingest_json(self, obj, result: UploadResult) -> None:
        if isinstance(obj, dict):
            meta = obj.get("meta") or {}
            if meta.get("as_of_date"):
                self.as_of = dt.date.fromisoformat(meta["as_of_date"])
            if obj.get("proficiency_scale"):
                self.proficiency_scale = obj["proficiency_scale"]
            known = False
            for key, kind in (
                ("skills", "skill"),
                ("role_profiles", "role_profile"),
                ("events", "event"),
                ("employees", "employee"),
                ("activity_history", "history"),
                ("history", "history"),
            ):
                if isinstance(obj.get(key), list):
                    known = True
                    for item in obj[key]:
                        self._upsert(kind, item, result)
            if not known:  # a single object
                self._upsert(_guess_kind(obj), obj, result)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    self._upsert(_guess_kind(item), item, result)

    def _ingest_csv(self, text: str, result: UploadResult, replace_history: bool = False) -> None:
        first = text.split("\n", 1)[0]
        delimiter = ";" if first.count(";") > first.count(",") else ","
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(io.StringIO(text), delimiter=delimiter)]
        if replace_history:
            for emp_id in {r.get("employee_id") for r in rows}:
                for rid in [rid for rid, h in self.history.items() if h.employee_id == emp_id]:
                    del self.history[rid]
        for r in rows:
            self._upsert("history", r, result)

    def _upsert(self, kind: str | None, item: dict, result: UploadResult) -> None:
        try:
            if kind == "skill":
                obj = Skill.model_validate(item)
                self._count(result, "skills", obj.skill_id in self.skills)
                self.skills[obj.skill_id] = obj
            elif kind == "role_profile":
                obj = RoleProfile.model_validate(item)
                key = (obj.role, obj.grade)
                self._count(result, "role_profiles", key in self.role_profiles)
                self.role_profiles[key] = obj
            elif kind == "event":
                obj = Event.model_validate(item)
                self._count(result, "events", obj.event_id in self.events)
                self.events[obj.event_id] = obj
            elif kind == "employee":
                obj = Employee.model_validate(item)
                if (obj.role, obj.grade) not in self.role_profiles:
                    result.warnings.append(f"{obj.employee_id}: нет профиля роли {obj.role}/{obj.grade}")
                self._count(result, "employees", obj.employee_id in self.employees)
                self.employees[obj.employee_id] = obj
                result.employee_ids.append(obj.employee_id)
            elif kind == "history":
                if not item.get("record_id"):
                    item = {**item, "record_id": self.next_record_id()}
                obj = HistoryRecord.model_validate(item)
                if obj.employee_id not in self.employees or obj.event_id not in self.events:
                    result.warnings.append(f"{obj.record_id}: неизвестный сотрудник или мероприятие — пропущено")
                    return
                clash = self.history.get(obj.record_id)
                if clash and clash.employee_id != obj.employee_id:  # never overwrite someone else's record
                    obj = obj.model_copy(update={"record_id": self.next_record_id()})
                    clash = None
                self._count(result, "history", clash is not None)
                self.history[obj.record_id] = obj
                result.employee_ids.append(obj.employee_id)
            else:
                result.warnings.append(f"Неизвестный объект: {str(item)[:80]}")
        except ValidationError as e:
            ident = next((item.get(k) for k in ("employee_id", "event_id", "skill_id", "record_id") if item.get(k)), "?")
            result.warnings.append(f"{ident}: {e.errors()[0]['loc']} {e.errors()[0]['msg']}")

    @staticmethod
    def _count(result: UploadResult, key: str, existed: bool) -> None:
        bucket = result.updated if existed else result.added
        bucket[key] = bucket.get(key, 0) + 1

    def _touch(self) -> None:
        self.version += 1
        by_emp: dict[str, list[HistoryRecord]] = defaultdict(list)
        for h in self.history.values():
            by_emp[h.employee_id].append(h)
        for lst in by_emp.values():
            lst.sort(key=lambda h: (h.date, h.record_id))
        self._by_emp = by_emp

    # ---------- queries / mutations ----------
    def history_of(self, employee_id: str) -> list[HistoryRecord]:
        return self._by_emp.get(employee_id, [])

    def next_record_id(self) -> str:
        nums = [int(m.group(1)) for rid in self.history if (m := re.fullmatch(r"R(\d+)", rid))]
        return f"R{(max(nums) + 1 if nums else 1):06d}"

    def add_record(self, record: HistoryRecord) -> None:
        with self.lock:
            self.history[record.record_id] = record
            self._touch()


def _empty_result() -> UploadResult:
    return UploadResult(added={}, updated={}, employee_ids=[], warnings=[])


def _guess_kind(item: dict) -> str | None:
    if "record_id" in item or ("employee_id" in item and "event_id" in item and "status" in item):
        return "history"
    if "employee_id" in item:
        return "employee"
    if "event_id" in item:
        return "event"
    if "required_skills" in item:
        return "role_profile"
    if "skill_id" in item:
        return "skill"
    return None
