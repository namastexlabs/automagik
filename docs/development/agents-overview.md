# Agent System Overview

This document provides an overview of the agent system within the Automagik Agents project, explaining core concepts, structure, and how agents interact with the broader system.

## Core Concepts

The agent system is designed to execute tasks autonomously or semi-autonomously using Large Language Models (LLMs) and a set of predefined tools. Key concepts include:

- **Agents:** Independent units responsible for processing input, maintaining state (memory), deciding on actions (which may involve calling tools or generating responses), and interacting with users or other systems. (e.g., `SimpleAgent` located in `src/agents/pydanticai/simple/`).
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
- `src/agents/models/`: Likely contains Pydantic models specific to agent data structures.
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

Follow these steps to create a new custom agent (e.g., `MyNewAgent`) based on the existing patterns:

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
    *   Implement the `__init__` method:
        *   Call `super().__init__(config, MY_AGENT_PROMPT)`.
        *   Configure `AutomagikAgentsDependencies`, setting at least the `model_name`.
        *   Register tools using `self.tool_registry.register_default_tools()` and `self.tool_registry.register_tool(custom_tool)` for any custom tools needed (imported from `src/tools/`).
    *   Implement `_initialize_pydantic_agent` (can often be adapted directly from `SimpleAgent`).
    *   Implement the `run` method (can often be adapted directly from `SimpleAgent`, ensuring input preparation and response processing match your agent's needs).

    ```python
    # src/agents/pydanticai/my_new/agent.py
    import logging
    from typing import Dict, Any, Optional
    
    from pydantic_ai import Agent # PydanticAI's agent
    from src.agents.models.automagik_agent import AutomagikAgent # Base class
    from src.agents.models.dependencies import AutomagikAgentsDependencies
    from src.agents.models.response import AgentResponse
    from src.memory.message_history import MessageHistory
    from src.agents.common.dependencies_helper import get_model_name, parse_model_settings, create_model_settings, add_system_message_to_history
    from src.agents.common.message_parser import extract_all_messages, extract_tool_calls, extract_tool_outputs
    
    # Import this agent's specific prompt
    from .prompts.prompt import MY_AGENT_PROMPT
    
    # (Import any custom tools if needed from src.tools)
    # from src.tools.my_custom_tool import my_custom_tool 
    
    logger = logging.getLogger(__name__)
    
    class MyNewAgent(AutomagikAgent):
        def __init__(self, config: Dict[str, str]) -> None:
            super().__init__(config, MY_AGENT_PROMPT)
            self._agent_instance: Optional[Agent] = None
            
            self.dependencies = AutomagikAgentsDependencies(
                model_name=get_model_name(config, default_model="openai:gpt-4.1-mini"), # Specify desired model
                model_settings=parse_model_settings(config)
            )
            if self.db_id: self.dependencies.set_agent_id(self.db_id)
            
            # Register tools
            self.tool_registry.register_default_tools(self.context) 
            # self.tool_registry.register_tool(my_custom_tool) # Uncomment to add custom tools
            
            logger.info("MyNewAgent initialized")

        async def _initialize_pydantic_agent(self) -> None:
            if self._agent_instance is not None: return
            
            model_name = self.dependencies.model_name
            model_settings = create_model_settings(self.dependencies.model_settings)
            tools = self.tool_registry.convert_to_pydantic_tools()
            
            try:
                self._agent_instance = Agent(
                    model=model_name,
                    system_prompt=self.system_prompt, # Uses the base class prompt
                    tools=tools,
                    model_settings=model_settings,
                    deps_type=AutomagikAgentsDependencies
                )
                logger.info(f"Initialized MyNewAgent PydanticAI instance with {len(tools)} tools")
            except Exception as e:
                logger.error(f"Failed to initialize MyNewAgent PydanticAI instance: {e}")
                raise
        
        async def run(self, input_text: str, *, message_history_obj: Optional[MessageHistory] = None, message_limit: Optional[int] = 20, **kwargs) -> AgentResponse:
            if self.db_id: await self.initialize_memory_variables(getattr(self.dependencies, 'user_id', None))
            await self._initialize_pydantic_agent()
            
            pydantic_message_history = []
            if message_history_obj: pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=message_limit)
            
            filled_system_prompt = await self.get_filled_system_prompt(user_id=getattr(self.dependencies, 'user_id', None))
            if filled_system_prompt: pydantic_message_history = add_system_message_to_history(pydantic_message_history, filled_system_prompt)
                
            if hasattr(self.dependencies, 'set_context'): self.dependencies.set_context(self.context)

            try:
                result = await self._agent_instance.run(
                    input_text, # Assuming text input for simplicity
                    message_history=pydantic_message_history,
                    usage_limits=getattr(self.dependencies, "usage_limits", None),
                    deps=self.dependencies
                )
                
                all_messages = extract_all_messages(result)
                tool_calls = [call for msg in all_messages for call in extract_tool_calls(msg)]
                tool_outputs = [output for msg in all_messages for output in extract_tool_outputs(msg)]
                
                return AgentResponse(
                    text=result.data,
                    success=True,
                    tool_calls=tool_calls,
                    tool_outputs=tool_outputs,
                    raw_message=all_messages,
                    system_prompt=filled_system_prompt,
                )
            except Exception as e:
                logger.error(f"Error running MyNewAgent: {e}", exc_info=True)
                return AgentResponse(text=f"Error: {e}", success=False, error_message=str(e))
    ```

5.  **Make Agent Discoverable:**
    How the application finds new agents isn't explicitly defined in the code snippets reviewed. It might involve:
    *   Adding an import for your new agent class in `src/agents/pydanticai/__init__.py` or a central registry.
    *   Relying on naming conventions and dynamic loading based on the directory structure.
    *   Updating the `AM_AGENTS_NAMES` environment variable if pre-loading is used.
    *(Further investigation or checking project conventions is needed for this step)*.

6.  **Testing:**
    Test your new agent thoroughly using the CLI or API (see [Running the Project](../getting-started/running.md)). Ensure it handles prompts, uses tools (if any), and manages memory correctly.

*(This guide provides a template based on SimpleAgent. Specific implementations might require adjustments.)*

## Available Agents

The Automagik Agents framework currently includes two main agents with synchronized features:

### Agent Comparison

| Feature | Simple Agent | Sofia Agent | Description |
|---------|--------------|-------------|-------------|
| **Base Framework** | ✅ AutomagikAgent | ✅ AutomagikAgent | Both extend the same base class |
| **Multimodal Processing** | ✅ Full Support | ✅ Full Support | Process images alongside text |
| **WhatsApp Integration** | ✅ Full Support | ✅ Full Support | Evolution API integration |
| **Reliability Features** | ✅ Retry Logic | ✅ Retry Logic | Exponential backoff and semaphore control |
| **Memory Integration** | ✅ Template Variables | ✅ Template Variables | Graphiti knowledge graph |
| **MCP Server Support** | ❌ Intentionally Excluded | ✅ Full Support | Dynamic tool loading |
| **Sub-Agent Patterns** | ❌ Minimal Design | ✅ Airtable Integration | Wrapper patterns for specialized agents |
| **Tool Registry** | ✅ Basic Tools | ✅ Extended Tools | Default + specialized tools |
| **Design Philosophy** | **Minimal & Focused** | **Full-Featured** | Different use cases |

### Simple Agent

**Location**: `src/agents/pydanticai/simple/`  
**Philosophy**: Minimal, focused agent for straightforward tasks

**Key Features**:
- ✅ **Multimodal processing** - Handle images and text
- ✅ **WhatsApp integration** - Evolution API support
- ✅ **Reliability features** - Retry logic and concurrency control
- ✅ **Memory templates** - Dynamic prompt variables
- ❌ **No MCP servers** - Maintains simplicity
- ❌ **No sub-agents** - Single-purpose design

**Best For**:
- Direct user interactions
- WhatsApp chatbots
- Image analysis tasks
- Simple automation workflows

### Sofia Agent

**Location**: `src/agents/pydanticai/sofia/`  
**Philosophy**: Full-featured agent with advanced capabilities

**Key Features**:
- ✅ **All Simple agent features** - Complete feature parity
- ✅ **MCP server integration** - Dynamic tool loading
- ✅ **Sub-agent patterns** - Airtable agent wrapper
- ✅ **Extended tool registry** - Specialized integrations
- ✅ **Advanced workflows** - Complex task orchestration

**Best For**:
- Complex business workflows
- Multi-system integrations
- Project management tasks
- Advanced automation scenarios

## Synchronized Features

Both agents now share core capabilities through the Agent Feature Synchronization project:

### Multimodal Processing

Both agents support image processing with:
- HTTP/HTTPS image URLs
- Multiple images per request
- PydanticAI ImageUrl conversion
- Graceful fallback handling

**Documentation**: [Multimodal Processing Guide](../integrations/multimodal.md)

### WhatsApp Integration

Both agents include Evolution API integration:
- Send/receive WhatsApp messages
- Context-aware tool wrappers
- Group chat support
- User information persistence

**Documentation**: [WhatsApp Integration Guide](../integrations/whatsapp.md)

### Reliability Features

Both agents implement robust error handling:
- Exponential backoff retry logic
- LLM semaphore concurrency control
- Configurable retry attempts
- Comprehensive error logging

### Memory Integration

Both agents support memory templates:
- Dynamic variable substitution
- User preference storage
- Context-aware responses
- Graphiti knowledge graph integration

## MCP Server Integration (Sofia Only)

Sofia agent includes Model Context Protocol support:
- Dynamic server loading
- Tool discovery and registration
- Server lifecycle management
- Linear, PostgreSQL, and Memory servers

**Documentation**: [MCP Integration Guide](../integrations/mcp.md)

## Capabilities and Limitations

### Capabilities
- **Multimodal Understanding**: Process images alongside text using vision-capable models
- **WhatsApp Integration**: Send/receive messages through Evolution API
- **External Tool Access**: Interact with databases, APIs, and external services
- **Memory Persistence**: Store and retrieve user information and preferences
- **Reliable Execution**: Retry logic and concurrency control for robust operation
- **Dynamic Tool Loading**: (Sofia) Load tools from MCP servers dynamically

### Limitations
- **Model Dependency**: Performance depends on underlying LLM capabilities
- **Tool Quality**: Effectiveness limited by available tool implementations
- **Memory Complexity**: Long-term memory and context management challenges
- **Hallucination Risk**: Standard LLM limitations apply
- **Resource Usage**: Vision models and MCP servers require additional resources

## Further Reading

### Core Documentation
- [Memory Management](../architecture/memory.md)
- [Database Documentation](../architecture/database.md)
- [API Documentation](./api.md)
- [MCP Integration](../integrations/mcp.md)

### Feature Guides
- [Multimodal Processing](../integrations/multimodal.md)
- [WhatsApp Integration](../integrations/whatsapp.md)
- [MCP Server Integration](../integrations/mcp.md)

### Development
- [Agent Development Patterns](./agent-mocking.md)
- [Configuration Guide](../getting-started/configuration.md)
- [Running the Project](../getting-started/running.md) 