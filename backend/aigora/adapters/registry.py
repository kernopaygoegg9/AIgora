"""Adapter registry: the core looks adapters up only by identifier.

HOT FILE (owner: ticket 01). All five identifiers are registered here up
front; adapter tickets only fill in their own module and must not edit this
file. Modules are imported lazily so a broken or unfinished adapter does not
break the others.
"""

import importlib
from types import ModuleType

_MODULES: dict[str, str] = {
    "claude": "aigora.adapters.claude",
    "codex": "aigora.adapters.codex",
    "gemini": "aigora.adapters.gemini",
    "ollama": "aigora.adapters.ollama",
    "fake": "aigora.adapters.fake",
}


class UnknownAdapterError(KeyError):
    """Raised when an identifier has no registered adapter."""


def adapter_ids() -> list[str]:
    return list(_MODULES)


def is_registered(adapter_id: str) -> bool:
    return adapter_id in _MODULES


def module_path(adapter_id: str) -> str:
    try:
        return _MODULES[adapter_id]
    except KeyError:
        raise UnknownAdapterError(adapter_id) from None


def load_module(adapter_id: str) -> ModuleType:
    return importlib.import_module(module_path(adapter_id))
