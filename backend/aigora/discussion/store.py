"""Discussion Store (討論紀錄儲存): one JSON file per discussion, `<data dir>/<id>.json`.

The engine overwrites the file after every round and when the discussion ends.
Listing and reading (history, ticket 09) belong here too.
"""

from __future__ import annotations

import os
from pathlib import Path

from aigora.config import REPO_ROOT
from aigora.record import DiscussionRecord


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
