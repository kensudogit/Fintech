import pytest

from app.tempest.evidence import EvidenceIntakeStore


def test_quant_parse_and_add():
    store = EvidenceIntakeStore()
    item = store.ingest_free_text(text="自己資本比率=18%", case_id="DEC-LOAN-0142")
    assert item["kind"] == "quantitative"
    assert item["unit"] == "ratio"
    assert item["value"] == pytest.approx(0.18)


def test_qual_polarity():
    store = EvidenceIntakeStore()
    item = store.ingest_free_text(text="懸念があり悪化リスクがある", case_id=None)
    assert item["kind"] in ("qualitative", "news")
    assert item["polarity"] == "negative"


def test_delete():
    store = EvidenceIntakeStore()
    item = store.add(
        {
            "kind": "note",
            "title": "memo",
            "narrative": "hello",
        }
    )
    assert store.delete(item["evidence_id"]) is True
    assert store.get(item["evidence_id"]) is None
