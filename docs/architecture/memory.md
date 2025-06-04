# Memory Management

This document explains how memory and state are managed for agents within the Automagik Agents project.

## Overview

Effective memory management is crucial for agents to maintain context, recall past interactions, and personalize responses. In this project, "memory" encompasses two primary concepts:

1. **Conversation History:** The sequence of messages exchanged between the user, the agent, and tools within a specific session.
2. **Structured Memory:** Persistent key-value storage associated with an agent and potentially a user, used for recalling specific facts, preferences, or configurations over longer periods.

Both types of memory are primarily persisted in the PostgreSQL database.

## Conversation History

- **Storage:** The chronological history of interactions within a session is stored in the `messages` database table. Each row represents a single message turn (user input, agent response, system message, tool call, tool output).
- **Model:** Defined by the `Message` Pydantic model in `src/db/models.py`.
- **Management:** The `MessageHistory` class in `src/memory/message_history.py` is responsible for managing this history.
  - It provides methods like `add()` (for user messages), `add_response()` (for agent/tool messages), `add_system_prompt()`, and `get_formatted_pydantic_messages()`.
  - It interacts directly with the message repository functions (e.g., `create_message`, `list_messages`) located in `src/db/repository/message.py` to read from and write to the `messages` table.
  - Each `MessageHistory` instance is typically associated with a specific `session_id`.
- **Usage:** The conversation history is retrieved (often with a limit on the number of recent messages) and used by the `PromptBuilder` (`src/agents/common/prompt_builder.py`) to construct the context window sent to the LLM for generating the next response.

## Structured Memory (Key-Value Store)

- **Purpose:** To store specific pieces of information that need to persist beyond a single conversation or that define agent characteristics or user preferences.
- **Storage:** Stored in the `memories` database table.
- **Model:** Defined by the `Memory` Pydantic model in `src/db/models.py` (fields include `name`, `content`, `description`, `agent_id`, `user_id`, `read_mode`, `access`).
- **Management:** The `MemoryHandler` class in `src/agents/common/memory_handler.py` provides static methods to interact with this structured memory.
  - `initialize_memory_variables_sync`: Ensures specific memory keys (often derived from prompt templates) exist in the database for a given agent/user, creating them with default values if necessary.
  - `store_memory_sync`: Creates or updates a specific memory key-value pair.
  - `fetch_memory_vars`: Retrieves the content of specified memory keys for an agent/user.
  - These methods interact directly with the memory repository functions (e.g., `get_memory_by_name`, `create_memory`, `update_memory`) located in `src/db/repository/memory.py`.
- **Usage:** Structured memory values fetched via `fetch_memory_vars` are often used by the `PromptBuilder` to inject specific information (like user preferences or agent capabilities defined in memory) into the system prompt or other parts of the LLM prompt.

## Persistence and Retrieval

- Both conversation history (`messages` table) and structured memory (`memories` table) are persisted in the PostgreSQL database.
- Retrieval is handled by the respective repository functions, which are called by `MessageHistory` and `MemoryHandler`.
- There is no mention of an explicit in-memory caching layer in the analyzed code, suggesting that data is typically fetched from the database when needed, though the database connection pool (`src/db/connection.py`) helps manage connection efficiency.

## Further Reading

- **[Database Documentation](./database.md)**
- [`src/memory/message_history.py`](mdc:src/memory/message_history.py)
- [`src/agents/common/memory_handler.py`](mdc:src/agents/common/memory_handler.py) ([Agent System Overview](../development/agents-overview.md))
- [`src/db/models.py`](mdc:src/db/models.py)
- [`src/db/repository/message.py`](mdc:src/db/repository/message.py)
- [`src/db/repository/memory.py`](mdc:src/db/repository/memory.py) 