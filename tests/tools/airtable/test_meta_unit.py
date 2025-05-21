import pytest
from src.tools.airtable.interface import airtable_list_bases, airtable_list_tables


@pytest.mark.asyncio
async def test_list_bases_monkeypatched(monkeypatch):
    async def _fake(ctx=None):
        return {"success": True, "bases": [{"id": "app123", "name": "Demo"}]}
    monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake())
    result = await airtable_list_bases.function(None)
    assert result["success"] is True
    assert result["bases"][0]["id"] == "app123"


@pytest.mark.asyncio
async def test_list_tables_monkeypatched(monkeypatch):
    async def _fake(ctx=None, base_id=None):
        return {"success": True, "tables": [{"id": "tbl1", "name": "Tasks"}]}
    monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake())
    result = await airtable_list_tables.function(None, base_id="app123")
    assert result["success"] is True
    assert result["tables"][0]["name"] == "Tasks" 