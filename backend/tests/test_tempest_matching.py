from app.tempest.matching import matching_engine


def test_list_companies():
    companies = matching_engine.list_companies()
    assert len(companies) >= 3


def test_search_precision():
    result = matching_engine.search("精密加工企業のビジネスマッチング候補を出して")
    assert result["matches"]
    assert result["matches"][0]["score"] > 0
    assert "message" in result
