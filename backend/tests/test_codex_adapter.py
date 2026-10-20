"""`codex` adapter, tested through its public interface against a scripted fake CLI."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from aigora.adapters import codex
from aigora.adapters.base import Completed, Delta, Failed, ModelOption, TurnRequest
from aigora.adapters.codex import CodexAdapter
from aigora.config import ParticipantConfig

FAKE_CLI = Path(__file__).with_name("fake_codex_cli.py")


def participant(model: str | None = None, **options) -> ParticipantConfig:
    return ParticipantConfig(id="codex", display_name="Codex", adapter="codex", model=model, options=options)


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    """Returns `script(**scenario) -> CodexAdapter` running the fake CLI with that scenario."""

    def script(**scenario) -> CodexAdapter:
        path = tmp_path / "scenario.json"
        path.write_text(json.dumps(scenario), encoding="utf-8")
        monkeypatch.setenv("AIGORA_FAKE_CODEX_SCENARIO", str(path))
        return CodexAdapter(command=[sys.executable, str(FAKE_CLI)])

    return script


def request(workspace: Path, prompt: str = "Q?", p: ParticipantConfig | None = None) -> TurnRequest:
    return TurnRequest(participant=p or participant(), prompt=prompt, workspace=workspace, timeout_seconds=30)


async def run(adapter: CodexAdapter, req: TurnRequest) -> list:
    return [event async for event in adapter.run_turn(req)]


def message(item_id: str, text: str, kind: str = "item.completed") -> dict:
    return {"type": kind, "item": {"id": item_id, "type": "agent_message", "text": text}}


def test_codex_participants_can_search_the_web_and_stream():
    caps = CodexAdapter().capabilities(participant())
    assert caps.web_access is True
    assert caps.streaming is True


async def test_reply_streams_as_deltas_then_completes_with_the_full_text(fake_cli, tmp_path):
    adapter = fake_cli(events=[
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"id": "r0", "type": "reasoning", "text": "thinking..."}},
        message("m1", "Hello", kind="item.updated"),
        message("m1", "Hello world"),
        {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 2}},
    ])
    events = await run(adapter, request(tmp_path))
    assert events == [Delta("Hello"), Delta(" world"), Completed("Hello world")]


async def test_runs_isolated_in_the_workspace_with_the_prompt_on_stdin(fake_cli, tmp_path):
    record = tmp_path / "record.json"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    adapter = fake_cli(record=str(record), events=[message("m1", "ok")])
    prompt = "討論內容 with \"quotes\" & <symbols>\nline two"

    events = await run(adapter, request(workspace, prompt=prompt, p=participant(model="gpt-5.5")))

    assert events[-1] == Completed("ok")
    seen = json.loads(record.read_text(encoding="utf-8"))
    argv = seen["argv"]
    assert Path(seen["cwd"]).resolve() == workspace.resolve()
    assert seen["stdin"] == prompt
    assert argv[:2] == ["exec", "--json"] and argv[-1] == "-"
    for flag in ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check"):
        assert flag in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert Path(argv[argv.index("--cd") + 1]).resolve() == workspace.resolve()
    assert argv[argv.index("--model") + 1] == "gpt-5.5"
    assert 'web_search="live"' in argv
    disabled = {argv[i + 1] for i, a in enumerate(argv) if a == "--disable"}
    assert disabled == {
        "shell_tool", "unified_exec", "view_image", "browser_use", "browser_use_external", "computer_use",
        "apps", "plugins", "multi_agent", "multi_agent_v2", "image_generation", "hooks", "in_app_browser",
        "skill_search", "workspace_dependencies",
    }
    assert "code_mode_host" not in argv  # disabling it breaks web search (ADR 0002)


async def test_default_model_passes_no_model_flag(fake_cli, tmp_path):
    record = tmp_path / "record.json"
    await run(fake_cli(record=str(record), events=[message("m1", "ok")]), request(tmp_path))
    assert "--model" not in json.loads(record.read_text(encoding="utf-8"))["argv"]


async def test_several_agent_messages_are_joined_and_streamed_consistently(fake_cli, tmp_path):
    adapter = fake_cli(events=[
        message("m1", "Let me search."),
        {"type": "item.completed", "item": {"id": "w1", "type": "web_search", "query": "x"}},
        "not json at all",
        message("m2", "Answer.\nSTANCE: AGREE"),
        {"type": "turn.completed"},
    ])
    events = await run(adapter, request(tmp_path))
    final = events[-1]
    assert final == Completed("Let me search.\n\nAnswer.\nSTANCE: AGREE")
    assert "".join(e.text for e in events if isinstance(e, Delta)) == final.text


async def test_available_when_installed_and_logged_in(fake_cli):
    adapter = fake_cli(login_status={"stdout": "Logged in using ChatGPT", "exit": 0})
    assert (await adapter.check_availability(participant())).available is True


async def test_unavailable_when_not_logged_in(fake_cli):
    adapter = fake_cli(login_status={"stdout": "Not logged in", "exit": 1})
    result = await adapter.check_availability(participant())
    assert result.available is False
    assert "not logged in" in result.reason.lower()


async def test_unavailable_when_the_cli_is_not_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))  # nothing named codex here
    adapter = CodexAdapter()
    result = await adapter.check_availability(participant())
    assert result.available is False
    assert "not found" in result.reason
    events = await run(adapter, request(tmp_path))
    assert len(events) == 1 and events[0].kind == "not_available" and "not found" in events[0].reason


async def test_unavailable_when_the_cli_cannot_start(tmp_path):
    adapter = CodexAdapter(command=[str(tmp_path / "missing-codex.exe")])
    assert (await adapter.check_availability(participant())).available is False
    events = await run(adapter, request(tmp_path))
    assert len(events) == 1 and events[0].kind == "not_available"


@pytest.mark.parametrize(
    ("scenario", "kind"),
    [
        ({"events": [{"type": "error", "message": "unexpected status 401 Unauthorized"}], "exit": 1}, "auth"),
        ({"stderr": "Error: Not logged in. Run `codex login`.", "exit": 1}, "auth"),
        ({"events": [{"type": "turn.failed", "error": {"message": "You've hit your usage limit. Try again later."}}],
          "exit": 1}, "quota"),
        ({"events": [{"type": "error", "message": "exceeded retry limit, last status: 429 Too Many Requests"}],
          "exit": 1}, "quota"),
        ({"events": [message("m1", "Half an ans", kind="item.updated")], "stderr": "panicked at core/src/x.rs",
          "exit": 101}, "crashed"),
        ({"exit": 3}, "crashed"),
    ],
)
async def test_failures_are_classified(fake_cli, tmp_path, scenario, kind):
    events = await run(fake_cli(**scenario), request(tmp_path))
    final = events[-1]
    assert isinstance(final, Failed)
    assert final.kind == kind
    assert final.reason.startswith("codex: ")
    assert all(isinstance(e, Delta) for e in events[:-1])


async def test_a_run_without_any_reply_is_a_failure(fake_cli, tmp_path):
    events = await run(fake_cli(events=[{"type": "turn.completed"}]), request(tmp_path))
    assert len(events) == 1 and events[0].kind == "unknown"


async def wait_for_heartbeat(heartbeat: Path) -> None:
    for _ in range(200):
        if heartbeat.exists() and heartbeat.stat().st_size > 2:
            return
        await asyncio.sleep(0.05)
    pytest.fail("fake CLI grandchild never started")


async def assert_heartbeat_stopped(heartbeat: Path) -> None:
    await asyncio.sleep(0.3)
    size = heartbeat.stat().st_size
    await asyncio.sleep(0.5)
    assert heartbeat.stat().st_size == size, "a CLI process is still running after cancellation"


async def test_closing_a_turn_kills_the_cli_and_its_children(fake_cli, tmp_path):
    heartbeat = tmp_path / "heartbeat.txt"
    adapter = fake_cli(events=[message("m1", "Thinking", kind="item.updated")], hang=True,
                       heartbeat=str(heartbeat))
    turn = adapter.run_turn(request(tmp_path))
    assert await anext(turn) == Delta("Thinking")
    await wait_for_heartbeat(heartbeat)

    await turn.aclose()  # what the engine does on stop

    await assert_heartbeat_stopped(heartbeat)


async def test_cancelling_the_task_kills_the_cli_and_its_children(fake_cli, tmp_path):
    heartbeat = tmp_path / "heartbeat.txt"
    adapter = fake_cli(events=[], hang=True, heartbeat=str(heartbeat))

    async def consume():
        async for _ in adapter.run_turn(request(tmp_path)):
            pass

    task = asyncio.create_task(consume())
    await wait_for_heartbeat(heartbeat)
    task.cancel()  # what the engine does on timeout
    with pytest.raises(asyncio.CancelledError):
        await task

    await assert_heartbeat_stopped(heartbeat)


def test_codex_has_no_options_yet():
    adapter = CodexAdapter()
    adapter.validate_options({})
    with pytest.raises(ValueError, match="sandbox"):
        adapter.validate_options({"sandbox": "danger-full-access"})


def test_registry_returns_the_codex_adapter():
    from aigora.adapters.base import get_adapter

    assert isinstance(get_adapter("codex"), CodexAdapter)



def catalog_entry(slug: str, priority: int, visibility: str = "list") -> dict:
    return {"slug": slug, "display_name": slug.upper(), "visibility": visibility, "priority": priority,
            "supported_in_api": True}


async def test_model_list_is_the_listed_catalog_models_by_priority_and_allows_free_text(fake_cli):
    catalog = {"models": [catalog_entry("gpt-b", 5), catalog_entry("gpt-hidden", 1, visibility="hide"),
                          catalog_entry("gpt-a", 2)]}
    adapter = fake_cli(debug_models={"stdout": json.dumps(catalog)})

    choices = await adapter.list_models(participant())

    assert choices.models == (ModelOption("gpt-a", "GPT-A"), ModelOption("gpt-b", "GPT-B"))
    assert choices.free_text is True
    assert choices.error is None


async def test_model_list_reports_why_when_the_cli_is_missing(monkeypatch):
    monkeypatch.setattr(codex.shutil, "which", lambda name: None)

    choices = await CodexAdapter().list_models(participant())

    assert choices.models == ()
    assert choices.free_text is True
    assert "not found" in choices.error


@pytest.mark.parametrize(
    ("debug_models", "expected"),
    [
        ({"stdout": "not json"}, "unreadable"),
        ({"stdout": json.dumps({"no_models": []})}, "unreadable"),
        ({"stderr": "config.toml: key with no value", "exit": 1}, "config.toml: key with no value"),
    ],
)
async def test_model_list_reports_unreadable_output_and_cli_errors(fake_cli, debug_models, expected):
    choices = await fake_cli(debug_models=debug_models).list_models(participant())

    assert choices.models == ()
    assert expected in choices.error


async def test_model_list_gives_up_after_the_timeout(fake_cli, monkeypatch):
    monkeypatch.setattr(codex, "_MODELS_TIMEOUT_SECONDS", 0.5)
    adapter = fake_cli(debug_models={"hang": True})

    choices = await asyncio.wait_for(adapter.list_models(participant()), timeout=10)

    assert choices.models == ()
    assert "did not answer" in choices.error
