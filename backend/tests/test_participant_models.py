"""GET /api/participants carries each participant's model list (spec "參與者與模型選擇")."""

import asyncio

import pytest

from aigora import participant_info
from aigora.adapters.base import Availability, ModelChoices, ModelOption
from aigora.adapters.fake import FakeAdapter
from conftest import fake_participant


@pytest.fixture(autouse=True)
def empty_model_cache():
    participant_info.clear_model_cache()
    yield
    participant_info.clear_model_cache()


def by_id(response) -> dict[str, dict]:
    assert response.status_code == 200
    return {p["id"]: p for p in response.json()}


def test_participants_carry_their_model_list(client, write_participants):
    write_participants(fake_participant("fake-a", "Fake A", models=["small", "large"])
                       + fake_participant("fake-b", "Fake B"))

    info = by_id(client.get("/api/participants"))

    assert info["fake-a"]["models"] == [{"id": "small", "label": "small"}, {"id": "large", "label": "large"}]
    assert info["fake-a"]["free_text_model"] is False
    assert info["fake-a"]["models_error"] is None
    assert info["fake-a"]["model"] is None  # still the configured model
    assert info["fake-b"]["models"] == []


def test_an_unavailable_participant_gets_no_model_list(client, write_participants):
    write_participants(fake_participant("fake-a", "Fake A", available=False, models=["small"]))

    info = by_id(client.get("/api/participants"))

    assert info["fake-a"]["available"] is False
    assert info["fake-a"]["models"] == []
    assert info["fake-a"]["free_text_model"] is False
    assert info["fake-a"]["models_error"] is None


def test_a_listing_error_is_reported_and_an_adapter_that_raises_does_not_break_the_endpoint(
    client, write_participants, monkeypatch
):
    async def list_models(self, participant):
        if participant.id == "broken":
            raise RuntimeError("catalog exploded")
        return ModelChoices(error="catalog offline")

    monkeypatch.setattr(FakeAdapter, "list_models", list_models)
    write_participants(fake_participant("broken", "Broken") + fake_participant("offline", "Offline"))

    info = by_id(client.get("/api/participants"))

    assert info["broken"]["available"] is True
    assert info["broken"]["models"] == []
    assert "catalog exploded" in info["broken"]["models_error"]
    assert info["offline"]["models_error"] == "catalog offline"


def test_model_lists_are_cached_per_adapter_and_options_for_five_minutes(client, write_participants, monkeypatch):
    calls: list[str] = []

    async def list_models(self, participant):
        calls.append(participant.options["models"][0])
        return ModelChoices(models=(ModelOption("m", "m"),))

    monkeypatch.setattr(FakeAdapter, "list_models", list_models)
    write_participants(fake_participant("fake-a", "Fake A", models=["x"])
                       + fake_participant("fake-c", "Fake C", models=["y"]))
    now = [1000.0]
    monkeypatch.setattr(participant_info.time, "monotonic", lambda: now[0])

    first = by_id(client.get("/api/participants"))
    assert sorted(calls) == ["x", "y"]

    now[0] += 299
    assert by_id(client.get("/api/participants")) == first
    assert sorted(calls) == ["x", "y"]

    write_participants(fake_participant("fake-b", "Fake B", models=["x"]))  # same adapter + options
    by_id(client.get("/api/participants"))
    assert sorted(calls) == ["x", "y"]

    now[0] += 2  # past 5 minutes
    by_id(client.get("/api/participants"))
    assert sorted(calls) == ["x", "x", "y"]


def test_errors_are_not_cached(client, write_participants, monkeypatch):
    results = iter([ModelChoices(error="Ollama is not running"), ModelChoices(models=(ModelOption("m", "m"),))])

    async def list_models(self, participant):
        return next(results)

    monkeypatch.setattr(FakeAdapter, "list_models", list_models)
    write_participants(fake_participant("fake-a", "Fake A"))

    assert by_id(client.get("/api/participants"))["fake-a"]["models_error"] == "Ollama is not running"
    assert by_id(client.get("/api/participants"))["fake-a"]["models"] == [{"id": "m", "label": "m"}]


def test_model_listing_runs_at_the_same_time_as_the_availability_check(client, write_participants, monkeypatch):
    # Each side waits until the other has started: run one after the other, this times out.
    events: dict[str, asyncio.Event] = {}

    def event(name: str) -> asyncio.Event:
        return events.setdefault(name, asyncio.Event())

    async def check_availability(self, participant):
        event("checking").set()
        await asyncio.wait_for(event("listing").wait(), timeout=2)
        return Availability(True)

    async def list_models(self, participant):
        event("listing").set()
        await asyncio.wait_for(event("checking").wait(), timeout=2)
        return ModelChoices(models=(ModelOption("m", "m"),))

    monkeypatch.setattr(FakeAdapter, "check_availability", check_availability)
    monkeypatch.setattr(FakeAdapter, "list_models", list_models)
    write_participants(fake_participant("fake-a", "Fake A"))

    info = by_id(client.get("/api/participants"))

    assert info["fake-a"]["available"] is True
    assert info["fake-a"]["models"] == [{"id": "m", "label": "m"}]
