"""Loading and validating `participants.toml`."""

import logging
from pathlib import Path

import pytest

from aigora.config import ConfigError, load_participants

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "participants.toml"
    path.write_text(text, encoding="utf-8")
    return path


TWO_FAKES = """
[[participant]]
id = "a"
display_name = "A"
adapter = "fake"

[[participant]]
id = "b"
display_name = "B"
adapter = "fake"
"""


def test_defaults_when_omitted(tmp_path):
    config = load_participants(write(tmp_path, TWO_FAKES))
    d = config.defaults
    assert (d.mode, d.judge, d.speaking_order) == ("ask", "stance_vote", "parallel")
    assert (d.max_rounds, d.turn_timeout_seconds, d.jev_threshold) == (15, 300, 0.8)
    assert d.moderator == "a"  # first participant


def test_participant_defaults(tmp_path):
    a = load_participants(write(tmp_path, TWO_FAKES)).participants[0]
    assert (a.id, a.display_name, a.adapter) == ("a", "A", "fake")
    assert a.model is None
    assert a.avatar == "fake.png"  # the adapter's default avatar
    assert a.enabled is True
    assert a.options == {}


def test_explicit_values_are_kept(tmp_path):
    path = write(
        tmp_path,
        """
[defaults]
mode = "consensus"
judge = "jev"
speaking_order = "sequential"
moderator = "b"
max_rounds = 4
turn_timeout_seconds = 30
jev_threshold = 0.9

[[participant]]
id = "a"
display_name = "A"
adapter = "fake"
model = "m1"
avatar = "custom.png"
enabled = false
[participant.options]
replies = ["hi"]

[[participant]]
id = "b"
display_name = "B"
adapter = "fake"
""",
    )
    config = load_participants(path)
    d = config.defaults
    assert (d.mode, d.judge, d.speaking_order, d.moderator) == ("consensus", "jev", "sequential", "b")
    assert (d.max_rounds, d.turn_timeout_seconds, d.jev_threshold) == (4, 30, 0.9)
    a = config.participants[0]
    assert (a.model, a.avatar, a.enabled, a.options) == ("m1", "custom.png", False, {"replies": ["hi"]})
    assert [p.id for p in config.enabled_participants()] == ["b"]
    assert config.get("b").display_name == "B"


def test_duplicate_id_fails_and_points_at_the_line(tmp_path):
    path = write(tmp_path, TWO_FAKES.replace('id = "b"', 'id = "a"'))
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 8
    assert "a" in err.value.message and "duplicate" in err.value.message
    assert str(err.value).startswith(f"{path}:8:")


def test_unknown_adapter_fails_and_points_at_the_line(tmp_path):
    path = write(tmp_path, TWO_FAKES.replace('adapter = "fake"\n\n', 'adapter = "nope"\n\n', 1))
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 5
    assert "nope" in err.value.message


def test_unknown_default_moderator_fails_and_points_at_the_line(tmp_path):
    path = write(tmp_path, '[defaults]\nmode = "ask"\nmoderator = "zed"\n' + TWO_FAKES)
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 3
    assert "zed" in err.value.message


def test_missing_required_field_points_at_the_participant(tmp_path):
    path = write(tmp_path, TWO_FAKES.replace('display_name = "B"\n', ""))
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 7
    assert "display_name" in err.value.message


def test_invalid_default_value_points_at_the_line(tmp_path):
    path = write(tmp_path, '[defaults]\nmode = "debate"\n' + TWO_FAKES)
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 2


def test_invalid_adapter_options_point_at_the_participant(tmp_path):
    path = write(tmp_path, TWO_FAKES + '[participant.options]\nfail_kind = "exploded"\n')
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 7
    assert "fail_kind" in err.value.message


def test_toml_syntax_error_points_at_the_line(tmp_path):
    path = write(tmp_path, TWO_FAKES + "\n[[participant]\n")
    with pytest.raises(ConfigError) as err:
        load_participants(path)
    assert err.value.line == 12


def test_missing_file_fails(tmp_path):
    with pytest.raises(ConfigError):
        load_participants(tmp_path / "nope.toml")


def test_persona_is_ignored_and_logged(tmp_path, caplog):
    path = write(tmp_path, TWO_FAKES.replace('adapter = "fake"\n\n', 'adapter = "fake"\npersona = "grumpy"\n\n', 1))
    with caplog.at_level(logging.INFO, logger="aigora.config"):
        config = load_participants(path)
    assert config.participants[0].id == "a"
    assert any("persona" in r.message and "a" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    "path",
    [REPO_ROOT / "participants.example.toml", REPO_ROOT / "frontend" / "e2e" / "participants.e2e.toml"],
)
def test_shipped_participant_files_load(path):
    assert load_participants(path).participants
