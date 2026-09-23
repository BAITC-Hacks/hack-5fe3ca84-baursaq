"""Read-only engine tools, bound to the server-selected employee for a single request."""

import json
import time

from app.models.api import TraceStep
from app.services import engine


def validated_plan(ctx: engine.Ctx, order: list[str], allowed: set[str]) -> list[engine.PlanStep]:
    if (not isinstance(order, list) or not 1 <= len(order) <= 3
            or any(not isinstance(eid, str) or eid not in allowed for eid in order)
            or len(set(order)) != len(order)):
        raise ValueError("invalid event selection")
    steps = engine.simulate(ctx, order)
    if [st.scored.event.event_id for st in steps] != order:
        raise ValueError("plan is not executable in this order")
    return steps


class EmployeeTools:
    def __init__(self, ctx: engine.Ctx, payload: str, allowed: set[str], trace: list[TraceStep]):
        self.ctx, self.payload, self.allowed, self.trace = ctx, json.loads(payload), allowed, trace
        self.definitions = []
        for name, description, properties in (
            ("list_candidates", "Get scored candidates for the current employee, including engine-plan steps.", {}),
            ("simulate_plan", "Simulate 1-3 distinct candidate IDs in order; prerequisites must hold at each step.",
             {"event_ids": {"type": "array", "items": {"type": "string", "enum": sorted(allowed)},
                            "minItems": 1, "maxItems": 3}}),
            ("get_history_signals", "Get participation, format preferences and motivation for the current employee.", {}),
        ):
            self.definitions.append({"type": "function", "name": name, "description": description, "strict": True,
                                     "parameters": {"type": "object", "properties": properties,
                                                    "required": list(properties), "additionalProperties": False}})

    def execute(self, name: str, arguments: str) -> str:
        started = time.perf_counter()
        detail = "invalid tool arguments"
        try:
            args = json.loads(arguments)
            expected = {"event_ids"} if name == "simulate_plan" else set()
            if not isinstance(args, dict) or set(args) != expected:
                raise ValueError("unexpected arguments; employee scope is fixed by the server")
            if name == "list_candidates":
                result = self.payload["candidates"]
                detail = f"{{}} → {len(result)} candidates: " + ", ".join(c["event_id"] for c in result)
            elif name == "get_history_signals":
                sig = engine.history_signals(self.ctx.history, self.ctx.store.events)
                result = {**self.payload["history"], "voluntary_completed": sig.voluntary_done,
                          "failures_by_event": dict(sig.neg_event), "format_attempts": dict(sig.fmt_total),
                          "format_failures": dict(sig.fmt_neg), "completed_by_type": dict(sig.type_done),
                          "self_initiated_by_skill": dict(sig.self_skill)}
                detail = f"{{}} → statuses={dict(sig.counts)}, voluntary_completed={sig.voluntary_done}"
            elif name == "simulate_plan":
                steps = validated_plan(self.ctx, args["event_ids"], self.allowed)
                result = [{"event_id": st.scored.event.event_id,
                           "gains": [g.model_dump() for g in engine.deltas(self.ctx, st.scored.gains)],
                           "readiness_before": st.readiness_before, "readiness_after": st.readiness_after,
                           "factors": [f.model_dump() for f in st.scored.factors]} for st in steps]
                detail = f"{json.dumps(args)} → readiness {steps[0].readiness_before}%→{steps[-1].readiness_after}%"
            else:
                raise ValueError("unknown tool")
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            detail = f"rejected ({type(exc).__name__}); {detail}"
            raise
        finally:
            # Only actual calls dispatched from a model response enter this trace.
            self.trace.append(TraceStep(step=f"llm→{name}", detail=detail,
                                        ms=int((time.perf_counter() - started) * 1000)))
