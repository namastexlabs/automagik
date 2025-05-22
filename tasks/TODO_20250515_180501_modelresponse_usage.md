# Task: Expose and Persist `ModelResponse.usage`
**Status**: Not Started

## Analysis
- [ ] Grep codebase for `result.data` and `text=result.data` usages to quantify scope
- [ ] Locate `AgentResponse` dataclass (`src/agents/models/response.py`) and downstream persistence points (DB, logging)
- [ ] Identify places where PydanticAI `RunResult` objects are created (all `*.agent.py` under `src/agents/simple` and `src/agents/models/...`)
- [ ] Confirm if any analytics tables already store token counts; else plan migration

## Plan
Step 1 — Schema changes
  - [ ] Add optional `usage: Usage | None` to `AgentResponse`
  - [ ] Implement `from_pydantic_result()` helper mapping `.output` and `.usage`
  - [ ] Add `model_dump` encoder for `Usage`

Step 2 — Agent refactors
  - [ ] Update `simple_agent`, `sofia_agent`, `stan_agent`, etc. to call the helper
  - [ ] Replace `result.data` → `result.output` post-upgrade
  - [ ] Ensure failure paths still populate `usage=None`

Step 3 — Logging & storage
  - [ ] Update `log_agent_response`, Notion sync, and DB `message_usage` table (create if missing)
  - [ ] Add aggregation to CLI report

Step 4 — Tests & lint
  - [ ] Add unit test for helper + one agent flow
  - [ ] Run `pytest`, fix breaking imports

## Execution
- [ ] Implementation 1: schema + helper
- [ ] Implementation 2: mass refactor via sed / ruff-format
- [ ] Implementation 3: logging enhancements

## Summary
- [ ] Files modified: `src/agents/models/response.py` …
- [ ] New helper tests added 