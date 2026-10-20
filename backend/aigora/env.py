"""Backend-only settings from `.env` (spec "設定載入"). Never sent to the browser.

`backend_env()` reads the file named by `AIGORA_ENV_FILE` (relative = repo root;
default: repo-root `.env`, missing file = empty) on every call, so edits apply
without a restart. Non-empty process environment variables override the file.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from aigora.config import REPO_ROOT

TYPESAFE_API_KEY = "TYPESAFE_API_KEY"


def env_file_path() -> Path:
    path = Path(os.environ.get("AIGORA_ENV_FILE", ".env"))
    return path if path.is_absolute() else REPO_ROOT / path


def backend_env() -> dict[str, str]:
    path = env_file_path()
    values = {k: v for k, v in dotenv_values(path).items() if v} if path.is_file() else {}
    values.update({k: v for k, v in os.environ.items() if v})
    return values


def has_typesafe_key(env: dict[str, str] | None = None) -> bool:
    env = backend_env() if env is None else env
    return bool(env.get(TYPESAFE_API_KEY, "").strip())
