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
