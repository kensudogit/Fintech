from app.tempest.loan import loan_engine


def test_list_applications():
    apps = loan_engine.list_applications()
    assert len(apps) >= 3
    assert "application_id" in apps[0]


def test_analyze_northwind():
    result = loan_engine.analyze("ノースウィンド製造の融資稟議を審査して")
    assert result["decision"]["code"] in ("approve", "conditional", "reject")
    assert "blended" in result["scores"]
    assert result["application"]["application_id"] == "LN-2026-0142"
