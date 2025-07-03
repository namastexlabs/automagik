import asyncio
import pytest
import pytest_asyncio

from automagik.utils.session_queue import SessionQueue

# Mark this module as asyncio
pytestmark = [
    pytest.mark.asyncio,
]

@pytest_asyncio.fixture
async def session_queue():
    """Create a SessionQueue for testing and clean it up afterward."""
    queue = SessionQueue()
    yield queue
    await queue.shutdown()

async def test_session_queue_cancels_prior_and_merges(session_queue):
    """If two messages arrive for the same session in quick succession, the first in-flight
    request should be cancelled and the processing function should only be called **once**
    with the merged (or latest) payload. The first caller must receive a `CancelledError`.
    """

    queue = session_queue

    processed_payloads = []

    async def fake_processor(session_id: str, messages: list[str], **kwargs):  # type: ignore[override]
        # Record what gets processed to assert later
        processed_payloads.append(messages)
        # Simulate a small amount of work
        await asyncio.sleep(0.02)
        return "\n---\n".join(messages)

    # Fire the first request and *do not await* – we want it in-flight
    first_task = asyncio.create_task(queue.process("s1", "hello", fake_processor))

    # Give the first task just enough time to enqueue but (likely) not finish
    await asyncio.sleep(0.001)

    # Second request for the same session – this should trigger cancellation/merge
    result_second = await queue.process("s1", "world", fake_processor)

    # The fake processor should have been called exactly once
    assert len(processed_payloads) == 1
    # Whatever was processed must contain the latest payload
    assert "world" in processed_payloads[0]

    # The second caller receives the processor's return value
    assert "world" in result_second

    # The first task must have been cancelled
    with pytest.raises(asyncio.CancelledError):
        await first_task 