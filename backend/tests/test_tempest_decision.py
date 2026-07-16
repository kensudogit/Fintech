from app.tempest.decision import decision_engine
from app.tempest.evidence import evidence_store


def test_list_cases():
    cases = decision_engine.list_cases()
    assert any(c["case_id"].startswith("DEC-") for c in cases)


def test_transform_includes_structure():
    result = decision_engine.transform("定性・定量を統合して意思決定構造を変革して", include_ingested=False)
    assert "criteria_tree" in result
    assert len(result["scenarios"]) == 3
    assert "stance" in result


def test_ingested_evidence_affects_transform():
    evidence_store.clear()
    evidence_store.ingest_free_text(
        text="DSCR=0.9",
        case_id="DEC-LOAN-0142",
        decision_relevance="test",
    )
    result = decision_engine.transform("設備資金", case_id="DEC-LOAN-0142", include_ingested=True)
    assert len(result["ingested_evidence"]) >= 1
    evidence_store.clear()
