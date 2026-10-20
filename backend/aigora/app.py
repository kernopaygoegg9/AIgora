"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from aigora.api.routes import build_router

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def _is_backend_path(path: str) -> bool:
    """Unknown paths under /api and /ws are 404, never the web page."""
    return any(path == p or path.startswith(p + "/") for p in ("/api", "/ws"))


class SpaStaticFiles(StaticFiles):
    """Static files that fall back to index.html so client-side routes survive a reload."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # Judge by the request path: `path` is already normalised (`..` resolved), so
            # `/api/discussions/..%2F..%2Fx` would no longer look like an API path.
            if exc.status_code != 404 or _is_backend_path(scope.get("path", "")):
                raise
            return await super().get_response("index.html", scope)


def create_app(frontend_dist: Path | None = FRONTEND_DIST) -> FastAPI:
    """`frontend_dist`: the built frontend to serve (None or missing folder = API only)."""
    app = FastAPI(title="AIgora")
    app.include_router(build_router())

    # v1 is a local web app: the backend also serves the built frontend.
    if frontend_dist is not None and frontend_dist.is_dir():
        app.mount("/", SpaStaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app
