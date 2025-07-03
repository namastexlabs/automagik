
import pytest
import pytest_asyncio

from automagik.agents.pydanticai.sofia.specialized.airtable import get_airtable_assistant
from automagik.config import settings


###############################################################################
# Helpers & Fixtures
###############################################################################


def _credentials_available() -> bool:
    """Return True if all necessary credentials are configured."""
    return bool(
        settings.AIRTABLE_TOKEN
        and settings.AIRTABLE_DEFAULT_BASE_ID
        and settings.OPENAI_API_KEY
    )


@pytest_asyncio.fixture(scope="module")
async def airtable_agent():
    """Fixture that yields a fresh Airtable assistant instance.

    The fixture is skipped automatically if required credentials are missing.
    """
    if not _credentials_available():
        pytest.skip(
            "Airtable and/or OpenAI credentials are not configured. "
            "Set AIRTABLE_TOKEN, AIRTABLE_DEFAULT_BASE_ID, and OPENAI_API_KEY "
            "in your .env file to run these tests."
        )

    # Always force a refresh to ensure schema is up-to-date for test consistency
    agent = await get_airtable_assistant(force_refresh=True)
    yield agent


###############################################################################
# Basic Capability Tests
###############################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "What tools and capabilities do you have available?",
        "How can you help me with Airtable?",
        "What is your purpose?",
    ],
)
async def test_basic_capabilities(airtable_agent, query: str):
    """Validate that the agent can answer basic capability questions."""

    class MockDeps:
        def __init__(self):
            self.context = {}

    result = await airtable_agent.run(query, deps=MockDeps())
    assert result.output, "Agent returned empty response"


###############################################################################
# Task-Specific Tests
###############################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Show me all Milestones",
        "Show me all tasks assigned to Cezar Vasconcelos",
        "Show me all tasks assigned to Cezar Vasconcelos that are not completed",
        "What tasks does Cezar Vasconcelos have in the Automagik - Plataforma Milestone?",
        "Show Cezar Vasconcelos's current tasks and their status",
    ],
)
async def test_cezar_task_queries(airtable_agent, query: str):
    """Ensure the agent can answer task-related queries for a specific assignee."""

    class MockDeps:
        def __init__(self):
            self.context = {}

    result = await airtable_agent.run(query, deps=MockDeps())
    assert result.output, f"Agent did not return output for query: {query}"


###############################################################################
# Improved Query Pattern Tests
###############################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        # Direct table queries
        "List all records from the Tasks table",
        "Show me the structure of the Tasks table",
        # Filtered queries
        "From the Tasks table, find records where any field contains 'Cezar'",
        "Query the Tasks table and filter by assignee or responsible person matching 'Cezar Vasconcelos'",
        # Status-focused queries
        "Show all tasks that are currently 'A fazer' (to do)",
        "List tasks with status 'Estou trabalhando' (working on)",
        # Exploratory queries
        "What fields are available in the Tasks table?",
        "Show me a sample of 3 records from the Tasks table",
    ],
)
async def test_improved_queries(airtable_agent, query: str):
    """Validate a variety of more complex or exploratory queries."""

    class MockDeps:
        def __init__(self):
            self.context = {}

    result = await airtable_agent.run(query, deps=MockDeps())
    assert result.output, f"Agent did not return output for query: {query}" 