"""Speaking orders (發言順序). Look one up with `get_speaking_order(id)`.

`sequential` is interface-only in v1 (spec "Out of Scope"); add its class here
and to `SPEAKING_ORDERS` when it is built. The engine never changes for it.
"""

from __future__ import annotations

from collections.abc import Sequence

from aigora.discussion.interfaces import SpeakingOrder


class ParallelOrder(SpeakingOrder):
    """同時: everyone speaks at once, in one batch."""

    id = "parallel"
    name = "同時"

    def schedule(self, participant_ids: Sequence[str], round_number: int) -> list[list[str]]:
        return [list(participant_ids)] if participant_ids else []


SPEAKING_ORDERS: dict[str, type[SpeakingOrder]] = {ParallelOrder.id: ParallelOrder}


def get_speaking_order(order_id: str) -> SpeakingOrder:
    """Raises KeyError for an unknown or not yet implemented order."""
    return SPEAKING_ORDERS[order_id]()
