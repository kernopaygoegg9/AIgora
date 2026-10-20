"""The adapter registry resolves every adapter identifier to its module."""

import pytest

from aigora.adapters import registry


def test_registry_lists_the_five_adapters():
    assert sorted(registry.adapter_ids()) == ["claude", "codex", "fake", "gemini", "ollama"]


@pytest.mark.parametrize(
    ("adapter_id", "module_name"),
    [
        ("claude", "aigora.adapters.claude"),
        ("codex", "aigora.adapters.codex"),
        ("gemini", "aigora.adapters.gemini"),
        ("ollama", "aigora.adapters.ollama"),
        ("fake", "aigora.adapters.fake"),
    ],
)
def test_registry_resolves_adapter_id_to_its_module(adapter_id, module_name):
    assert registry.module_path(adapter_id) == module_name
    assert registry.load_module(adapter_id).__name__ == module_name


def test_unknown_adapter_id_is_rejected():
    assert not registry.is_registered("nope")
    with pytest.raises(registry.UnknownAdapterError):
        registry.module_path("nope")
