"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from aigora.api.routes import build_router

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


class SpaStaticFiles(StaticFiles):
    """Static files that fall back to index.html so client-side routes survive a reload."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # `path` is OS-normalised (backslashes on Windows).
            if exc.status_code != 404 or path.replace("\\", "/").startswith(("api/", "ws/")):
                raise
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    app = FastAPI(title="AIgora")
    app.include_router(build_router())

    # v1 is a local web app: the backend also serves the built frontend.
    if FRONTEND_DIST.is_dir():
        app.mount("/", SpaStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app
