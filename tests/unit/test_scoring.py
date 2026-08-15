from src.domain.scoring import _is_pass
from src.domain.models import ClaimStatus


def test_undisclosed_counts_as_pass(undisclosed_claim):
    assert _is_pass(undisclosed_claim) is True


def test_verified_counts_as_pass(verified_claim):
    assert _is_pass(verified_claim) is True
