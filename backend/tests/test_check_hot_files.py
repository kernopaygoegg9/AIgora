"""Tests for scripts/check_hot_files.py, run as a command against a throwaway git repo."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_hot_files.py"

HOT_FILES = """\
[files]
"frontend/package.json" = ["01", "06"]
"backend/uv.lock" = ["01"]
".github/workflows/**" = ["02"]
"backend/tests/test_*_real.py" = ["03"]
"AGENTS.md" = "*"
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def write(repo: Path, rel: str, text: str = "x\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo whose `base` branch holds the feature's hot-files.toml; HEAD is branch `work`."""
    git(tmp_path, "init", "-q", "-b", "base")
    write(tmp_path, ".scratch/feat/hot-files.toml", HOT_FILES)
    write(tmp_path, "README.md")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "work")
    return tmp_path


def commit_changes(repo: Path, *paths: str) -> None:
    for rel in paths:
        write(repo, rel, f"changed {rel}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "work")


def run_check(repo: Path, ticket: str, rng: str = "base..work") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--feature", "feat", "--ticket", ticket, rng],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_branch_that_changes_only_its_own_hot_files_passes(repo: Path) -> None:
    commit_changes(repo, "frontend/package.json", "backend/uv.lock")

    result = run_check(repo, "01")

    assert result.returncode == 0, result.stdout + result.stderr
