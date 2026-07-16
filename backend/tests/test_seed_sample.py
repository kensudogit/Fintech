from app.seed import SAMPLE_DIALOGUE, SAMPLE_EVENTS, SAMPLE_KNOWLEDGE


def test_sample_knowledge_has_tempest_docs():
    cats = {k.get("category") for k in SAMPLE_KNOWLEDGE}
    assert "decision_structure" in cats or any("意思決定" in k["title"] for k in SAMPLE_KNOWLEDGE)
    assert any("企業価値" in k["title"] or k.get("category") == "value_forecast" for k in SAMPLE_KNOWLEDGE)


def test_sample_events_and_dialogue():
    assert len(SAMPLE_EVENTS) >= 5
    assert len(SAMPLE_DIALOGUE) >= 2
