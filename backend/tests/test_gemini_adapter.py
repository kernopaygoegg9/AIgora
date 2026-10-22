"""Gemini Adapter, with the `gemini` CLI replaced by `fake_gemini_cli.py`."""

import asyncio
import json
import os
import sys
import time
import tomllib
from pathlib import Path

import pytest

from aigora.adapters.base import (
    Availability,
    Capabilities,
    Completed,
    Delta,
    Failed,
    TurnRequest,
    get_adapter,
)
from aigora.adapters.gemini import GeminiAdapter
from aigora.config import ParticipantConfig

FAKE_CLI = Path(__file__).with_name("fake_gemini_cli.py")
AUTH_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA")


def participant(model: str | None = None, **options) -> ParticipantConfig:
    return ParticipantConfig(
        id="gem", display_name="Gemini", adapter="gemini", model=model, options=options
    )


def stream_lines(*events: dict) -> str:
    return "".join(json.dumps(e) + "\n" for e in events)


def assistant(text: str) -> dict:
    return {
        "type": "message",
        "timestamp": "t",
        "role": "assistant",
        "content": text,
        "delta": True,
    }


INIT = {"type": "init", "timestamp": "t", "session_id": "s1", "model": "gemini-x"}
USER = {"type": "message", "timestamp": "t", "role": "user", "content": "the prompt"}
OK = {"type": "result", "timestamp": "t", "status": "success", "stats": {"total_tokens": 1}}


class FakeCli:
    """Scripts one run of the fake CLI through env vars."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        self.dir = tmp_path / "fakecli"
        self.dir.mkdir()
        self.home = self.dir / "home"
        self.monkeypatch = monkeypatch
        self.record_path = self.dir / "record.json"
        monkeypatch.setenv("FAKE_GEMINI_RECORD", str(self.record_path))
        for name in AUTH_ENV:
            monkeypatch.delenv(name, raising=False)
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        self.script()

    def script(
        self,
        stdout: str = "",
        stderr: str = "",
        exit: int = 0,
        sleep: float = 0,
        line_delay: float = 0,
    ):
        out = self.dir / "stdout.txt"
        out.write_text(stdout, encoding="utf-8")
        self.monkeypatch.setenv("FAKE_GEMINI_STDOUT", str(out))
        self.monkeypatch.setenv("FAKE_GEMINI_STDERR", stderr)
        self.monkeypatch.setenv("FAKE_GEMINI_EXIT", str(exit))
        self.monkeypatch.setenv("FAKE_GEMINI_SLEEP", str(sleep))
        self.monkeypatch.setenv("FAKE_GEMINI_LINE_DELAY", str(line_delay))

    def log_in(self):
        (self.home / ".gemini").mkdir(parents=True, exist_ok=True)
        (self.home / ".gemini" / "oauth_creds.json").write_text("{}", encoding="utf-8")

    @property
    def record(self) -> dict:
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def adapter(self) -> GeminiAdapter:
        return GeminiAdapter(command=[sys.executable, str(FAKE_CLI)], user_home=self.home)

    def request(self, p: ParticipantConfig | None = None, prompt: str = "Q?") -> TurnRequest:
        return TurnRequest(
            participant=p or participant(),
            prompt=prompt,
            workspace=self.workspace,
            timeout_seconds=30,
        )

    async def run(self, p: ParticipantConfig | None = None, prompt: str = "Q?") -> list:
        return [e async for e in self.adapter().run_turn(self.request(p, prompt))]


@pytest.fixture
def cli(tmp_path, monkeypatch, cli_processes) -> FakeCli:
    return FakeCli(tmp_path, monkeypatch)


def _alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


# --- plug-in, capabilities, options -------------------------------------------


def test_registered_as_gemini_with_web_access_and_streaming():
    adapter = get_adapter("gemini")
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.capabilities(participant()) == Capabilities(web_access=True, streaming=True)


def test_has_no_options():
    adapter = get_adapter("gemini")
    adapter.validate_options({})
    with pytest.raises(ValueError, match="yolo"):
        adapter.validate_options({"yolo": True})


# --- availability ---------------------------------------------------------------


async def test_available_when_installed_and_logged_in_with_google(cli):
    cli.log_in()
    assert await cli.adapter().check_availability(participant()) == Availability(True)


async def test_available_with_an_api_key(cli, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert (await cli.adapter().check_availability(participant())).available


async def test_api_key_in_the_gemini_env_file_counts(cli):
    (cli.home / ".gemini").mkdir(parents=True)
    (cli.home / ".gemini" / ".env").write_text("GEMINI_API_KEY=abc\n", encoding="utf-8")
    assert (await cli.adapter().check_availability(participant())).available


async def test_unavailable_when_not_logged_in(cli):
    result = await cli.adapter().check_availability(participant())
    assert not result.available and "log" in result.reason.lower()


async def test_unavailable_when_not_installed(cli):
    cli.log_in()
    adapter = GeminiAdapter(command=[str(cli.dir / "no-such-gemini.exe")], user_home=cli.home)
    result = await adapter.check_availability(participant())
    assert not result.available and "@google/gemini-cli" in result.reason


async def test_unavailable_when_the_cli_is_broken(cli):
    cli.log_in()
    cli.script(stderr="SyntaxError: bad node", exit=1)
    result = await cli.adapter().check_availability(participant())
    assert not result.available and "SyntaxError" in result.reason


async def test_unavailable_when_the_model_name_is_invalid(cli):
    cli.log_in()
    result = await cli.adapter().check_availability(participant(model="--yolo"))
    assert not result.available and "model" in result.reason


# --- a normal turn --------------------------------------------------------------


async def test_streams_assistant_chunks_then_completes_with_the_full_text(cli):
    cli.script(
        stream_lines(INIT, USER, assistant("Hello "), assistant("world.\nSTANCE: AGREE"), OK)
    )
    events = await cli.run()
    assert events == [
        Delta("Hello "),
        Delta("world.\nSTANCE: AGREE"),
        Completed("Hello world.\nSTANCE: AGREE"),
    ]


async def test_streams_before_the_process_finishes(cli):
    cli.script(
        stream_lines(assistant("first"), assistant(" second"), OK), line_delay=1.0, sleep=2.0
    )
    gen = cli.adapter().run_turn(cli.request())
    start = time.monotonic()
    assert await gen.__anext__() == Delta("first")
    assert time.monotonic() - start < 2.5  # the whole run takes over 4 s
    rest = [e async for e in gen]
    assert rest[-1] == Completed("first second")


async def test_non_delta_assistant_messages_and_noise_lines_are_handled(cli):
    out = "Loaded cached credentials.\n" + stream_lines(
        INIT,
        {
            "type": "tool_use",
            "timestamp": "t",
            "tool_name": "google_web_search",
            "tool_id": "1",
            "parameters": {},
        },
        {
            "type": "tool_result",
            "timestamp": "t",
            "tool_id": "1",
            "status": "success",
            "output": "...",
        },
        {"type": "error", "timestamp": "t", "severity": "warning", "message": "loop detected"},
        {"type": "message", "timestamp": "t", "role": "assistant", "content": "Full answer."},
        OK,
    )
    cli.script(out)
    assert await cli.run() == [Delta("Full answer."), Completed("Full answer.")]


async def test_runs_in_the_workspace_and_sends_the_prompt_on_stdin(cli):
    cli.script(stream_lines(INIT, assistant("ok"), OK))
    prompt = 'Line one\n第二行 with "quotes" & <brackets> %PATH%\n' + "x" * 40_000
    await cli.run(prompt=prompt)
    assert Path(cli.record["cwd"]).resolve() == cli.workspace.resolve()
    assert cli.record["stdin"] == prompt
    assert "--prompt" not in cli.record["argv"] and "-p" not in cli.record["argv"]


async def test_uses_the_participant_model_or_the_cli_default(cli):
    cli.script(stream_lines(assistant("ok"), OK))
    await cli.run(participant(model="gemini-2.5-flash"))
    argv = cli.record["argv"]
    assert argv[argv.index("--model") + 1] == "gemini-2.5-flash"
    await cli.run(participant())
    assert "--model" not in cli.record["argv"]


async def test_rejects_a_model_name_that_could_smuggle_flags(cli):
    events = await cli.run(participant(model="--yolo"))
    assert len(events) == 1 and isinstance(events[0], Failed) and events[0].kind == "unknown"
    assert not cli.record_path.exists()


# --- isolation (ADR 0002) -------------------------------------------------------


async def test_isolation_flags(cli):
    cli.script(stream_lines(assistant("ok"), OK))
    await cli.run()
    argv = cli.record["argv"]

    def value(flag):
        return argv[argv.index(flag) + 1]

    assert value("--output-format") == "stream-json"
    assert value("--approval-mode") == "default"
    assert value("--extensions") == "none"
    assert value("--allowed-mcp-server-names") == "__aigora_no_mcp__"
    for flag in ("--yolo", "-y", "--sandbox", "--include-directories", "--resume", "-r"):
        assert flag not in argv


async def test_system_settings_override_keeps_only_web_tools(cli):
    cli.script(stream_lines(assistant("ok"), OK))
    await cli.run()
    s = json.loads(cli.record["settings"])
    assert s["tools"]["core"] == ["google_web_search", "web_fetch"]
    assert {
        "run_shell_command",
        "read_file",
        "read_many_files",
        "list_directory",
        "glob",
        "grep_search",
        "write_file",
        "replace",
        "activate_skill",
        "read_mcp_resource",
        "list_mcp_resources",
        "save_memory",
    } <= set(s["tools"]["exclude"])
    assert s["mcp"]["allowed"] == ["__aigora_no_mcp__"]
    assert s["mcpServers"] == {}
    assert s["hooksConfig"]["enabled"] is False
    assert s["skills"]["enabled"] is False
    assert s["admin"]["extensions"]["enabled"] is False
    assert s["admin"]["mcp"]["enabled"] is False
    assert s["admin"]["skills"]["enabled"] is False
    assert s["experimental"]["enableAgents"] is False
    assert s["security"]["disableYoloMode"] is True
    assert s["general"]["checkpointing"]["enabled"] is False


async def test_admin_policy_denies_everything_but_web_tools(cli):
    cli.script(stream_lines(assistant("ok"), OK))
    await cli.run()
    rules = tomllib.loads(cli.record["policy"])["rule"]
    allowed = [r for r in rules if r["decision"] == "allow"]
    denied = [r for r in rules if r["decision"] == "deny"]
    assert sorted(r["toolName"] for r in allowed) == ["google_web_search", "web_fetch"]
    catch_all = [r for r in denied if r.get("toolName") == "*" and "mcpName" not in r]
    mcp_deny = [r for r in denied if r.get("mcpName") == "*"]
    assert catch_all and mcp_deny
    assert all(catch_all[0]["priority"] < r["priority"] < mcp_deny[0]["priority"] for r in allowed)


async def test_config_files_are_temporary_and_outside_the_workspace(cli):
    cli.script(stream_lines(assistant("ok"), OK))
    await cli.run()
    argv = cli.record["argv"]
    policy = Path(argv[argv.index("--admin-policy") + 1])
    assert cli.workspace.resolve() not in policy.resolve().parents
    assert not policy.exists()
    assert list(cli.workspace.iterdir()) == []


# --- failures -------------------------------------------------------------------


async def test_missing_cli_is_not_available(cli):
    adapter = GeminiAdapter(command=[str(cli.dir / "no-such-gemini.exe")], user_home=cli.home)
    events = [e async for e in adapter.run_turn(cli.request())]
    assert len(events) == 1 and events[0].kind == "not_available"


async def test_result_error_after_partial_output(cli):
    cli.script(
        stream_lines(
            assistant("half"),
            {
                "type": "result",
                "timestamp": "t",
                "status": "error",
                "error": {"type": "Error", "message": "boom"},
            },
        ),
        exit=1,
    )
    events = await cli.run()
    assert events == [Delta("half"), Failed("crashed", "gemini: boom")]


@pytest.mark.parametrize(
    ("message", "kind"),
    [
        ("[API Error: You exceeded your current quota. RESOURCE_EXHAUSTED (429)]", "quota"),
        ("Rate limit exceeded, status 429", "quota"),
        ("Please set an Auth method in your settings.json or specify GEMINI_API_KEY", "auth"),
        ("Failed to login. Message: invalid_grant", "auth"),
        ("API key not valid. Please pass a valid API key. (403 PERMISSION_DENIED)", "auth"),
        ("Unexpected end of input", "crashed"),
    ],
)
async def test_failure_kind_from_cli_error_text(cli, message, kind):
    cli.script(stderr=message, exit=1)
    events = await cli.run()
    assert len(events) == 1
    assert events[0].kind == kind
    assert message in events[0].reason


async def test_fatal_error_event_fails_the_turn(cli):
    cli.script(
        stream_lines(
            assistant("partial"),
            {
                "type": "error",
                "timestamp": "t",
                "severity": "error",
                "message": "Quota exceeded for model",
            },
        ),
        exit=1,
    )
    events = await cli.run()
    assert events[0] == Delta("partial")
    assert events[-1].kind == "quota" and "Quota exceeded" in events[-1].reason


async def test_exit_zero_without_a_result_is_crashed(cli):
    cli.script(stream_lines(assistant("cut off")))
    events = await cli.run()
    assert isinstance(events[-1], Failed) and events[-1].kind == "crashed"


async def test_input_error_exit_code_42(cli):
    cli.script(stderr="Unknown argument: frobnicate", exit=42)
    events = await cli.run()
    assert events[-1].kind == "unknown" and "Unknown argument" in events[-1].reason


async def test_turn_limit_exit_code_53(cli):
    cli.script(exit=53)
    events = await cli.run()
    assert events[-1].kind == "unknown" and "turn limit" in events[-1].reason


# --- cancellation ---------------------------------------------------------------


async def test_closing_the_stream_kills_the_cli(cli, tmp_path, monkeypatch):
    pidfile = tmp_path / "pid"
    monkeypatch.setenv("FAKE_GEMINI_PIDFILE", str(pidfile))
    cli.script(stream_lines(assistant("thinking...")), sleep=60)
    gen = cli.adapter().run_turn(cli.request())
    assert await gen.__anext__() == Delta("thinking...")
    await gen.aclose()
    assert not _alive(int(pidfile.read_text()))


async def test_cancelling_the_task_kills_the_cli(cli, tmp_path, monkeypatch):
    pidfile = tmp_path / "pid"
    monkeypatch.setenv("FAKE_GEMINI_PIDFILE", str(pidfile))
    cli.script(sleep=60)
    adapter = cli.adapter()

    async def consume():
        return [e async for e in adapter.run_turn(cli.request())]

    task = asyncio.create_task(consume())
    for _ in range(200):
        if pidfile.exists():
            break
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not _alive(int(pidfile.read_text()))
