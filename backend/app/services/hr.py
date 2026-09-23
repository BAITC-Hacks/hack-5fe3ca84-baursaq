"""HR analytics: lagging skills, employees without a recommended step, participation, drop-out signals.

Aggregates only — no rankings of employees against each other (ТЗ constraint).
"""

import datetime as dt
from collections import Counter, defaultdict

from app.models.api import AtRiskEmployee, EventParticipation, HROverview, LaggingSkill, NoStepEmployee
from app.services import engine
from app.services.store import DataStore

_cache: dict[int, HROverview] = {}


def overview(store: DataStore) -> HROverview:
    if store.version in _cache:
        return _cache[store.version]
    lag: dict[str, dict[str, float]] = defaultdict(Counter)
    no_step: list[NoStepEmployee] = []
    at_risk: list[AtRiskEmployee] = []
    year_ago = store.as_of - dt.timedelta(days=365)

    for emp in store.employees.values():
        ctx = engine.build_context(store, emp.employee_id, lang="ru")
        for sid, need in ctx.current_req.items():
            if ctx.effective.get(sid, 0) < need:
                lag[sid]["below_current"] += 1
        for sid, eff, need in engine.gaps(ctx):
            lag[sid]["below_target"] += 1
            lag[sid]["gap_sum"] += need - eff
            if sid in ctx.target_critical:
                lag[sid]["critical_blockers"] += 1

        if not engine.plan(ctx, k=1):
            open_gaps = engine.gaps(ctx)
            if not open_gaps:
                reason = "Требования цели выполнены — обсудить повышение"
            else:
                names = ", ".join(ctx.skill_name(sid) for sid, _, _ in open_gaps[:3])
                reason = f"Нет доступных активностей для: {names}"
            no_step.append(NoStepEmployee(employee_id=emp.employee_id, full_name=emp.full_name, role=emp.role,
                                          grade=emp.grade, reason=reason))

        signals = []
        recent = [h for h in ctx.history if h.date >= year_ago]
        voluntary = [h for h in recent if not store.events[h.event_id].mandatory]
        fails = sum(h.status in engine.NEGATIVE for h in voluntary)
        if fails >= 2:
            signals.append(f"{fails} срыва добровольных активностей за 12 мес")
        if emp.tenure_months >= 12 and not any(h.status == "completed" for h in voluntary):
            signals.append("Нет пройденных добровольных активностей за 12 мес")
        overdue = sum(h.status == "overdue" for h in recent)
        if signals and overdue:  # context only — mandatory training alone is not "dropping out of development"
            signals.append(f"Просрочено обязательное обучение: {overdue}")
        if signals:
            at_risk.append(AtRiskEmployee(employee_id=emp.employee_id, full_name=emp.full_name, role=emp.role,
                                          grade=emp.grade, signals=signals,
                                          last_voluntary_date=ctx.signals.last_voluntary))

    lagging = [
        LaggingSkill(skill_id=sid, name=store.skills[sid].name if sid in store.skills else sid,
                     category=store.skills[sid].category if sid in store.skills else "",
                     below_current=int(v["below_current"]), below_target=int(v["below_target"]),
                     critical_blockers=int(v["critical_blockers"]),
                     avg_gap=round(v["gap_sum"] / v["below_target"], 2) if v["below_target"] else 0.0)
        for sid, v in lag.items()
    ]
    lagging.sort(key=lambda x: (-x.below_current, -x.below_target))
    at_risk.sort(key=lambda a: -len(a.signals))

    per_event: dict[str, Counter] = defaultdict(Counter)
    feedback: dict[str, list[int]] = defaultdict(list)
    for h in store.history.values():
        per_event[h.event_id][h.status] += 1
        if h.feedback_rating:
            feedback[h.event_id].append(h.feedback_rating)
    participation = []
    for ev in store.events.values():
        c = per_event.get(ev.event_id, Counter())
        total = sum(c.values())
        fb = feedback.get(ev.event_id)
        participation.append(EventParticipation(
            event_id=ev.event_id, title=ev.title, type=ev.type, format=ev.format, mandatory=ev.mandatory,
            total=total, completed=c["completed"], in_progress=c["in_progress"], dropped=c["dropped"],
            no_show=c["no_show"], declined=c["declined"], overdue=c["overdue"],
            completion_rate=round(c["completed"] / total, 3) if total else 0.0,
            avg_feedback=round(sum(fb) / len(fb), 2) if fb else None))

    result = HROverview(
        as_of=store.as_of,
        totals={"employees": len(store.employees), "events": len(store.events), "history": len(store.history),
                "no_recommendation": len(no_step), "at_risk": len(at_risk)},
        lagging_skills=lagging[:20], no_recommendation=no_step, participation=participation, at_risk=at_risk)
    _cache.clear()
    _cache[store.version] = result
    return result
