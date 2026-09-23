"""Single entry point for LLM calls: shared deadline, provider fallback and one log line per call
(provider, model, tokens in/out, estimated cost, latency) — see AGENTS.md §7."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger("llm")
T = TypeVar("T", bound=BaseModel)

# USD per 1M tokens (input, output) — rough, only for the cost estimate in logs
PRICES = {  # unknown models are logged with cost 0 — check real spend in the OpenAI dashboard
    "gpt-5-mini": (0.25, 2.0),
    "gpt-5": (1.25, 10.0),
    "gpt-5-nano": (0.05, 0.4),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4o-mini": (0.15, 0.6),
}


@dataclass
class CallMeta:
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


_clients: dict[tuple[str, int], AsyncOpenAI] = {}


def _client(name: str, key: str, base_url: str | None) -> AsyncOpenAI:
    # one client per event loop: a client bound to a closed loop fails ("Event loop is closed") in scripts/tests
    k = (name, id(asyncio.get_running_loop()))
    if k not in _clients:
        _clients[k] = AsyncOpenAI(api_key=key, base_url=base_url, max_retries=0)
    return _clients[k]


def _providers():
    if settings.openai_api_key:
        yield "openai", settings.openai_api_key, settings.openai_base_url, settings.openai_model, True
    if settings.fallback_api_key:
        yield "fallback", settings.fallback_api_key, settings.fallback_base_url, settings.fallback_model, False


async def structured(system: str, user: str, schema: type[T], timeout: float) -> tuple[T, CallMeta]:
    """Ask for a JSON object matching `schema`. Tries OpenAI, then the fallback provider, within one deadline."""
    deadline = time.monotonic() + timeout
    errors = []
    for name, key, base_url, model, native in _providers():
        remaining = deadline - time.monotonic()
        if remaining < 1:
            break
        t0 = time.perf_counter()
        try:
            parsed, usage = await asyncio.wait_for(
                _call(_client(name, key, base_url), model, native, system, user, schema), remaining)
        except Exception as e:  # noqa: BLE001 — any provider failure means "try the next one"
            log.warning("llm FAIL provider=%s model=%s err=%r after %dms", name, model, e,
                        (time.perf_counter() - t0) * 1000)
            errors.append(f"{name}: {type(e).__name__}")
            continue
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        pin, pout = PRICES.get(model, (0.0, 0.0))
        meta = CallMeta(name, model, tin, tout, round((tin * pin + tout * pout) / 1e6, 6),
                        int((time.perf_counter() - t0) * 1000))
        log.info("llm OK provider=%s model=%s in=%d out=%d cost=$%.5f latency=%dms",
                 name, model, tin, tout, meta.cost_usd, meta.latency_ms)
        return parsed, meta
    raise RuntimeError("; ".join(errors) or "no LLM provider configured")


async def _call(client: AsyncOpenAI, model: str, native: bool, system: str, user: str, schema: type[T]):
    if native:  # OpenAI structured outputs
        extra = {"reasoning_effort": settings.openai_reasoning_effort} if settings.openai_reasoning_effort else {}
        resp = await client.chat.completions.parse(
            model=model, response_format=schema,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **extra)
        parsed = resp.choices[0].message.parsed
        if parsed is None:
            raise ValueError("empty or refused structured output")
        return parsed, resp.usage
    # OpenAI-compatible providers (NVIDIA NIM): JSON mode + validation
    resp = await client.chat.completions.create(
        model=model, temperature=0.2, response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"{system}\nReturn ONLY a JSON object with this JSON schema:\n"
                                          f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"},
            {"role": "user", "content": user},
        ])
    return schema.model_validate_json(resp.choices[0].message.content or "{}"), resp.usage
