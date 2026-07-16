from app.testing.inventory import list_python_sources


def test_inventory_lists_app_modules():
    rows = list_python_sources()
    paths = {r["path"] for r in rows}
    assert any(p.startswith("app/") for p in paths)
    assert any("tempest" in p for p in paths)
    assert all("lines" in r for r in rows)
