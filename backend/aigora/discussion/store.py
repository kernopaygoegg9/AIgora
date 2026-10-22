"""Discussion Store (討論紀錄儲存): one JSON file per discussion, `<data dir>/<id>.json`.

The engine overwrites the file after every round and when the discussion ends.
Listing and reading (history, ticket 09) belong here too.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from pydantic import ValidationError

from aigora.config import REPO_ROOT
from aigora.record import DiscussionRecord

log = logging.getLogger(__name__)

# Record ids are `YYYYMMDD-HHMMSS-<6 hex>`; anything else (e.g. `../x`) is never a record.
_ID_PATTERN = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")


def data_dir_path() -> Path:
    """`AIGORA_DATA_DIR` (relative paths are against the repo root), else `data/discussions`."""
    path = Path(os.environ.get("AIGORA_DATA_DIR", "data/discussions"))
    return path if path.is_absolute() else REPO_ROOT / path


class DiscussionStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or data_dir_path()

    def path_for(self, discussion_id: str) -> Path:
        return self.directory / f"{discussion_id}.json"

    def save(self, record: DiscussionRecord) -> Path:
        """Write atomically (temp file + replace) so a crash never leaves half a record."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(record.id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return path

    def read(self, discussion_id: str) -> DiscussionRecord | None:
        """The record with this id, or None if there is none (or it cannot be parsed)."""
        if not _ID_PATTERN.match(discussion_id):
            return None
        return self._load(self.path_for(discussion_id))

    def list(self) -> list[DiscussionRecord]:
        """Every readable record, newest first (by `created_at`). In-progress ones included."""
        if not self.directory.is_dir():
            return []
        records = [
            r for path in self.directory.glob("*.json") if (r := self._load(path)) is not None
        ]
        return sorted(records, key=lambda r: (r.created_at, r.id), reverse=True)

    def _load(self, path: Path) -> DiscussionRecord | None:
        try:
            return DiscussionRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValidationError, ValueError) as exc:
            log.warning("skipping unreadable discussion record %s: %s", path, exc)
            return None
