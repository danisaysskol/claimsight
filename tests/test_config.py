"""Tests for configuration and small helpers."""

from __future__ import annotations

from claimsight.config import Settings, get_settings


def test_sqlalchemy_url_shape():
    s = Settings(
        postgres_user="u", postgres_password="p", postgres_host="h",
        postgres_port=5555, postgres_db="d",
    )
    assert s.sqlalchemy_url == "postgresql+psycopg2://u:p@h:5555/d"


def test_get_settings_cached():
    assert get_settings() is get_settings()


def test_defaults_present():
    s = get_settings()
    assert s.raw_schema
    assert s.reporting_schema
    assert s.claimsight_n_claim_lines > 0
