# Database

(Placeholder for database documentation) 

# Database Interaction

This document describes how the Automagik Agents project interacts with the PostgreSQL database, focusing on the structure, models, and access patterns used.

## Overview

The database layer is located in the `src/db/` directory and utilizes PostgreSQL as the backend storage. It follows a **Repository Pattern** to abstract database operations and ensure clean, type-safe interactions.

Key components:

*   **Connection (`src/db/connection.py`):** Manages the database connection pool and provides low-level query execution functions.
*   **Models (`src/db/models.py`):** Pydantic models (`User`, `Agent`, `Session`, `Message`, `Memory`) that define the structure of the data corresponding to database tables. These models ensure type safety.
*   **Repositories (`src/db/repository/`):** Modules containing functions for specific CRUD (Create, Read, Update, Delete) operations for each model/entity (e.g., `src/db/repository/agent.py`, `src/db/repository/user.py`).
*   **Migrations (`src/db/migrations/`):** Likely contains database schema migration files (e.g., using Alembic) to manage changes to the database structure over time.
*   **Instructions (`src/db/db_instructions.md`):** Provides more in-depth documentation and examples directly within the codebase.

## Data Models

The primary data models defined in `src/db/models.py` are:

*   **`User`:** Represents users interacting with the system (contains `id`, `email`, `phone_number`, `user_data`, timestamps).
*   **`Agent`:** Represents the AI agents configured in the system (contains `id`, `name`, `type`, `model`, `description`, `config`, `active`, `run_id`, `system_prompt`, timestamps).
*   **`Session`:** Represents a specific interaction session between a user and an agent (contains `id`, `user_id`, `agent_id`, `name`, `platform`, `metadata`, timestamps).
*   **`Message`:** Represents individual messages within a session (contains `id`, `session_id`, `user_id`, `agent_id`, `role`, `text_content`, `media_url`, tool calls/outputs, timestamps, etc.). This table is crucial for storing conversation history.
*   **`Memory`:** Represents stored memories or persistent state associated with agents or sessions (contains `id`, `name`, `description`, `content`, `session_id`, `user_id`, `agent_id`, timestamps). See [Memory Management](./memory.md) for how this is used.

Refer to `src/db/models.py` for the exact fields, types, and descriptions for each model.

## Repository Pattern Usage

Instead of writing raw SQL queries or interacting directly with an ORM in the main application logic, the system uses repository functions defined in `src/db/repository/`. Each entity (Agent, User, etc.) has its own repository module.

**Example Usage:**

```python
from src.db import (
    # Models (for creating data)
    Agent, User, Session,
    
    # Repository functions (for DB operations)
    create_agent, 
    get_user_by_email,
    list_sessions,
    update_session,
    delete_agent
)

# --- Agent Operations ---
# Create a new agent object
new_agent_data = Agent(
    name="docs_agent",
    type="helpful_writer",
    model="gpt-4.1-mini",
    description="Writes project documentation"
)
# Save to database
agent_id = create_agent(new_agent_data)
print(f"Created agent with ID: {agent_id}")

# --- User Operations ---
# Get a user
user = get_user_by_email("developer@example.com")
if user:
    print(f"Found user: {user.id}")

# --- Session Operations ---
# List sessions for a specific user
if user:
    user_sessions, total = list_sessions(user_id=user.id, page=1, page_size=10)
    print(f"User {user.id} has {total} sessions. Showing page 1:")
    for session in user_sessions:
        print(f"- Session ID: {session.id}, Name: {session.name}")
```

**Benefits:**

*   **Abstraction:** Hides the underlying database implementation details.
*   **Consistency:** Provides a uniform way to interact with different data entities.
*   **Testability:** Repositories can be mocked or tested independently.
*   **Maintainability:** Database logic is centralized within the `src/db/repository/` modules.

## Database Schema (Conceptual)

While the exact schema depends on the migration files in `src/db/migrations/`, the models suggest the following key tables and potential relationships:

*   `users`: Stores user information.
*   `agents`: Stores agent configurations. See [Agent System Overview](./agents_overview.md).
*   `sessions`: Links `users` and `agents`, representing interaction contexts.
*   `messages`: Stores individual messages, linked to `sessions`, `users`, and `agents`. Contains conversation history and tool interactions. See [Memory Management](./memory.md).
*   `memories`: Stores persistent agent memory, potentially linked to `sessions`, `users`, or `agents`. See [Memory Management](./memory.md).

*(A visual diagram like Mermaid could be added here if the schema is formally documented or easily inferred from migrations.)*

## Further Details

For more comprehensive examples, specific function signatures, and detailed explanations of the database layer, please refer to the primary source of truth: **[`src/db/db_instructions.md`](mdc:src/db/db_instructions.md)**. 