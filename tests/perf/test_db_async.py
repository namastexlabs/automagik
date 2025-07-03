import threading
from typing import List, Tuple

import pytest

# Import the module under test
from automagik.db import connection as db_connection


@pytest.mark.asyncio
async def test_async_execute_query_runs_in_thread(monkeypatch):
    """Ensure `async_execute_query` executes the blocking query function in a worker thread.

    The test patches `execute_query` so we can capture the thread identifier where it
    executes.  We expect it to be *different* from the main thread that is running the
    asyncio event-loop – proving the wrapper is truly non-blocking for the loop.
    """

    main_thread_id = threading.get_ident()
    captured_thread_id = None

    def fake_execute_query(query: str, params: Tuple | None = None, fetch: bool = True, commit: bool = True):  # noqa: D401,E501
        nonlocal captured_thread_id
        captured_thread_id = threading.get_ident()
        # Simulate a typical DB response shape
        return [{"ok": True}]

    # Patch the sync implementation so nothing actually hits the database
    monkeypatch.setattr(db_connection, "execute_query", fake_execute_query)

    # Run the wrapper – it should delegate to our fake implementation in a threadpool
    result = await db_connection.async_execute_query("SELECT 1")

    assert result == [{"ok": True}]
    # Ensure the function ran in *a* thread, and importantly *not* the event-loop thread
    assert captured_thread_id is not None and captured_thread_id != main_thread_id


@pytest.mark.asyncio
async def test_async_execute_batch_runs_in_thread(monkeypatch):
    """Same assertion as above but for `async_execute_batch`."""

    main_thread_id = threading.get_ident()
    captured_thread_id = None

    def fake_execute_batch(query: str, params_list: List[Tuple], commit: bool = True):  # noqa: D401
        nonlocal captured_thread_id
        captured_thread_id = threading.get_ident()
        # Pretend we inserted rows successfully – nothing to return
        return None

    monkeypatch.setattr(db_connection, "execute_batch", fake_execute_batch)

    await db_connection.async_execute_batch("INSERT INTO foo VALUES ($1)", [(1,), (2,)])

    assert captured_thread_id is not None and captured_thread_id != main_thread_id 