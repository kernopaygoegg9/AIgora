"""A scripted stand-in for the `codex` CLI, used by test_codex_adapter.py.

Behaviour comes from the JSON file named by env `AIGORA_FAKE_CODEX_SCENARIO`:

    {
      "login_status": {"stdout": "Logged in using ChatGPT", "exit": 0},
      "debug_models": {"stdout": "{...}", "stderr": "", "exit": 0, "hang": false},  # `debug models`
      "events": [{"type": "turn.started"}, "raw line", ...],  # JSONL printed by `exec`
      "stderr": "...",          # printed to stderr by `exec`
      "exit": 0,                # exit code of `exec`
      "hang": false,            # after the events, start a heartbeat grandchild and wait forever
      "heartbeat": "path",      # file the grandchild appends to every 50 ms
      "record": "path"          # where `exec` writes {"argv", "cwd", "stdin"}
    }
"""

import json
import os
import subprocess
import sys
import time

HEARTBEAT = (
    "import sys, time\nwhile True:\n    open(sys.argv[1], 'a').write('.')\n    time.sleep(0.05)\n"
)


def main() -> int:
    with open(os.environ["AIGORA_FAKE_CODEX_SCENARIO"], encoding="utf-8") as f:
        scenario = json.load(f)
    args = sys.argv[1:]

    if args[:2] == ["login", "status"]:
        status = scenario.get("login_status", {"stdout": "Logged in using ChatGPT", "exit": 0})
        print(status.get("stdout", ""))
        return status.get("exit", 0)

    if args[:2] == ["debug", "models"]:
        catalog = scenario.get("debug_models", {"stdout": '{"models": []}'})
        sys.stdout.write(catalog.get("stdout", ""))
        sys.stderr.write(catalog.get("stderr", ""))
        sys.stdout.flush()
        sys.stderr.flush()
        while catalog.get("hang"):
            time.sleep(1)
        return catalog.get("exit", 0)

    stdin = sys.stdin.buffer.read().decode("utf-8")
    if scenario.get("record"):
        with open(scenario["record"], "w", encoding="utf-8") as f:
            json.dump({"argv": args, "cwd": os.getcwd(), "stdin": stdin}, f)

    for event in scenario.get("events", []):
        line = event if isinstance(event, str) else json.dumps(event, ensure_ascii=False)
        sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
        sys.stdout.flush()

    if scenario.get("stderr"):
        sys.stderr.write(scenario["stderr"])
        sys.stderr.flush()

    if scenario.get("hang"):
        # Like the npm shim -> native binary: the real work happens in a grandchild.
        subprocess.Popen([sys.executable, "-c", HEARTBEAT, scenario["heartbeat"]])
        while True:
            time.sleep(1)

    return scenario.get("exit", 0)


if __name__ == "__main__":
    sys.exit(main())
