# Task: Enhance Prompt Management System

**Status**: Not Started

## Analysis
- [ ] Requirements
  - [ ] Implement a new `prompts` database table for versioned prompt storage.
  - [ ] Link prompts to agents (many-to-one: multiple prompts per agent).
  - [ ] Allow agents to have different active prompts based on a `status_key` (e.g., for StanAgent's states).
  - [ ] Repurpose `agents.system_prompt` column to `agents.active_default_prompt_id`.
  - [ ] Ensure first prompt registered from code is marked as `is_default_from_code`.
  - [ ] Version prompts, incrementing for each new prompt per agent/status_key.
  - [ ] Flag active prompts (`is_active`) and reflect this in `agents.active_default_prompt_id` for the primary default status.
  - [ ] Refactor existing agents (`SimpleAgent`, `StanAgent`, and others in `src/agents/simple/` and any other relevant directories) to use the new prompt system.
  - [ ] Develop a data migration strategy for existing agent prompts.
- [ ] Challenges
  - [ ] Ensuring smooth data migration for existing `system_prompt` data.
  - [ ] Correctly identifying and refactoring all existing agent implementations.
  - [ ] Designing robust logic for `_register_code_defined_prompt` and `load_active_prompt_template` in `AutomagikAgent`.
  - [ ] Managing active prompt switching, especially for agents with multiple status keys.
- [ ] Dependencies
  - [ ] Database migration tools/scripts.
  - [ ] Access to modify all relevant agent code.

## Plan

### Phase 1: Database and Core Logic
- [ ] **Step 1: Define Database Schema**
  - [ ] Create SQL migration script for the new `prompts` table:
    - `id`: SERIAL PRIMARY KEY (or UUID)
    - `agent_id`: INTEGER, Foreign Key to `agents.id` (CASCADE on delete)
    - `prompt_text`: TEXT
    - `version`: INTEGER (default 1)
    - `is_active`: BOOLEAN (default False)
    - `is_default_from_code`: BOOLEAN (default False)
    - `status_key`: VARCHAR(255) (e.g., "default", "NOT_REGISTERED", "APPROVED")
    - `name`: VARCHAR(255) (Optional, human-readable name)
    - `created_at`, `updated_at`: TIMESTAMPS
    - `UNIQUE(agent_id, status_key, version)`
  - [ ] Create SQL migration script to modify `agents` table:
    - Rename `system_prompt` column to `active_default_prompt_id`.
    - Change `active_default_prompt_id` type to INTEGER (or UUID), make it nullable.
- [ ] **Step 2: Implement Prompt Model and Repository**
  - [ ] Create Pydantic model `Prompt` in `src/db/models/prompt.py`.
  - [ ] Create `src/db/repository/prompt.py` with functions:
    - `create_prompt(db_session, prompt_data: PromptCreate) -> Prompt`
    - `get_prompt_by_id(db_session, prompt_id: int) -> Prompt | None`
    - `get_active_prompt(db_session, agent_id: int, status_key: str) -> Prompt | None`
    - `set_prompt_active(db_session, agent_id: int, prompt_id: int, status_key: str) -> Prompt | None` (Handles deactivating others for the same agent/status_key)
    - `find_code_default_prompt(db_session, agent_id: int, status_key: str) -> Prompt | None`
    - `get_latest_version_for_status(db_session, agent_id: int, status_key: str) -> int | None`
    - `get_prompts_by_agent_id(db_session, agent_id: int, status_key: Optional[str] = None) -> List[Prompt]`
- [ ] **Step 3: Refactor `AutomagikAgent`**
  - [ ] Remove `system_prompt` from `__init__` signature. Add `self.current_prompt_template: Optional[str] = None`.
  - [ ] Implement `_register_code_defined_prompt(self, code_prompt_text: str, status_key: str, prompt_name: Optional[str] = None, is_primary_default: bool = False)`:
    - Checks `find_code_default_prompt`.
    - If not found, calls `create_prompt` (version 1, `is_default_from_code=True`).
    - If `is_primary_default`, calls `set_prompt_active` and updates `agents.active_default_prompt_id`.
  - [ ] Implement `load_active_prompt_template(self, status_key: str) -> bool`:
    - Uses `get_active_prompt`.
    - Sets `self.current_prompt_template` and updates `self.template_vars = PromptBuilder.extract_template_variables(self.current_prompt_template)`.
  - [ ] Modify `get_filled_system_prompt()` to use `self.current_prompt_template`.

### Phase 2: Agent Refactoring
- [ ] **Step 4: Refactor `SimpleAgent`** (`src/agents/simple/simple_agent/agent.py`)
  - [ ] Modify `__init__`:
    - Remove `AGENT_PROMPT` pass to `super()`.
    - Call `self._register_code_defined_prompt(AGENT_PROMPT, status_key="default", prompt_name="Default SimpleAgent Prompt", is_primary_default=True)`.
  - [ ] Modify `run()`:
    - Call `await self.load_active_prompt_template(status_key="default")` before `get_filled_system_prompt`.
- [ ] **Step 5: Refactor `StanAgent`** (`src/agents/simple/stan_agent/agent.py`)
  - [ ] Modify `__init__`:
    - Remove `DEFAULT_PROMPT` pass to `super()`.
    - Loop through its prompt files (e.g., `not_registered.py`, `approved.py` from `prompts/` dir).
    - For each, call `self._register_code_defined_prompt(prompt_text, status_key="<status_from_filename>", prompt_name="StanAgent <Status> Prompt", is_primary_default=(status_key=="NOT_REGISTERED"))`.
  - [ ] Modify `_use_prompt_based_on_contact_status()`:
    - Determine `current_status_key`.
    - Call `await self.load_active_prompt_template(status_key=current_status_key)`.
    - Implement fallback to "default" or "NOT_REGISTERED" status key if specific one isn't found/active.
- [ ] **Step 6: Identify and Refactor Other Agents**
  - [ ] Scan `src/agents/simple/` and other potential directories (e.g. `src/agents/`) for agent implementations inheriting from `AutomagikAgent`.
  - [ ] For each identified agent:
    - Apply similar refactoring as `SimpleAgent` or `StanAgent` depending on its prompt needs.
    - Ensure prompts are loaded from files and registered using `_register_code_defined_prompt`.
    - Update `run()` or equivalent methods to call `load_active_prompt_template` with appropriate `status_key`(s).

### Phase 3: Data Migration & Finalization
- [ ] **Step 7: Develop and Test Data Migration Script**
  - [ ] Create a script to:
    - Iterate through all entries in the `agents` table.
    - For each agent, read its current `system_prompt` text.
    - Call `prompt_repository.create_prompt` with this text, `agent_id`, `version=1`, `is_active=True`, `is_default_from_code=True`, `status_key="default"`, `name="Migrated Default Prompt"`.
    - Update the agent's `active_default_prompt_id` in the `agents` table with the new prompt's ID.
  - [ ] Test the script thoroughly in a development environment.
- [ ] **Step 8: Testing and Validation**
  - [ ] Write unit tests for new repository functions and `AutomagikAgent` methods.
  - [ ] Perform integration tests for each refactored agent to ensure prompts are loaded and used correctly.
  - [ ] Test prompt versioning and activation/deactivation (manual tests or new API endpoints if planned).
- [ ] **Step 9: Documentation**
  - [ ] Update any relevant developer documentation regarding prompt management.
  - [ ] Document the new `prompts` table and its fields.
  - [ ] Explain how to add/manage prompts for existing and new agents.

## Execution
- [ ] (Subtasks will be filled as work progresses)

## Summary
- [ ] Files modified: (Will list all files touched)
- [ ] Dependencies added/changed: (e.g., new Pydantic models, repository modules)
- [ ] Edge cases considered: Fallback for missing status_key prompts, multiple agents of same type.
- [ ] Known limitations: UI/API for managing prompts by users is out of scope for this task.
- [ ] Future impact points: Enables UI for prompt management, A/B testing of prompts. 