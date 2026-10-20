"""WS /ws/discussion: one connection per discussion (`start`, `interject`, `stop` in; events out).

The first client message must be `start`. The engine then runs as a task
while this handler keeps reading the socket (ticket 06 handles `interject`
and `stop` there). A closed browser tab cancels the discussion.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from aigora.api import messages as m
from aigora.config import ConfigError, load_participants, participants_file_path
from aigora.discussion.derived import SourceError, derived_engine, load_source
from aigora.discussion.engine import DiscussionEngine
from aigora.discussion.modes import get_mode
from aigora.discussion.orders import get_speaking_order
from aigora.discussion.settings import SettingsError, resolve_settings
from aigora.discussion.store import DiscussionStore

async def _send_error(websocket: WebSocket, message: str) -> None:
    """An error before any discussion exists (the only message on this connection)."""
    await websocket.send_json(m.to_wire(m.ErrorMessage(discussion_id=None, seq=1, message=message)))


async def _receive_start(websocket: WebSocket) -> m.StartMessage | None:
    data: Any = await websocket.receive_json()
    try:
        msg = m.parse_client_message(data)
    except ValidationError as exc:
        await _send_error(websocket, f"訊息格式錯誤：{exc.errors()[0]['msg']}")
        return None
    if not isinstance(msg, m.StartMessage):
        await _send_error(websocket, "討論尚未開始：第一個訊息必須是 start")
        return None
    return msg


def _build_engine(start: m.StartMessage, websocket: WebSocket) -> DiscussionEngine:
    """Raises SettingsError / SourceError / ConfigError when the discussion cannot start.

    With `from_discussion_id` (提問轉共識討論) the question and participants come from
    that ask, whose answers become round 1; the other settings come from `start`.
    """
    store = DiscussionStore()
    requested = start.settings
    source = None
    if start.from_discussion_id is not None:
        source = load_source(store, start.from_discussion_id)
        if requested.mode != "consensus":
            raise SettingsError("提問只能轉成共識討論")
        requested = requested.model_copy(update={"participant_ids": list(source.settings.participant_ids)})
    config = load_participants(participants_file_path())
    settings = resolve_settings(requested, config)
    common = dict(
        settings=settings,
        participants=[config.get(pid) for pid in settings.participant_ids],
        mode=get_mode(settings.mode),
        order=get_speaking_order(settings.speaking_order),
        store=store,
        send=websocket.send_json,
    )
    if source is not None:
        return derived_engine(source=source, **common)
    return DiscussionEngine(question=start.question, **common)


async def discussion_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        start = await _receive_start(websocket)
        if start is None:
            await websocket.close()
            return
        try:
            engine = _build_engine(start, websocket)
        except (SettingsError, SourceError, ConfigError) as exc:
            await _send_error(websocket, str(exc))
            await websocket.close()
            return

        run = asyncio.create_task(engine.run())
        receive = asyncio.create_task(_read_until_closed(websocket, engine))
        done, _ = await asyncio.wait({run, receive}, return_when=asyncio.FIRST_COMPLETED)
        if run not in done:  # the browser went away: stop the discussion
            run.cancel()
        receive.cancel()
        await asyncio.gather(run, receive, return_exceptions=True)
        if run in done:
            await websocket.close()
    except WebSocketDisconnect:
        pass


async def _read_until_closed(websocket: WebSocket, engine: DiscussionEngine) -> None:
    """Client messages after `start`: `interject` queues an interjection, `stop` ends the discussion."""
    while True:
        data = await websocket.receive_json()
        try:
            msg = m.parse_client_message(data)
        except ValidationError as exc:
            await engine.report_error(f"訊息格式錯誤：{exc.errors()[0]['msg']}")
            continue
        if isinstance(msg, m.InterjectMessage):
            await engine.interject(msg.text)
        elif isinstance(msg, m.StopMessage):
            await engine.stop()
        else:
            await engine.report_error("討論已經開始：不能再送出 start")
