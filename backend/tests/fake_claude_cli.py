"""Stand-in for the `claude` executable in the claude adapter's unit tests.

Behaviour comes from the JSON file named by `FAKE_CLAUDE_SCENARIO`:

    {
      "auth": {"stdout": "...", "stderr": "...", "exit_code": 0},   # `claude auth status ...`
      "turn": {"lines": [{...}, "raw text"], "stderr": "...", "exit_code": 0,
               "sleep_before_seconds": 0, "sleep_after_seconds": 0},
      "record": "path/to/record.json",  # optional: argv / cwd / stdin / env are written here
      "heartbeat": "path"               # optional: before sleep_after, start a grandchild that
                                        # appends to this file every 50 ms (like npm shim -> node)
    }

`lines` entries are JSON-encoded unless they are strings (written verbatim).
With env `AIGORA_TEST_PID_DIR` set, its own pid and the grandchild's are recorded there
(conftest `cli_processes` ends them at teardown).
"""

import json
import os
import subprocess
import sys
import time

HEARTBEAT = (
    "import sys, time\nwhile True:\n    open(sys.argv[1], 'a').write('.')\n    time.sleep(0.05)\n"
)


def record_pid(pid: int) -> None:
    """Leave `<pid>.pid` in AIGORA_TEST_PID_DIR so the test's teardown can end that process."""
    if pid_dir := os.environ.get("AIGORA_TEST_PID_DIR"):
        open(os.path.join(pid_dir, f"{pid}.pid"), "w").close()


def main() -> int:
    record_pid(os.getpid())
    scenario = json.loads(open(os.environ["FAKE_CLAUDE_SCENARIO"], encoding="utf-8").read())
    args = sys.argv[1:]
    is_auth = args[:2] == ["auth", "status"]
    stdin = "" if is_auth else sys.stdin.buffer.read().decode("utf-8")

    if record := scenario.get("record"):
        with open(record, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "argv": args,
                    "cwd": os.getcwd(),
                    "stdin": stdin,
                    "env_CLAUDECODE": os.environ.get("CLAUDECODE"),
                    "env_ENABLE_CLAUDEAI_MCP_SERVERS": os.environ.get(
                        "ENABLE_CLAUDEAI_MCP_SERVERS"
                    ),
                    "pid": os.getpid(),
                },
                f,
            )

    if is_auth:
        auth = scenario.get("auth", {})
        sys.stdout.write(auth.get("stdout", ""))
        sys.stderr.write(auth.get("stderr", ""))
        return auth.get("exit_code", 0)

    turn = scenario.get("turn", {})
    time.sleep(turn.get("sleep_before_seconds", 0))
    for line in turn.get("lines", []):
        text = line if isinstance(line, str) else json.dumps(line)
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
        sys.stdout.flush()
    sys.stderr.write(turn.get("stderr", ""))
    sys.stderr.flush()
    if heartbeat := scenario.get("heartbeat"):
        record_pid(subprocess.Popen([sys.executable, "-c", HEARTBEAT, heartbeat]).pid)
    time.sleep(turn.get("sleep_after_seconds", 0))
    return turn.get("exit_code", 0)


if __name__ == "__main__":
    sys.exit(main())
