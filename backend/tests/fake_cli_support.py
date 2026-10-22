"""Helpers the fake CLIs (fake_*_cli.py) share.

The fakes run as scripts (`python fake_x_cli.py ...`), so Python puts this folder first on
`sys.path` and `import fake_cli_support` works without the package being installed.
"""

import os
import subprocess
import sys

from process_reaper import PID_DIR_ENV

HEARTBEAT = (
    "import sys, time\nwhile True:\n    open(sys.argv[1], 'a').write('.')\n    time.sleep(0.05)\n"
)


def record_pid(pid: int) -> None:
    """Leave `<pid>.pid` in AIGORA_TEST_PID_DIR so the test's teardown can end that process."""
    if pid_dir := os.environ.get(PID_DIR_ENV):
        open(os.path.join(pid_dir, f"{pid}.pid"), "w").close()


def start_heartbeat(path: str) -> None:
    """Start (and record) a child that appends to `path` every 50 ms, like npm shim -> node."""
    record_pid(subprocess.Popen([sys.executable, "-c", HEARTBEAT, path]).pid)
