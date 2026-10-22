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


def test_branch_that_changes_another_tickets_hot_file_fails_and_names_file_and_owners(
    repo: Path,
) -> None:
    commit_changes(repo, "frontend/package.json", "backend/uv.lock")

    result = run_check(repo, "06")

    assert result.returncode == 1
    assert "backend/uv.lock" in result.stdout
    assert "01" in result.stdout
    assert "frontend/package.json" not in result.stdout


def test_any_ticket_may_change_a_file_marked_star(repo: Path) -> None:
    commit_changes(repo, "AGENTS.md")

    assert run_check(repo, "05").returncode == 0


def test_files_not_in_the_table_are_unrestricted(repo: Path) -> None:
    commit_changes(repo, "backend/aigora/new_module.py", "README.md")

    assert run_check(repo, "05").returncode == 0


def test_glob_patterns_match_changed_files(repo: Path) -> None:
    commit_changes(repo, ".github/workflows/ci.yml", "backend/tests/test_claude_real.py")

    assert run_check(repo, "02").returncode == 1
    assert run_check(repo, "03").returncode == 1
    both_owned = run_check(repo, "04")
    assert both_owned.returncode == 1
    assert ".github/workflows/ci.yml: owned by 02" in both_owned.stdout
    assert "backend/tests/test_claude_real.py: owned by 03" in both_owned.stdout


def test_hot_files_changed_on_base_after_the_branch_forked_are_not_blamed_on_it(
    repo: Path,
) -> None:
    commit_changes(repo, ".github/workflows/ci.yml")
    git(repo, "checkout", "-q", "base")
    commit_changes(repo, "backend/uv.lock")
    git(repo, "checkout", "-q", "work")

    result = run_check(repo, "02")

    assert result.returncode == 0, result.stdout


def test_unknown_feature_or_bad_range_is_a_usage_error(repo: Path) -> None:
    commit_changes(repo, "README.md")

    missing_table = subprocess.run(
        [sys.executable, str(SCRIPT), "--feature", "nope", "--ticket", "01", "base..work"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    bad_range = run_check(repo, "01", "base..no-such-branch")

    assert missing_table.returncode == 2
    assert "hot-files.toml" in missing_table.stderr
    assert bad_range.returncode == 2
    assert "no-such-branch" in bad_range.stderr


def write_table(repo: Path, text: str) -> None:
    write(repo, ".scratch/feat/hot-files.toml", text)


@pytest.mark.parametrize(
    "table",
    [
        '[files]\n"a.txt" = "01"\n',
        '[files]\n"a.txt" = 1\n',
        '[files]\n"a.txt" = ["01", 2]\n',
        '"a.txt" = ["01"]\n',
        "files = 1\n",
    ],
    ids=["string-not-star", "integer", "non-string-owner", "no-files-table", "files-not-table"],
)
def test_malformed_hot_files_table_is_a_usage_error(repo: Path, table: str) -> None:
    write_table(repo, table)
    commit_changes(repo, "a.txt")

    result = run_check(repo, "01")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "hot-files.toml" in result.stderr


def test_one_digit_ticket_numbers_are_padded_on_both_sides(repo: Path) -> None:
    write_table(repo, '[files]\n"a.txt" = ["7"]\n"b.txt" = ["07"]\n')
    commit_changes(repo, "a.txt", "b.txt")

    assert run_check(repo, "7").returncode == 0
    assert run_check(repo, "07").returncode == 0
    other = run_check(repo, "8")
    assert other.returncode == 1
    assert "a.txt: owned by 07" in other.stdout


@pytest.mark.parametrize("ticket", ["123", "ab", ""])
def test_ticket_that_is_not_one_or_two_digits_is_a_usage_error(repo: Path, ticket: str) -> None:
    commit_changes(repo, "README.md")

    result = run_check(repo, ticket)

    assert result.returncode == 2
    assert "ticket" in result.stderr


def test_owner_entry_that_is_not_one_or_two_digits_is_a_usage_error(repo: Path) -> None:
    write_table(repo, '[files]\n"a.txt" = ["abc"]\n')
    commit_changes(repo, "a.txt")

    result = run_check(repo, "01")

    assert result.returncode == 2
    assert "abc" in result.stderr
