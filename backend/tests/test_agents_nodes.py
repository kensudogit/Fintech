from app.agents.nodes import VALID_INTENTS, _detect_intents


def test_valid_intents_cover_packages():
    for name in (
        "operations",
        "knowledge",
        "loan_screening",
        "b2b_matching",
        "decision_structure",
        "value_forecast",
        "evidence_intake",
    ):
        assert name in VALID_INTENTS


def test_detect_value_forecast():
    assert "value_forecast" in _detect_intents("企業価値を推定して")


def test_detect_evidence_intake():
    assert "evidence_intake" in _detect_intents("意思決定情報を投入: DSCR=1.2")


def test_detect_loan():
    assert "loan_screening" in _detect_intents("融資稟議を審査して")


def test_fee_faq_not_operations():
    intents = _detect_intents("振込手数料について教えて")
    assert "operations" not in intents
    assert "knowledge" in intents
