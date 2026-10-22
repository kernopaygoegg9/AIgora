"""Route registration for every HTTP and WebSocket endpoint in the spec.

HOT FILE (owner: ticket 01). Other tickets must not edit this file; they
implement the handler functions in `aigora/api/handlers/` instead.
"""

from fastapi import APIRouter

from aigora.api.handlers import avatars, discussion_socket, discussions, options, participants

API_PREFIX = "/api"
DISCUSSION_SOCKET_PATH = "/ws/discussion"


def build_router() -> APIRouter:
    router = APIRouter()

    router.add_api_route(
        f"{API_PREFIX}/participants", participants.list_participants, methods=["GET"]
    )
    router.add_api_route(f"{API_PREFIX}/options", options.get_options, methods=["GET"])
    router.add_api_route(f"{API_PREFIX}/discussions", discussions.list_discussions, methods=["GET"])
    router.add_api_route(
        f"{API_PREFIX}/discussions/{{discussion_id}}", discussions.get_discussion, methods=["GET"]
    )
    router.add_api_route(f"{API_PREFIX}/avatars/{{filename}}", avatars.get_avatar, methods=["GET"])

    router.add_api_websocket_route(DISCUSSION_SOCKET_PATH, discussion_socket.discussion_socket)

    return router
