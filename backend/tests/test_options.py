"""GET /api/options: modes, consensus judges (with availability), speaking orders, defaults."""

from __future__ import annotations

import pytest

from tests.conftest import fake_participant

PARTICIPANTS = fake_participant("alpha", "Alpha") + fake_participant("beta", "Beta")


@pytest.fixture
def no_key_env(tmp_path, monkeypatch):
    """A `.env` without TYPESAFE_API_KEY, and none in the process environment."""
    env_file = tmp_path / ".env"
    env_file.write_text("# nothing here\n", encoding="utf-8")
    monkeypatch.setenv("AIGORA_ENV_FILE", str(env_file))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    return env_file


def test_defaults_come_from_the_participants_file(client, write_participants, no_key_env):
    write_participants(
        """
[defaults]
mode = "consensus"
judge = "stance_vote"
speaking_order = "parallel"
moderator = "beta"
max_rounds = 7
turn_timeout_seconds = 42
jev_threshold = 0.65

"""
        + PARTICIPANTS
    )
    response = client.get("/api/options")
    assert response.status_code == 200
    assert response.json()["defaults"] == {
        "mode": "consensus",
        "judge": "stance_vote",
        "speaking_order": "parallel",
        "moderator_id": "beta",
        "max_rounds": 7,
        "turn_timeout_seconds": 42,
        "jev_threshold": 0.65,
    }


def _judges(client) -> dict[str, dict]:
    return {j["id"]: j for j in client.get("/api/options").json()["judges"]}


def test_judge_b_is_unavailable_with_a_reason_when_env_has_no_typesafe_key(
    client, write_participants, no_key_env
):
    write_participants(PARTICIPANTS)
    judges = _judges(client)
    assert list(judges) == ["stance_vote", "jev"]
    assert judges["stance_vote"]["available"] is True
    assert judges["jev"]["available"] is False
    assert "TYPESAFE_API_KEY" in judges["jev"]["unavailable_reason"]


def _jev_reason(client) -> str | None:
    return _judges(client)["jev"]["unavailable_reason"]


def test_with_a_key_in_the_env_file_judge_b_is_no_longer_blocked_by_the_key_and_the_key_is_never_sent(
    client, write_participants, no_key_env
):
    write_participants(PARTICIPANTS)
    no_key_env.write_text("TYPESAFE_API_KEY=sk-test-secret-123\n", encoding="utf-8")
    response = client.get("/api/options")
    jev = {j["id"]: j for j in response.json()["judges"]}["jev"]
    # Available once ticket 08 registers judge B; until then only "not built yet".
    assert jev["available"] or "TYPESAFE_API_KEY" not in jev["unavailable_reason"]
    assert "sk-test-secret-123" not in response.text


def test_an_empty_key_counts_as_missing(client, write_participants, no_key_env):
    write_participants(PARTICIPANTS)
    no_key_env.write_text("TYPESAFE_API_KEY=\n", encoding="utf-8")
    assert "TYPESAFE_API_KEY" in _jev_reason(client)


def test_a_key_in_the_process_environment_also_counts(client, write_participants, no_key_env, monkeypatch):
    write_participants(PARTICIPANTS)
    monkeypatch.setenv("TYPESAFE_API_KEY", "sk-from-environment")
    reason = _jev_reason(client)
    assert reason is None or "TYPESAFE_API_KEY" not in reason


def test_each_mode_lists_the_settings_it_uses(client, write_participants, no_key_env):
    write_participants(PARTICIPANTS)
    modes = {m["id"]: m for m in client.get("/api/options").json()["modes"]}
    assert list(modes) == ["ask", "consensus"]
    assert modes["ask"]["name"] == "提問"
    assert modes["consensus"]["name"] == "共識討論"
    # Spec: ask uses only participants and speaking order (plus the turn timeout);
    # consensus also uses moderator, judge and max rounds.
    ask = set(modes["ask"]["uses_settings"])
    assert {"participant_ids", "speaking_order"} <= ask
    assert not ask & {"moderator_id", "judge", "max_rounds"}
    assert {"participant_ids", "speaking_order", "moderator_id", "judge", "max_rounds"} <= set(
        modes["consensus"]["uses_settings"]
    )


def test_speaking_orders_say_which_are_implemented(client, write_participants, no_key_env):
    write_participants(PARTICIPANTS)
    orders = client.get("/api/options").json()["speaking_orders"]
    assert orders == [
        {"id": "parallel", "name": "同時", "implemented": True},
        {"id": "sequential", "name": "依序", "implemented": False},
    ]
