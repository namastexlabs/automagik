# Architecture Decisions Record - REVISED

## ADR-001: Model Descriptor Pattern for Clean Model Selection

### Context
Current model selection in AutomagikAgent requires complex configuration through multiple layers (config, dependencies, framework), making it difficult to understand and maintain. Agents like FlashinhoPro have complex model switching logic scattered across initialization and runtime methods.

### Decision
Implement a **Model Descriptor Pattern** that provides clean, declarative model selection through class-level attributes while handling all complexity behind the scenes.

### Rationale
- **Simplicity**: Enables single-line model declarations: `model = "openai:gpt-4o"`
- **Flexibility**: Supports dynamic model selection through callable patterns
- **Automatic Propagation**: Descriptor handles updating all dependent objects automatically
- **Backward Compatibility**: Existing config-based approach continues to work
- **Framework Agnostic**: Works with PydanticAI, Claude Code, and future frameworks

### Implementation Pattern
```python
class MyAgent(AutomagikAgent):
    model = "openai:gpt-4o"  # Static model selection
    
class SmartAgent(AutomagikAgent):
    def _select_model(self, context):
        return "pro-model" if context.user.is_pro else "free-model"
    model = _select_model  # Dynamic model selection
```

### Consequences
- **Positive**: Dramatically simplifies agent development, reduces boilerplate code
- **Positive**: Centralizes model selection logic, easier debugging and maintenance
- **Negative**: Requires migration of existing agents to new pattern
- **Negative**: Adds complexity to AutomagikAgent base class

### Alternatives Considered
1. **Configuration-only approach**: Rejected due to continued complexity
2. **Framework-specific solutions**: Rejected due to coupling concerns
3. **Decorator pattern**: Rejected due to Python class definition limitations

---

## ADR-002: Virtual Agents Using Existing Database Infrastructure

### Context
Current agent deployment requires code changes, rebuilds, and deployments for each new agent. There's no way to create specialized agents dynamically or manage agent configurations centrally.

### Decision
Implement **Virtual Agents** by leveraging the existing `agents` table and adding a configuration flag to distinguish database-only agents from code-based agents.

### Rationale
- **Zero New Tables**: Use existing `agents` table with `config.agent_source = "virtual"`
- **Simplicity**: Virtual agents are just regular agents without code files
- **Existing Infrastructure**: Leverage all current patterns (routing, execution, etc.)
- **Clear Distinction**: `agent_source` flag clearly separates virtual from code-based agents

### Architecture Components
1. **Enhanced Config Field**: Use existing `config` JSON field with `agent_source` indicator
2. **Agent Factory Logic**: Detect virtual agents and load everything from database
3. **Existing API Routes**: No new endpoints needed, `/agent/{name}/run` works for all
4. **Tool Integration**: Use existing MCP and tool infrastructure

### Configuration Schema
```json
{
  "agent_source": "virtual",
  "default_model": "openai:gpt-4o",
  "tool_config": {
    "enabled_tools": ["search", "memory", "evolution_send_message"],
    "tool_permissions": {
      "search": {"max_results": 10}
    }
  }
}
```

### Implementation Strategy
```python
# In AutomagikAgent factory
if config.get("agent_source") == "virtual":
    # Load everything from database config
    # No code file lookup needed
    return create_virtual_agent_instance(config)
else:
    # Existing code-based agent behavior
    return create_code_based_agent(agent_name)
```

### Consequences
- **Positive**: Minimal code changes, leverages existing infrastructure
- **Positive**: No database migrations or new tables required
- **Positive**: Virtual agents behave identically to code-based agents
- **Negative**: Config JSON field becomes more complex for virtual agents

### Alternatives Considered
1. **New virtual_agents table**: Rejected due to unnecessary complexity
2. **New agent types**: Rejected, `type="pydanticai"` works for both
3. **Separate VirtualAgent class**: Rejected, AutomagikAgent handles both

---

## ADR-003: Tool Management and Discovery System

### Context
Need ability to list available tools, understand their capabilities, and execute them directly for testing and virtual agent configuration.

### Decision
Create a **Tool Discovery and Execution API** that leverages existing MCP infrastructure and code-based tools with a unified interface.

### Rationale
- **Existing Infrastructure**: MCP servers already track `tools_discovered`
- **Unified Interface**: All tools use `RunContext[Dict]` pattern consistently
- **Tool Types**: Support 'mcp' (from MCP servers) and 'code' (built-in tools)
- **Human Readable**: Use tool names instead of server IDs for configuration

### API Design
```python
# List all available tools with metadata
GET /tools
# Response:
[
  {
    "name": "search",
    "type": "mcp", 
    "description": "Search the knowledge base",
    "server_name": "knowledge_base_server",
    "context_signature": "RunContext[Dict]",
    "parameters": [
      {"name": "query", "type": "str", "required": true},
      {"name": "max_results", "type": "int", "required": false}
    ]
  },
  {
    "name": "send_message", 
    "type": "code",
    "description": "Send message via Evolution API",
    "module": "src.tools.evolution.tool",
    "context_signature": "RunContext[Dict]",
    "parameters": [
      {"name": "phone", "type": "str", "required": true},
      {"name": "message", "type": "str", "required": true}
    ]
  }
]

# Execute tool directly with context
POST /tools/{tool_name}/run
# Body:
{
  "context": {
    "agent_name": "customer_support",
    "user_id": "user123",
    "session_id": "session456"
  },
  "parameters": {
    "query": "product pricing",
    "max_results": 5
  }
}
```

### Tool Configuration in Virtual Agents
```json
{
  "agent_source": "virtual",
  "default_model": "openai:gpt-4o",
  "tool_config": {
    "enabled_tools": ["search", "memory", "send_message"],
    "tool_permissions": {
      "search": {"max_results": 10},
      "send_message": {"rate_limit": 5}
    }
  }
}
```

### Implementation Strategy
1. **Tool Discovery**: Scan MCP servers' `tools_discovered` + enumerate code-based tools
2. **Unified Execution**: Common interface that routes to MCP or code tools
3. **Permission Validation**: Check tool_config permissions before execution
4. **Context Injection**: Provide agent context to all tool executions

### Consequences
- **Positive**: Unified tool management across MCP and code tools
- **Positive**: Human-readable tool names in configurations
- **Positive**: Direct tool testing capabilities for development
- **Negative**: Need to maintain tool discovery logic as tools change

---

## ADR-004: Simplified Agent Factory Pattern

### Context
Virtual agents need to be created dynamically from database configuration without requiring code files, while maintaining compatibility with existing code-based agents.

### Decision
Enhance the existing **AutomagikAgent factory** to detect and handle virtual agents through configuration flags.

### Rationale
- **Single Factory**: One factory handles both virtual and code-based agents
- **Configuration-Driven**: Virtual agents defined entirely through database config
- **Existing Patterns**: Reuse all current initialization and execution patterns
- **Type Consistency**: Both use `type="pydanticai"` with different sources

### Factory Logic
```python
class EnhancedAgentFactory:
    @classmethod
    async def create_agent(cls, agent_name: str, config: Dict):
        agent_source = config.get("agent_source", "code")
        
        if agent_source == "virtual":
            return cls._create_virtual_agent(agent_name, config)
        else:
            return cls._create_code_agent(agent_name, config)
    
    @classmethod 
    def _create_virtual_agent(cls, agent_name: str, config: Dict):
        # Create AutomagikAgent instance with DB config
        agent = AutomagikAgent(config)
        agent.name = agent_name
        
        # Load tools from tool_config
        agent._setup_virtual_tools(config.get("tool_config", {}))
        
        # Set model from config or class attribute
        agent._setup_model_selection(config)
        
        return agent
    
    @classmethod
    def _create_code_agent(cls, agent_name: str, config: Dict):
        # Existing code-based agent creation
        return cls._load_agent_from_code(agent_name, config)
```

### Virtual Agent Initialization
```python
# Virtual agent setup in AutomagikAgent
def _setup_virtual_tools(self, tool_config: Dict):
    enabled_tools = tool_config.get("enabled_tools", [])
    permissions = tool_config.get("tool_permissions", {})
    
    # Load tools by name from discovery system
    for tool_name in enabled_tools:
        tool = ToolRegistry.get_tool_by_name(tool_name)
        if tool:
            self.register_tool(tool, permissions.get(tool_name, {}))

def _setup_model_selection(self, config: Dict):
    # Class-level model override takes precedence
    if hasattr(self.__class__, 'model'):
        self.model = self.__class__.model
    else:
        self.model = config.get("default_model", "openai:gpt-4o-mini")
```

### Consequences
- **Positive**: Single factory pattern, no separate virtual agent classes
- **Positive**: Virtual agents behave identically to code-based agents
- **Positive**: Easy migration path for converting code agents to virtual
- **Negative**: AutomagikAgent becomes slightly more complex

---

## ADR-005: Tool Permission and Security Model

### Context
Virtual agents need fine-grained control over tool access and permissions to ensure security and proper resource usage.

### Decision
Implement **configuration-based tool permissions** using the existing tool infrastructure with permission validation at execution time.

### Rationale
- **Security**: Prevent unauthorized tool access by virtual agents
- **Resource Control**: Limit tool usage (rate limits, parameter constraints)
- **Flexibility**: Per-agent tool configuration without code changes
- **Existing Infrastructure**: Build on current MCP and tool patterns

### Permission Model
```json
{
  "tool_config": {
    "enabled_tools": ["search", "memory", "send_message"],
    "disabled_tools": ["file_operations", "system_commands"],
    "tool_permissions": {
      "search": {
        "max_results": 10,
        "timeout_seconds": 30,
        "rate_limit_per_minute": 20
      },
      "send_message": {
        "rate_limit_per_minute": 5,
        "allowed_phone_patterns": ["+55*"]
      }
    }
  }
}
```

### Permission Enforcement
```python
class ToolPermissionValidator:
    @staticmethod
    def validate_tool_access(agent_config: Dict, tool_name: str, parameters: Dict):
        tool_config = agent_config.get("tool_config", {})
        
        # Check if tool is enabled
        enabled_tools = tool_config.get("enabled_tools", [])
        disabled_tools = tool_config.get("disabled_tools", [])
        
        if tool_name in disabled_tools:
            raise PermissionError(f"Tool {tool_name} is disabled for this agent")
        
        if enabled_tools and tool_name not in enabled_tools:
            raise PermissionError(f"Tool {tool_name} is not enabled for this agent")
        
        # Apply parameter constraints
        permissions = tool_config.get("tool_permissions", {}).get(tool_name, {})
        cls._apply_parameter_constraints(parameters, permissions)
    
    @staticmethod
    def _apply_parameter_constraints(parameters: Dict, permissions: Dict):
        # Apply max_results constraint
        if "max_results" in permissions and "max_results" in parameters:
            parameters["max_results"] = min(
                parameters["max_results"], 
                permissions["max_results"]
            )
        
        # Additional constraint logic...
```

### Consequences
- **Positive**: Fine-grained security control over tool access
- **Positive**: Configurable without code changes
- **Positive**: Consistent with existing permission patterns
- **Negative**: Permission validation adds execution overhead

---

## Decision Matrix & Dependencies

| Decision | Impact | Risk | Implementation Effort | Dependencies |
|----------|--------|------|----------------------|-------------|
| ADR-001: Model Descriptor | High | Low | Low | AutomagikAgent enhancement |
| ADR-002: Virtual Agents | High | Low | Low | Existing database schema |
| ADR-003: Tool Management | Medium | Low | Medium | MCP infrastructure |
| ADR-004: Agent Factory | Medium | Low | Low | Current factory patterns |
| ADR-005: Tool Permissions | Low | Low | Low | Tool execution framework |

## Implementation Priority

1. **Phase 1**: ADR-001 (Model Descriptor) - Foundation for clean model selection
2. **Phase 2**: ADR-002 (Virtual Agents) - Core virtual agent support
3. **Phase 3**: ADR-003 (Tool Management) - Tool discovery and execution API
4. **Phase 4**: ADR-004 (Agent Factory) - Enhanced factory for virtual agents
5. **Phase 5**: ADR-005 (Tool Permissions) - Security and permission system

Each phase builds upon previous decisions while maintaining full backward compatibility and leveraging existing infrastructure.