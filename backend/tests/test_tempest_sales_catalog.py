from app.tempest.catalog import list_packages
from app.tempest.sales import sales_engine


def test_packages_include_core_products():
    ids = {p["id"] for p in list_packages()}
    assert "tempest-valuation" in ids
    assert "tempest-decision" in ids
    assert "tempest-loan" in ids


def test_sales_support():
    result = sales_engine.support("法人営業のトークスクリプトを作って")
    assert result["talk_track"]
    assert "message" in result
