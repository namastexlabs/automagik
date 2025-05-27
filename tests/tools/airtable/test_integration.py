"""Airtable Web API integration tests.

These tests hit the real Airtable API. They are executed only when the
necessary environment variables are set so that regular CI runs do not
fail.  Set the following variables in your environment or .env file to
run the tests:

    AIRTABLE_TOKEN            – Personal access token
    AIRTABLE_TEST_BASE_ID     – Test base ID (e.g. appXXXXXXXXXXXXXX) - separate from production
    AIRTABLE_TEST_TABLE       – Table name or ID to query (should contain at least one record)
"""

import logging
import pytest

from pydantic_ai import RunContext
from src.config import settings
from src.tools.airtable.tool import list_records

# ---------------------------------------------------------------------------
# Test configuration & helpers
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

skip_airtable_tests = pytest.mark.skipif(
    not (settings.AIRTABLE_TOKEN and settings.AIRTABLE_TEST_BASE_ID and settings.AIRTABLE_TEST_TABLE),
    reason="Airtable integration variables not configured (AIRTABLE_TOKEN, AIRTABLE_TEST_BASE_ID, AIRTABLE_TEST_TABLE)"
)

ctx: RunContext[dict] = {}  # Dummy context for tool signature

# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@skip_airtable_tests
@pytest.mark.asyncio
async def test_list_records_basic():
    """Verify that list_records returns data from Airtable."""
    logger.info("Running Airtable list_records integration test against table %s", settings.AIRTABLE_TEST_TABLE)
    result = await list_records(ctx, table=settings.AIRTABLE_TEST_TABLE, base_id=settings.AIRTABLE_TEST_BASE_ID, page_size=1)

    assert isinstance(result, dict)
    assert result.get("success") is True, f"API call failed: {result}"
    assert "records" in result and isinstance(result["records"], list), "No records key present"
    assert len(result["records"]) <= 1, "page_size limit not respected" 