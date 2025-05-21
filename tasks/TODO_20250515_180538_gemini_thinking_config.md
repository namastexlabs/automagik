# Task: Integrate `thinking_config` into Gemini Model Settings
**Status**: Not Started

## Analysis
- [ ] Locate helper `create_model_settings` (`dependencies_helper.py`) – currently builds model_settings from config dict.
- [ ] Confirm SofiaAgent hard-codes `model_name="google-gla:gemini-2.5-pro-preview-05-06"` and passes `model_settings`.
- [ ] Determine typical structure of `thinking_config` as per docs (dict of safety & depth params).
- [ ] Check if any other agents use Gemini provider.

## Plan
Step 1 — Settings defaults
  - [ ] Add `GEMINI_THINKING_CONFIG` to `src/config.Settings` with sensible defaults.
  - [ ] Add env var mapping `.env` example.

Step 2 — Builder update
  - [ ] Extend `create_model_settings` so that when `model_name` starts with `google-gla:` it constructs `GeminiModelSettings(thinking_config=…)` merging:
        a) agent-level override in `config`
        b) runtime override via `context['thinking_config']`
        c) fallback to Settings default.

Step 3 — SofiaAgent wiring
  - [ ] Ensure `self.dependencies.model_settings` picks up the gemini thinking_config.
  - [ ] Add optional `thinking_config` param in SofiaAgent constructor config mapping (docs update).

Step 4 — Telemetry
  - [ ] Log applied thinking_config at INFO level when initializing agent.

Step 5 — Tests
  - [ ] Unit test builder for merge precedence.

## Execution
- [ ] Implementation 1: config + env
- [ ] Implementation 2: builder function
- [ ] Implementation 3: SofiaAgent adjustments

## Summary
- [ ] Files modified: config.py, dependencies_helper.py, sofia_agent.agent 