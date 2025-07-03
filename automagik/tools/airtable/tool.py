"""Airtable tool implementation.

This module provides the core functionality for Airtable tools.
It mirrors the style of existing Notion / Google Drive tools.

The functions below are deliberately lightweight wrappers around the
Airtable Web API, returning response payloads that conform to our
pydantic response models defined in `schema.py`.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Any, List, Optional

import requests
from pydantic_ai import RunContext

from automagik.config import settings

from .schema import (
    ListRecordsResponse,
    GetRecordResponse,
    CreateRecordsResponse,
    UpdateRecordsResponse,
    DeleteRecordsResponse,
    ListBasesResponse,
    ListTablesResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

API_BASE_URL = "https://api.airtable.com/v0"
DEFAULT_PAGE_SIZE = 100  # Airtable maximum
MAX_RECORDS_PER_BATCH = 10  # Airtable maximum for writes


def _get_token() -> str:
    """Return the Airtable personal access token from configuration."""
    token = getattr(settings, "AIRTABLE_TOKEN", None)
    if not token:
        raise ValueError("AIRTABLE_TOKEN is not configured. Please set it in your .env")
    return token


def _headers() -> Dict[str, str]:
    """Common HTTP headers for Airtable requests."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "User-Agent": "automagik-agents/airtable-tool",
    }


def _request(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    retry_on_rate_limit: bool = True,
) -> requests.Response:
    """Make an HTTP request with basic rate-limit retry logic."""

    while True:
        response = requests.request(method, url, headers=_headers(), params=params, json=json, timeout=30)
        if response.status_code != 429:
            # Normal exit path
            return response

        # Handle 429 — wait 30 seconds as per docs, then retry once
        if not retry_on_rate_limit:
            return response

        wait_time = 30
        logger.warning("Airtable rate-limited (429). Sleeping for %s seconds and retrying once…", wait_time)
        time.sleep(wait_time)
        # Only retry once
        retry_on_rate_limit = False


# ---------------------------------------------------------------------------
# Description helpers (used by interface.py)
# ---------------------------------------------------------------------------

def get_list_records_description() -> str:
    return (
        "List up to 100 records from a specific Airtable table (parameter: table – the table id like 'tblXXXX'). "
        "Requires a base_id argument OR rely on the default ENV setting AIRTABLE_DEFAULT_BASE_ID. "
        "If you do NOT yet know the table id, FIRST call `airtable_list_tables` (pass base_id) to discover it. "
        "Optional keyword args: view, fields (list of names), filter_formula (Airtable formula), page_size, offset."
    )


def get_get_record_description() -> str:
    return (
        "Retrieve a single Airtable record by its record ID. Params: table (tbl id), record_id (rec id). "
        "Make sure you have discovered table id first via `airtable_list_tables` if unknown."
    )


def get_create_records_description() -> str:
    return (
        "Create up to 10 records in a table. Params: table (tbl id), records (list of field dictionaries). "
        "Use `airtable_list_tables` to discover the table id if necessary."
    )


def get_update_records_description() -> str:
    return (
        "Update up to 10 existing records. Each element in `records` list must contain id and fields keys. "
        "Useful flow: 1) `airtable_list_records` with filter to find rec ids -> 2) call this tool to update."
    )


def get_delete_records_description() -> str:
    return (
        "Delete up to 10 records from a table. Supply table id and list of record ids. "
        "Consider calling `airtable_list_records` first to gather the record ids you wish to remove."
    )


def get_list_bases_description() -> str:
    return (
        "Return a list of Airtable bases (id & name) available to the auth token. "
        "Typical first step before any other Airtable operations if the base id is unknown."
    )


def get_list_tables_description() -> str:
    return (
        "Return tables (id & name) for the given base_id. Always call this if you only have the human table name; "
        "then use the returned table id in subsequent record CRUD tools."
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def list_records(
    ctx: RunContext[Dict],
    table: str,
    *,
    base_id: Optional[str] = None,
    view: Optional[str] = None,
    fields: Optional[List[str]] = None,
    filter_formula: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    offset: Optional[str] = None,
) -> Dict[str, Any]:
    """List (the first page of) records from a table."""

    base = base_id or getattr(settings, "AIRTABLE_DEFAULT_BASE_ID", None)
    if not base:
        return ListRecordsResponse(success=False, error="Missing base_id and no default configured").model_dump()

    params: Dict[str, Any] = {
        "pageSize": min(page_size, DEFAULT_PAGE_SIZE),
    }
    if view:
        params["view"] = view
    if fields:
        for field in fields:
            params.setdefault("fields[]", []).append(field)
    if filter_formula:
        params["filterByFormula"] = filter_formula
    if offset:
        params["offset"] = offset

    url = f"{API_BASE_URL}/{base}/{table}"

    try:
        response = _request("GET", url, params=params)
        if response.status_code != 200:
            return ListRecordsResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        return ListRecordsResponse(
            success=True,
            records=data.get("records", []),
            offset=data.get("offset"),
        ).model_dump()
    except Exception as e:
        logger.error("Error listing Airtable records: %s", e)
        return ListRecordsResponse(success=False, error=str(e)).model_dump()


async def get_record(
    ctx: RunContext[Dict],
    table: str,
    record_id: str,
    *,
    base_id: Optional[str] = None,
) -> Dict[str, Any]:
    base = base_id or getattr(settings, "AIRTABLE_DEFAULT_BASE_ID", None)
    if not base:
        return GetRecordResponse(success=False, error="Missing base_id and no default configured").model_dump()

    url = f"{API_BASE_URL}/{base}/{table}/{record_id}"
    try:
        response = _request("GET", url)
        if response.status_code != 200:
            return GetRecordResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        return GetRecordResponse(success=True, record=data).model_dump()
    except Exception as e:
        logger.error("Error getting Airtable record: %s", e)
        return GetRecordResponse(success=False, error=str(e)).model_dump()


async def create_records(
    ctx: RunContext[Dict],
    table: str,
    records: List[Dict[str, Any]],
    *,
    base_id: Optional[str] = None,
    typecast: bool = False,
) -> Dict[str, Any]:
    """Create up to 10 records."""

    base = base_id or getattr(settings, "AIRTABLE_DEFAULT_BASE_ID", None)
    if not base:
        return CreateRecordsResponse(success=False, error="Missing base_id and no default configured").model_dump()

    if len(records) > MAX_RECORDS_PER_BATCH:
        return CreateRecordsResponse(success=False, error="Airtable limit: max 10 records per create").model_dump()

    url = f"{API_BASE_URL}/{base}/{table}"
    payload = {
        "records": [{"fields": r} for r in records],
        "typecast": typecast,
    }
    try:
        response = _request("POST", url, json=payload)
        if response.status_code != 200 and response.status_code != 201:
            return CreateRecordsResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        return CreateRecordsResponse(success=True, records=data.get("records", [])).model_dump()
    except Exception as e:
        logger.error("Error creating Airtable records: %s", e)
        return CreateRecordsResponse(success=False, error=str(e)).model_dump()


async def update_records(
    ctx: RunContext[Dict],
    table: str,
    records: List[Dict[str, Any]],
    *,
    base_id: Optional[str] = None,
    typecast: bool = False,
) -> Dict[str, Any]:
    """Update up to 10 records. Each record dict must include an 'id' key and optional 'fields'."""

    base = base_id or getattr(settings, "AIRTABLE_DEFAULT_BASE_ID", None)
    if not base:
        return UpdateRecordsResponse(success=False, error="Missing base_id and no default configured").model_dump()

    if len(records) > MAX_RECORDS_PER_BATCH:
        return UpdateRecordsResponse(success=False, error="Airtable limit: max 10 records per update").model_dump()

    processed = []
    for rec in records:
        rec_id = rec.get("id")
        fields = rec.get("fields", {})
        if not rec_id:
            return UpdateRecordsResponse(success=False, error="Each record must include an 'id'").model_dump()
        processed.append({"id": rec_id, "fields": fields})

    url = f"{API_BASE_URL}/{base}/{table}"
    payload = {"records": processed, "typecast": typecast}
    try:
        response = _request("PATCH", url, json=payload)
        if response.status_code != 200:
            return UpdateRecordsResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        return UpdateRecordsResponse(success=True, records=data.get("records", [])).model_dump()
    except Exception as e:
        logger.error("Error updating Airtable records: %s", e)
        return UpdateRecordsResponse(success=False, error=str(e)).model_dump()


async def delete_records(
    ctx: RunContext[Dict],
    table: str,
    record_ids: List[str],
    *,
    base_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete up to 10 records."""

    base = base_id or getattr(settings, "AIRTABLE_DEFAULT_BASE_ID", None)
    if not base:
        return DeleteRecordsResponse(success=False, error="Missing base_id and no default configured").model_dump()

    if len(record_ids) > MAX_RECORDS_PER_BATCH:
        return DeleteRecordsResponse(success=False, error="Airtable limit: max 10 records per delete").model_dump()

    params = [("records[]", rid) for rid in record_ids]
    url = f"{API_BASE_URL}/{base}/{table}"
    try:
        # Pass list of tuples directly to preserve duplicates
        response = _request("DELETE", url, params=params)
        if response.status_code != 200:
            return DeleteRecordsResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        deleted_ids = [rec.get("id") for rec in data.get("records", []) if rec.get("deleted")]
        return DeleteRecordsResponse(success=True, deleted_record_ids=deleted_ids).model_dump()
    except Exception as e:
        logger.error("Error deleting Airtable records: %s", e)
        return DeleteRecordsResponse(success=False, error=str(e)).model_dump()


async def list_bases(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """List bases the PAT has access to."""
    url = f"{API_BASE_URL}/meta/bases"
    try:
        response = _request("GET", url)
        if response.status_code != 200:
            return ListBasesResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        bases = [{"id": b.get("id"), "name": b.get("name")} for b in data.get("bases", data.get("bases", []))] or data.get("bases", [])
        return ListBasesResponse(success=True, bases=bases).model_dump()
    except Exception as e:
        logger.error("Error listing Airtable bases: %s", e)
        return ListBasesResponse(success=False, error=str(e)).model_dump()


async def list_tables(ctx: RunContext[Dict], base_id: str) -> Dict[str, Any]:
    """List tables inside a base (requires base_id)."""
    url = f"{API_BASE_URL}/meta/bases/{base_id}/tables"
    try:
        response = _request("GET", url)
        if response.status_code != 200:
            return ListTablesResponse(success=False, error=f"HTTP {response.status_code}: {response.text}").model_dump()
        data = response.json()
        tables = [{"id": t.get("id"), "name": t.get("name")} for t in data.get("tables", [])]
        return ListTablesResponse(success=True, tables=tables).model_dump()
    except Exception as e:
        logger.error("Error listing Airtable tables: %s", e)
        return ListTablesResponse(success=False, error=str(e)).model_dump() 