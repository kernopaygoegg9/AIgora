"""List hot files a ticket branch changed but does not own.

Usage (from anywhere inside the repo):
    python scripts/check_hot_files.py --feature <slug> --ticket <NN> <base>..<branch>

Reads `.scratch/<slug>/hot-files.toml` (format: docs/agents/issue-tracker.md). Exits 1 and
prints each offending file with its owners when the branch changed a hot file the ticket does
not own, 0 otherwise, 2 on a usage or git error.
"""

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_files(rng: str) -> list[str]:
    return [line for line in git("diff", "--name-only", rng).splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feature", required=True, help="feature slug under .scratch/")
    parser.add_argument("--ticket", required=True, help="ticket number, e.g. 07")
    parser.add_argument("range", help="<base>..<branch>")
    args = parser.parse_args(argv)

    root = Path(git("rev-parse", "--show-toplevel").strip())
    table = tomllib.loads((root / ".scratch" / args.feature / "hot-files.toml").read_text("utf-8"))
    hot = table.get("files", {})

    violations = []
    for path in changed_files(args.range):
        owners = hot.get(path)
        if owners is None or owners == "*" or args.ticket in owners:
            continue
        violations.append((path, owners))

    for path, owners in violations:
        print(f"{path}: owned by {', '.join(owners)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
