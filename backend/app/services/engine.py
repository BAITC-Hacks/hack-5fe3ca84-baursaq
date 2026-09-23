"""Deterministic, explainable recommendation engine — the part the jury can verify.

Per employee: effective skills (last review + activities completed after it) → target role/grade →
gaps → history signals → eligible events → multi-factor score → greedy 3-step plan with simulated
skill growth → "why not" list. The LLM layer (agents/recommender.py) only re-ranks and explains
what this module produces; every number shown to the user comes from here.
"""

import datetime as dt
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.models.api import (
    CompleteResponse,
    EmployeeProfile,
    Factor,
    HistoryItem,
    NextStep,
    Rejected,
    SkillDelta,
    SkillState,
    Target,
    TrajectoryStep,
)
from app.models.dataset import GRADES, Employee, Event, HistoryRecord
from app.services.i18n import fmt, t, typ
from app.services.store import DataStore

NEGATIVE = {"no_show", "declined", "dropped"}
RECURRING = {"EV_036"}  # the only event that may be repeated after completion
LANGS = ("kk", "ru", "en")

# Scoring weights (documented in README → «Как считается рекомендация»)
W_GAP = 1.0  # per level of a target-grade gap closed
W_CRITICAL_EXTRA = 1.0  # extra per level when the skill is critical for the target grade
W_CATCHUP = 0.75  # extra per level while still below the CURRENT grade requirement
W_GROWTH = 0.2  # per level of growth beyond requirements
W_GOAL = 0.2  # closes a gap of an explicit career goal
P_SAME = 1.0  # per past failure (no-show/declined/dropped) of the same event, cap 3
P_SIMILAR = 0.6  # per past failure of other events developing the same skill, cap 2.4
P_FORMAT = 0.8  # the format failed in >= 50% of voluntary attempts (min 2)
P_REMOTE_OFFLINE = 0.8
P_LONG = 0.2  # > 16 hours
B_TYPE = 0.4  # >= 2 completed voluntary activities of the same type
B_FEEDBACK = 0.3  # average own rating of this type >= 4
B_MOTIVATION = 0.3  # self-initiated completion on the same skill
B_IN_PROGRESS = 0.6
B_SOON = 0.2  # next session within 21 days
B_SELF_PACED = 0.15


# ---------------------------------------------------------------- building blocks
@dataclass
class Signals:
    counts: Counter = field(default_factory=Counter)
    completed: set[str] = field(default_factory=set)
    in_progress: dict[str, int] = field(default_factory=dict)
    neg_event: Counter = field(default_factory=Counter)
    neg_skill_event: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    fmt_total: Counter = field(default_factory=Counter)
    fmt_neg: Counter = field(default_factory=Counter)
    fmt_neg_events: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    type_done: Counter = field(default_factory=Counter)
    type_feedback: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    self_skill: Counter = field(default_factory=Counter)
    voluntary_done: int = 0
    last_voluntary: dt.date | None = None


def history_signals(history: list[HistoryRecord], events: dict[str, Event]) -> Signals:
    s = Signals()
    for h in history:
        s.counts[h.status] += 1
        ev = events.get(h.event_id)
        if ev is None:
            continue
        if h.status == "completed":
            s.completed.add(h.event_id)
            s.in_progress.pop(h.event_id, None)
        elif h.status == "in_progress" and h.event_id not in s.completed:
            s.in_progress[h.event_id] = h.completion_pct
        if ev.mandatory:
            continue  # mandatory processes say nothing about motivation
        s.fmt_total[ev.format] += 1
        if h.status in NEGATIVE:
            s.neg_event[h.event_id] += 1
            s.fmt_neg[ev.format] += 1
            s.fmt_neg_events[ev.format].add(h.event_id)
            for g in ev.develops_skills:
                s.neg_skill_event[g.skill_id][h.event_id] += 1
        if h.status == "completed":
            s.type_done[ev.type] += 1
            s.voluntary_done += 1
            s.last_voluntary = max(s.last_voluntary or h.date, h.date)
            if h.assigned_by == "self":
                for g in ev.develops_skills:
                    s.self_skill[g.skill_id] += 1
        if h.feedback_rating:
            s.type_feedback[ev.type].append(h.feedback_rating)
    return s


def effective_skills(emp: Employee, history: list[HistoryRecord], events: dict[str, Event]):
    """Skill levels = last review + gains of activities completed AFTER last_review_date."""
    eff = dict(emp.skills)
    pending: dict[str, list[str]] = defaultdict(list)
    for h in history:
        if h.status != "completed" or emp.last_review_date is None or h.date <= emp.last_review_date:
            continue
        ev = events.get(h.event_id)
        for sid, before, after in gains_of(ev, eff) if ev else []:
            eff[sid] = after
            pending[sid].append(ev.event_id)
    return eff, dict(pending)


def gains_of(ev: Event, skills: dict[str, int]) -> list[tuple[str, int, int]]:
    out = []
    for g in ev.develops_skills:
        cur = skills.get(g.skill_id, 0)
        new = max(cur, min(cur + g.gain, g.max_level))
        if new > cur:
            out.append((g.skill_id, cur, new))
    return out


def readiness(skills: dict[str, int], required: dict[str, int], critical: set[str]) -> int:
    """Weighted share of the requirement covered; critical skills count double."""
    num = den = 0.0
    for sid, need in required.items():
        if need <= 0:
            continue
        w = 2.0 if sid in critical else 1.0
        num += w * min(skills.get(sid, 0), need) / need
        den += w
    return round(100 * num / den) if den else 100


def availability(ev: Event, as_of: dt.date) -> tuple[bool, dt.date | None]:
    if ev.format == "self_paced":
        return True, None
    upcoming = sorted(d for d in ev.upcoming_sessions if d >= as_of)
    return bool(upcoming), (upcoming[0] if upcoming else None)


# ---------------------------------------------------------------- per-employee context
@dataclass
class Ctx:
    store: DataStore
    emp: Employee
    lang: str
    history: list[HistoryRecord]
    effective: dict[str, int]
    pending: dict[str, list[str]]
    target_role: str
    target_grade: str
    target_source: str
    target_req: dict[str, int]
    target_critical: set[str]
    current_req: dict[str, int]
    signals: Signals

    def skill_name(self, sid: str) -> str:
        s = self.store.skills.get(sid)
        return s.name if s else sid

    @property
    def readiness_now(self) -> int:
        return readiness(self.effective, self.target_req, self.target_critical)


def resolve_target(store: DataStore, emp: Employee) -> tuple[str, str, str]:
    goal = emp.career_goal
    if goal and (goal.target_role, goal.target_grade) in store.role_profiles and (
        goal.target_role != emp.role or goal.target_grade != emp.grade
    ):
        return goal.target_role, goal.target_grade, "career_goal"
    idx = GRADES.index(emp.grade) if emp.grade in GRADES else 0
    if idx + 1 < len(GRADES) and (emp.role, GRADES[idx + 1]) in store.role_profiles:
        return emp.role, GRADES[idx + 1], "next_grade"
    return emp.role, emp.grade, "current_grade"


def build_context(store: DataStore, emp_id: str, lang: str | None = None) -> Ctx:
    emp = store.employees[emp_id]
    history = store.history_of(emp_id)
    eff, pending = effective_skills(emp, history, store.events)
    role, grade, source = resolve_target(store, emp)
    tp = store.role_profiles.get((role, grade))
    cp = store.role_profiles.get((emp.role, emp.grade))
    lang = lang if lang in LANGS else (emp.preferred_language if emp.preferred_language in LANGS else "ru")
    return Ctx(
        store=store,
        emp=emp,
        lang=lang,
        history=history,
        effective=eff,
        pending=pending,
        target_role=role,
        target_grade=grade,
        target_source=source,
        target_req=dict(tp.required_skills) if tp else {},
        target_critical=set(tp.critical_skills) if tp else set(),
        current_req=dict(cp.required_skills) if cp else {},
        signals=history_signals(history, store.events),
    )


# ---------------------------------------------------------------- eligibility & scoring
def eligibility(ctx: Ctx, ev: Event, skills: dict[str, int]) -> str | None:
    """None if the event can be recommended now, otherwise a reason code."""
    if ev.mandatory:
        return "mandatory"
    emp = ctx.emp
    own = (not ev.target_roles or emp.role in ev.target_roles) and (
        not ev.target_grades or emp.grade in ev.target_grades
    )
    for_goal = (
        ctx.target_source == "career_goal"
        and ctx.target_role != emp.role
        and ctx.target_role in ev.target_roles
        and (emp.grade in ev.target_grades or ctx.target_grade in ev.target_grades)
    )
    if not (own or for_goal):
        return "audience"
    if ev.event_id in ctx.signals.completed and ev.event_id not in RECURRING:
        return "completed"
    if not availability(ev, ctx.store.as_of)[0]:
        return "no_sessions"
    for sid, need in ev.prerequisites.items():
        if skills.get(sid, 0) < need:
            return f"prereq:{sid}:{need}"
    return None


@dataclass
class Scored:
    event: Event
    score: float
    factors: list[Factor]
    gains: list[tuple[str, int, int]]
    closes_gap: bool
    next_session: dt.date | None


def score_event(ctx: Ctx, ev: Event, skills: dict[str, int], unlocked_by: int | None = None) -> Scored | None:
    gains = gains_of(ev, skills)
    if not gains:
        return None  # already at max_level for everything it develops
    L, s, F = ctx.lang, ctx.signals, []
    closes = False
    for sid, before, after in gains:
        name = ctx.skill_name(sid)
        need_t = ctx.target_req.get(sid, 0)
        closed = max(0, min(after, need_t) - before)
        if closed:
            closes = True
            F.append(Factor(kind="skill_gap", impact=W_GAP * closed, label=t(
                "gap", L, skill=name, before=before, after=after, grade=ctx.target_grade, req=need_t)))
            if sid in ctx.target_critical:
                F.append(Factor(kind="critical_skill", impact=W_CRITICAL_EXTRA * closed, label=t(
                    "critical", L, skill=name, grade=ctx.target_grade)))
        need_c = ctx.current_req.get(sid, 0)
        catch = max(0, min(after, need_c) - before)
        if catch:
            closes = True
            F.append(Factor(kind="grade_requirement", impact=W_CATCHUP * catch, label=t(
                "catchup", L, skill=name, eff=before, req=need_c)))
        if not closed and not catch:
            F.append(Factor(kind="growth", impact=W_GROWTH * (after - before), label=t("growth", L, skill=name)))
    if closes and ctx.target_source == "career_goal":
        F.append(Factor(kind="career_goal", impact=W_GOAL, label=t(
            "goal", L, role=ctx.target_role, grade=ctx.target_grade)))

    # participation history
    n_same = s.neg_event.get(ev.event_id, 0)
    if n_same:
        F.append(Factor(kind="history", impact=-min(3.0, P_SAME * n_same), label=t("neg_same", L, n=n_same)))
    worst_sid, n_sim = None, 0
    for g in ev.develops_skills:
        n = sum(c for e, c in s.neg_skill_event.get(g.skill_id, {}).items() if e != ev.event_id)
        if n > n_sim:
            worst_sid, n_sim = g.skill_id, n
    if n_sim:
        F.append(Factor(kind="history", impact=-min(2.4, P_SIMILAR * n_sim), label=t(
            "neg_similar", L, skill=ctx.skill_name(worst_sid), n=n_sim)))
    # format aversion only if failures span >= 2 OTHER activities in this format (not one disliked club)
    total, neg = s.fmt_total.get(ev.format, 0), s.fmt_neg.get(ev.format, 0)
    if len(s.fmt_neg_events.get(ev.format, set()) - {ev.event_id}) >= 2 and neg / total >= 0.5:
        F.append(Factor(kind="history", impact=-P_FORMAT, label=t(
            "neg_format", L, format=fmt(ev.format, L), n=neg, total=total)))
    done = s.type_done.get(ev.type, 0)
    if done >= 2:
        F.append(Factor(kind="history", impact=B_TYPE, label=t("pos_type", L, n=done, type=typ(ev.type, L))))
    fb = s.type_feedback.get(ev.type)
    if fb and sum(fb) / len(fb) >= 4:
        F.append(Factor(kind="history", impact=B_FEEDBACK, label=t(
            "pos_feedback", L, type=typ(ev.type, L), avg=round(sum(fb) / len(fb), 1))))
    mot = next((g.skill_id for g in ev.develops_skills if s.self_skill.get(g.skill_id)), None)
    if mot:
        F.append(Factor(kind="motivation", impact=B_MOTIVATION, label=t("motivation", L, skill=ctx.skill_name(mot))))
    if ev.event_id in s.in_progress:
        F.append(Factor(kind="history", impact=B_IN_PROGRESS, label=t("in_progress", L, pct=s.in_progress[ev.event_id])))
    if not any(f.kind in ("history", "motivation") for f in F):  # history is always part of the explanation
        F.append(Factor(kind="history", impact=0.0, label=t("clean", L, done=s.voluntary_done)))

    # logistics
    _, nxt = availability(ev, ctx.store.as_of)
    if ev.format == "self_paced":
        F.append(Factor(kind="schedule", impact=B_SELF_PACED, label=t("self_paced", L)))
    elif nxt:
        soon = (nxt - ctx.store.as_of).days <= 21
        F.append(Factor(kind="schedule", impact=B_SOON if soon else 0.0, label=t(
            "session", L, date=nxt.strftime("%d.%m"))))
    if ctx.emp.work_format == "remote" and ev.format == "offline":
        F.append(Factor(kind="work_format", impact=-P_REMOTE_OFFLINE, label=t("remote_offline", L)))
    if ev.duration_hours > 16:
        F.append(Factor(kind="effort", impact=-P_LONG, label=t("long", L, hours=int(ev.duration_hours))))
    if unlocked_by:
        F.append(Factor(kind="prerequisites", impact=0.0, label=t("unlocked", L, n=unlocked_by)))
    F = [f.model_copy(update={"impact": round(f.impact, 2)}) for f in F]
    return Scored(ev, round(sum(f.impact for f in F), 2), F, gains, closes, nxt)


def candidates(ctx: Ctx, skills: dict[str, int] | None = None, exclude=()):
    """Eligible events scored against `skills`, plus blocked events with the reason."""
    skills = ctx.effective if skills is None else skills
    ok: list[Scored] = []
    blocked: list[tuple[Event, str]] = []
    for ev in ctx.store.events.values():
        if ev.event_id in exclude:
            continue
        reason = eligibility(ctx, ev, skills)
        if reason:
            blocked.append((ev, reason))
            continue
        sc = score_event(ctx, ev, skills)
        if sc:
            ok.append(sc)
    ok.sort(key=lambda c: (not c.closes_gap, -c.score))
    return ok, blocked


@dataclass
class PlanStep:
    scored: Scored
    readiness_before: int
    readiness_after: int


def plan(ctx: Ctx, k: int = 3) -> list[PlanStep]:
    """Greedy plan: pick the best step, simulate its growth, re-score the rest (prerequisites may unlock)."""
    skills = dict(ctx.effective)
    initially_ok = {c.event.event_id for c in candidates(ctx)[0]}
    has_gaps = bool(gaps(ctx))
    steps: list[PlanStep] = []
    for i in range(k):
        cands, _ = candidates(ctx, skills, exclude=[st.scored.event.event_id for st in steps])
        pool = [c for c in cands if c.closes_gap and c.score > 0]
        if not pool and not has_gaps:  # target already met → stretch growth toward the next level
            pool = [c for c in cands if c.score > 0.3]
        if not pool:
            break
        best = max(pool, key=lambda c: c.score)
        if i and best.event.event_id not in initially_ok:
            best = score_event(ctx, best.event, skills, unlocked_by=i)
        before = readiness(skills, ctx.target_req, ctx.target_critical)
        skills = {**skills, **{sid: after for sid, _, after in best.gains}}
        steps.append(PlanStep(best, before, readiness(skills, ctx.target_req, ctx.target_critical)))
    return steps


def simulate(ctx: Ctx, event_ids: list[str]) -> list[PlanStep]:
    """Re-score a given order of events (used when the LLM re-orders the plan)."""
    skills = dict(ctx.effective)
    steps: list[PlanStep] = []
    for i, eid in enumerate(event_ids):
        ev = ctx.store.events.get(eid)
        if not ev or eligibility(ctx, ev, skills):
            continue
        sc = score_event(ctx, ev, skills, unlocked_by=i if eligibility(ctx, ev, ctx.effective) else None)
        if not sc:
            continue
        before = readiness(skills, ctx.target_req, ctx.target_critical)
        skills = {**skills, **{sid: after for sid, _, after in sc.gains}}
        steps.append(PlanStep(sc, before, readiness(skills, ctx.target_req, ctx.target_critical)))
    return steps


def gaps(ctx: Ctx) -> list[tuple[str, int, int]]:
    """(skill_id, effective, required) below the target requirement; critical first, then biggest gap."""
    out = [(sid, ctx.effective.get(sid, 0), need) for sid, need in ctx.target_req.items()
           if ctx.effective.get(sid, 0) < need]
    return sorted(out, key=lambda g: (g[0] not in ctx.target_critical, -(g[2] - g[1])))


def lowest_gap(ctx: Ctx) -> tuple[str, int, int] | None:
    """What a naive 'pick the lowest skill' rule would choose (ties → the skill with a failure history)."""
    gap_list = gaps(ctx)
    fails = {sid: sum(c.values()) for sid, c in ctx.signals.neg_skill_event.items()}
    return min(gap_list, key=lambda g: (g[1], -fails.get(g[0], 0), -(g[2] - g[1]))) if gap_list else None


def why_not(ctx: Ctx, steps: list[PlanStep], cands: list[Scored], blocked: list[tuple[Event, str]]) -> list[Rejected]:
    """Explain the obvious alternatives we did NOT pick — starting with the naive 'lowest skill' rule."""
    L, out = ctx.lang, []
    chosen = {st.scored.event.event_id for st in steps}
    improved = {sid for st in steps for sid, _, _ in st.scored.gains}
    top = ""
    if steps:
        first = steps[0].scored.gains
        top = ctx.skill_name(next((g[0] for g in first if g[0] in ctx.target_critical), first[0][0]))
    gap_list = gaps(ctx)
    # 1) a critical blocker that no available activity can close — the most important thing to explain
    for sid, eff, need in gap_list:
        if sid not in ctx.target_critical or sid in improved or any(any(g[0] == sid for g in c.gains) for c in cands):
            continue
        name = ctx.skill_name(sid)
        done = [e for e in ctx.signals.completed if any(g.skill_id == sid for g in ctx.store.events[e].develops_skills)]
        pre = [(ev, r) for ev, r in blocked if r.startswith("prereq:") and any(g.skill_id == sid for g in ev.develops_skills)]
        if pre:
            ev, r = pre[0]
            _, psid, preq = r.split(":")
            out.append(Rejected(event_id=ev.event_id, skill_id=sid, title=ev.title, reason=t(
                "why_prereq", L, skill=ctx.skill_name(psid), req=preq, eff=ctx.effective.get(psid, 0))))
        elif done:
            out.append(Rejected(skill_id=sid, title=name, reason=t(
                "why_critical_done", L, skill=name, grade=ctx.target_grade, eff=eff, req=need, events=", ".join(done))))
        else:
            out.append(Rejected(skill_id=sid, title=name, reason=t("why_no_events", L, skill=name)))
        break
    # 2) the naive "lowest skill first" rule
    low = lowest_gap(ctx)
    if low:
        sid, eff, _ = low
        name = ctx.skill_name(sid)
        if sid not in improved and not any(r.skill_id == sid for r in out):
            related = [c for c in cands if any(g[0] == sid for g in c.gains)]
            if related and top:
                best = max(related, key=lambda c: c.score)
                n_neg = sum(ctx.signals.neg_skill_event.get(sid, {}).values())
                reason = (t("why_lowest_history", L, skill=name, eff=eff, n=n_neg, top=top) if n_neg
                          else t("why_lowest_priority", L, skill=name, eff=eff, grade=ctx.target_grade, top=top))
                out.append(Rejected(event_id=best.event.event_id, skill_id=sid, title=best.event.title, reason=reason))
            elif not related:
                pre = [(ev, r) for ev, r in blocked if r.startswith("prereq:")
                       and any(g.skill_id == sid for g in ev.develops_skills)]
                if pre:
                    ev, r = pre[0]
                    _, psid, need = r.split(":")
                    out.append(Rejected(event_id=ev.event_id, skill_id=sid, title=ev.title, reason=t(
                        "why_prereq", L, skill=ctx.skill_name(psid), req=need, eff=ctx.effective.get(psid, 0))))
                else:
                    out.append(Rejected(skill_id=sid, title=name, reason=t("why_no_events", L, skill=name)))
    for c in sorted(cands, key=lambda c: -sum(f.impact for f in c.factors if f.impact > 0)):
        if len(out) >= 3:
            break
        negatives = [f for f in c.factors if f.impact < 0]
        if c.event.event_id in chosen or not c.closes_gap or sum(f.impact for f in negatives) > -0.8 or any(
                r.event_id == c.event.event_id for r in out):
            continue
        worst = min(negatives, key=lambda f: f.impact)
        out.append(Rejected(event_id=c.event.event_id, title=c.event.title, reason=t("why_penalty", L, detail=worst.label)))
    return out[:3]


# ---------------------------------------------------------------- profile & progress
def build_profile(store: DataStore, emp_id: str, lang: str | None = None) -> EmployeeProfile:
    ctx = build_context(store, emp_id, lang)
    emp = ctx.emp
    order = list(dict.fromkeys(
        sorted(ctx.target_req, key=lambda s: (s not in ctx.target_critical, s))
        + list(ctx.current_req) + list(emp.skills)))
    skills = []
    for sid in order:
        sk = store.skills.get(sid)
        eff = ctx.effective.get(sid, 0)
        need = ctx.target_req.get(sid, 0)
        skills.append(SkillState(
            skill_id=sid, name=sk.name if sk else sid, type=sk.type if sk else "hard",
            category=sk.category if sk else "", assessed=emp.skills.get(sid, 0), effective=eff,
            required_current=ctx.current_req.get(sid, 0), required_target=need, gap=max(0, need - eff),
            critical=sid in ctx.target_critical, pending_from=ctx.pending.get(sid, [])))
    target = Target(
        role=ctx.target_role, grade=ctx.target_grade, source=ctx.target_source, readiness_pct=ctx.readiness_now,
        blockers=[sid for sid, eff, need in gaps(ctx) if sid in ctx.target_critical],
        total_gap=sum(need - eff for _, eff, need in gaps(ctx)))
    history = []
    for h in reversed(ctx.history):
        ev = store.events.get(h.event_id)
        history.append(HistoryItem(
            record_id=h.record_id, event_id=h.event_id, title=ev.title if ev else h.event_id,
            type=ev.type if ev else "", format=ev.format if ev else "", mandatory=ev.mandatory if ev else False,
            date=h.date, status=h.status, completion_pct=h.completion_pct, score=h.score,
            feedback_rating=h.feedback_rating, assigned_by=h.assigned_by))
    cands, _ = candidates(ctx)
    next_steps = [NextStep(
        event_id=c.event.event_id, title=c.event.title, type=c.event.type, format=c.event.format,
        duration_hours=c.event.duration_hours, next_session=c.next_session, gains=deltas(ctx, c.gains),
        closes_gap=c.closes_gap, in_progress=c.event.event_id in ctx.signals.in_progress) for c in cands]
    manager = store.employees.get(emp.manager_id or "")
    stats = dict(ctx.signals.counts)
    stats["voluntary_completed"] = ctx.signals.voluntary_done
    return EmployeeProfile(
        employee=emp, manager_name=manager.full_name if manager else None, skills=skills, target=target,
        trajectory=trajectory(ctx), history=history, history_stats=stats, next_steps=next_steps)


def trajectory(ctx: Ctx) -> list[TrajectoryStep]:
    emp, store = ctx.emp, ctx.store
    cur = GRADES.index(emp.grade) if emp.grade in GRADES else 0

    def step(role: str, grade: str, status: str) -> TrajectoryStep | None:
        prof = store.role_profiles.get((role, grade))
        if not prof:
            return None
        return TrajectoryStep(role=role, grade=grade, status=status, readiness_pct=readiness(
            ctx.effective, prof.required_skills, set(prof.critical_skills)))

    out: list[TrajectoryStep | None] = []
    if ctx.target_role == emp.role:
        for i, g in enumerate(GRADES):
            status = ("passed" if i < cur else "current" if i == cur
                      else "target" if g == ctx.target_grade else "future")
            out.append(step(emp.role, g, status))
    else:  # career change: own ladder up to now, then the goal role
        out += [step(emp.role, g, "passed" if i < cur else "current") for i, g in enumerate(GRADES[:cur + 1])]
        t_idx = GRADES.index(ctx.target_grade) if ctx.target_grade in GRADES else 0
        out += [step(ctx.target_role, g, "target" if i == 0 else "future") for i, g in enumerate(GRADES[t_idx:])]
    return [s for s in out if s]


def deltas(ctx: Ctx, gains: list[tuple[str, int, int]]) -> list[SkillDelta]:
    return [SkillDelta(skill_id=sid, name=ctx.skill_name(sid), before=b, after=a) for sid, b, a in gains]


def complete(store: DataStore, emp_id: str, event_id: str, score: int | None = None,
             feedback: int | None = None) -> CompleteResponse:
    before = build_context(store, emp_id)
    ev = store.events[event_id]
    if event_id in before.signals.completed and event_id not in RECURRING:
        raise ValueError("already_completed")
    existing = next((h for h in before.history if h.event_id == event_id and h.status == "in_progress"), None)
    review = before.emp.last_review_date
    day = max(store.as_of, review + dt.timedelta(days=1)) if review else store.as_of
    record = HistoryRecord(
        record_id=existing.record_id if existing else store.next_record_id(), employee_id=emp_id,
        event_id=event_id, date=day, status="completed", completion_pct=100,
        score=score if ev.type in ("course", "certification", "compliance") else None,
        feedback_rating=feedback, assigned_by=existing.assigned_by if existing else "self")
    if review is None:  # without a review date gains cannot be attributed — treat this record as post-review
        store.employees[emp_id] = before.emp.model_copy(update={"last_review_date": day - dt.timedelta(days=1)})
    store.add_record(record)
    after = build_context(store, emp_id)
    changes = [SkillDelta(skill_id=sid, name=after.skill_name(sid), before=before.effective.get(sid, 0),
                          after=after.effective.get(sid, 0))
               for sid in after.effective if after.effective.get(sid, 0) != before.effective.get(sid, 0)]
    return CompleteResponse(
        record=record, changes=changes, readiness_before=before.readiness_now, readiness_after=after.readiness_now,
        profile=build_profile(store, emp_id))
