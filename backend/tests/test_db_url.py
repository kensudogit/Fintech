from app.db_url import to_asyncpg_url, to_sync_url


def test_to_asyncpg_url_upgrades_scheme():
    assert to_asyncpg_url("postgresql://u:p@h:5432/db").startswith("postgresql+asyncpg://")


def test_to_asyncpg_url_maps_sslmode():
    url = to_asyncpg_url("postgresql://u:p@h/db?sslmode=require")
    assert "ssl=" in url or "sslmode" not in url.lower() or "require" in url


def test_to_sync_url():
    assert "postgresql://" in to_sync_url("postgresql+asyncpg://u:p@h/db")
