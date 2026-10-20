"""Stand-in for the `gemini` executable in the Gemini Adapter tests.

Run as `python fake_gemini_cli.py <args...>`. Behaviour comes from env vars:

- FAKE_GEMINI_RECORD: path; writes a JSON record of argv, cwd, stdin, the
  system settings file (from GEMINI_CLI_SYSTEM_SETTINGS_PATH) and the admin
  policy file (from `--admin-policy`).
- FAKE_GEMINI_STDOUT: path of a file whose content is written to stdout,
  line by line (with FAKE_GEMINI_LINE_DELAY seconds between lines).
- FAKE_GEMINI_STDERR: text written to stderr.
- FAKE_GEMINI_EXIT: exit code (default 0).
- FAKE_GEMINI_SLEEP: seconds to sleep after writing stdout (cancellation tests).
- FAKE_GEMINI_PIDFILE: path; the process writes its pid there first.
"""

import json
import os
import sys
import time
from pathlib import Path


def _read(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else None


def main() -> int:
    env = os.environ
    if env.get("FAKE_GEMINI_PIDFILE"):
        Path(env["FAKE_GEMINI_PIDFILE"]).write_text(str(os.getpid()), encoding="utf-8")

    args = sys.argv[1:]
    if args == ["--version"]:
        print("0.0.0-fake")
        sys.stderr.write(env.get("FAKE_GEMINI_STDERR", ""))
        return int(env.get("FAKE_GEMINI_EXIT", "0"))

    stdin = sys.stdin.buffer.read().decode("utf-8")
    if env.get("FAKE_GEMINI_RECORD"):
        policy = args[args.index("--admin-policy") + 1] if "--admin-policy" in args else None
        record = {
            "argv": args,
            "cwd": os.getcwd(),
            "stdin": stdin,
            "settings": _read(env.get("GEMINI_CLI_SYSTEM_SETTINGS_PATH")),
            "policy": _read(policy),
        }
        Path(env["FAKE_GEMINI_RECORD"]).write_text(json.dumps(record), encoding="utf-8")

    delay = float(env.get("FAKE_GEMINI_LINE_DELAY", "0"))
    out = _read(env.get("FAKE_GEMINI_STDOUT")) or ""
    for line in out.splitlines(keepends=True):
        sys.stdout.buffer.write(line.encode("utf-8"))
        sys.stdout.flush()
        if delay:
            time.sleep(delay)
    if env.get("FAKE_GEMINI_STDERR"):
        sys.stderr.write(env["FAKE_GEMINI_STDERR"])
        sys.stderr.flush()
    if env.get("FAKE_GEMINI_SLEEP"):
        time.sleep(float(env["FAKE_GEMINI_SLEEP"]))
    return int(env.get("FAKE_GEMINI_EXIT", "0"))


if __name__ == "__main__":
    sys.exit(main())
