"""The fake CLIs' processes never outlive a test, even when the adapter fails to end them."""

import asyncio
import contextlib
import json
import sys
from pathlib import Path

import pytest
from process_reaper import alive, reap_cli_processes, recorded_pids

from aigora.adapters import claude
from aigora.adapters.base import TurnRequest
from aigora.adapters.claude import ClaudeAdapter
from aigora.config import ParticipantConfig

FAKE_CLAUDE = Path(__file__).with_name("fake_claude_cli.py")


async def kill_only_the_cli(proc: asyncio.subprocess.Process) -> None:
    """A broken cancellation: ends the CLI but leaves its children running.

    The wait is bounded like kill_tree's: on POSIX, asyncio's wait() also waits for the pipes
    to close, and the surviving grandchild holds them open.
    """
    if proc.returncode is None:
        proc.kill()
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(proc.wait(), timeout=1)


async def heartbeat_size_after_a_pause(heartbeat: Path) -> tuple[int, int]:
    await asyncio.sleep(0.3)
    before = heartbeat.stat().st_size
    await asyncio.sleep(0.5)
    return before, heartbeat.stat().st_size


async def test_teardown_ends_a_grandchild_that_cancellation_left_running(tmp_path, monkeypatch):
    monkeypatch.setattr(claude, "kill_tree", kill_only_the_cli)
    heartbeat = tmp_path / "heartbeat.txt"
    scenario = tmp_path / "scenario.json"
    scenario.write_text(
        json.dumps({"turn": {"sleep_after_seconds": 60}, "heartbeat": str(heartbeat)}),
        encoding="utf-8",
    )
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", str(scenario))
    adapter = ClaudeAdapter(command=[sys.executable, str(FAKE_CLAUDE)])
    participant = ParticipantConfig(id="claude", display_name="Claude", adapter="claude")
    request = TurnRequest(
        participant=participant, prompt="Q?", workspace=tmp_path, timeout_seconds=30
    )

    async def consume():
        async for _ in adapter.run_turn(request):
            pass

    with reap_cli_processes(tmp_path / "pids") as pid_dir:  # what the fixture wraps around a test
        task = asyncio.create_task(consume())
        for _ in range(200):
            if heartbeat.exists() and heartbeat.stat().st_size > 2:
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("fake CLI grandchild never started")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        before, after = await heartbeat_size_after_a_pause(heartbeat)
        assert after > before, "the broken cancellation should have left the grandchild running"
        pids = recorded_pids(pid_dir)
        assert len(pids) == 2, "the fake CLI should have recorded itself and its grandchild"
        assert any(alive(pid) for pid in pids)

    before, after = await heartbeat_size_after_a_pause(heartbeat)
    assert after == before, "the grandchild is still running after teardown"
    assert [pid for pid in pids if alive(pid)] == [], "a recorded process outlived teardown"
