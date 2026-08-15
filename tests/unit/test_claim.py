import pytest
from pydantic import ValidationError

from src.domain.models import Claim, ClaimStatus


def test_verified_claim_requires_quote():
    with pytest.raises(ValidationError):
        Claim(field="purchase_price", status=ClaimStatus.VERIFIED, value="$14M")


def test_not_found_claim_does_not_require_quote():
    claim = Claim(field="adviser", status=ClaimStatus.NOT_FOUND)
    assert claim.value is None


def test_undisclosed_claim_requires_quote(undisclosed_claim):
    assert undisclosed_claim.status == ClaimStatus.EXPLICITLY_UNDISCLOSED
    assert undisclosed_claim.verbatim_quote
