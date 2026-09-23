"""Black-box checks against a running API; uploads only synthetic T001-T005 profiles."""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def request(base, path, data=None, content_type="application/json"):
    headers = {"X-Role": "hr", "Content-Type": content_type}
    req = urllib.request.Request(base.rstrip("/") + "/api" + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def upload(base):
    boundary = "careerquest-" + uuid.uuid4().hex
    body = bytearray()
    for name, mime in [("employees.json", "application/json"), ("activity_history.csv", "text/csv")]:
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{name}\""
                     f"\r\nContent-Type: {mime}\r\n\r\n").encode())
        body.extend((ROOT / "data/test_profiles" / name).read_bytes())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    result = request(base, "/dataset/upload", bytes(body), f"multipart/form-data; boundary={boundary}")
    if result.get("warnings"):
        raise ValueError("Upload warnings: " + json.dumps(result["warnings"], ensure_ascii=True))


def check_profile(profile, response, catalog, elapsed, require_llm):
    errors = []

    def check(ok, message):
        if not ok:
            errors.append(message)

    emp = profile["employee"]
    pid = emp["employee_id"]
    recs = response["recommendations"]
    events = {e["event_id"]: e for e in catalog["events"]}
    skills = {s["skill_id"]: s["effective"] for s in profile["skills"]}
    initial = dict(skills)
    completed = {h["event_id"] for h in profile["history"] if h["status"] == "completed"}
    ids = [r["event_id"] for r in recs]
    check(len(ids) == len(set(ids)), "duplicate recommendation")
    check(len(ids) <= 3, "more than three recommendations")
    check(elapsed <= 10, "response exceeded 10 seconds")
    check(response["source"] in ("llm", "fallback"), "missing source")
    if require_llm and pid != "T005":
        check(response["source"] == "llm", "real LLM required, got fallback")
    if pid != "T005":
        check(bool(recs), "expected at least one useful step")
    for rec in recs:
        event = events.get(rec["event_id"])
        check(event is not None, "unknown event")
        if event is None:
            continue
        check(not event["mandatory"], "mandatory event recommended")
        check(event["event_id"] not in completed or event["event_id"] == "EV_036", "completed event repeated")
        check(not event["target_roles"] or emp["role"] in event["target_roles"], "wrong target role")
        check(not event["target_grades"] or emp["grade"] in event["target_grades"], "wrong grade")
        check(event["format"] == "self_paced" or any(d >= catalog["as_of"] for d in event["upcoming_sessions"]), "no future session")
        check(all(skills.get(s, 0) >= n for s, n in event["prerequisites"].items()), "unmet prerequisite in sequential plan")
        check(bool(rec["rationale"].strip()), "empty explanation")
        expected = dict(skills)
        for gain in event["develops_skills"]:
            sid = gain["skill_id"]
            cur = expected.get(sid, 0)
            expected[sid] = max(cur, min(cur + gain["gain"], gain["max_level"]))
        actual_gains = {g["skill_id"]: (g["before"], g["after"]) for g in rec["gains"]}
        expected_gains = {s: (skills.get(s, 0), n) for s, n in expected.items() if n > skills.get(s, 0)}
        check(actual_gains == expected_gains, "gain differs from catalog and previous plan steps")
        skills = expected
        if pid == "T004" and event["format"] == "offline":
            check(any(f["kind"] == "work_format" and abs(f["impact"] + 0.8) < 0.001 for f in rec["factors"]), "offline recommendation lacks remote penalty")
    if pid == "T001" and recs:
        check(initial["SK_PUBLIC_SPEAKING"] == 0, "fixture no longer has lowest speaking skill")
        check(sum(h["status"] == "no_show" for h in profile["history"]) == 3, "fixture lost three no-shows")
        check(any(f["kind"] == "critical_skill" for f in recs[0]["factors"]), "first step does not address critical skills")
        check(any(g["skill_id"] != "SK_PUBLIC_SPEAKING" for g in recs[0]["gains"]), "lowest-skill-only choice")
        check(len({f["kind"] for r in recs for f in r["factors"]}) >= 3, "plan lacks three distinct factor kinds")
        check(bool(response["rejected"]), "missing explanation of alternatives")
    if pid == "T002":
        # Independently replay the fixture history using catalog caps; do not import engine code.
        expected = dict(emp["skills"])
        for h in sorted(profile["history"], key=lambda h: (h["date"], h["record_id"])):
            if h["status"] == "completed" and h["date"] > emp["last_review_date"]:
                for gain in events[h["event_id"]]["develops_skills"]:
                    sid = gain["skill_id"]
                    cur = expected.get(sid, 0)
                    expected[sid] = max(cur, min(cur + gain["gain"], gain["max_level"]))
        check(all(initial.get(s, 0) == n for s, n in expected.items()), "post-review gains not applied correctly")
        check(initial["SK_SYSTEM_DESIGN"] > emp["skills"]["SK_SYSTEM_DESIGN"], "post-review fixture did not raise skill")
    if pid == "T003":
        blocked = {e["event_id"] for e in events.values() if any(initial.get(s, 0) < n for s, n in e["prerequisites"].items())}
        check(bool(blocked), "fixture has no prerequisite trap")
        if recs:
            check(recs[0]["event_id"] not in blocked, "first step requires unearned prerequisites")
    if pid == "T004":
        check(emp["work_format"] == "remote", "fixture is not remote")
        # Offline is a soft penalty, not a ban. An offline step may still be best.
        check(any(e["format"] == "offline" for e in events.values()), "catalog lacks offline options")
    if pid == "T005":
        check(profile["target"]["readiness_pct"] == 100, "fully skilled profile not ready")
        check(not recs, "invented a step for fully skilled profile")
        check(bool(response["summary"].strip()), "no explanation for empty plan")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-llm", action="store_true", help="Fail fallback responses for T001-T004")
    parser.add_argument("--output", type=Path, help="Write structured results as JSON")
    args = parser.parse_args()
    results = []
    try:
        upload(args.base_url)
        catalog = request(args.base_url, "/catalog")
        print("Profile  Result  Source     Seconds  Steps / errors")
        for pid in ("T001", "T002", "T003", "T004", "T005"):
            profile = request(args.base_url, f"/employees/{pid}")
            started = time.perf_counter()
            response = request(args.base_url, f"/employees/{pid}/recommendations", b'{"language":"ru"}')
            elapsed = time.perf_counter() - started
            errors = check_profile(profile, response, catalog, elapsed, args.require_llm)
            row = dict(profile=pid, passed=not errors, source=response["source"], seconds=round(elapsed, 3),
                       steps=[r["event_id"] for r in response["recommendations"]], errors=errors)
            results.append(row)
            print(f"{pid:7}  {'FAIL' if errors else 'PASS':6}  {row['source']:9}  {elapsed:7.3f}  {', '.join(row['steps']) or '(none)'}")
            for error in errors:
                print("  - " + error)
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("Checks cover structured properties; a human must review explanation quality and language.")
    return int(any(not r["passed"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
