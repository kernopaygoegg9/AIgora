"""Stance parsing (表態解析).

A turn that has to take a stance on the consensus draft must end with a last
line of exactly `STANCE: AGREE` or `STANCE: DISAGREE` (case and the space
after the colon are not significant; trailing blank lines are ignored).
Anything else is unparseable and returns None; the consensus judges treat
None as "disagree" and the next round reminds the participant of the format.
"""

import re

from aigora.domain import Stance

_STANCE_LINE = re.compile(r"STANCE:\s*(AGREE|DISAGREE)", re.IGNORECASE)


def parse_stance(text: str) -> Stance | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    match = _STANCE_LINE.fullmatch(lines[-1])
    if match is None:
        return None
    return "AGREE" if match.group(1).upper() == "AGREE" else "DISAGREE"
