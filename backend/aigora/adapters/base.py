"""The Adapter contract. Every adapter module implements this; the core uses nothing else.

How an adapter module plugs in (the registry in `registry.py` is frozen):

    # aigora/adapters/<id>.py
    class MyAdapter(Adapter):
        id = "<id>"
        ...

    def create_adapter() -> Adapter:
        return MyAdapter()

The core then gets it with `get_adapter("<id>")`.

Rules every adapter follows (spec "Adapter 介面", ADR 0001 / 0002):

- `run_turn` is an async generator: zero or more `Delta` (streaming adapters
  only), then exactly one `Completed` or `Failed`, then it returns. Expected
  failures (CLI missing, not logged in, quota, crash) are yielded as
  `Failed`, not raised.
- Cancellation (stop or timeout) arrives as `asyncio.CancelledError` /
  generator close; the adapter must terminate its subprocess before
  re-raising. The engine enforces `timeout_seconds` by cancelling and
  reports `kind="timeout"` itself; an adapter may also yield
  `Failed("timeout", ...)` if it detects one.
- Stateless: `prompt` is the full discussion every time; never use CLI resume.
- Isolation (ADR 0002): run inside `workspace`, disable every local tool
  (shell, file read/write, MCP, plugins, hooks, skills), ignore the user's own
  CLI config, keep only web search/fetch tools.
- Adapters never build prompts, parse stances or judge consensus.
- `list_models` (like `check_availability`) must not spend quota; expected
  failures go into `ModelChoices.error`, not raised.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from aigora.adapters import registry
from aigora.domain import FAILURE_KINDS, TURN_PURPOSES, FailureKind, TurnPurpose

if TYPE_CHECKING:
    from aigora.config import ParticipantConfig

__all__ = [
    "FAILURE_KINDS",
    "TURN_PURPOSES",
    "FailureKind",
    "TurnPurpose",
    "Capabilities",
    "Availability",
    "ModelOption",
    "ModelChoices",
    "TurnRequest",
    "Delta",
    "Completed",
    "Failed",
    "AdapterEvent",
    "Adapter",
    "get_adapter",
]


@dataclass(frozen=True)
class Capabilities:
    web_access: bool
    streaming: bool


@dataclass(frozen=True)
class Availability:
    available: bool
    reason: str | None = None  # why it is unavailable (shown in the participant picker)


@dataclass(frozen=True)
class ModelOption:
    id: str  # passed as the participant's `model`
    label: str  # shown in the model picker


@dataclass(frozen=True)
class ModelChoices:
    """The models a participant can be switched to (spec "參與者與模型選擇")."""

    models: tuple[ModelOption, ...] = ()
    free_text: bool = False  # may the user type a model name that is not in `models`?
    error: str | None = None  # why the list could not be loaded (then `models` is empty)


@dataclass(frozen=True)
class TurnRequest:
    """One turn (發言請求): everything an adapter needs to answer once."""

    participant: ParticipantConfig  # model, display name, persona, adapter-specific `options`
    prompt: str  # full text built by the Prompt Builder
    workspace: Path  # empty temp folder to run in
    timeout_seconds: float
    round: int = 1  # 1-based round number this call belongs to
    purpose: TurnPurpose = "turn"


@dataclass(frozen=True)
class Delta:
    """A new piece of text, appended to what was streamed so far."""

    text: str


@dataclass(frozen=True)
class Completed:
    """The full text of the turn."""

    text: str


@dataclass(frozen=True)
class Failed:
    kind: FailureKind
    reason: str


AdapterEvent = Delta | Completed | Failed


class Adapter(ABC):
    id: ClassVar[str]

    @abstractmethod
    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        """What this participant can do. Constant for most adapters."""

    @abstractmethod
    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        """Is the CLI installed / logged in / the model present? Must not spend quota."""

    @abstractmethod
    def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        """Run one turn. Implement as `async def run_turn(...)` with `yield`."""

    async def list_models(self, participant: ParticipantConfig) -> ModelChoices:
        """Models this participant can use instead of its configured one. Must not spend quota.

        Default: no list and no free-text model.
        """
        return ModelChoices()

    def validate_options(self, options: Mapping[str, Any]) -> None:
        """Raise ValueError if the participant's `options` table is invalid.

        Called while loading `participants.toml`, so mistakes fail at startup.
        """


def get_adapter(adapter_id: str) -> Adapter:
    """Look up an adapter by identifier (raises `registry.UnknownAdapterError`)."""
    return registry.load_module(adapter_id).create_adapter()
