"""WS /ws/discussion: one connection per discussion (`start`, `interject`, `stop` in; events out)."""

from fastapi import WebSocket

from aigora.api.not_implemented import reject_websocket


async def discussion_socket(websocket: WebSocket):
    await reject_websocket(websocket)
