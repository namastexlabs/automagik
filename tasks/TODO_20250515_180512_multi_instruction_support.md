# Task: Adopt PydanticAI Multi-Instruction Support
**Status**: Not Started

## Analysis
- [ ] Review PR #1591 diff – instructions functions added via `@agent.instructions`
- [ ] Locate current prompt architecture: `prompts/prompt.py` contains static mega-prompt; agent loads it via `self.get_filled_system_prompt()`
- [ ] Identify dynamic elements already substituted (run_id, user_information, etc.)
- [ ] Search for `@agent.system_prompt` decorators (none today) ➜ new pattern

## Plan
Step 1 — New helper module
  - [ ] Create `src/agents/common/instructions_helper.py` with utilities to register default instruction functions given a prompt template fragment list.
  - [ ] Provide function `parse_instruction_sections(prompt_text) -> list[str]` splitting the mega prompt at `###` or comment markers.

Step 2 — SofiaAgent migration prototype
  - [ ] In `sofia_agent.agent`, before creating the `Agent`, convert parsed instruction blocks into `@agent.instructions` decorated closures so they are attached at runtime.
  - [ ] Keep the long "System Role" section as `system_prompt` for history retention; move everything under "Framework for Interactions", "Output Guidelines", etc. into instructions list.

Step 3 — Generic template loader
  - [ ] Extend `AutomagikAgent` base class with optional `instructions_builder` that subclasses can override; default returns empty list, letting future agents reuse the mechanism.

Step 4 — Back-compat & tests
  - [ ] Ensure tests render the same final prompt tokens after concatenation (snapshot test)
  - [ ] Validate that message history does NOT include past-run instructions when continuing a thread (confirm via pydantic-ai agent.iter())

## Execution
- [ ] Impl 1: helper module + unit tests
- [ ] Impl 2: SofiaAgent migration
- [ ] Impl 3: Adopt pattern in 1-2 additional agents (simple_agent & stan_agent)

## Summary
- [ ] Files modified: new helper, agent changes
- [ ] Edge cases: heartbeat personal instructions toggled per run 