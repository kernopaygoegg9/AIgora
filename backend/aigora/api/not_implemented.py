from fastapi import HTTPException, WebSocket

NOT_IMPLEMENTED = "not implemented"


def not_implemented() -> HTTPException:
    """Return the 501 error raised by endpoints that are registered but not built yet."""
    return HTTPException(status_code=501, detail=NOT_IMPLEMENTED)


async def reject_websocket(websocket: WebSocket) -> None:
    """Accept, report "not implemented" as an `error` message, and close."""
    await websocket.accept()
    await websocket.send_json({"type": "error", "message": NOT_IMPLEMENTED})
    await websocket.close(code=1011)
