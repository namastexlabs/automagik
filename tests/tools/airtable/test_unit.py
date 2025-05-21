"""Unit tests for Airtable tool helpers."""

import pytest

from src.config import settings
from src.tools.airtable.tool import _headers


def test_headers_contains_token(monkeypatch):
    """_headers() should build correct Authorization header."""
    monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "unit_test_token")
    headers = _headers()
    assert headers["Authorization"] == "Bearer unit_test_token"
    assert headers["Content-Type"] == "application/json" 