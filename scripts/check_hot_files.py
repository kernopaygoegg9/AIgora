"""List hot files a ticket branch changed but does not own.

Usage (from anywhere inside the repo):
    python scripts/check_hot_files.py --feature <slug> --ticket <NN> <base>..<branch>

Reads `.scratch/<slug>/hot-files.toml` (format: docs/agents/issue-tracker.md). Exits 1 and
prints each offending file with its owners when the branch changed a hot file the ticket does
not own, 0 otherwise, 2 on a usage error, a malformed table, or a git error. Ticket numbers
are one or two digits; `7` is read as `07` both in `--ticket` and in the table.
"""

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_files(rng: str) -> list[str]:
    """Files the branch changed since it forked from base (`base...branch`), renames split."""
    if "..." not in rng:
        rng = rng.replace("..", "...", 1)
    out = git("diff", "--name-only", "--no-renames", rng)
    return [line for line in out.splitlines() if line]


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**` matches across `/`; `*` and `?` stay inside one path segment."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def owners_of(path: str, hot: dict[str, list[str] | str]) -> list[str] | str | None:
    """Owners from every pattern matching `path`: "*" if any says so, None if none match."""
    owners: list[str] = []
    matched = False
    for pattern, who in hot.items():
        if glob_to_regex(pattern).fullmatch(path):
            if who == "*":
                return "*"
            matched = True
            owners += [w for w in who if w not in owners]
    return owners if matched else None


class TableError(Exception):
    """The hot-files table or the ticket number is malformed."""


def ticket_number(value: object) -> str:
    """`7` -> `07`; anything but one or two digits raises TableError."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,2}", value):
        raise TableError(f"ticket number must be one or two digits, got {value!r}")
    return value.zfill(2)


def load_table(text: str) -> dict[str, list[str] | str]:
    """Parse and validate `[files]`: each value is "*" or a list of ticket numbers (padded)."""
    files = tomllib.loads(text).get("files")
    if not isinstance(files, dict):
        raise TableError("missing [files] table")
    hot: dict[str, list[str] | str] = {}
    for pattern, who in files.items():
        if who == "*":
            hot[pattern] = "*"
        elif isinstance(who, list):
            try:
                hot[pattern] = [ticket_number(w) for w in who]
            except TableError as exc:
                raise TableError(f"{pattern!r}: {exc}") from None
        else:
            raise TableError(
                f'{pattern!r}: owners must be "*" or a list of ticket numbers, got {who!r}'
            )
    return hot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feature", required=True, help="feature slug under .scratch/")
    parser.add_argument("--ticket", required=True, help="ticket number, e.g. 07")
    parser.add_argument("range", help="<base>..<branch>")
    args = parser.parse_args(argv)
    try:
        ticket = ticket_number(args.ticket)
    except TableError as exc:
        print(f"error: --ticket: {exc}", file=sys.stderr)
        return 2

    try:
        root = Path(git("rev-parse", "--show-toplevel").strip())
        table_path = root / ".scratch" / args.feature / "hot-files.toml"
        if not table_path.is_file():
            print(f"error: {table_path} not found", file=sys.stderr)
            return 2
        hot = load_table(table_path.read_text("utf-8"))
        changed = changed_files(args.range)
    except subprocess.CalledProcessError as exc:
        print(f"error: {' '.join(exc.cmd)} failed:\n{exc.stderr}", file=sys.stderr)
        return 2
    except (tomllib.TOMLDecodeError, TableError) as exc:
        print(f"error: {table_path}: {exc}", file=sys.stderr)
        return 2

    violations = []
    for path in changed:
        owners = owners_of(path, hot)
        if owners is None or owners == "*" or ticket in owners:
            continue
        violations.append((path, owners))

    for path, owners in violations:
        print(f"{path}: owned by {', '.join(owners)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
