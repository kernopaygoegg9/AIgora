"""claude adapter, driven against a fake `claude` executable (tests/fake_claude_cli.py)."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from aigora.adapters.base import Availability, Capabilities, Completed, Delta, Failed, TurnRequest, get_adapter
from aigora.adapters.claude import ClaudeAdapter
from aigora.config import ParticipantConfig

FAKE_CLI = Path(__file__).with_name("fake_claude_cli.py")


def text_delta(text: str) -> dict:
    return {"type": "stream_event", "event": {"type": "content_block_delta", "index": 0,
                                              "delta": {"type": "text_delta", "text": text}}}


def block_start(index: int = 0) -> dict:
    return {"type": "stream_event", "event": {"type": "content_block_start", "index": index,
                                              "content_block": {"type": "text", "text": ""}}}


def result(text: str, is_error: bool = False, subtype: str = "success") -> dict:
    return {"type": "result", "subtype": subtype, "is_error": is_error, "result": text}


INIT = {"type": "system", "subtype": "init", "tools": ["WebSearch", "WebFetch"], "mcp_servers": []}


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """Returns `setup(**scenario) -> (adapter, record_path)`."""

    def setup(**scenario):
        record = tmp_path / "record.json"
        scenario.setdefault("record", str(record))
        path = tmp_path / "scenario.json"
        path.write_text(json.dumps(scenario), encoding="utf-8")
        monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", str(path))
        return ClaudeAdapter(command=[sys.executable, str(FAKE_CLI)]), record

    return setup


def participant(model: str | None = None, **options) -> ParticipantConfig:
    return ParticipantConfig(id="claude", display_name="Claude", adapter="claude", model=model, options=options)


def request(workspace: Path, prompt: str = "Q?", model: str | None = None) -> TurnRequest:
    return TurnRequest(participant=participant(model), prompt=prompt, workspace=workspace, timeout_seconds=30)


async def collect(adapter, req) -> list:
    return [event async for event in adapter.run_turn(req)]


async def test_streams_text_deltas_then_completes_with_the_full_text(fake_claude, tmp_path):
    adapter, _ = fake_claude(turn={"lines": [
        INIT, block_start(), text_delta("Hello"), text_delta(" world"),
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello world"}]}},
        result("Hello world"),
    ]})
    events = await collect(adapter, request(tmp_path))
    assert events == [Delta("Hello"), Delta(" world"), Completed("Hello world")]


async def test_runs_isolated_in_the_workspace_with_the_prompt_on_stdin(fake_claude, tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    adapter, record = fake_claude(turn={"lines": [result("ok")]})
    workspace = tmp_path / "ws"
    workspace.mkdir()
    prompt = "第一輪：What is 2+2?\n" + "x" * 50_000  # long prompts must not go on the command line
    events = await collect(adapter, request(workspace, prompt=prompt, model="sonnet"))
    assert events == [Completed("ok")]

    seen = json.loads(record.read_text(encoding="utf-8"))
    argv = seen["argv"]
    assert Path(seen["cwd"]).resolve() == workspace.resolve()
    assert seen["stdin"] == prompt
    assert prompt not in argv
    # ADR 0002: non-interactive, only web tools (pre-approved), no MCP, no settings, no skills.
    assert "-p" in argv
    assert argv[argv.index("--tools") + 1] == "WebSearch,WebFetch"
    assert argv[argv.index("--allowedTools") + 1] == "WebSearch,WebFetch"
    assert "--strict-mcp-config" in argv and "--mcp-config" not in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--disable-slash-commands" in argv
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--include-partial-messages" in argv
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert not any(a in argv for a in ("--resume", "--continue", "-c", "-r"))
    assert seen["env_CLAUDECODE"] is None
    assert seen["env_ENABLE_CLAUDEAI_MCP_SERVERS"] == "false"


async def test_omits_model_when_the_participant_has_none(fake_claude, tmp_path):
    adapter, record = fake_claude(turn={"lines": [result("ok")]})
    await collect(adapter, request(tmp_path))
    assert "--model" not in json.loads(record.read_text(encoding="utf-8"))["argv"]


async def test_text_after_a_web_search_is_kept_as_a_separate_paragraph(fake_claude, tmp_path):
    adapter, _ = fake_claude(turn={"lines": [
        block_start(0), text_delta("Let me search."),
        {"type": "stream_event", "event": {"type": "content_block_start", "index": 1,
                                           "content_block": {"type": "server_tool_use", "name": "web_search"}}},
        block_start(0), text_delta("Answer: https://example.com"),
        "not json at all",
        result("Answer: https://example.com"),
    ]})
    events = await collect(adapter, request(tmp_path))
    assert [e.text for e in events if isinstance(e, Delta)] == ["Let me search.", "\n\nAnswer: https://example.com"]
    assert events[-1] == Completed("Let me search.\n\nAnswer: https://example.com")


async def test_without_partial_messages_completes_with_the_result_text(fake_claude, tmp_path):
    adapter, _ = fake_claude(turn={"lines": [result("whole answer\nSTANCE: AGREE")]})
    assert await collect(adapter, request(tmp_path)) == [Completed("whole answer\nSTANCE: AGREE")]


# --- failures ---------------------------------------------------------------------------


@pytest.mark.parametrize("turn, kind", [
    ({"lines": [result("Not logged in · Please run /login", is_error=True)], "exit_code": 1}, "auth"),
    ({"lines": [result("Invalid API key · Please run /login", is_error=True)], "exit_code": 1}, "auth"),
    ({"lines": [{"type": "assistant", "error": "authentication_failed", "message": {"content": []}},
                result("Failed to authenticate", is_error=True)], "exit_code": 1}, "auth"),
    ({"lines": [result("Claude AI usage limit reached|1760000000", is_error=True)], "exit_code": 1}, "quota"),
    ({"lines": [{"type": "assistant", "error": "rate_limit", "message": {"content": []}},
                result("You've hit your limit · resets 5pm", is_error=True)], "exit_code": 1}, "quota"),
    ({"lines": [result("", is_error=True, subtype="error_during_execution")], "exit_code": 1}, "unknown"),
    ({"lines": [block_start(), text_delta("half")], "stderr": "Segmentation fault", "exit_code": 139}, "crashed"),
    ({"lines": [], "exit_code": 0}, "crashed"),
])
async def test_failures_are_classified(fake_claude, tmp_path, turn, kind):
    adapter, _ = fake_claude(turn=turn)
    events = await collect(adapter, request(tmp_path))
    assert isinstance(events[-1], Failed)
    assert events[-1].kind == kind
    assert events[-1].reason
    assert sum(isinstance(e, (Completed, Failed)) for e in events) == 1


async def test_missing_cli_fails_as_not_available(tmp_path):
    adapter = ClaudeAdapter(command=[str(tmp_path / "no-such-claude.exe")])
    events = await collect(adapter, request(tmp_path))
    assert len(events) == 1 and events[0].kind == "not_available"


def _alive(pid: int) -> bool:
    if sys.platform == "win32":
        import subprocess
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


async def test_cancelling_a_turn_kills_the_cli(fake_claude, tmp_path):
    adapter, record = fake_claude(turn={"lines": [block_start(), text_delta("thinking...")],
                                        "sleep_after_seconds": 60})
    gen = adapter.run_turn(request(tmp_path))
    first = await asyncio.wait_for(gen.__anext__(), timeout=15)
    assert first == Delta("thinking...")
    pid = json.loads(record.read_text(encoding="utf-8"))["pid"]
    assert _alive(pid)

    task = asyncio.ensure_future(gen.__anext__())
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await gen.aclose()
    for _ in range(50):
        if not _alive(pid):
            break
        await asyncio.sleep(0.1)
    assert not _alive(pid)


# --- availability -----------------------------------------------------------------------


async def test_logged_in_cli_is_available(fake_claude):
    adapter, record = fake_claude(auth={"stdout": json.dumps({"loggedIn": True, "authMethod": "claude.ai"})})
    assert await adapter.check_availability(participant()) == Availability(True)
    assert json.loads(record.read_text(encoding="utf-8"))["argv"][:2] == ["auth", "status"]


async def test_logged_out_cli_is_unavailable_with_a_reason(fake_claude):
    adapter, _ = fake_claude(auth={"stdout": json.dumps({"loggedIn": False}), "exit_code": 1})
    availability = await adapter.check_availability(participant())
    assert not availability.available and "not logged in" in availability.reason


async def test_unreadable_login_status_is_unavailable_with_the_cli_message(fake_claude):
    adapter, _ = fake_claude(auth={"stderr": "boom: config corrupt", "exit_code": 2})
    availability = await adapter.check_availability(participant())
    assert not availability.available and "boom: config corrupt" in availability.reason


async def test_missing_cli_is_unavailable(tmp_path):
    adapter = ClaudeAdapter(command=[str(tmp_path / "no-such-claude.exe")])
    availability = await adapter.check_availability(participant())
    assert not availability.available and availability.reason


async def test_cli_not_on_path_is_unavailable(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name, *a, **k: None)
    availability = await ClaudeAdapter().check_availability(participant())
    assert not availability.available and "not installed" in availability.reason


# --- contract -------------------------------------------------------------------------


def test_registered_and_declares_web_access_and_streaming():
    adapter = get_adapter("claude")
    assert isinstance(adapter, ClaudeAdapter)
    assert adapter.capabilities(participant()) == Capabilities(web_access=True, streaming=True)


def test_rejects_unknown_options():
    with pytest.raises(ValueError):
        ClaudeAdapter().validate_options({"tools": "Bash"})
    ClaudeAdapter().validate_options({})
