"""GET /api/avatars/{filename}: avatar images from `assets/avatars/` (fallback `default.png`)."""

from pathlib import Path

from fastapi.responses import FileResponse

AVATARS_DIR = Path(__file__).resolve().parents[4] / "assets" / "avatars"
DEFAULT_AVATAR = "default.png"


def _avatar_path(filename: str) -> Path:
    """The PNG directly inside `AVATARS_DIR` named `filename`, else the default avatar.

    Only plain `*.png` names are accepted, so a path (`../x`, `a\\b`) never leaves the folder.
    """
    if filename.endswith(".png") and Path(filename).name == filename and "\\" not in filename:
        path = AVATARS_DIR / filename
        if path.is_file():
            return path
    return AVATARS_DIR / DEFAULT_AVATAR


async def get_avatar(filename: str):
    return FileResponse(_avatar_path(filename), media_type="image/png")
