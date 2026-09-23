import json

from tests.conftest import HR


def test_health(client):
    body = client.get("/api/health").json()
    assert body["employees"] == 200 and body["events"] == 40 and body["history"] == 2743


def test_effective_skills_trap(client):
    """E0028 (example from the task) completed EV_006 after the last review: System Design is 3, not 2."""
    p = client.get("/api/employees/E0028", headers=HR).json()
    sd = next(s for s in p["skills"] if s["skill_id"] == "SK_SYSTEM_DESIGN")
    assert (sd["assessed"], sd["effective"], sd["pending_from"]) == (2, 3, ["EV_006"])
    assert p["target"]["grade"] == "Senior" and "SK_SYSTEM_DESIGN" in p["target"]["blockers"]


def test_recommendations_are_multifactor(client):
    r = client.post("/api/employees/E0028/recommendations", headers=HR, json={"language": "ru"}).json()
    assert 1 <= len(r["recommendations"]) <= 3
    for rec in r["recommendations"]:
        assert rec["event_id"] not in {"EV_001", "EV_002", "EV_003", "EV_004", "EV_006"}  # mandatory / done
        assert len({f["kind"] for f in rec["factors"]}) >= 2 and len(rec["factors"]) >= 3
        assert rec["rationale"]
    assert r["trace"] and r["source"] == "fallback"


def test_complete_moves_progress(client):
    before = client.get("/api/employees/E0028", headers=HR).json()
    step = next(s for s in before["next_steps"] if s["closes_gap"])
    res = client.post("/api/employees/E0028/complete", headers=HR, json={"event_id": step["event_id"]}).json()
    assert res["changes"] and res["readiness_after"] >= res["readiness_before"]
    assert step["event_id"] not in {s["event_id"] for s in res["profile"]["next_steps"]}


def test_permissions(client):
    me = {"X-Role": "employee", "X-Employee-Id": "E0028"}
    assert client.get("/api/employees/E0028", headers=me).status_code == 200
    assert client.get("/api/employees/E0001", headers=me).status_code == 403
    assert client.get("/api/hr/overview", headers=me).status_code == 403
    hr = client.get("/api/hr/overview", headers=HR).json()
    assert hr["lagging_skills"] and hr["participation"]


def test_bad_history_csv_changes_nothing(client):
    """Found in review: a CSV with an unknown event used to wipe the employee's history."""
    before = len(client.get("/api/employees/E0001", headers=HR).json()["history"])
    csv = "record_id,employee_id,event_id,date,status,completion_pct\nR999999,E0001,EV_999,2026-09-01,completed,100"
    up = client.post("/api/dataset/upload", headers=HR, files=[("files", ("activity_history.csv", csv, "text/csv"))])
    assert up.status_code == 200 and up.json()["warnings"]
    assert len(client.get("/api/employees/E0001", headers=HR).json()["history"]) == before


def test_malformed_uploads_warn_instead_of_500(client):
    """Found in QA audit: null/str items, extra CSV values and a foreign meta date broke or shifted the store."""
    files = [
        ("files", ("employees.json", json.dumps({"meta": {"as_of_date": "2030-01-01"}, "employees": [None, "bad"]}),
                   "application/json")),
        ("files", ("activity_history.csv",
                   "record_id,employee_id,event_id,date,status,completion_pct\nQA1,E0001,EV_005,2026-09-20,completed,100,X",
                   "text/csv")),
        ("files", ("scalar.json", "42", "application/json")),
    ]
    r = client.post("/api/dataset/upload", headers=HR, files=files)
    assert r.status_code == 200 and len(r.json()["warnings"]) >= 3
    assert client.get("/api/health").json()["as_of"] == "2026-10-01"


def test_complete_respects_eligibility(client):
    """Found in review: a Junior could 'complete' a Middle+ workshop and get free skill points."""
    r = client.post("/api/employees/E0001/complete", headers=HR, json={"event_id": "EV_006"})
    assert r.status_code == 409
    club = client.post("/api/employees/E0028/complete", headers=HR, json={"event_id": "EV_036"})
    again = client.post("/api/employees/E0028/complete", headers=HR, json={"event_id": "EV_036"})
    assert club.status_code == 200 and again.status_code == 409  # recurring club: same day counts once


def test_not_now_hides_step_without_touching_history(client):
    first = client.post("/api/employees/E0028/recommendations", headers=HR, json={}).json()["recommendations"][0]
    history = len(client.get("/api/employees/E0028", headers=HR).json()["history"])
    r = client.post("/api/employees/E0028/feedback", headers=HR, json={"event_id": first["event_id"]})
    assert r.status_code == 200 and r.json()["status"] == "snoozed"
    again = client.post("/api/employees/E0028/recommendations", headers=HR, json={}).json()["recommendations"]
    assert first["event_id"] not in {x["event_id"] for x in again}
    assert len(client.get("/api/employees/E0028", headers=HR).json()["history"]) == history


def test_upload_jury_like_trap_profile(client):
    """Lowest skill is Public Speaking, but 3 no-shows at the speaking club; System Design is critical for Senior."""
    emp = {
        "employee_id": "T0001", "full_name": "Test Trap", "department": "Backend Development",
        "role": "Backend Engineer", "grade": "Middle", "manager_id": "E0050", "hire_date": "2023-03-01",
        "tenure_months": 43, "work_format": "office", "preferred_language": "ru", "career_goal": None,
        "skills": {"SK_PYTHON": 3, "SK_SQL": 3, "SK_API_DESIGN": 3, "SK_SYSTEM_DESIGN": 2, "SK_CLOUD": 2,
                   "SK_CONTAINERS": 2, "SK_CICD": 2, "SK_APP_SECURITY": 2, "SK_COMMUNICATION": 3,
                   "SK_PUBLIC_SPEAKING": 0, "SK_TEAMWORK": 3, "SK_PROBLEM_SOLVING": 3},
        "last_review_date": "2026-06-01",
    }
    rows = ["record_id,employee_id,event_id,date,due_date,status,completion_pct,score,feedback_rating,assigned_by"]
    rows += [f"R9{i:05d},T0001,EV_036,2026-0{i + 2}-10,,no_show,0,,,manager" for i in range(3)]
    rows += ["R900010,T0001,EV_011,2026-03-02,,completed,100,,5,self",
             "R900011,T0001,EV_019,2026-04-14,,completed,100,,4,self"]
    files = [("files", ("employees.json", json.dumps({"employees": [emp]}), "application/json")),
             ("files", ("activity_history.csv", "\n".join(rows), "text/csv"))]
    up = client.post("/api/dataset/upload", headers=HR, files=files).json()
    assert up["added"] == {"employees": 1, "history": 5} and up["employee_ids"][0] == "T0001"

    r = client.post("/api/employees/T0001/recommendations", headers=HR, json={}).json()
    first = r["recommendations"][0]
    assert any(g["skill_id"] == "SK_SYSTEM_DESIGN" for g in first["gains"])
    assert all(rec["event_id"] != "EV_036" for rec in r["recommendations"])
    assert any(x.get("skill_id") == "SK_PUBLIC_SPEAKING" for x in r["rejected"])
