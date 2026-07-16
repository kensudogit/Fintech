"""Normalize DB URLs for SQLAlchemy async (asyncpg) and sync drivers."""

from __future__ import annotations


def to_asyncpg_url(url: str) -> str:
    """Convert Railway/Heroku-style DATABASE_URL to postgresql+asyncpg://."""
    if not url:
        return url

    replacements = (
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
        ("postgresql+psycopg://", "postgresql+asyncpg://"),
        ("postgres://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
    )
    for old, new in replacements:
        if url.startswith(old):
            url = new + url[len(old) :]
            break

    # asyncpg uses ssl= instead of libpq sslmode=
    url = url.replace("sslmode=require", "ssl=require")
    url = url.replace("sslmode=prefer", "ssl=prefer")
    url = url.replace("sslmode=verify-ca", "ssl=require")
    url = url.replace("sslmode=verify-full", "ssl=require")
    return url


def to_sync_url(url: str) -> str:
    """Convert URL to a sync psycopg2-compatible postgresql:// form."""
    if not url:
        return url
    for old in (
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        "postgresql+psycopg://",
        "postgres://",
    ):
        if url.startswith(old):
            url = "postgresql://" + url[len(old) :]
            break
    return url
