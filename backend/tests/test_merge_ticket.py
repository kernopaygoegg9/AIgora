"""Tests for scripts/merge-ticket.sh, run with Git's bash against a throwaway git repo."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "merge-ticket.sh"


def bash() -> str:
    if sys.platform != "win32":
        return "bash"
    # Not plain "bash": on Windows that finds WSL's System32\bash.exe first.
    exec_path = subprocess.run(
        ["git", "--exec-path"], check=True, capture_output=True, text=True
    ).stdout.strip()
    return str(Path(exec_path).parents[2] / "bin" / "bash.exe")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Integration branch `main` checked out; branch `work` has one commit to merge."""
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "work")
    git(tmp_path, "checkout", "-q", "main")
    return tmp_path


def merge(repo: Path, check_cmd: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "AIGORA_MERGE_CHECK_CMD": check_cmd,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        [bash(), str(SCRIPT), "work"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_passing_check_keeps_the_merge_commit(repo: Path) -> None:
    before = git(repo, "rev-parse", "HEAD")

    result = merge(repo, "true")

    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "HEAD^1") == before
    assert (repo / "b.txt").exists()


def test_failing_check_resets_to_the_pre_merge_commit(repo: Path) -> None:
    before = git(repo, "rev-parse", "HEAD")

    result = merge(repo, "exit 1")

    assert result.returncode == 1
    assert git(repo, "rev-parse", "HEAD") == before


@pytest.mark.parametrize("signal_name, code", [("INT", 130), ("TERM", 143)])
def test_interrupt_during_the_check_resets_to_the_pre_merge_commit(
    repo: Path, signal_name: str, code: int
) -> None:
    before = git(repo, "rev-parse", "HEAD")

    # The check signals merge-ticket.sh (its parent shell), then would report success.
    result = merge(repo, f"kill -{signal_name} $PPID; exit 0")

    assert result.returncode == code, result.stdout + result.stderr
    assert git(repo, "rev-parse", "HEAD") == before
    assert "interrupted" in result.stderr
