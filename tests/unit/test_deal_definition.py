from src.domain.deal_definition import DealKind, classify, is_in_scope


def test_plain_acquisition_is_majority():
    assert classify("Volaris Group announces the acquisition of Acme Software.") == DealKind.MAJORITY_ACQUISITION


def test_minority_stake_is_not_majority():
    assert classify("Volaris Group acquires a minority stake in Acme Software.") == DealKind.MINORITY_INVESTMENT


def test_intra_portfolio_merger_is_not_majority():
    assert (
        classify("Volaris Group merges with sister company Acme within its portfolio.")
        == DealKind.INTRA_PORTFOLIO_MERGER
    )


def test_irrelevant_text_is_unknown():
    assert classify("Volaris Group reports quarterly earnings.") == DealKind.UNKNOWN


def test_only_majority_acquisition_is_in_scope():
    assert is_in_scope(DealKind.MAJORITY_ACQUISITION) is True
    assert is_in_scope(DealKind.MINORITY_INVESTMENT) is False
    assert is_in_scope(DealKind.INTRA_PORTFOLIO_MERGER) is False
    assert is_in_scope(DealKind.UNKNOWN) is False
