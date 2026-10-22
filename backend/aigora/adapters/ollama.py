"""`ollama` adapter: a local Ollama model through Ollama's HTTP API.

    [[participant]]
    id = "ollama"
    display_name = "Ollama"
    adapter = "ollama"
    model = "llama3.2"          # required; `llama3.2` matches `llama3.2:latest`
    [participant.options]
    base_url = "http://127.0.0.1:11434"   # optional, this is the default

Ollama has no tools, so isolation (ADR 0002) needs nothing extra and
`web_access` is false. Each turn is one streamed `POST /api/generate` with
the full prompt (stateless, no `context`). Availability = `GET /api/tags`
lists the model; the model picker lists every model in it. Failure kinds: not running / model missing / no model ->
not_available; httpx timeout -> timeout; HTTP error, `error` line in the
stream, bad stream, dropped connection -> crashed. Cancelling the turn closes
the HTTP connection, which stops Ollama's generation.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from aigora.adapters.base import (
    Adapter,
    AdapterEvent,
    Availability,
    Capabilities,
    Completed,
    Delta,
    Failed,
    ModelChoices,
    ModelOption,
    TurnRequest,
)
from aigora.config import ParticipantConfig

DEFAULT_BASE_URL = "http://127.0.0.1:11434"


def _name_variants(model: str) -> set[str]:
    """Ollama lists `llama3.2` as `llama3.2:latest`; accept either spelling."""
    return {model, model if ":" in model else f"{model}:latest"}


def _error_text(raw: bytes) -> str:
    """Ollama error bodies are `{"error": "..."}`; fall back to the raw text."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])
    except ValueError:
        pass
    return raw.decode(errors="replace").strip()[:500] or "(empty body)"


class OllamaAdapter(Adapter):
    id = "ollama"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    def _base_url(self, participant: ParticipantConfig) -> str:
        return participant.options.get("base_url", DEFAULT_BASE_URL).rstrip("/")

    def _client(self, participant: ParticipantConfig, timeout: httpx.Timeout) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url(participant), transport=self._transport, timeout=timeout
        )

    def validate_options(self, options: Mapping[str, Any]) -> None:
        unknown = sorted(set(options) - {"base_url"})
        if unknown:
            raise ValueError(f"unknown ollama option(s): {', '.join(unknown)}")
        if "base_url" in options:
            url = options["base_url"]
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise ValueError(
                    "`base_url` must be an http:// or https:// URL, e.g. http://127.0.0.1:11434"
                )

    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        return Capabilities(web_access=False, streaming=True)

    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        base = self._base_url(participant)
        model = participant.model
        if not model:
            return Availability(
                False, "ollama: no model configured; set `model` in participants.toml"
            )
        try:
            async with self._client(participant, httpx.Timeout(5.0)) as client:
                response = await client.get("/api/tags")
        except httpx.TransportError:
            return Availability(False, f"Ollama is not running at {base}")
        if response.status_code != 200:
            return Availability(False, f"Ollama at {base} answered HTTP {response.status_code}")
        try:
            names = {m.get("name") for m in response.json().get("models", [])}
        except (ValueError, AttributeError):
            return Availability(False, f"Ollama at {base} sent an unexpected model list")
        if not names & _name_variants(model):
            return Availability(
                False, f"Ollama model `{model}` is not installed (run `ollama pull {model}`)"
            )
        return Availability(True)

    async def list_models(self, participant: ParticipantConfig) -> ModelChoices:
        """Installed models (`GET /api/tags`). No free text: a model that is not pulled always fails."""
        base = self._base_url(participant)
        try:
            async with self._client(participant, httpx.Timeout(5.0)) as client:
                response = await client.get("/api/tags")
        except httpx.TransportError:
            return ModelChoices(error=f"Ollama is not running at {base}")
        if response.status_code != 200:
            return ModelChoices(error=f"Ollama at {base} answered HTTP {response.status_code}")
        try:
            models = []
            for entry in response.json()["models"]:
                name = entry["name"]
                size = (entry.get("details") or {}).get("parameter_size")
                models.append(ModelOption(name, f"{name} ({size})" if size else name))
        except (ValueError, KeyError, TypeError, AttributeError):
            return ModelChoices(error=f"Ollama at {base} sent an unexpected model list")
        return ModelChoices(models=tuple(models))

    async def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        participant = request.participant
        base = self._base_url(participant)
        if not participant.model:
            yield Failed(
                "not_available", "ollama: no model configured; set `model` in participants.toml"
            )
            return
        body = {"model": participant.model, "prompt": request.prompt, "stream": True}
        timeout = httpx.Timeout(request.timeout_seconds, connect=5.0)
        parts: list[str] = []
        try:
            # Leaving these `async with` blocks (also on cancellation / generator
            # close) closes the HTTP connection, which makes Ollama stop generating.
            async with self._client(participant, timeout) as client:
                async with client.stream("POST", "/api/generate", json=body) as response:
                    if response.status_code != 200:
                        error = _error_text(await response.aread())
                        kind = "not_available" if response.status_code == 404 else "crashed"
                        yield Failed(kind, f"Ollama answered HTTP {response.status_code}: {error}")
                        return
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except ValueError:
                            yield Failed(
                                "crashed", f"Ollama sent an unreadable stream line: {line[:200]!r}"
                            )
                            return
                        if not isinstance(chunk, dict):
                            yield Failed(
                                "crashed", f"Ollama sent an unexpected stream line: {line[:200]!r}"
                            )
                            return
                        if chunk.get("error"):
                            yield Failed("crashed", f"Ollama error: {chunk['error']}")
                            return
                        text = chunk.get("response") or ""
                        if text:
                            parts.append(text)
                            yield Delta(text)
                        if chunk.get("done"):
                            yield Completed("".join(parts))
                            return
        except httpx.ConnectError:
            yield Failed("not_available", f"Ollama is not running at {base}")
            return
        except httpx.TimeoutException as exc:
            yield Failed("timeout", f"Ollama did not answer in time ({type(exc).__name__})")
            return
        except httpx.HTTPError as exc:
            yield Failed("crashed", f"Ollama connection failed: {type(exc).__name__}: {exc}")
            return
        yield Failed("crashed", "Ollama stream ended before the reply was done")


def create_adapter() -> Adapter:
    return OllamaAdapter()
