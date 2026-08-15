"""What counts as an "acquisition" — see docs/PROJECT_PROPOSAL.md, section 4.

Encoded here as config + a predicate function, not left as an implicit
convention inside a prompt, so the Normalizer's filtering is testable and
the definition is reviewable on its own.
"""

from enum import StrEnum


class DealKind(StrEnum):
    MAJORITY_ACQUISITION = "majority_acquisition"
    MINORITY_INVESTMENT = "minority_investment"
    INTRA_PORTFOLIO_MERGER = "intra_portfolio_merger"
    UNKNOWN = "unknown"


# Only this kind counts toward the tracked deal set. Everything else is
# logged to data/omissions.json with its DealKind as the reason — excluded,
# not silently dropped.
IN_SCOPE = {DealKind.MAJORITY_ACQUISITION}


def classify(candidate_snippet: str) -> DealKind:
    """Classify a raw candidate's kind from its source snippet.

    Heuristic first pass (keyword cues for "minority stake", "joint venture",
    "merges its portfolio company" etc.); ambiguous cases fall to UNKNOWN and
    are surfaced for manual review rather than guessed into IN_SCOPE.
    """
    raise NotImplementedError


def is_in_scope(kind: DealKind) -> bool:
    return kind in IN_SCOPE
