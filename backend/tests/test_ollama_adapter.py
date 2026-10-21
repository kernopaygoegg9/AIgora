"""Ollama Adapter against a fake Ollama HTTP API (httpx.MockTransport)."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from aigora.adapters.base import (
    Availability,
    Capabilities,
    Completed,
    Delta,
    Failed,
    ModelOption,
    TurnRequest,
    get_adapter,
)
from aigora.adapters.ollama import OllamaAdapter
from aigora.config import ConfigError, ParticipantConfig, load_participants

BASE = "http://ollama.test:11434"


def participant(model: str | None = "llama3.2", **options) -> ParticipantConfig:
    options.setdefault("base_url", BASE)
    return ParticipantConfig(id="ollama", display_name="Ollama", adapter="ollama", model=model, options=options)


def adapter(handler) -> OllamaAdapter:
    return OllamaAdapter(transport=httpx.MockTransport(handler))


def tags(*names: str):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET" and req.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": n, "model": n} for n in names]})

    return handler


def not_running(req: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=req)


async def test_unavailable_with_reason_when_ollama_is_not_running():
    result = await adapter(not_running).check_availability(participant())
    assert result.available is False
    assert BASE in result.reason


async def test_unavailable_with_reason_when_the_model_is_not_pulled():
    result = await adapter(tags("qwen3:8b")).check_availability(participant(model="llama3.2"))
    assert result.available is False
    assert "llama3.2" in result.reason


async def test_available_when_the_model_is_present_with_or_without_tag():
    a = adapter(tags("llama3.2:latest", "qwen3:8b"))
    assert await a.check_availability(participant(model="llama3.2")) == Availability(True)
    assert await a.check_availability(participant(model="qwen3:8b")) == Availability(True)


async def test_unavailable_when_no_model_is_configured():
    result = await adapter(tags("llama3.2:latest")).check_availability(participant(model=None))
    assert result.available is False
    assert "model" in result.reason


async def test_unavailable_when_the_server_answers_with_an_error():
    result = await adapter(lambda req: httpx.Response(500, text="boom")).check_availability(participant())
    assert result.available is False
    assert "500" in result.reason


def test_declares_no_web_access_and_streaming():
    assert OllamaAdapter().capabilities(participant()) == Capabilities(web_access=False, streaming=True)


def request(p: ParticipantConfig | None = None, prompt: str = "Q?") -> TurnRequest:
    return TurnRequest(participant=p or participant(), prompt=prompt, workspace=Path("."), timeout_seconds=5)


def ndjson(*chunks: dict) -> bytes:
    return b"".join(json.dumps(c).encode() + b"\n" for c in chunks)


async def run(a: OllamaAdapter, req: TurnRequest | None = None) -> list:
    return [event async for event in a.run_turn(req or request())]


async def test_streams_deltas_then_completed_with_the_full_text():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        body = ndjson(
            {"model": "llama3.2", "response": "Hello", "done": False},
            {"model": "llama3.2", "response": ", world", "done": False},
            {"model": "llama3.2", "response": "", "done": True, "done_reason": "stop"},
        )
        return httpx.Response(200, content=body)

    events = await run(adapter(handler), request(prompt="Say hello"))
    assert events == [Delta("Hello"), Delta(", world"), Completed("Hello, world")]
    assert seen["path"] == "/api/generate"
    assert seen["body"]["model"] == "llama3.2"
    assert seen["body"]["prompt"] == "Say hello"
    assert seen["body"]["stream"] is True


def only_failure(events) -> Failed:
    assert isinstance(events[-1], Failed), events
    assert not any(isinstance(e, Completed) for e in events)
    return events[-1]


async def test_fails_as_not_available_when_ollama_is_not_running():
    failed = only_failure(await run(adapter(not_running)))
    assert failed.kind == "not_available"
    assert BASE in failed.reason


async def test_fails_as_not_available_when_the_model_is_missing():
    handler = lambda req: httpx.Response(404, json={"error": "model 'llama3.2' not found"})  # noqa: E731
    failed = only_failure(await run(adapter(handler)))
    assert failed.kind == "not_available"
    assert "not found" in failed.reason


async def test_fails_as_not_available_without_calling_ollama_when_no_model_is_configured():
    def handler(req):
        raise AssertionError("must not call Ollama")

    failed = only_failure(await run(adapter(handler), request(participant(model=None))))
    assert failed.kind == "not_available"


async def test_server_error_status_fails_as_crashed_with_the_error_text():
    handler = lambda req: httpx.Response(500, json={"error": "out of memory"})  # noqa: E731
    failed = only_failure(await run(adapter(handler)))
    assert failed.kind == "crashed"
    assert "out of memory" in failed.reason


async def test_error_in_the_middle_of_the_stream_fails_as_crashed_after_the_partial_text():
    body = ndjson({"response": "Half", "done": False}, {"error": "runner terminated"})
    events = await run(adapter(lambda req: httpx.Response(200, content=body)))
    assert events[0] == Delta("Half")
    failed = only_failure(events)
    assert failed.kind == "crashed"
    assert "runner terminated" in failed.reason


async def test_stream_ending_without_done_fails_as_crashed():
    body = ndjson({"response": "Half", "done": False})
    assert only_failure(await run(adapter(lambda req: httpx.Response(200, content=body)))).kind == "crashed"


async def test_malformed_stream_line_fails_as_crashed():
    body = b'{"response": "ok", "done": false}\nnot json\n'
    assert only_failure(await run(adapter(lambda req: httpx.Response(200, content=body)))).kind == "crashed"


async def test_read_timeout_fails_as_timeout():
    def handler(req):
        raise httpx.ReadTimeout("timed out", request=req)

    assert only_failure(await run(adapter(handler))).kind == "timeout"


async def test_connection_dropped_mid_request_fails_as_crashed():
    def handler(req):
        raise httpx.RemoteProtocolError("peer closed connection", request=req)

    assert only_failure(await run(adapter(handler))).kind == "crashed"


def test_registered_as_the_ollama_adapter():
    assert isinstance(get_adapter("ollama"), OllamaAdapter)


def test_accepts_a_base_url_option():
    OllamaAdapter().validate_options({})
    OllamaAdapter().validate_options({"base_url": "http://127.0.0.1:11434"})


@pytest.mark.parametrize(
    "options",
    [{"base_url": 11434}, {"base_url": "127.0.0.1:11434"}, {"host": "http://127.0.0.1:11434"}],
)
def test_rejects_invalid_options(options):
    with pytest.raises(ValueError):
        OllamaAdapter().validate_options(options)


def test_bad_options_fail_while_loading_participants_toml(tmp_path):
    path = tmp_path / "participants.toml"
    path.write_text(
        '[[participant]]\nid = "o"\ndisplay_name = "O"\nadapter = "ollama"\nmodel = "llama3.2"\n'
        '[participant.options]\nbase_url = "localhost"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_participants(path)


class HangingStream(httpx.AsyncByteStream):
    """Sends one chunk, then hangs like a model still generating; records when it is closed."""

    def __init__(self):
        self.closed = False

    async def __aiter__(self):
        yield ndjson({"response": "Thinking", "done": False})
        await asyncio.Event().wait()

    async def aclose(self):
        self.closed = True


async def test_cancelling_a_turn_closes_the_connection_to_ollama():
    stream = HangingStream()
    a = adapter(lambda req: httpx.Response(200, stream=stream))
    first_delta = asyncio.Event()
    seen = []

    async def consume():
        async for event in a.run_turn(request()):
            seen.append(event)
            first_delta.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(first_delta.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert seen == [Delta("Thinking")]
    assert stream.closed


async def test_closing_the_turn_early_closes_the_connection_to_ollama():
    stream = HangingStream()
    turn = adapter(lambda req: httpx.Response(200, stream=stream)).run_turn(request())
    assert await anext(turn) == Delta("Thinking")
    await turn.aclose()
    assert stream.closed



async def test_model_list_is_the_installed_models_with_their_size_and_no_free_text():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET" and req.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [
            {"name": "qwen3:8b", "model": "qwen3:8b", "details": {"parameter_size": "8.2B", "family": "qwen3"}},
            {"name": "custom:latest", "model": "custom:latest"},
        ]})

    choices = await adapter(handler).list_models(participant())

    assert choices.models == (ModelOption("qwen3:8b", "qwen3:8b (8.2B)"), ModelOption("custom:latest", "custom:latest"))
    assert choices.free_text is False
    assert choices.error is None


async def test_model_list_reports_why_when_ollama_is_not_running():
    choices = await adapter(not_running).list_models(participant())

    assert choices.models == ()
    assert BASE in choices.error


@pytest.mark.parametrize(
    "response", [httpx.Response(500, text="boom"), httpx.Response(200, text="not json"), httpx.Response(200, json={})]
)
async def test_model_list_reports_bad_answers(response):
    choices = await adapter(lambda req: response).list_models(participant())

    assert choices.models == ()
    assert choices.error
