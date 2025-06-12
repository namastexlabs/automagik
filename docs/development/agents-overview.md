# Agent System Overview

This document provides an overview of the agent system within the Automagik Agents project, explaining core concepts, structure, and how agents interact with the broader system.

## Core Concepts

The agent system is designed to execute tasks autonomously or semi-autonomously using Large Language Models (LLMs) and a set of predefined tools. Key concepts include:

- **Agents:** Independent units responsible for processing input, maintaining state (memory), deciding on actions (which may involve calling tools or generating responses), and interacting with users or other systems. All agents extend `AutomagikAgent` with optional feature flags.
- **Memory:** Agents maintain state and conversation history. This is managed by the `MemoryHandler` (`src/agents/common/memory_handler.py`) which likely interacts with the database via `src/memory/`. See [Memory Management](../architecture/memory.md).
- **Tools:** Reusable functions or integrations that agents can invoke to perform specific actions beyond simple text generation (e.g., web search, database queries, API calls). Tool availability and usage are managed by the `ToolRegistry` (`src/agents/common/tool_registry.py`) and implemented in `src/tools/`.
- **Sessions & Context:** Interactions are typically managed within sessions (`SessionManager` in `src/agents/common/session_manager.py`), each having a unique ID. Context might include user ID, agent ID, session ID, and run ID.
- **Prompts:** Interactions with LLMs are driven by carefully constructed prompts, handled by the `PromptBuilder` (`src/agents/common/prompt_builder.py`).
- **Messages:** Communication involves parsing and formatting messages (user messages, agent responses, tool calls/outputs), handled by functions in `src/agents/common/message_parser.py`.

## Structure (`src/agents/`)

The agent-related code is primarily organized within the `src/agents/` directory:

- `src/agents/common/`: Contains shared utilities and handlers used across different agent implementations:
  - `memory_handler.py`: Manages agent memory interactions.
  - `message_parser.py`: Parses incoming/outgoing messages, extracts tool calls/outputs.
  - `prompt_builder.py`: Constructs prompts for LLMs.
  - `session_manager.py`: Handles session IDs, run IDs, and context.
  - `tool_registry.py`: Manages registration and lookup of available tools.
  - `dependencies_helper.py`: Assists with model settings, usage limits, etc.
  - `__init__.py`: Exports common utilities.
- `src/agents/models/`: Contains Pydantic models and the base `AutomagikAgent` class.
- `src/agents/pydanticai/<agent_name>/` (e.g., `src/agents/pydanticai/simple/`): Each subdirectory typically contains the specific implementation logic for a particular agent.
  - This might include the agent's main class, specific prompt templates, or custom logic.

## Agent Lifecycle (Conceptual)

A typical agent interaction might follow these steps:

1. **Initialization:** An agent instance is created, potentially loading configuration and tools.
2. **Session Start:** A new session is initiated (`create_session_id`, `create_run_id`).
3. **Receive Input:** The agent receives user input or a trigger.
4. **Parse Message:** The input message is parsed (`parse_user_message`).
5. **Load Memory:** Relevant conversation history or state is loaded (`MemoryHandler`).
6. **Build Prompt:** A prompt is constructed for the LLM, including history, user input, and available tools (`PromptBuilder`).
7. **LLM Call:** The prompt is sent to the configured LLM (e.g., OpenAI via `OPENAI_API_KEY`).
8. **Process Response:** The LLM response is received.
9. **Parse Response:** The response is parsed (`extract_tool_calls`, `extract_all_messages`).
10. **Tool Execution (if needed):**
    - If tool calls are identified, the `ToolRegistry` is used to find and execute the corresponding tools.
    - Tool outputs are collected.
    - The process might loop back to step 6 (Build Prompt) to send tool outputs back to the LLM for a final response.
11. **Generate Final Response:** A final response is formulated for the user.
12. **Update Memory:** The interaction (inputs, outputs, tool calls) is saved to memory (`MemoryHandler`, `format_message_for_db`).
13. **Session End:** The specific run or interaction concludes.

## Creating a New Agent

Follow these steps to create a new custom agent (e.g., `MyNewAgent`) based on the current architecture:

1.  **Create Directory Structure:**
    Create a new directory for your agent within `src/agents/pydanticai/` (or another applicable category):
    ```bash
    mkdir src/agents/pydanticai/my_new
    mkdir src/agents/pydanticai/my_new/prompts
    ```

2.  **Create Core Files:**
    Inside the new directory, create the following Python files:
    *   `src/agents/pydanticai/my_new/__init__.py` (Can potentially import and export the agent class)
    *   `src/agents/pydanticai/my_new/agent.py` (Will contain the main agent class)
    *   `src/agents/pydanticai/my_new/prompts/__init__.py` (Empty)
    *   `src/agents/pydanticai/my_new/prompts/prompt.py` (Will define the agent's system prompt)

3.  **Define the Agent Prompt (`prompts/prompt.py`):**
    Define the core instructions for your agent as a Python string. You can use `{{variable_name}}` for dynamic content injection from structured memory.
    ```python
    # src/agents/pydanticai/my_new/prompts/prompt.py
    MY_AGENT_PROMPT = """
    You are MyNewAgent. Your goal is to [... specific instructions ...].
    
    Personality: {{personality}}
    User Preferences: {{user_preferences}}
    
    Follow these guidelines:
    1. [...]
    2. [...]
    """
    ```

4.  **Implement the Agent Class (`agent.py`):**
    *   Import necessary components, including `AutomagikAgent` and your specific prompt.
    *   Define your class, inheriting from `AutomagikAgent`.
    *   Configure optional features via constructor parameters.
    *   Register tools using `self.tool_registry.register_default_tools()` and custom tools as needed.

    ```python
    # src/agents/pydanticai/my_new/agent.py
    import logging
    from typing import Dict, Optional

    from src.agents.models.automagik_agent import AutomagikAgent
    from src.agents.models.response import AgentResponse
    from src.memory.message_history import MessageHistory

    # Import this agent's specific prompt
    from .prompts.prompt import MY_AGENT_PROMPT

    logger = logging.getLogger(__name__)

    class MyNewAgent(AutomagikAgent):
        def __init__(self, config: Dict[str, str]) -> None:
            if config is None:
                config = {}
            
            # Configure optional features
            config.setdefault("enable_multi_prompt", False)  # Enable if needed
            # Multimodal is enabled by default with vision_model="openai:gpt-4o"
            
            super().__init__(config)
            
            # Set the agent prompt
            self._code_prompt_text = MY_AGENT_PROMPT
            
            # Initialize dependencies
            self.dependencies = self.create_default_dependencies()
            if self.db_id:
                self.dependencies.set_agent_id(self.db_id)
            
            # Register tools
            self.tool_registry.register_default_tools(self.context)
            # Add custom tools if needed:
            # self.tool_registry.register_tool(my_custom_tool)
            
            logger.info("MyNewAgent initialized")

        async def run(
            self, 
            input_text: str, 
            *, 
            multimodal_content=None, 
            system_message=None, 
            message_history_obj: Optional[MessageHistory] = None,
            channel_payload: Optional[dict] = None,
            message_limit: Optional[int] = 20
        ) -> AgentResponse:
            """Run the agent with the provided input."""
            
            # Initialize prompts if using multi-prompt
            if not self.prompt_manager.is_registered() and self.db_id:
                await self.initialize_prompts()
            
            # Use the base class implementation which handles:
            # - Multimodal processing (automatic vision model switching)
            # - Channel payload processing (WhatsApp/Evolution)
            # - Memory template variable substitution
            # - Tool execution and response formatting
            return await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )

    def create_agent(config: Dict[str, str]) -> MyNewAgent:
        """Factory function to create the agent."""
        try:
            return MyNewAgent(config)
        except Exception as e:
            logger.error(f"Failed to create MyNewAgent: {e}")
            from src.agents.models.placeholder import PlaceholderAgent
            return PlaceholderAgent(config)
    ```

5.  **Make Agent Discoverable:**
    Add your agent to the re-exports in `src/agents/pydanticai/__init__.py`:
    ```python
    from .my_new.agent import MyNewAgent
    ```

6.  **Testing:**
    Test your new agent thoroughly using the CLI or API (see [Running the Project](../getting-started/running.md)). Ensure it handles prompts, uses tools (if any), and manages memory correctly.

## Available Agents

The Automagik Agents framework includes several agents, all built on the unified `AutomagikAgent` base class with feature flags:

### Agent Architecture

All agents now inherit directly from `AutomagikAgent` and configure features through constructor parameters:

| Feature | Configuration | Description |
|---------|---------------|-------------|
| **Multimodal Processing** | `vision_model`, `supported_media`, `auto_enhance_prompts` | Process images alongside text (enabled by default) |
| **Multi-Prompt Support** | `enable_multi_prompt=True` | Status-based prompt switching |
| **WhatsApp Integration** | Built-in via channel handlers | Evolution API integration |
| **Memory Templates** | Built-in | Dynamic variable substitution in prompts |
| **Tool Registry** | Built-in | Default and custom tool registration |

### Simple Agent

**Location**: `src/agents/pydanticai/simple/`  
**Philosophy**: Minimal, focused agent for straightforward tasks

**Configuration**:
```python
config = {
    "vision_model": "openai:gpt-4o",  # Default multimodal
    "supported_media": ["image", "audio", "document"],
    "auto_enhance_prompts": True
}
```

**Best For**:
- Direct user interactions
- WhatsApp chatbots
- Image analysis tasks
- Simple automation workflows

### FlashinhoPro Agent

**Location**: `src/agents/pydanticai/flashinho/`  
**Philosophy**: Pro/Free tier agent with multimodal and multi-prompt support

**Configuration**:
```python
config = {
    "enable_multi_prompt": True,  # Status-based prompts
    "vision_model": "openai:gpt-4o",
    "auto_enhance_prompts": True
}
```

**Features**:
- Pro/Free model switching logic
- Multi-prompt management
- Full multimodal support
- Image analysis tools

### Stan Agent

**Location**: `src/agents/pydanticai/stan/`  
**Philosophy**: Business integration agent with BlackPearl CRM

**Configuration**:
```python
config = {
    "enable_multi_prompt": True,  # Status-based prompts
    "vision_model": "openai:gpt-4o"
}
```

**Features**:
- BlackPearl CRM integration
- Contact management
- Status-based prompt loading
- Specialized business tools (product, backoffice, order agents)

### Sofia Agent

**Location**: `src/agents/pydanticai/sofia/`  
**Philosophy**: Full-featured agent with MCP server integration

**Features**:
- MCP server integration
- Advanced tool loading
- Complex workflow orchestration
- Extended integrations

## Feature Details

### Multimodal Processing (All Agents)

All agents support multimodal processing by default:
- Automatic vision model switching when images are present
- Support for HTTP/HTTPS image URLs
- Multiple images per request
- Auto-enhanced system prompts with media context

**Configuration**:
```python
config = {
    "vision_model": "openai:gpt-4o",  # Model for vision tasks
    "supported_media": ["image", "audio", "document"],
    "auto_enhance_prompts": True  # Auto-enhance prompts for media
}
```

### Multi-Prompt Support (Optional)

Agents can enable status-based prompt switching:
```python
config = {"enable_multi_prompt": True}
```

This enables:
- Automatic prompt directory discovery
- Status-based prompt loading (`load_prompt_by_status()`)
- Dynamic prompt switching based on user state

### WhatsApp Integration (Built-in)

All agents include Evolution API integration through the channel handler system:
- Automatic user information extraction
- Context-aware tool wrappers
- Group chat support
- Message formatting and delivery

### Memory Templates (Built-in)

All agents support dynamic variable substitution in prompts:
```python
PROMPT = """
You are an agent.
User: {{user_name}}
Preferences: {{user_preferences}}
Context: {{recent_context}}
"""
```

Variables are automatically populated from the knowledge graph.

## Migration from Specialized Classes

The framework previously used specialized inheritance classes that have been consolidated:

### Removed Classes
- `EvolutionAgent` → Use `AutomagikAgent` (WhatsApp support is built-in)
- `MultiPromptAgent` → Use `AutomagikAgent` with `enable_multi_prompt=True`
- `BlackPearlAgent` → Use `AutomagikAgent` and copy helper methods locally
- `MultimodalAgent` → Use `AutomagikAgent` (multimodal is default)
- `APIIntegrationAgent` → Use `AutomagikAgent` with custom tools
- `DiscordAgent` → Use `AutomagikAgent` with Discord tools

### Migration Pattern
```python
# Before
class MyAgent(SpecializedAgent):
    def __init__(self, config):
        super().__init__(config)

# After  
class MyAgent(AutomagikAgent):
    def __init__(self, config):
        if config is None:
            config = {}
        config.setdefault("enable_multi_prompt", True)  # If needed
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)
```

## Capabilities and Limitations

### Capabilities
- **Unified Architecture**: Single base class with feature flags
- **Multimodal Understanding**: Process images alongside text using vision-capable models
- **WhatsApp Integration**: Send/receive messages through Evolution API
- **External Tool Access**: Interact with databases, APIs, and external services
- **Memory Persistence**: Store and retrieve user information and preferences
- **Reliable Execution**: Retry logic and concurrency control for robust operation
- **Dynamic Prompts**: Template variables and multi-prompt support

### Limitations
- **Model Dependency**: Performance depends on underlying LLM capabilities
- **Tool Quality**: Effectiveness limited by available tool implementations
- **Memory Complexity**: Long-term memory and context management challenges
- **Hallucination Risk**: Standard LLM limitations apply
- **Resource Usage**: Vision models require additional resources

## Further Reading

### Core Documentation
- [Memory Management](../architecture/memory.md)
- [Database Documentation](../architecture/database.md)
- [API Documentation](./api.md)

### Feature Guides
- [Multimodal Processing](../integrations/multimodal.md)
- [WhatsApp Integration](../integrations/whatsapp.md)
- [MCP Server Integration](../integrations/mcp.md)

### Development
- [Agent Development Patterns](./agent-mocking.md)
- [Configuration Guide](../getting-started/configuration.md)
- [Running the Project](../getting-started/running.md) 