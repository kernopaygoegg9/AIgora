"""`fake` adapter: a real adapter for tests and quota-free development.

Everything is scripted through the participant's `options` table, e.g.

    [[participant]]
    id = "fake-a"
    display_name = "Fake A"
    adapter = "fake"
    [participant.options]
    replies = ["Round 1 answer", "Round 2 answer\\nSTANCE: AGREE"]
    fail_rounds = [3]
    fail_kind = "timeout"

Options (all optional):

| option | default | meaning |
|---|---|---|
| `replies` | generated | text of normal turns, one per round; the last one repeats |
| `drafts` | generated | consensus draft text (purpose `draft`), one per round; last repeats |
| `confirmations` | generated | answer to a judge-B confirmation question, one per round; last repeats |
| `final` | generated | final consensus result (purpose `final_result`) |
| `summary` | generated | final positions + disagreements (purpose `no_consensus_summary`) |
| `echo_prompt` | false | reply with the received prompt instead (for prompt tests) |
| `stream` | true | send `Delta`s before `Completed`; also the `streaming` capability |
| `chunk_chars` | 8 | characters per `Delta` |
| `chunk_delay_seconds` | 0.02 | pause between `Delta`s |
| `delay_seconds` | 0 | pause before any output (use for timeout / parallelism tests) |
| `fail_rounds` | [] | rounds in which the call fails |
| `fail_purposes` | ["turn"] | which purposes `fail_rounds` applies to |
| `fail_kind` | "crashed" | failure kind: not_available, auth, quota, timeout, crashed, unknown |
| `fail_reason` | generated | failure reason text |
| `available` | true | availability check result; when false every call fails as not_available |
| `unavailable_reason` | "fake: configured unavailable" | reason shown when unavailable |
| `web_access` | true | the `web_access` capability |
| `cancel_log` | none | file path; a cancelled call (stop / timeout) appends the participant id as one line |

Generated texts name the participant; generated normal turns end with
`STANCE: AGREE` from round 2 on and generated confirmations agree, so a
default fake discussion reaches consensus in round 2.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from typing import Any

from aigora.adapters.base import (
    FAILURE_KINDS,
    TURN_PURPOSES,
    Adapter,
    AdapterEvent,
    Availability,
    Capabilities,
    Completed,
    Delta,
    Failed,
    TurnRequest,
)
from aigora.config import ParticipantConfig

_DEFAULTS: dict[str, Any] = {
    "replies": None,
    "drafts": None,
    "confirmations": None,
    "final": None,
    "summary": None,
    "echo_prompt": False,
    "stream": True,
    "chunk_chars": 8,
    "chunk_delay_seconds": 0.02,
    "delay_seconds": 0.0,
    "fail_rounds": [],
    "fail_purposes": ["turn"],
    "fail_kind": "crashed",
    "fail_reason": None,
    "available": True,
    "unavailable_reason": "fake: configured unavailable",
    "web_access": True,
    "cancel_log": None,
}


def _check(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class FakeAdapter(Adapter):
    id = "fake"

    def validate_options(self, options: Mapping[str, Any]) -> None:
        unknown = sorted(set(options) - set(_DEFAULTS))
        _check(not unknown, f"unknown fake option(s): {', '.join(unknown)}")
        o = options
        for key in ("replies", "drafts", "confirmations"):
            if key in o:
                _check(_is_str_list(o[key]) and len(o[key]) > 0, f"`{key}` must be a non-empty list of strings")
        for key in ("final", "summary", "fail_reason", "unavailable_reason", "cancel_log"):
            if key in o:
                _check(isinstance(o[key], str), f"`{key}` must be a string")
        for key in ("echo_prompt", "stream", "available", "web_access"):
            if key in o:
                _check(isinstance(o[key], bool), f"`{key}` must be true or false")
        if "chunk_chars" in o:
            _check(isinstance(o["chunk_chars"], int) and not isinstance(o["chunk_chars"], bool)
                   and o["chunk_chars"] > 0, "`chunk_chars` must be a positive integer")
        for key in ("chunk_delay_seconds", "delay_seconds"):
            if key in o:
                _check(_is_number(o[key]) and o[key] >= 0, f"`{key}` must be a number >= 0")
        if "fail_rounds" in o:
            rounds = o["fail_rounds"]
            _check(isinstance(rounds, list) and all(isinstance(r, int) and not isinstance(r, bool) and r >= 1
                                                    for r in rounds), "`fail_rounds` must be a list of round numbers >= 1")
        if "fail_purposes" in o:
            _check(_is_str_list(o["fail_purposes"]) and set(o["fail_purposes"]) <= set(TURN_PURPOSES),
                   f"`fail_purposes` must be a list of: {', '.join(TURN_PURPOSES)}")
        if "fail_kind" in o:
            _check(o["fail_kind"] in FAILURE_KINDS, f"`fail_kind` must be one of: {', '.join(FAILURE_KINDS)}")

    def _options(self, participant: ParticipantConfig) -> dict[str, Any]:
        self.validate_options(participant.options)
        return {**_DEFAULTS, **participant.options}

    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        o = self._options(participant)
        return Capabilities(web_access=o["web_access"], streaming=o["stream"])

    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        o = self._options(participant)
        if o["available"]:
            return Availability(True)
        return Availability(False, o["unavailable_reason"])

    async def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        o = self._options(request.participant)
        ended = False
        try:
            async for event in self._run_turn(request, o):
                ended = isinstance(event, (Completed, Failed))
                yield event
        except (asyncio.CancelledError, GeneratorExit):
            # Cancelled (or closed) before the final event: lets tests observe a stop / timeout.
            if o["cancel_log"] and not ended:
                with open(o["cancel_log"], "a", encoding="utf-8") as log:
                    log.write(f"{request.participant.id}\n")
            raise

    async def _run_turn(self, request: TurnRequest, o: dict[str, Any]) -> AsyncIterator[AdapterEvent]:
        if not o["available"]:
            yield Failed("not_available", o["unavailable_reason"])
            return

        if o["delay_seconds"]:
            await asyncio.sleep(o["delay_seconds"])

        text = request.prompt if o["echo_prompt"] else self._scripted_text(request, o)
        fails = request.round in o["fail_rounds"] and request.purpose in o["fail_purposes"]

        if o["stream"]:
            # A failing streamed call fails half-way, like a CLI crashing mid-reply.
            streamed = text[: len(text) // 2] if fails else text
            size = o["chunk_chars"]
            for start in range(0, len(streamed), size):
                yield Delta(streamed[start : start + size])
                if o["chunk_delay_seconds"]:
                    await asyncio.sleep(o["chunk_delay_seconds"])

        if fails:
            reason = o["fail_reason"] or (
                f"fake: configured {o['fail_kind']} failure in round {request.round}"
            )
            yield Failed(o["fail_kind"], reason)
            return
        yield Completed(text)

    @staticmethod
    def _scripted_text(request: TurnRequest, o: dict[str, Any]) -> str:
        name = request.participant.display_name
        n = request.round

        def per_round(key: str) -> str | None:
            items = o[key]
            if not items:
                return None
            return items[min(n, len(items)) - 1]

        match request.purpose:
            case "turn":
                text = per_round("replies")
                if text is None:
                    text = f"{name}: reply for round {n}."
                    if n >= 2:
                        text += "\nSTANCE: AGREE"
                return text
            case "draft":
                return per_round("drafts") or f"{name}: consensus draft after round {n}."
            case "confirmation":
                return per_round("confirmations") or f"{name}: I agree consensus is reached.\nSTANCE: AGREE"
            case "final_result":
                return o["final"] or f"{name}: final consensus result."
            case "no_consensus_summary":
                return o["summary"] or f"{name}: final positions and remaining disagreements."
        raise ValueError(f"unknown purpose: {request.purpose}")


def create_adapter() -> Adapter:
    return FakeAdapter()
