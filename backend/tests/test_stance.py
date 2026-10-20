"""Stance parsing: the last line of a turn must be `STANCE: AGREE` or `STANCE: DISAGREE`."""

import pytest

from aigora.stance import parse_stance


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I like the draft.\nSTANCE: AGREE", "AGREE"),
        ("Not yet.\nSTANCE: DISAGREE", "DISAGREE"),
        ("Fine.\nSTANCE: AGREE\n\n  ", "AGREE"),  # trailing blank lines are ignored
        ("Fine.\n  STANCE:AGREE  ", "AGREE"),
        ("Fine.\nstance: disagree", "DISAGREE"),
        ("Fine.\r\nSTANCE: AGREE\r\n", "AGREE"),
    ],
)
def test_last_line_stance_is_parsed(text, expected):
    assert parse_stance(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "No stance at all.",
        "STANCE: AGREE\nBut then I kept talking.",  # not the last line
        "Fine.\nSTANCE: MAYBE",
        "Fine.\nMy STANCE: AGREE",
        "Fine.\n**STANCE: AGREE**",
        "Fine.\nSTANCE: AGREE, mostly",
    ],
)
def test_anything_else_is_unparseable(text):
    assert parse_stance(text) is None
