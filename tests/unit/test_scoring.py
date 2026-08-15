from src.domain.models import Claim, ClaimStatus, DealRecord
from src.domain.scoring import _is_pass, score_deal

_NOT_FOUND = Claim(field="_", status=ClaimStatus.NOT_FOUND)

_ALL_FIELDS = [
    "acquirer",
    "target",
    "date_announced",
    "target_description",
    "geography",
    "adviser",
    "purchase_price",
]


def test_undisclosed_counts_as_pass(undisclosed_claim):
    assert _is_pass(undisclosed_claim) is True


def test_verified_counts_as_pass(verified_claim):
    assert _is_pass(verified_claim) is True


def test_not_found_does_not_count_as_pass():
    assert _is_pass(_NOT_FOUND) is False


def _full_record(all_verified: bool) -> DealRecord:
    def make(field: str) -> Claim:
        return Claim(
            field=field,
            status=ClaimStatus.VERIFIED,
            value="x",
            source_url="https://volarisgroup.com/press",
            verbatim_quote="x",
            verified=all_verified,
        )

    return DealRecord(
        deal_id="volaris-acme",
        source_urls=["https://volarisgroup.com/press"],
        **{f: make(f) for f in _ALL_FIELDS},
    )


def _empty_record() -> DealRecord:
    return DealRecord(deal_id="volaris-acme", **{f: _NOT_FOUND for f in _ALL_FIELDS})


def test_score_deal_zero_when_nothing_found():
    assert score_deal(_empty_record(), source_tiers={}) == 0.0


def test_score_deal_fully_verified_scores_higher_than_unverified():
    tiers = {f: "acquirer_press_release" for f in _ALL_FIELDS}
    assert score_deal(_full_record(all_verified=True), tiers) > score_deal(
        _full_record(all_verified=False), tiers
    )


def test_score_deal_higher_for_regulatory_filing_than_aggregator():
    record = _full_record(all_verified=True)
    filing_tiers = {f: "regulatory_filing" for f in _ALL_FIELDS}
    aggregator_tiers = {f: "aggregator" for f in _ALL_FIELDS}
    assert score_deal(record, filing_tiers) > score_deal(record, aggregator_tiers)


def test_score_deal_is_bounded_between_zero_and_one():
    record = _full_record(all_verified=True)
    tiers = {f: "regulatory_filing" for f in _ALL_FIELDS}
    assert 0.0 <= score_deal(record, tiers) <= 1.0


def test_partial_record_scores_between_empty_and_full():
    empty = score_deal(_empty_record(), {})
    full = score_deal(_full_record(all_verified=True), {"target": "acquirer_press_release"})

    partial = _empty_record()
    partial.target = Claim(
        field="target",
        status=ClaimStatus.VERIFIED,
        value="Acme",
        source_url="https://volarisgroup.com/press",
        verbatim_quote="Acme",
        verified=True,
    )
    partial_score = score_deal(partial, {"target": "acquirer_press_release"})

    assert empty < partial_score < full
