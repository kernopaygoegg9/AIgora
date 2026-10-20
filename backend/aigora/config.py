"""Settings loading (設定載入): `participants.toml`.

`load_participants(path)` reads and validates the file and fills in defaults.
Any problem raises `ConfigError` naming the file and line, so the app refuses
to start. Validation: required fields present, ids unique, adapter
registered, adapter `options` accepted by the adapter, default moderator
exists, default values in range. `persona` is reserved: v1 ignores it and logs
a note.
"""

from __future__ import annotations

import logging
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aigora.adapters import registry
from aigora.domain import JUDGE_IDS, MODE_IDS, SPEAKING_ORDER_IDS, JudgeId, ModeId, SpeakingOrderId

log = logging.getLogger("aigora.config")

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    def __init__(self, path: Path | str, line: int | None, message: str):
        self.path = Path(path)
        self.line = line
        self.message = message
        where = f"{self.path}:{line}" if line is not None else f"{self.path}"
        super().__init__(f"{where}: {message}")


@dataclass(frozen=True)
class ParticipantConfig:
    id: str
    display_name: str  # also the name other participants see in the discussion
    adapter: str  # adapter identifier, see adapters/registry.py
    model: str | None = None  # None: the adapter's default model
    avatar: str = ""  # filename under assets/avatars/; loader fills "<adapter>.png" when omitted
    enabled: bool = True  # False: hidden from the participant picker
    persona: str | None = None  # reserved; ignored in v1
    options: dict[str, Any] = field(default_factory=dict)  # adapter-specific options

    def __post_init__(self) -> None:
        if not self.avatar:
            object.__setattr__(self, "avatar", f"{self.adapter}.png")


@dataclass(frozen=True)
class Defaults:
    mode: ModeId = "ask"
    judge: JudgeId = "stance_vote"
    speaking_order: SpeakingOrderId = "parallel"
    moderator: str = ""  # participant id; loader fills the first participant when omitted
    max_rounds: int = 15
    turn_timeout_seconds: float = 300
    jev_threshold: float = 0.8


@dataclass(frozen=True)
class ParticipantsConfig:
    defaults: Defaults
    participants: list[ParticipantConfig]

    def enabled_participants(self) -> list[ParticipantConfig]:
        return [p for p in self.participants if p.enabled]

    def get(self, participant_id: str) -> ParticipantConfig:
        for p in self.participants:
            if p.id == participant_id:
                return p
        raise KeyError(participant_id)


def participants_file_path() -> Path:
    """`AIGORA_PARTICIPANTS_FILE` (relative paths are against the repo root), else `participants.toml`."""
    raw = os.environ.get("AIGORA_PARTICIPANTS_FILE", "participants.toml")
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


# --- loading -----------------------------------------------------------------

_PARTICIPANT_HEADER = re.compile(r"^\s*\[\[\s*participant\s*\]\]")
_TABLE_HEADER = re.compile(r"^\s*\[")
_TOML_ERROR_LINE = re.compile(r"line (\d+)")


class _Lines:
    """Finds the source line of a key, since tomllib does not report positions."""

    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.participant_headers = [i for i, line in enumerate(self.lines) if _PARTICIPANT_HEADER.match(line)]

    def _find_key(self, start: int, end: int, key: str) -> int | None:
        pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
        for i in range(start, end):
            if pattern.match(self.lines[i]):
                return i + 1
        return None

    def defaults_key(self, key: str) -> int | None:
        for i, line in enumerate(self.lines):
            if re.match(r"^\s*\[\s*defaults\s*\]", line):
                end = next((j for j in range(i + 1, len(self.lines)) if _TABLE_HEADER.match(self.lines[j])),
                           len(self.lines))
                return self._find_key(i + 1, end, key) or i + 1
        return None

    def participant(self, index: int) -> int | None:
        if index < len(self.participant_headers):
            return self.participant_headers[index] + 1
        return None

    def participant_key(self, index: int, key: str) -> int | None:
        if index >= len(self.participant_headers):
            return None
        start = self.participant_headers[index] + 1
        end = next((j for j in range(start, len(self.lines)) if _TABLE_HEADER.match(self.lines[j])), len(self.lines))
        return self._find_key(start, end, key) or start


def load_participants(path: Path | str) -> ParticipantsConfig:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(path, None, f"cannot read participants file: {exc}") from None
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        m = _TOML_ERROR_LINE.search(str(exc))
        raise ConfigError(path, int(m.group(1)) if m else None, f"invalid TOML: {exc}") from None

    lines = _Lines(text)

    def fail(line: int | None, message: str) -> ConfigError:
        return ConfigError(path, line, message)

    raw_participants = data.get("participant", [])
    if not isinstance(raw_participants, list) or not raw_participants:
        raise fail(None, "no [[participant]] defined")

    participants: list[ParticipantConfig] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_participants):
        participants.append(_participant(raw, index, seen, lines, fail))

    defaults = _defaults(data.get("defaults", {}), participants, lines, fail)
    return ParticipantsConfig(defaults=defaults, participants=participants)


def _participant(raw: dict[str, Any], index: int, seen: set[str], lines: _Lines, fail) -> ParticipantConfig:
    header = lines.participant(index)

    def key_line(key: str) -> int | None:
        return lines.participant_key(index, key)

    known = {"id", "display_name", "adapter", "model", "avatar", "enabled", "persona", "options"}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise fail(key_line(unknown[0]), f"unknown participant field(s): {', '.join(unknown)}")
    for key in ("id", "display_name", "adapter"):
        if key not in raw:
            raise fail(header, f"participant is missing required field `{key}`")
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise fail(key_line(key), f"`{key}` must be a non-empty string")
    for key in ("model", "avatar", "persona"):
        if key in raw and not isinstance(raw[key], str):
            raise fail(key_line(key), f"`{key}` must be a string")
    if "enabled" in raw and not isinstance(raw["enabled"], bool):
        raise fail(key_line("enabled"), "`enabled` must be true or false")
    options = raw.get("options", {})
    if not isinstance(options, dict):
        raise fail(key_line("options"), "`options` must be a table")

    pid = raw["id"]
    if pid in seen:
        raise fail(key_line("id"), f"duplicate participant id `{pid}`")
    seen.add(pid)

    adapter_id = raw["adapter"]
    if not registry.is_registered(adapter_id):
        raise fail(key_line("adapter"), f"unknown adapter `{adapter_id}` (known: {', '.join(registry.adapter_ids())})")
    adapter = _try_adapter(adapter_id)
    if adapter is not None:
        try:
            adapter.validate_options(options)
        except ValueError as exc:
            raise fail(header, f"invalid options for participant `{pid}`: {exc}") from None

    if "persona" in raw:
        log.info("participant %s: `persona` is reserved and ignored in this version", pid)

    return ParticipantConfig(
        id=pid,
        display_name=raw["display_name"],
        adapter=adapter_id,
        model=raw.get("model"),
        avatar=raw.get("avatar", ""),
        enabled=raw.get("enabled", True),
        persona=raw.get("persona"),
        options=options,
    )


def _try_adapter(adapter_id: str):
    """The adapter instance, or None while its module is still a placeholder (no `create_adapter`)."""
    module = registry.load_module(adapter_id)
    factory = getattr(module, "create_adapter", None)
    return factory() if factory else None


def _defaults(raw: dict[str, Any], participants: list[ParticipantConfig], lines: _Lines, fail) -> Defaults:
    if not isinstance(raw, dict):
        raise fail(None, "[defaults] must be a table")
    base = Defaults()
    known = {"mode", "judge", "speaking_order", "moderator", "max_rounds", "turn_timeout_seconds", "jev_threshold"}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise fail(lines.defaults_key(unknown[0]), f"unknown [defaults] field(s): {', '.join(unknown)}")

    def choice(key: str, allowed: tuple[str, ...], default: str) -> str:
        value = raw.get(key, default)
        if value not in allowed:
            raise fail(lines.defaults_key(key), f"`{key}` must be one of: {', '.join(allowed)}")
        return value

    def number(key: str, default: float, *, integer: bool = False, low: float = 0, high: float | None = None):
        value = raw.get(key, default)
        ok_type = isinstance(value, int) if integer else isinstance(value, (int, float))
        if isinstance(value, bool) or not ok_type or value <= low or (high is not None and value > high):
            kind = "an integer" if integer else "a number"
            bound = f" > {low}" + (f" and <= {high}" if high is not None else "")
            raise fail(lines.defaults_key(key), f"`{key}` must be {kind}{bound}")
        return value

    moderator = raw.get("moderator", participants[0].id)
    if not any(p.id == moderator for p in participants):
        raise fail(lines.defaults_key("moderator"), f"default moderator `{moderator}` is not a participant id")

    return Defaults(
        mode=choice("mode", MODE_IDS, base.mode),
        judge=choice("judge", JUDGE_IDS, base.judge),
        speaking_order=choice("speaking_order", SPEAKING_ORDER_IDS, base.speaking_order),
        moderator=moderator,
        max_rounds=number("max_rounds", base.max_rounds, integer=True),
        turn_timeout_seconds=number("turn_timeout_seconds", base.turn_timeout_seconds),
        jev_threshold=number("jev_threshold", base.jev_threshold, high=1),
    )
