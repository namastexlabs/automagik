# Prompt Management System

This document describes the prompt management system for the Automagik agents platform.

## Overview

The prompt management system provides a way to store, version, and manage system prompts for agents. It supports:

- Multiple versions of prompts for each agent
- Different prompts based on status keys (e.g., "default", "APPROVED", "REJECTED")
- Tracking whether prompts come from code or from manual edits
- Setting active prompts per agent and status key

## Database Schema

### Prompts Table

The `prompts` table stores all versions of prompts:

| Column                | Type        | Description                                       |
|-----------------------|-------------|---------------------------------------------------|
| id                    | SERIAL      | Primary key                                       |
| agent_id              | INTEGER     | Foreign key to agents.id                          |
| prompt_text           | TEXT        | The actual prompt content                         |
| version               | INTEGER     | Version number (auto-incremented per agent/status)|
| is_active             | BOOLEAN     | Whether this is the active prompt for this status |
| is_default_from_code  | BOOLEAN     | Whether this prompt was defined in code          |
| status_key            | VARCHAR     | Status key (e.g., "default", "APPROVED")         |
| name                  | VARCHAR     | Human-readable name for the prompt               |
| created_at            | TIMESTAMP   | When this prompt was created                      |
| updated_at            | TIMESTAMP   | When this prompt was last updated                 |

The table has a unique constraint on `(agent_id, status_key, version)` to ensure version numbers are unique per agent and status key.

### Agents Table Changes

The `agents` table now has an `active_default_prompt_id` column that references the active prompt for the agent's default status:

| Column                    | Type        | Description                                       |
|---------------------------|-------------|---------------------------------------------------|
| active_default_prompt_id  | INTEGER     | Foreign key to prompts.id                         |

## Repository Functions

The `src/db/repository/prompt.py` file provides the following functions:

- `get_prompt_by_id(prompt_id)`: Get a prompt by ID
- `get_active_prompt(agent_id, status_key)`: Get the active prompt for an agent and status key
- `find_code_default_prompt(agent_id, status_key)`: Find the default prompt from code for an agent and status key
- `get_latest_version_for_status(agent_id, status_key)`: Get the latest version number for a prompt
- `create_prompt(prompt_data)`: Create a new prompt
- `update_prompt(prompt_id, update_data)`: Update an existing prompt
- `set_prompt_active(prompt_id, is_active)`: Set a prompt as active/inactive
- `get_prompts_by_agent_id(agent_id, status_key)`: Get all prompts for an agent
- `delete_prompt(prompt_id)`: Delete a prompt

## AutomagikAgent Integration

The `AutomagikAgent` class has been enhanced with the following methods:

- `_register_code_defined_prompt(code_prompt_text, status_key, prompt_name, is_primary_default)`: Register a prompt defined in code
- `load_active_prompt_template(status_key)`: Load the active prompt template for the given status key
- `get_filled_system_prompt()`: Get the system prompt filled with memory variables (now uses the loaded prompt template)

## Agent Implementations

There are two main patterns for using the prompt management system in agent implementations:

### Simple Agents (Single Prompt)

`SimpleAgent` uses a single prompt with the "default" status key:

```python
# In __init__
self._code_prompt_text = AGENT_PROMPT
self._prompt_registered = False

# In run()
if not self._prompt_registered and self.db_id:
    await self._register_code_defined_prompt(
        self._code_prompt_text,
        status_key="default",
        prompt_name="Default SimpleAgent Prompt", 
        is_primary_default=True
    )
    self._prompt_registered = True

# Load the active prompt template
await self.load_active_prompt_template(status_key="default")
```

### Complex Agents (Multiple Status-Based Prompts)

`StanAgent` uses multiple prompts based on user status:

```python
# In __init__
self._prompts_registered = False

# Register all prompts from prompt files
async def _register_all_prompts(self):
    # Find prompt files, dynamically import them, and register with different status_keys
    # ...

# Select and load the appropriate prompt based on user status
async def _use_prompt_based_on_contact_status(self, status, contact_id):
    # Load the prompt matching the user's status
    # Fall back to default if needed
    # ...

# In run()
# Register prompts if needed
if not self._prompts_registered and self.db_id:
    await self._register_all_prompts()
    
# Load the appropriate prompt based on user status
await self._use_prompt_based_on_contact_status(user_status, user_id)
```

## Migration

A migration script (`scripts/migrate_agent_prompts.py`) is provided to migrate existing agent system prompts to the new system:

```bash
# Run in dry-run mode (no changes)
python scripts/migrate_agent_prompts.py --dry-run

# Migrate prompts
python scripts/migrate_agent_prompts.py

# Migrate prompts and drop the system_prompt column
python scripts/migrate_agent_prompts.py --drop
```

## Best Practices

1. **Agent Implementation:**
   - Always use `await self._register_code_defined_prompt()` to register prompts from code
   - Always call `await self.load_active_prompt_template()` before using the prompt
   - Use the status key feature for agents with different modes or states
   
2. **Naming Prompts:**
   - Use descriptive names for prompts to make them easier to manage
   - Include the agent name and status in the prompt name
   
3. **Versioning:**
   - Let the system handle versioning automatically (don't set version manually)
   - The system will automatically increment the version number for each new prompt
   
4. **Status Keys:**
   - Use "default" for simple agents with a single prompt
   - Use uppercase status keys for status-based prompts (e.g., "APPROVED", "REJECTED")
   - Keep status keys consistent across the codebase 