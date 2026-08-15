import pytest

from src.domain.models import Claim, ClaimStatus


@pytest.fixture
def verified_claim() -> Claim:
    return Claim(
        field="purchase_price",
        status=ClaimStatus.VERIFIED,
        value="$14M",
        source_url="https://example.com/press-release",
        verbatim_quote="for approximately $14 million",
        source_language="en",
        verified=True,
    )


@pytest.fixture
def undisclosed_claim() -> Claim:
    return Claim(
        field="purchase_price",
        status=ClaimStatus.EXPLICITLY_UNDISCLOSED,
        source_url="https://example.com/press-release",
        verbatim_quote="financial terms were not disclosed",
        source_language="en",
        verified=True,
    )
