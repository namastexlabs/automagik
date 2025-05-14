# Task: Agent performance improvements & stateless handling
**Status**: Not Started

## Analysis
- [ ] Requirements
  - [ ] Replace blocking psycopg2 calls with non-blocking solution (initially `run_in_threadpool`, later `asyncpg`)
  - [ ] Keep agent instances stateless per request (no shared mutable state)
  - [ ] Guarantee per-session message ordering (FIFO)
  - [ ] When two consecutive messages arrive for the same session, cancel the first still-running request and merge payloads into one processing call
  - [ ] Unit / load tests proving concurrent safety & throughput gain
- [ ] Challenges
  - [ ] Refactor repository layer without breaking existing call sites
  - [ ] Avoid race conditions when cancelling / merging in-flight requests
  - [ ] Preserve history consistency while reducing DB round-trips
- [ ] Dependencies
  - [ ] FastAPI concurrency utilities or asyncpg library
  - [ ] Potential Redis (or in-memory) queue for per-session sequencing

## Plan
- [ ] Step 1: Protect DB access
  - [ ] Subtask 1.1  Wrap `execute_query` & batch helpers with `run_in_threadpool`
    - Files: `src/db/connection.py`, all repository helpers.
    - Add async wrappers `async_execute_query`, `async_execute_batch` that internally call their sync counterparts via `fastapi.concurrency.run_in_threadpool`.
    - Replace direct calls in controllers / `MessageHistory` with async versions (search-replace).
    - Acceptance: running `pytest tests/perf/test_db_async.py` shows no `BlockingIOWarning`; benchmark shows event-loop free during query.
  - [ ] Subtask 1.2  Benchmark latency vs baseline
    - Script: `scripts/benchmarks/agent_run_bench.py` (uses `hey` / AnyIO to fire 200 concurrent requests).
    - Success criteria: ≥30 % drop in average latency and worker CPU idle-time visible in `uvicorn --access-log`.
- [ ] Step 2: Make AgentFactory return fresh, immutable instances
  - [ ] Subtask 2.1  Clone (deepcopy) base config per call or instantiate per request
    - Remove global `_initialized_agents` cache **or** change `get_agent` to `copy.deepcopy` the cached template.
    - Ensure `SimpleAgent.run()` doesn't mutate instance state; move mutable fields (e.g. tool_registry) into local scope.
  - [ ] Subtask 2.2  Guard first-time initialisation with `asyncio.Lock`
    - Introduce class-level `_init_lock = asyncio.Lock()`; wrap costly discovery / prompt registration in `async with _init_lock:` to avoid thundering herd.
- [ ] Step 3: Per-session message queue
  - [ ] Subtask 3.1  Introduce `SessionQueue` object (asyncio.Queue) keyed by `session_id`
    - New file: `src/utils/session_queue.py` with `get_queue(session_id)` factory, `enqueue(payload)` returns `asyncio.Future` for result.
    - Stores last `future` per session to support cancellation.
  - [ ] Subtask 3.2  Worker coroutine consumes queue in order, cancelling older task if needed
    - If a new message arrives while a previous task is still pending, cancel previous task, merge message contents (`"\n---\n"` separator) and process once.
    - Ensure DB history records **both** original messages but only one LLM call.
- [ ] Step 4: API layer modifications
  - [ ] Subtask 4.1  Add dependency that enqueues incoming `/agent/{name}/run` calls
    - Wrap existing `run_agent` endpoint: instead of directly calling `handle_agent_run`, call `await session_queue.process(request_payload)`.
  - [ ] Subtask 4.2  Aggregate payloads if multiple messages arrive before worker runs
    - Merge logic lives inside `SessionQueue`; update `MessageHistory.add()` so merged content still maps to correct user messages.
- [ ] Step 5: Tests & docs
  - [ ] Subtask 5.1  Unit tests for queue cancellation logic
    - Simulate 2 rapid calls, assert first future is cancelled, second returns combined response.
  - [ ] Subtask 5.2  Locust/hey benchmark script & results
    - Document RPS, latency before/after in `docs/performance.md`.
  - [ ] Subtask 5.3  Update README with performance guidelines
    - Add env-vars for pool sizing, queue parameters, worker count hints.

## Execution
- [ ] Implementation 1
  - [ ] Added async wrappers `async_execute_query` and `async_execute_batch` in `src/db/connection.py` (lines TBD) that delegate to `run_in_threadpool`.
  - [ ] Next: incrementally migrate repository functions or controller paths to use these wrappers.
- [ ] Implementation 2
  - [ ] Updated `src/api/controllers/agent_controller.py` to off-load heavy DB calls via `run_in_threadpool`.
  - [ ] Files modified: `src/db/connection.py`, `src/api/controllers/agent_controller.py`

## Summary
- [ ] Files modified: `filename.ext` (lines X-Y)
- [ ] Dependencies added/changed
- [ ] Edge cases considered
- [ ] Known limitations
- [ ] Future impact points 