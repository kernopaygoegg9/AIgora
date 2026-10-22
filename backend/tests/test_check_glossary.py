"""Tests for scripts/check_glossary.py, run as a CLI against a fake repo."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_glossary.py"

GLOSSARY = """\
# Fake

**討論模式 (Discussion Mode)**:
一場討論遵循的規則。
_Avoid_: 玩法

**發言 (Turn)**:
一個參與者在一輪中的一次回覆。
_Avoid_: 訊息、回答

**發言順序 (Speaking Order)**:
同時或依序。
_Avoid_: 模式（「模式」只指討論模式）

**參與者 (Participant)**:
一個 AI 設定。
_Avoid_: 成員、bot
"""


def run_check(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    (tmp_path / "GLOSSARY.md").write_text(GLOSSARY, encoding="utf-8")
    for name, content in files.items():
        path = tmp_path / "frontend" / "src" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        encoding="utf-8",
    )


def test_template_text_hit_is_reported_with_location_and_preferred_term(tmp_path):
    result = run_check(
        tmp_path,
        {"components/Card.vue": "<template>\n  <p>\n    現有的回答當作第 1 輪\n  </p>\n</template>\n"},
    )

    assert result.returncode != 0
    assert result.stdout.strip() == "frontend/src/components/Card.vue:3: 用詞「回答」，請改用「發言」"
