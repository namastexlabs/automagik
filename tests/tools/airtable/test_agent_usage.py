"""Test that a PydanticAI agent can successfully utilise Airtable tools.

This test uses TestModel from pydantic_ai.models.test so no real LLM
requests are made and no network traffic is triggered. We monkey-patch
the Airtable tool implementation to avoid HTTP calls and return a dummy
payload. The objective is to validate the agent+tool plumbing rather
than Airtable behaviour.
"""


import pytest

from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from automagik.tools.airtable.interface import airtable_list_records

pytestmark = pytest.mark.anyio


def _dummy_list_records(*args, **kwargs):  # type: ignore
    """Return a canned Airtable list_records result."""
    return {
        "success": True,
        "records": [
            {"id": "recDummy", "fields": {"Name": "Test"}, "createdTime": "2025-01-01T00:00:00.000Z"}
        ],
    }


@pytest.fixture
def anyio_backend() -> str:
    """Force pytest-anyio to use the asyncio backend only."""
    return "asyncio"


async def test_agent_can_use_airtable_tool(monkeypatch):
    """Ensure an agent run triggers the Airtable list_records tool call."""

    # Monkey-patch the actual implementation to avoid network calls
    monkeypatch.setattr(airtable_list_records, "function", lambda *a, **k: _dummy_list_records())

    agent = Agent(
        "test",  # model placeholder; will be overridden with TestModel
        tools=[airtable_list_records],
        system_prompt="You can query Airtable using the tools provided.",
    )

    with capture_run_messages() as messages:
        with agent.override(model=TestModel()):
            # Run a simple query that should lead the model to call the tool
            await agent.run("Get the latest records from the demo table")

    # Expect at least: request -> tool call -> tool return -> response
    assert len(messages) >= 4
    # First message should be the model request containing user prompt
    first = messages[0]
    assert isinstance(first, ModelRequest)
    assert isinstance(first.parts[0], SystemPromptPart)
    # Second should be model response with a tool call part
    second = messages[1]
    assert isinstance(second, ModelResponse)
    tool_call_parts = [p for p in second.parts if isinstance(p, ToolCallPart)]
    assert tool_call_parts, "No tool call detected in model response"
    assert tool_call_parts[0].tool_name == "airtable_list_records"
    # Third should be model request with tool return part
    third = messages[2]
    assert isinstance(third, ModelRequest)
    assert any(isinstance(p, ToolReturnPart) for p in third.parts)

    # Basic usage sanity
    last_usage = next((m.usage for m in messages if isinstance(m, ModelResponse) and m.usage), None)
    assert last_usage is not None
    assert last_usage.requests >= 1 