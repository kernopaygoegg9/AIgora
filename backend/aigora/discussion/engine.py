"""Discussion Engine (討論引擎): runs one discussion and emits its events.

The engine owns execution: rounds, parallel turns, timeouts, events, saving.
It owns no rules: what each round asks for and what happens after it come
from the `DiscussionMode`; how a round is split into batches comes from the
`SpeakingOrder` (see `interfaces.py` for the flow). Extra calls (moderator
draft / summary) and judge reports are run and emitted here (ticket 04);
interjections and stop are ticket 06; failure handling is ticket 07: a
participant whose turns fail in 2 rounds in a row is removed, fewer than 2
active participants ends the discussion as `insufficient_participants`, and a
moderator whose turn or moderator call fails, or who is removed, hands over to
the next active participant in the list. Judge B's confirmations (ticket 08) are extra
calls like any other; their answers are reported by the mode
(`confirmation_result`) and the disagreeing reasons reach the next round
through `DiscussionView.pending_disagreements`.

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
from dataclasses import dataclass
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
from aigora.domain import FailureKind, TurnPurpose, TurnStatus
from aigora.participant_info import snapshot_of
from aigora.record import (
    DiscussionRecord,
    RecordInterjection,
    RecordJudge,
    RecordModeratorChange,
    RecordRemoval,
    RecordRound,
    RecordTurn,
)
from aigora.stance import parse_stance

log = logging.getLogger("aigora.engine")

# Receives each server message as a JSON-ready dict, in `seq` order.
Send = Callable[[dict[str, Any]], Awaitable[None]]


STOPPED_REASON = "使用者停止了討論，這次發言已取消"

# A participant whose turns fail in this many rounds in a row is removed (移出).
FAILED_ROUNDS_TO_REMOVE = 2
# With fewer participants left the discussion ends as `insufficient_participants`.
MIN_PARTICIPANTS = 2
# Extra calls that are the moderator's job: when the moderator fails one, the next
# active participant takes over (the mode decides whether to retry the call).
MODERATOR_PURPOSES: frozenset[str] = frozenset({"draft", "final_result", "no_consensus_summary"})


def _status_of(kind: str) -> TurnStatus:
    """A failed call's record status from its `turn_failed` kind."""
    return "timeout" if kind == "timeout" else "failed"


def _kind_of(status: TurnStatus) -> FailureKind:
    """The `turn_failed` kind for a recorded non-ok turn (the inverse of `_status_of`)."""
    return "timeout" if status == "timeout" else "unknown"


def _turn_of(round_: RecordRound, participant_id: str) -> RecordTurn | None:
    return next((t for t in round_.turns if t.participant_id == participant_id), None)


@dataclass
class _CancelledCall:
    """A call that was running when the user stopped the discussion."""

    ids: dict[str, Any]  # round / participant_id / purpose
    started_at: str
    streamed: list[str]


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
        derived_from: str | None = None,
        first_round: RecordRound | None = None,
    ):
        """`first_round`: a prefilled round 1 (提問轉共識討論: the source ask's round 1). Its
        turns of the discussion's participants are replayed as events; nobody is called.
        `derived_from`: the id of the discussion this one continues."""
        self.mode = mode
        self.order = order
        self.store = store
        self._send = send
        self._participants = {p.id: p for p in participants}
        self._seq = 0
        self._send_lock = asyncio.Lock()
        self._finishing = False
        self._main: asyncio.Task[DiscussionRecord] | None = None
        self._stop_requested = False
        self._cancelled_calls: list[_CancelledCall] = []
        self._schedule_order: dict[int, list[str]] = {}  # round -> participant ids in scheduled order
        self._first_round = first_round
        self.record = DiscussionRecord(
            id=discussion_id or new_discussion_id(),
            question=question,
            created_at=now_iso(),
            settings=settings,
            participants=[snapshot_of(p) for p in participants],
            derived_from=derived_from,
        )

    @property
    def discussion_id(self) -> str:
        return self.record.id

    @property
    def settings(self) -> m.DiscussionSettings:
        return self.record.settings

    # --- running -------------------------------------------------------------

    async def run(self) -> DiscussionRecord:
        """Run to the end. An unexpected error ends the discussion with outcome `error`.

        The rounds run in their own task so that `stop()` can cancel everything
        in flight (turns, extra calls, judges); cancelling `run()` itself (the
        browser went away) cancels it too, without a `discussion_finished`.
        """
        self._main = asyncio.create_task(self._run())
        try:
            return await self._main
        except asyncio.CancelledError:
            task = asyncio.current_task()
            if not self._stop_requested or (task is not None and task.cancelling()):
                raise
            await self._finish_stopped()
            return self.record
        except Exception as exc:  # noqa: BLE001 - reported to the user, saved in the record
            log.exception("discussion %s crashed", self.discussion_id)
            await self._finish(Finish(outcome="error", result=None, reason=f"討論發生錯誤：{exc!r}"))
            return self.record

    async def stop(self) -> None:
        """The user's stop (停止): cancel every running call, save, and finish as `stopped`."""
        if self._stop_requested or self._finishing or self._main is None or self._main.done():
            return
        self._stop_requested = True
        self._main.cancel()

    async def _finish_stopped(self) -> None:
        """After the stop's cancellation: report the cancelled calls, keep the cancelled turns."""
        for call in self._cancelled_calls:
            await self._emit(m.TurnFailed, **call.ids, reason=STOPPED_REASON, kind="unknown")
            if call.ids["purpose"] != "turn":
                continue  # an unfinished extra call leaves nothing in the record
            round_ = next(r for r in self.record.rounds if r.number == call.ids["round"])
            round_.turns.append(
                RecordTurn(
                    participant_id=call.ids["participant_id"],
                    status="failed",
                    text="".join(call.streamed) or None,
                    stance=None,
                    started_at=call.started_at,
                    ended_at=now_iso(),
                    error=STOPPED_REASON,
                )
            )
        if self.record.rounds:
            self._sort_turns(self.record.rounds[-1])
        await self._finish(Finish(outcome="stopped", result=None, reason="使用者停止了討論"))

    async def interject(self, text: str) -> None:
        """Queue the user's interjection (插話) for the next round; the running round is not touched.

        Rounds take their prompts' view when they start, so an interjection made
        while round N runs (or before round N+1 has started) applies to round N+1.
        """
        text = text.strip()
        if not text:
            await self.report_error("插話內容不能是空白")
            return
        if self._stop_requested:
            await self.report_error("討論已停止，無法插話")
            return
        if self.record.outcome is not None or self._finishing:
            await self.report_error("討論已結束，無法插話")
            return
        applies_to_round = len(self.record.rounds) + 1
        self.record.interjections.append(
            RecordInterjection(text=text, at=now_iso(), applies_to_round=applies_to_round)
        )
        await self._emit(m.InterjectionQueued, text=text, applies_to_round=applies_to_round)

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
            await self._hand_over_if_moderator_failed(round_number)
            await self._remove_failing(round_number)
            active = len(self.active_participant_ids())
            if active < MIN_PARTICIPANTS:
                await self._complete_round(round_number)
                await self._finish(
                    Finish(
                        outcome="insufficient_participants",
                        result=None,
                        reason=f"在場參與者只剩 {active} 個（少於 {MIN_PARTICIPANTS} 個），討論結束",
                    )
                )
                return self.record
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
        if number == 1 and self._first_round is not None:
            await self._replay_first_round(self._first_round)
            return
        round_ = RecordRound(number=number, turns=[])
        self.record.rounds.append(round_)
        order = self._schedule_order.setdefault(number, [])
        await self._emit(m.RoundStarted, round=number)

        async def turn(pid: str, view: DiscussionView) -> None:
            # Kept as soon as it ends, so a stop mid-round keeps the finished turns.
            round_.turns.append(
                await self._run_call(pid, number, "turn", self.mode.round_instructions(view, pid), view)
            )

        for batch in self.order.schedule(self.active_participant_ids(), number):
            # Everyone in a batch sees the same view: earlier batches and rounds only.
            view = self.view()
            order.extend(batch)
            await asyncio.gather(*(turn(pid, view) for pid in batch))
            self._sort_turns(round_)

    async def _replay_first_round(self, source: RecordRound) -> None:
        """Round 1 from a prefilled round: shown through the ordinary events, turns kept as they were."""
        active = set(self.active_participant_ids())
        turns = [t.model_copy() for t in source.turns if t.participant_id in active]
        self.record.rounds.append(RecordRound(number=1, turns=turns))
        self._schedule_order[1] = [t.participant_id for t in turns]
        await self._emit(m.RoundStarted, round=1)
        for turn in turns:
            ids = {"round": 1, "participant_id": turn.participant_id, "purpose": "turn"}
            await self._emit(m.TurnStarted, **ids)
            if turn.status == "ok":
                await self._emit(m.TurnCompleted, **ids, text=turn.text or "", stance=turn.stance)
            else:
                await self._emit(m.TurnFailed, **ids, reason=turn.error or "發言失敗", kind=_kind_of(turn.status))

    async def _remove_failing(self, number: int) -> None:
        """Remove every active participant whose turns failed in this round and the one before."""
        if number < FAILED_ROUNDS_TO_REMOVE:
            return
        recent = self.record.rounds[::-1][:FAILED_ROUNDS_TO_REMOVE]  # latest first
        for pid in self.active_participant_ids():
            turns = [_turn_of(r, pid) for r in recent]
            if not all(t is not None and t.status != "ok" for t in turns):
                continue
            last_error = turns[0].error if turns[0] is not None else None
            reason = f"連續 {FAILED_ROUNDS_TO_REMOVE} 輪發言失敗（最後一次：{last_error or '未知原因'}），已移出討論"
            self.record.removed_participants.append(RecordRemoval(participant_id=pid, round=number, reason=reason))
            await self._emit(m.ParticipantRemoved, participant_id=pid, reason=reason, round=number)
            if pid == self.moderator_id():
                await self._hand_over_moderator(number)

    async def _hand_over_if_moderator_failed(self, number: int) -> None:
        """The moderator's own turn in this round failed: the next active participant takes over."""
        moderator = self.moderator_id()
        turn = _turn_of(self.record.rounds[-1], moderator) if moderator is not None else None
        if turn is not None and turn.status != "ok":
            await self._hand_over_moderator(number)

    async def _hand_over_moderator(self, number: int) -> None:
        """The moderator failed or was removed: the next active participant in the list takes over."""
        current = self.moderator_id()
        if current is None:
            return  # the mode has no moderator (e.g. 提問)
        ids = list(self.settings.participant_ids)
        active = set(self.active_participant_ids()) - {current}
        start = ids.index(current) if current in ids else -1
        after = ids[start + 1:] + ids[: start + 1]  # the list wraps around
        successor = next((pid for pid in after if pid in active), None)
        if successor is None:
            return
        self.record.moderator_changes.append(RecordModeratorChange(round=number, participant_id=successor))
        await self._emit(m.ModeratorChanged, participant_id=successor, round=number)

    def _sort_turns(self, round_: RecordRound) -> None:
        """Record a round's turns in speaking order, not in the order they finished."""
        order = self._schedule_order.get(round_.number, [])
        round_.turns.sort(key=lambda t: order.index(t.participant_id) if t.participant_id in order else len(order))

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
            if turn.status != "ok" and call.purpose in MODERATOR_PURPOSES and call.participant_id == self.moderator_id():
                await self._hand_over_moderator(number)
            results.append(
                ExtraCallResult(call=call, status=turn.status, text=turn.text, stance=turn.stance, error=turn.error)
            )
        return results

    async def _apply_reports(self, number: int, decision: ContinueRound | ExtraCalls | Finish) -> None:
        """Store and emit the confirmation / judge reports a decision carries.

        Confirmation answers come first: judge B's verdict after a confirmation is based
        on them. A later judge report of the same round replaces the earlier one in the
        record's `judge`; every verdict stays in `judge_history` (judge B: `confirm`, then
        `reached` / `not_reached`)."""
        round_ = self.record.rounds[-1]
        if decision.confirmation_report is not None:
            answers = list(decision.confirmation_report.answers)
            round_.confirmations = answers
            await self._emit(m.ConfirmationResult, round=number, answers=answers)
        if decision.judge_report is not None:
            r = decision.judge_report
            round_.judge = RecordJudge(judge=r.judge, outcome=r.outcome, detail=r.detail)
            round_.judge_history.append(round_.judge)
            await self._emit(m.JudgeResult, round=number, judge=r.judge, outcome=r.outcome, detail=r.detail)

    async def _complete_round(self, number: int) -> None:
        self.store.save(self.record)
        await self._emit(m.RoundCompleted, round=number)

    async def _finish(self, decision: Finish) -> None:
        self._finishing = True
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
        streamed: list[str] = []
        try:
            await self._emit(m.TurnStarted, **ids)
            prompt = build_prompt(view, participant_id, instructions)
            text, failure = await self._call_adapter(participant, prompt, round_number, purpose, ids, streamed)
        except asyncio.CancelledError:
            if self._stop_requested:
                self._cancelled_calls.append(_CancelledCall(ids=ids, started_at=started_at, streamed=streamed))
            raise

        if failure is not None:
            kind, reason = failure
            await self._emit(m.TurnFailed, **ids, reason=reason, kind=kind)
            return RecordTurn(
                participant_id=participant_id,
                status=_status_of(kind),
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
        streamed: list[str],
    ) -> tuple[str, tuple[str, str] | None]:
        """Stream the adapter's events (collected in `streamed`); returns (text, (kind, reason) on failure)."""
        timeout = self.settings.turn_timeout_seconds
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
                    judge_detail=r.judge.detail if r.judge else None,
                    confirmations=list(r.confirmations) if r.confirmations is not None else None,
                )
                for r in self.record.rounds
            ],
            pending_disagreements=self._pending_disagreements(),
        )

    def _pending_disagreements(self) -> dict[str, str]:
        """Disagreeing confirmation answers of the previous round only (older ones are stale)."""
        if len(self.record.rounds) < 2:
            return {}
        previous = self.record.rounds[-2]
        return {a.participant_id: a.reason for a in previous.confirmations or () if not a.agree}

    # --- events --------------------------------------------------------------

    async def _emit(self, model: type[BaseModel], **fields: Any) -> None:
        """Send one server message; parallel turns share the connection, so sends are serialised."""
        async with self._send_lock:
            self._seq += 1
            message = model(discussion_id=self.discussion_id, seq=self._seq, **fields)
            await self._send(m.to_wire(message))
