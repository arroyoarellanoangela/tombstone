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


_MINORITY_CUES = (
    "minority stake",
    "minority investment",
    "strategic investment in",
    "acquires a stake in",
    "acquires a minority",
    "takes a stake in",
)

_INTRA_PORTFOLIO_CUES = (
    "portfolio companies merge",
    "merges with sister company",
    "combines its portfolio company",
    "merger of its portfolio",
    "consolidates its portfolio",
)

_ACQUISITION_CUES = (
    "acquires",
    "acquisition of",
    "has acquired",
    "acquired by",
    "to acquire",
    "completes acquisition",
    "announces the acquisition",
    "acquires the assets of",
)


def classify(candidate_snippet: str) -> DealKind:
    """Classify a raw candidate's kind from its source snippet.

    Keyword heuristic, checked in order of specificity: minority-stake and
    intra-portfolio language are checked first because their snippets often
    also contain generic acquisition-shaped words ("acquires a minority
    stake" contains "acquires"). Ambiguous cases fall to UNKNOWN and are
    excluded rather than guessed into IN_SCOPE — see is_in_scope.
    """
    text = candidate_snippet.lower()

    if any(cue in text for cue in _MINORITY_CUES):
        return DealKind.MINORITY_INVESTMENT
    if any(cue in text for cue in _INTRA_PORTFOLIO_CUES):
        return DealKind.INTRA_PORTFOLIO_MERGER
    if any(cue in text for cue in _ACQUISITION_CUES):
        return DealKind.MAJORITY_ACQUISITION
    return DealKind.UNKNOWN


def is_in_scope(kind: DealKind) -> bool:
    return kind in IN_SCOPE
