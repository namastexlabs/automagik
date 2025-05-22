"""Airtable Web API integration tests.

These tests hit the real Airtable API. They are executed only when the
necessary environment variables are set so that regular CI runs do not
fail.  Set the following variables in your environment or .env file to
run the tests:

    AIRTABLE_TOKEN            – Personal access token
    AIRTABLE_DEFAULT_BASE_ID  – Base ID (e.g. appXXXXXXXXXXXXXX)
    AIRTABLE_TEST_TABLE       – Table name or ID to query (should contain at least one record)
"""

import os
import logging
import pytest

from pydantic_ai import RunContext

from src.tools.airtable.tool import list_records

# ---------------------------------------------------------------------------
# Test configuration & helpers
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE = os.getenv("AIRTABLE_DEFAULT_BASE_ID")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TEST_TABLE") or os.getenv("AIRTABLE_TABLE_ID")

skip_airtable_tests = pytest.mark.skipif(
    not (AIRTABLE_TOKEN and AIRTABLE_BASE and AIRTABLE_TABLE),
    reason="Airtable integration variables not configured"
)

ctx: RunContext[dict] = {}  # Dummy context for tool signature

# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@skip_airtable_tests
@pytest.mark.asyncio
async def test_list_records_basic():
    """Verify that list_records returns data from Airtable."""
    logger.info("Running Airtable list_records integration test against table %s", AIRTABLE_TABLE)
    result = await list_records(ctx, table=AIRTABLE_TABLE, base_id=AIRTABLE_BASE, page_size=1)

    assert isinstance(result, dict)
    assert result.get("success") is True, f"API call failed: {result}"
    assert "records" in result and isinstance(result["records"], list), "No records key present"
    assert len(result["records"]) <= 1, "page_size limit not respected" 