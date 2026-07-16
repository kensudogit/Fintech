from app.tempest.valuation import valuation_agent


def test_universe():
    uni = valuation_agent.list_universe()
    tickers = {u["ticker"] for u in uni}
    assert {"NWD", "MDB", "GLG"} <= tickers


def test_analyze_has_multimodal_blocks():
    result = valuation_agent.analyze("ノースウィンド製造の企業価値を推定して")
    assert "valuation" in result
    assert "time_series" in result
    assert "deep_fusion" in result
    assert "qualitative" in result
    assert result["valuation"]["fair_price"] > 0
    assert result["valuation"]["market_price"] > 0
