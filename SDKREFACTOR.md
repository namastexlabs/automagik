# Claude-Code SDK Migration – **Definitive Execution Plan**

## 🔑 Executive summary (read me first)

1. **Goal**  → completely replace the bespoke Node-CLI command builder with the official `claude-code-sdk` _without_ keeping any fallback.  The legacy `ClaudeCLIExecutor`, related env helpers and the `--append-system-prompt` flag will be removed from the code base.
2. **Trajectory**  → work happens in a _single long-lived branch_ `feature/sdk-migration` owned by our workflow squad.  Each task below lands via small self-contained patches that stack on that branch – no parallel feature branches to reduce merge friction.

4. **Source-of-truth prompt**  → `prompt.md` (if present) will now feed **`system_prompt`** instead of `append_system_prompt`.  We intentionally drop the *append* semantics to keep behaviour congruent with the SDK API.
5. **Roll-back policy**  → None.  Once merged to `main` the old executor disappears.  Therefore CI must be green before the merge gates open.

Legend for status markers in the tables below:  
✅ already covered by SDK or implemented  
⚠️ partial  
❌ missing / to-do

------------------------------------------------------------------------------------------------------------------------------------

## 0  Current gap summary (quick refresher)

| Area | Item | Upstream status | Importance | Notes |
|------|------|-----------------|------------|-------|
| Core exec | `execute_until_first_response` helper | ❌ | blocker | Used by UI for optimistic streaming |
| Model opts | `max_thinking_tokens` flag honoured | ⚠️ | medium | Flag exists but SDK CLI builder ignores it |
| Prompts    | `prompt.md` → `system_prompt` auto-loader | ❌ | high | All our workflows depend on this convenience |
| Tools      | lookup `allowed_tools.json` automatically | ❌ | high | Non-dev power-users rely on file drop-in |
| MCP        | `--mcp-config <path>` | ❌ | high | Remote execution is a hard requirement |
| Environ.   | Workspace-specific env injection | ❌ | high | Our EnvMgr injects ~10 runtime vars |
| Timeouts   | Hard kill + graceful cancel | ❌ | medium | Needed for CI stability |

------------------------------------------------------------------------------------------------------------------------------------

## 1  Work-breakdown structure (single branch)

All work is serialised on the **`feature/sdk-migration`** branch.  Each bullet represents a pull-request that must be merged before the next one starts.  Even though only one branch is used, we still keep tasks small so code-review remains manageable.

### Epic A – Dependency & Build plumbing (Owner `@core-squad`)

1A. Upgrade project dependencies
 • Edit `pyproject.toml` → add `claude-code-sdk>=0.0.10` (no upper pin yet).  
 • Run `pip install -e .[dev]` locally and verify `import claude_code` succeeds.


🟡 **Blockers / sequencing**: none – this may land first; everything else can re-base on it.

---

### Epic B – Thin wrapper implementation

**Goal**: introduce `ClaudeSDKExecutor` that mimics the public surface of `ClaudeCLIExecutor`.

B1. Create file `src/agents/claude_code/sdk_executor.py` with skeleton:
```py
class ClaudeSDKExecutor:
    async def execute(...): ...
    async def execute_until_first_response(...): ...
```
Mirror parameter list & return value (`CLIResult`) exactly so **no downstream code changes** are required.

B2. Option mapping helper
 • `def _build_options(env_mgr: CLIEnvironmentManager, *, resume_id: str | None, ...) -> ClaudeCodeOptions:`  
 • Reads:
  – `workspace/.mcp.json` (json.load → ClaudeCodeOptions.mcp_servers)  
  – `workspace/allowed_tools.json` (list → .allowed_tools)  
  – `workspace/prompt.md` if exists (Path read_text → .system_prompt)

B3. Streaming integration
 • `async for raw in claude_code.query(prompt, opts): forward_to_raw_stream_processor(raw)`  
 • Keep identical message ordering semantics; unit-test with canned stream.

B4. Early return feature
 • Implement `_yield_until_first_assistant(opts)` which  
  – yields messages until `role == "assistant" and content` first appears (then cancel task)  
  – returns both the stream consumed so far **and** the still-running task for caller to await if desired.

B5. Timeout wrapper
 • `asyncio.wait_for(execute_task, timeout=passed_in_or_default)`  
 • If timeout fired → send `proc.kill()` via SDK’s exposed handle, capture `ProcessError`.

🟡 **Blockers**: depends on Epic A installing the SDK.

---

### Epic C – Environment Manager bridge 

C1. Refactor `CLIEnvironmentManager` so that it exposes **pure data** instead of CLI-flags
 • Add `def as_dict(self, workspace: Path) -> dict[str, str]` returning environment variables to inject.

C2. Modify `sdk_executor` to call `asyncio.create_subprocess_exec(..., env=os.environ | env_mgr.as_dict(ws))` through the SDK’s hook `extra_env` (exists in v0.0.10).

C3. Unit-test: given custom `EnvVar=1` verify target child process sees it (use dummy Node script).

🟡 **Blockers**: begins after A is merged.  Stub implementations may be sketched locally earlier but **no commits** until A lands.

---

### Epic D – Flag fidelity & file-based convenience 

D1. `max_thinking_tokens`
 • PR upstream is in progress, but locally we patch by monkey-punching `claude_code._cli_builder._build_cmd` until upstream merges; place patch in `src/agents/claude_code/sdk_shims.py`.

D2. `prompt.md` convenience loader  
 • When `workspace/prompt.md` exists, load its contents and populate **`system_prompt`**.  
 • Update README examples to show `<!-- System prompt resides here -->` comment at top of file for clarity.

D3. Allowed / disallowed tools file search  
 • If neither list passed explicitly and `workspace/allowed_tools.json` exists → load it.

Pure-Python utilities – merge after C is accepted.

---

### Epic E – Testing & quality gates 

E1. Unit tests (pytest)
 • `tests/claude_sdk_executor_test.py`  
  – mock `claude_code.query` → canned async generator to assert wrapper behaviour.

E2. Contract test with real CLI (marked `@pytest.mark.e2e`)  
 • Spin up hello-world Node project; assert end-to-end run returns `console.log` output.

E3. CI wiring  
 • `pytest -n auto` still passes.
 • Ensure tests skip if CLI binary missing (for OSS contributors).

🟡 **Blockers**: relies on B1+ for wrapper code, but may stub with mocks early.

---

### Epic F – Legacy removal & rollout 

F1. **Immediate hard-switch**  
 • Replace every import `from …cli_executor` → `from …sdk_executor`.  No feature-flag.  
 • Delete `workflow/executor_factory.py` branching logic – it will now always return the SDK executor.

F2. **Code purge**  
 • Remove files:
  – `src/agents/claude_code/cli_executor.py`  
  – `src/agents/claude_code/cli_environment.py` (keep only what is reused, otherwise migrate logic then delete)  
  – `src/agents/claude_code/utils/find_claude_executable.py` if present.  

F3. **Prompt strategy change**  
 • Rename any `prompt.md` references from _append_ semantics to _system_ semantics.  Update code so content is passed to `ClaudeCodeOptions.system_prompt`.

F4. **CI enforcement**  
 • Add `pytest -q tests/legacy_not_present_test.py` that simply asserts `import agents.claude_code.cli_executor` raises `ImportError` so no one re-adds it.

---


G1. Update README root section “Agents runtime” to reference SDK.  
G2. Add `docs/sdk_migration.md` containing a subset of this file so public users understand new env-vars.

------------------------------------------------------------------------------------------------------------------------------------

## 2  File-impact lookup matrix (not for concurrency)

Single-branch work means tasks merge serially; this table merely shows which areas of the code each Epic touches so that reviewers know where to focus.

| Epic | Main files impacted |
|------|--------------------|
| A | `pyproject.toml`,`.github/*` |
| B | `src/agents/claude_code/sdk_executor.py`, `src/agents/claude_code/__init__.py` |
| C | `src/agents/claude_code/cli_environment.py`, new `env_bridge.py` |
| D | `src/agents/claude_code/sdk_shims.py`, `workspace/prompt.md` |
| E | `tests/**` |
| F | delete legacy executor files, update call-sites |
| G | `README.md`, `docs/**` |

------------------------------------------------------------------------------------------------------------------------------------

## 3  Definition of Done (per Epic)

*Epic A* – CI pipeline installs SDK without errors.  
*Epic B* – All unit tests in E1 pass.  
*Epic C* – E2 test confirms environment vars visible in child process.  
*Epic D* – `system_prompt=<prompt.md contents>` path works in manual run.  
*Epic E* – GitHub action `tests.yml` green.  
*Epic F* – Legacy executor deleted, import check test passes.  
*Epic G* – PR merged & docs site redeployed.

------------------------------------------------------------------------------------------------------------------------------------

## 4  Long-term follow-ups (not in initial sprint)

• Submit upstream PR to `claude-code-sdk` exposing `mcp_config_path` and `append_system_prompt_path` so we can delete shim code.  
• Investigate pure-HTTP transport once Anthropic opens it – would eliminate Node dep.  
• Add Prometheus metrics emitter inside `sdk_executor` for latency & cost.

------------------------------------------------------------------------------------------------------------------------------------

## 5  Changelog snippet (to be appended on release)

```
### Added
* **claude-code-sdk** integration; executor now powered solely by the SDK-backed transport layer.

### Removed
* Legacy Node-CLI wrappers (`cli_executor.py`, `cli_environment.find_claude_executable`, etc.).
```

------------------------------------------------------------------------------------------------------------------------------------

_Last updated: {{ auto-generated on commit }}_
