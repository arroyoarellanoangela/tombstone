"""Stage 4 — Adviser Hunter. Conditionally invoked, only when Research
leaves the M&A adviser field empty.

A distinct search strategy from Research: advisory-side sources (tombstone
announcements, sector press, the target's own release in its local
language) rather than the acquirer's press room, which the brief notes
"often" omits the adviser. This is the clearest real delegation in the
system — a different agent handed the problem because the first approach
didn't work, not run in parallel by default for every deal.
"""

from src.domain.models import Claim, DealRecord


async def run(record: DealRecord) -> Claim:
    """Lateral search for `record`'s M&A adviser. Returns a Claim —
    status=NOT_FOUND (not a guess) if no source names one.
    """
    raise NotImplementedError
