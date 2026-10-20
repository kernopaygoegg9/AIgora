"""Prompt Builder: the full text sent to a participant for one call.

Adapters are stateless (ADR 0001), so every prompt carries the whole
discussion: the shared system prompt (who is in the discussion, answer in the
question's language, cite URLs), the question, every earlier turn and
consensus draft, the user's interjections, and this call's instructions from
the discussion mode. Personas are not included in v1.
"""

from __future__ import annotations

from aigora.discussion.interfaces import DiscussionView, RoundView


def build_prompt(view: DiscussionView, participant_id: str, instructions: str | None) -> str:
    sections = [
        _system_prompt(view, participant_id),
        f"## Question\n\n{view.question}",
    ]
    history = _history(view)
    if history:
        sections.append("## Discussion so far\n\n" + history)
    current = view.current_round
    if current and current.interjections:
        notes = "\n".join(f"- {text}" for text in current.interjections)
        sections.append(f"## Notes from the user (apply from this round)\n\n{notes}")
    if instructions:
        sections.append(f"## Instructions for this round\n\n{instructions}")
    return "\n\n".join(sections) + "\n"


def _system_prompt(view: DiscussionView, participant_id: str) -> str:
    me = view.participant_names.get(participant_id, participant_id)
    others = [view.participant_names[pid] for pid in view.active_participant_ids if pid != participant_id]
    who = (
        f"You are {me}, discussing the user's question with: {', '.join(others)}."
        if others
        else f"You are {me}, answering the user's question."
    )
    return "\n".join(
        [
            who,
            "- Answer in the same language as the question.",
            "- You may search the web. When you use information from the web, cite it with its URL.",
            "- You cannot read or write local files; do not try.",
        ]
    )


def _history(view: DiscussionView) -> str:
    """Earlier rounds; the current round's interjections get their own section instead."""
    parts: list[str] = []
    current = view.current_round
    for round_ in view.rounds:
        if round_ is not current and round_.interjections:
            notes = "\n".join(f"- {text}" for text in round_.interjections)
            parts.append(f"### Notes from the user (from round {round_.number})\n\n{notes}")
        parts.extend(_round_lines(view, round_))
    return "\n\n".join(parts)


def _round_lines(view: DiscussionView, round_: RoundView) -> list[str]:
    lines: list[str] = []
    for turn in round_.turns:
        name = view.participant_names.get(turn.participant_id, turn.participant_id)
        if turn.status == "ok" and turn.text:
            lines.append(f"### Round {round_.number} - {name}\n\n{turn.text}")
        else:
            lines.append(f"### Round {round_.number} - {name}\n\n(no reply: {turn.error or turn.status})")
    if round_.draft:
        moderator = view.participant_names.get(view.moderator_id or "", "the moderator")
        lines.append(f"### Consensus draft after round {round_.number} (by {moderator})\n\n{round_.draft}")
    return lines
