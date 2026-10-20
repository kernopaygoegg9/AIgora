"""Discussion Engine (討論引擎): runs one discussion and emits its events.

The engine owns execution: rounds, parallel turns, timeouts, events, saving.
It owns no rules: what each round asks for and what happens after it come
from the `DiscussionMode`; how a round is split into batches comes from the
`SpeakingOrder` (see `interfaces.py` for the flow). Extra calls (moderator
draft / summary) and judge reports are run and emitted here (ticket 04);
tickets 06 -> 07 -> 08 extend it (interjections / stop, failure counting and
removal, judge B confirmations).

The discussion record (`aigora.record.DiscussionRecord`) is the engine's
single source of state; the read-only `DiscussionView` handed to modes and
judges is built from it.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import tempfile
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from aigora.adapters.base import Completed, Delta, Failed, TurnRequest, get_adapter
from aigora.api import messages as m
from aigora.config import ParticipantConfig
from aigora.discussion.interfaces import (
    ContinueRound,
    DiscussionMode,
    DiscussionView,
    ExtraCall,
    ExtraCallResult,
    ExtraCalls,
    Finish,
    RoundView,
    SpeakingOrder,
    TurnView,
)
from aigora.discussion.prompt_builder import build_prompt
from aigora.discussion.store import DiscussionStore
from aigora.domain import TurnPurpose
from aigora.participant_info import snapshot_of
from aigora.record import DiscussionRecord, RecordJudge, RecordRound, RecordTurn
from aigora.stance import parse_stance

log = logging.getLogger("aigora.engine")

# Receives each server message as a JSON-ready dict, in `seq` order.
Send = Callable[[dict[str, Any]], Awaitable[None]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_discussion_id() -> str:
    """Sortable by start time, readable as a filename: `20261020-153012-a1b2c3`."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


class DiscussionEngine:
    def __init__(
        self,
        *,
        question: str,
        settings: m.DiscussionSettings,
        participants: Sequence[ParticipantConfig],  # the discussion's participants, in settings order
        mode: DiscussionMode,
        order: SpeakingOrder,
        store: DiscussionStore,
        send: Send,
        discussion_id: str | None = None,
    ):
        self.mode = mode
        self.order = order
        self.store = store
        self._send = send
        self._participants = {p.id: p for p in participants}
        self._seq = 0
        self._send_lock = asyncio.Lock()
        self.record = DiscussionRecord(
            id=discussion_id or new_discussion_id(),
            question=question,
            created_at=now_iso(),
            settings=settings,
            participants=[snapshot_of(p) for p in participants],
        )

    @property
    def discussion_id(self) -> str:
        return self.record.id

    @property
    def settings(self) -> m.DiscussionSettings:
        return self.record.settings

    # --- running -------------------------------------------------------------

    async def run(self) -> DiscussionRecord:
        """Run to the end. An unexpected error ends the discussion with outcome `error`."""
        try:
            return await self._run()
        except Exception as exc:  # noqa: BLE001 - reported to the user, saved in the record
            log.exception("discussion %s crashed", self.discussion_id)
            await self._finish(Finish(outcome="error", result=None, reason=f"討論發生錯誤：{exc!r}"))
            return self.record

    async def report_error(self, message: str) -> None:
        """An `error` message for this discussion (e.g. an invalid client message)."""
        await self._emit(m.ErrorMessage, message=message)

    async def _run(self) -> DiscussionRecord:
        await self._emit(
            m.DiscussionStarted,
            question=self.record.question,
            derived_from=self.record.derived_from,
            settings=self.settings,
            participants=self.record.participants,
        )
        round_number = 0
        while True:
            round_number += 1
            await self._run_round(round_number)
            decision = await self.mode.after_round(self.view(), None)
            while isinstance(decision, ExtraCalls):
                await self._apply_reports(round_number, decision)
                results = await self._run_extra_calls(round_number, decision.calls)
                decision = await self.mode.after_round(self.view(), results)
            await self._apply_reports(round_number, decision)
            await self._complete_round(round_number)
            if isinstance(decision, Finish):
                await self._finish(decision)
                return self.record
            assert isinstance(decision, ContinueRound)

    async def _run_round(self, number: int) -> None:
        round_ = RecordRound(number=number, turns=[])
        self.record.rounds.append(round_)
        await self._emit(m.RoundStarted, round=number)
        for batch in self.order.schedule(self.active_participant_ids(), number):
            # Everyone in a batch sees the same view: earlier batches and rounds only.
            view = self.view()
            calls = [
                self._run_call(pid, number, "turn", self.mode.round_instructions(view, pid), view)
                for pid in batch
            ]
            round_.turns.extend(await asyncio.gather(*calls))

    async def _run_extra_calls(self, number: int, calls: Sequence[ExtraCall]) -> list[ExtraCallResult]:
        """Run the mode's extra calls in parallel; a finished `draft` call becomes the round's draft."""
        view = self.view()
        turns = await asyncio.gather(
            *(self._run_call(c.participant_id, number, c.purpose, c.instructions, view) for c in calls)
        )
        round_ = self.record.rounds[-1]
        results: list[ExtraCallResult] = []
        for call, turn in zip(calls, turns):
            if call.purpose == "draft" and turn.status == "ok" and turn.text:
                round_.draft = turn.text
                await self._emit(m.DraftCreated, round=number, text=turn.text)
            results.append(
                ExtraCallResult(call=call, status=turn.status, text=turn.text, stance=turn.stance, error=turn.error)
            )
        return results

    async def _apply_reports(self, number: int, decision: ContinueRound | ExtraCalls | Finish) -> None:
        """Store and emit the judge / confirmation reports a decision carries."""
        round_ = self.record.rounds[-1]
        if decision.judge_report is not None:
            r = decision.judge_report
            round_.judge = RecordJudge(judge=r.judge, outcome=r.outcome, detail=r.detail)
            await self._emit(m.JudgeResult, round=number, judge=r.judge, outcome=r.outcome, detail=r.detail)
        if decision.confirmation_report is not None:
            answers = list(decision.confirmation_report.answers)
            round_.confirmations = answers
            await self._emit(m.ConfirmationResult, round=number, answers=answers)

    async def _complete_round(self, number: int) -> None:
        self.store.save(self.record)
        await self._emit(m.RoundCompleted, round=number)

    async def _finish(self, decision: Finish) -> None:
        self.record.outcome = decision.outcome
        self.record.result = decision.result
        self.record.finished_at = now_iso()
        self.store.save(self.record)
        await self._emit(
            m.DiscussionFinished, outcome=decision.outcome, result=decision.result, reason=decision.reason
        )

    async def _run_call(
        self,
        participant_id: str,
        round_number: int,
        purpose: TurnPurpose,
        instructions: str | None,
        view: DiscussionView,
    ) -> RecordTurn:
        """One call to a participant (a turn or an extra call), streamed as `turn_*` events."""
        participant = self._participants[participant_id]
        ids = {"round": round_number, "participant_id": participant_id, "purpose": purpose}
        started_at = now_iso()
        await self._emit(m.TurnStarted, **ids)

        prompt = build_prompt(view, participant_id, instructions)
        text, failure = await self._call_adapter(participant, prompt, round_number, purpose, ids)

        if failure is not None:
            kind, reason = failure
            await self._emit(m.TurnFailed, **ids, reason=reason, kind=kind)
            return RecordTurn(
                participant_id=participant_id,
                status="timeout" if kind == "timeout" else "failed",
                text=text or None,
                stance=None,
                started_at=started_at,
                ended_at=now_iso(),
                error=reason,
            )
        stance = parse_stance(text)
        await self._emit(m.TurnCompleted, **ids, text=text, stance=stance)
        return RecordTurn(
            participant_id=participant_id,
            status="ok",
            text=text,
            stance=stance,
            started_at=started_at,
            ended_at=now_iso(),
            error=None,
        )

    async def _call_adapter(
        self,
        participant: ParticipantConfig,
        prompt: str,
        round_number: int,
        purpose: TurnPurpose,
        ids: dict[str, Any],
    ) -> tuple[str, tuple[str, str] | None]:
        """Stream the adapter's events; returns (text so far, (kind, reason) on failure)."""
        timeout = self.settings.turn_timeout_seconds
        streamed: list[str] = []
        with tempfile.TemporaryDirectory(prefix="aigora-turn-", ignore_cleanup_errors=True) as workspace:
            request = TurnRequest(
                participant=participant,
                prompt=prompt,
                workspace=Path(workspace),
                timeout_seconds=timeout,
                round=round_number,
                purpose=purpose,
            )
            events = get_adapter(participant.adapter).run_turn(request)
            try:
                async with asyncio.timeout(timeout):
                    async for event in events:
                        if isinstance(event, Delta):
                            streamed.append(event.text)
                            await self._emit(m.TurnDelta, **ids, text=event.text)
                        elif isinstance(event, Completed):
                            return event.text, None
                        elif isinstance(event, Failed):
                            return "".join(streamed), (event.kind, event.reason)
                return "".join(streamed), ("crashed", f"{participant.adapter}: ended without a reply")
            except TimeoutError:
                return "".join(streamed), ("timeout", f"沒有在 {timeout:g} 秒內完成發言")
            except Exception as exc:  # noqa: BLE001 - an adapter bug must not kill the discussion
                return "".join(streamed), ("unknown", f"{participant.adapter}: {exc!r}")
            finally:
                await events.aclose()  # type: ignore[attr-defined]

    # --- state ---------------------------------------------------------------

    def active_participant_ids(self) -> list[str]:
        removed = {r.participant_id for r in self.record.removed_participants}
        return [pid for pid in self.settings.participant_ids if pid not in removed]

    def moderator_id(self) -> str | None:
        changes = self.record.moderator_changes
        return changes[-1].participant_id if changes else self.settings.moderator_id

    def view(self) -> DiscussionView:
        interjections: dict[int, list[str]] = {}
        for i in self.record.interjections:
            interjections.setdefault(i.applies_to_round, []).append(i.text)
        return DiscussionView(
            question=self.record.question,
            settings=self.settings,
            participant_names={p.id: p.display_name for p in self.record.participants},
            active_participant_ids=self.active_participant_ids(),
            moderator_id=self.moderator_id(),
            rounds=[
                RoundView(
                    number=r.number,
                    turns=[
                        TurnView(participant_id=t.participant_id, status=t.status, text=t.text,
                                 stance=t.stance, error=t.error)
                        for t in r.turns
                    ],
                    draft=r.draft,
                    interjections=interjections.get(r.number, ()),
                )
                for r in self.record.rounds
            ],
        )

    # --- events --------------------------------------------------------------

    async def _emit(self, model: type[BaseModel], **fields: Any) -> None:
        """Send one server message; parallel turns share the connection, so sends are serialised."""
        async with self._send_lock:
            self._seq += 1
            message = model(discussion_id=self.discussion_id, seq=self._seq, **fields)
            await self._send(m.to_wire(message))
