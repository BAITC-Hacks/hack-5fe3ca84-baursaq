"""Exercise the real agent and Responses orchestration with a mocked OpenAI client; no network."""

import asyncio
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from app import llm
from app.agents import recommender
from app.config import settings
from app.services import engine
from app.services.store import DataStore


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setattr(settings, "agent_mode", "tools")
    monkeypatch.setattr(settings, "use_mocks", False)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    recommender._cache.clear()
    store = DataStore(settings.data_dir)
    ctx = engine.build_context(store, "E0072", "ru")
    order = [st.scored.event.event_id for st in engine.plan(ctx)]
    calls = [NS(type="function_call", name=name, call_id=str(i), arguments=json.dumps(args))
             for i, (name, args) in enumerate([
                 ("list_candidates", {}), ("get_history_signals", {}), ("simulate_plan", {"event_ids": order})])]
    answer = recommender.LLMAnswer(
        summary="План развития", why_not_lowest_skill="Учтены цель, история и формат.",
        picks=[recommender.LLMPick(event_id=eid, rationale="Цель Senior, рост 2→3, учтена история участия.")
               for eid in order])
    usage = NS(input_tokens=100, output_tokens=50)
    first = NS(output=calls, usage=usage, status="completed")
    final = NS(output=[], output_parsed=answer, usage=usage, status="completed")
    responses = NS(create=AsyncMock(return_value=first), parse=AsyncMock(return_value=final))
    monkeypatch.setattr(llm, "_client", lambda *args: NS(responses=responses))
    yield NS(store=store, ctx=ctx, order=order, responses=responses, first=first, final=final)
    recommender._cache.clear()


def run(agent):
    return asyncio.run(recommender.recommend(agent.store, "E0072", "ru"))


def assert_fallback(result):
    assert result.source == "fallback"
    assert result.recommendations
    assert all(len(rec.factors) >= 3 for rec in result.recommendations)


def test_tools_recommendation_and_protocol(agent):
    result = run(agent)
    assert result.source == "llm"
    assert len(result.recommendations) >= 1
    assert all(len(rec.factors) >= 3 for rec in result.recommendations)
    expected = engine.simulate(agent.ctx, agent.order)
    for rec, st in zip(result.recommendations, expected, strict=True):
        assert rec.gains == engine.deltas(agent.ctx, st.scored.gains)
        assert rec.readiness_after_pct == st.readiness_after
    assert [s.step for s in result.trace if s.step.startswith("llm→")] == [
        "llm→list_candidates", "llm→get_history_signals", "llm→simulate_plan"]
    first = agent.responses.create.call_args.kwargs
    final = agent.responses.parse.call_args.kwargs
    assert first["parallel_tool_calls"] and first["tool_choice"] == "required"
    assert final["tool_choice"] == "none" and final["text_format"] is recommender.LLMAnswer
    outputs = [item for item in final["input"] if isinstance(item, dict) and item.get("type") == "function_call_output"]
    assert len(outputs) == 3 and [o["call_id"] for o in outputs] == ["0", "1", "2"]
    assert all(call in final["input"] for call in agent.first.output)
    agent.responses.create.assert_awaited_once()
    agent.responses.parse.assert_awaited_once()


@pytest.mark.parametrize("bad_id", ["EV_999", "EV_001"])
def test_invalid_pick_rejects_entire_answer(agent, bad_id):
    agent.final.output_parsed.picks[-1].event_id = bad_id
    assert_fallback(run(agent))


@pytest.mark.parametrize("round_number", [1, 2])
def test_shared_timeout(agent, monkeypatch, round_number):
    monkeypatch.setattr(settings, "llm_timeout_s", 0.08)

    async def slow_first(**kwargs):
        await asyncio.sleep(0.05 if round_number == 2 else 1)
        return agent.first

    async def slow_final(**kwargs):
        await asyncio.sleep(0.05)
        return agent.final

    agent.responses.create.side_effect = slow_first
    agent.responses.parse.side_effect = slow_final
    result = run(agent)
    assert_fallback(result)
    assert result.latency_ms < 500
    assert agent.responses.parse.await_count == (round_number == 2)


@pytest.mark.parametrize("name,args", [
    ("get_history_signals", {"employee_id": "E0052"}),
    ("simulate_plan", {"event_ids": ["EV_999"]}),
    ("simulate_plan", {"event_ids": "EV_006"}),
    ("unknown", {}),
])
def test_invalid_tool_call_falls_back(agent, name, args):
    agent.first.output = [NS(type="function_call", name=name, call_id="bad", arguments=json.dumps(args))]
    result = run(agent)
    assert_fallback(result)
    assert len([s for s in result.trace if s.step.startswith("llm→")]) == 1
    agent.responses.parse.assert_not_awaited()


def test_no_tool_calls_does_not_fake_trace(agent):
    agent.first.output = []
    result = run(agent)
    assert_fallback(result)
    assert not any(s.step.startswith("llm→") for s in result.trace)
    agent.responses.parse.assert_not_awaited()


def test_refusal_and_third_round_fall_back(agent):
    answer = agent.final.output_parsed
    agent.final.output_parsed = None
    assert_fallback(run(agent))
    agent.final.output_parsed = answer
    agent.final.output = agent.first.output
    assert_fallback(run(agent))


def test_duplicate_pick_falls_back(agent):
    agent.final.output_parsed.picks[-1].event_id = agent.order[0]
    assert_fallback(run(agent))


def test_partial_simulation_falls_back(agent, monkeypatch):
    simulate = engine.simulate
    monkeypatch.setattr(engine, "simulate", lambda ctx, ids: simulate(ctx, ids)[:-1])
    assert_fallback(run(agent))


def test_provider_error_falls_back_without_retry(agent):
    agent.responses.create.side_effect = RuntimeError("provider unavailable")
    assert_fallback(run(agent))
    agent.responses.create.assert_awaited_once()
    agent.responses.parse.assert_not_awaited()


def test_mocks_bypass_cached_llm(agent, monkeypatch):
    assert run(agent).source == "llm"
    monkeypatch.setattr(settings, "use_mocks", True)
    assert_fallback(run(agent))
    agent.responses.create.assert_awaited_once()


def test_single_mode_preserved(agent, monkeypatch):
    monkeypatch.setattr(settings, "agent_mode", "single")
    mock = AsyncMock(return_value=(agent.final.output_parsed, llm.CallMeta("openai", "test", 1, 1, 0, 1)))
    monkeypatch.setattr(llm, "structured", mock)
    assert run(agent).source == "llm"
    agent.responses.create.assert_not_awaited()
    mock.assert_awaited_once()
