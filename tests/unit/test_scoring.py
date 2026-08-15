from src.domain.models import Claim, ClaimStatus, DealRecord
from src.domain.scoring import _is_pass, score_claim, score_deal

_NOT_FOUND = Claim(field="_", status=ClaimStatus.NOT_FOUND)


def test_undisclosed_counts_as_pass(undisclosed_claim):
    assert _is_pass(undisclosed_claim) is True


def test_verified_counts_as_pass(verified_claim):
    assert _is_pass(verified_claim) is True


def test_not_found_does_not_count_as_pass():
    assert _is_pass(_NOT_FOUND) is False


def test_score_claim_zero_for_not_found():
    assert score_claim(_NOT_FOUND, source_tier="regulatory_filing", corroborating_domains=5) == 0.0


def test_score_claim_higher_when_verified_than_when_merely_claimed():
    unverified = Claim(
        field="x", status=ClaimStatus.VERIFIED, value="v", source_url="https://x", verbatim_quote="q"
    )
    verified = unverified.model_copy(update={"verified": True})

    assert score_claim(verified, "acquirer_press_release", 1) > score_claim(
        unverified, "acquirer_press_release", 1
    )


def test_score_claim_higher_for_regulatory_filing_than_aggregator():
    claim = Claim(
        field="x", status=ClaimStatus.VERIFIED, value="v", source_url="https://x",
        verbatim_quote="q", verified=True,
    )
    assert score_claim(claim, "regulatory_filing", 1) > score_claim(claim, "aggregator", 1)


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
        acquirer=make("acquirer"),
        target=make("target"),
        date_announced=make("date_announced"),
        target_description=make("target_description"),
        geography=make("geography"),
        adviser=make("adviser"),
        purchase_price=make("purchase_price"),
        source_urls=["https://volarisgroup.com/press"],
    )


def _empty_record() -> DealRecord:
    return DealRecord(
        deal_id="volaris-acme",
        acquirer=_NOT_FOUND,
        target=_NOT_FOUND,
        date_announced=_NOT_FOUND,
        target_description=_NOT_FOUND,
        geography=_NOT_FOUND,
        adviser=_NOT_FOUND,
        purchase_price=_NOT_FOUND,
    )


def test_score_deal_zero_when_nothing_found():
    record = _empty_record()
    assert score_deal(record, source_tiers={}) == 0.0


def test_score_deal_fully_verified_scores_higher_than_unverified():
    verified_record = _full_record(all_verified=True)
    unverified_record = _full_record(all_verified=False)
    tiers = {f: "acquirer_press_release" for f in [
        "acquirer", "target", "date_announced", "target_description", "geography", "adviser", "purchase_price"
    ]}

    assert score_deal(verified_record, tiers) > score_deal(unverified_record, tiers)


def test_score_deal_is_bounded_between_zero_and_one():
    record = _full_record(all_verified=True)
    tiers = {f: "regulatory_filing" for f in [
        "acquirer", "target", "date_announced", "target_description", "geography", "adviser", "purchase_price"
    ]}
    score = score_deal(record, tiers)
    assert 0.0 <= score <= 1.0


def test_partial_record_scores_between_empty_and_full():
    empty = score_deal(_empty_record(), {})
    full = score_deal(_full_record(all_verified=True), {"target": "acquirer_press_release"})

    partial = _empty_record()
    partial.target = Claim(
        field="target", status=ClaimStatus.VERIFIED, value="Acme",
        source_url="https://volarisgroup.com/press", verbatim_quote="Acme", verified=True,
    )
    partial_score = score_deal(partial, {"target": "acquirer_press_release"})

    assert empty < partial_score < full
