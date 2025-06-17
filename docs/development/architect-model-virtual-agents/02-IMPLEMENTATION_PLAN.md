# Implementation Plan - REVISED SIMPLE APPROACH

## Overview

This implementation plan follows the revised architecture that leverages existing infrastructure instead of creating new tables or complex abstractions. The plan focuses on enhancing what's already built rather than adding complexity.

---

## Phase 1: Model Descriptor Foundation (Week 1)

### Overview
Implement single-line model selection while maintaining backward compatibility with existing configuration patterns.

### Tasks and Timeline

#### Day 1-2: Model Descriptor Implementation
**Core Model Selection Enhancement**
- Enhance `AutomagikAgent` to support class-level model attributes
- Add model override logic: class attribute > config.default_model > fallback
- Maintain full backward compatibility with existing agents

**Implementation**:
```python
# src/agents/models/automagik_agent.py enhancement
class AutomagikAgent:
    def __init__(self, config, framework_type=None):
        # Model selection priority: class attribute > config > default
        if hasattr(self.__class__, 'model'):
            if callable(self.__class__.model):
                config['default_model'] = self.__class__.model(self, config)
            else:
                config['default_model'] = self.__class__.model
        
        # Rest of existing initialization unchanged
        super().__init__(config, framework_type)
```

#### Day 3: Testing and Validation
**Comprehensive Testing**
- Test model selection with existing agents (no class attribute)
- Test new pattern with simple static model assignment
- Test dynamic model selection with callable
- Performance validation (no overhead for existing agents)

#### Day 4-5: Migration Guide and Examples
**Documentation and Examples**
- Create migration examples for FlashinhoPro (before/after)
- Document best practices for model selection
- Add examples for static and dynamic selection patterns

### Validation Criteria
- [ ] `model = "openai:gpt-4o"` works in agent class definitions
- [ ] Dynamic model selection via callables works
- [ ] All existing agents continue working unchanged
- [ ] No performance impact for existing patterns

---

## Phase 2: Virtual Agents Core Support (Week 2)

### Overview
Add support for database-configured virtual agents using existing infrastructure.

### Tasks and Timeline

#### Day 1-2: Virtual Agent Detection
**Agent Factory Enhancement**
- Enhance agent factory to detect `config.agent_source = "virtual"`
- Add virtual agent creation path alongside existing code-based path
- No changes to database schema or API routes needed

**Implementation**:
```python
# src/agents/models/agent_factory.py enhancement
class AgentFactory:
    @classmethod
    async def create_agent(cls, agent_name: str, config: Dict):
        agent_source = config.get("agent_source", "code")
        
        if agent_source == "virtual":
            return await cls._create_virtual_agent(agent_name, config)
        else:
            return await cls._create_code_agent(agent_name, config)
    
    @classmethod
    async def _create_virtual_agent(cls, agent_name: str, config: Dict):
        # Create AutomagikAgent instance without code file lookup
        agent = AutomagikAgent(config)
        agent.name = agent_name
        
        # Setup tools from config
        if "tool_config" in config:
            await agent._setup_tools_from_config(config["tool_config"])
        
        return agent
```

#### Day 3-4: Virtual Agent Configuration
**Configuration Loading and Validation**
- Add configuration validation for virtual agents
- Implement tool loading from configuration
- Add error handling for missing tools or invalid config

#### Day 5: Testing Virtual Agents
**End-to-End Testing**
- Create test virtual agent in database
- Test execution via existing `/agent/{name}/run` endpoint
- Validate tool access and permissions work correctly

### Validation Criteria
- [ ] Virtual agents can be created in database with `agent_source: "virtual"`
- [ ] Virtual agents execute via existing API endpoints
- [ ] Tool configuration works from database config
- [ ] Error handling for invalid configurations

---

## Phase 3: Tool Management API (Week 3)

### Overview
Create tool discovery and execution endpoints to support virtual agent configuration and testing.

### Tasks and Timeline

#### Day 1-2: Tool Discovery System
**Tool Enumeration**
- Scan MCP servers' `tools_discovered` field for MCP tools
- Enumerate code-based tools from `src/tools/` modules
- Create unified tool metadata structure

**Implementation**:
```python
# src/api/routes/tool_routes.py
@router.get("/tools")
async def list_tools():
    """List all available tools from MCP servers and code modules."""
    tools = []
    
    # Get MCP tools
    mcp_servers = await get_all_mcp_servers()
    for server in mcp_servers:
        tools_discovered = json.loads(server.tools_discovered or "[]")
        for tool in tools_discovered:
            tools.append({
                "name": tool["name"],
                "type": "mcp",
                "description": tool.get("description", ""),
                "server_name": server.name,
                "parameters": tool.get("inputSchema", {}).get("properties", {})
            })
    
    # Get code-based tools
    code_tools = discover_code_tools()  # Scan src/tools/ modules
    tools.extend(code_tools)
    
    return tools
```

#### Day 3-4: Tool Execution Endpoint
**Direct Tool Execution**
- Create `/tools/{tool_name}/run` endpoint
- Route to MCP servers or code modules based on tool type
- Implement context injection for all tool calls

#### Day 5: Tool Testing and Validation
**Integration Testing**
- Test tool discovery finds all available tools
- Test tool execution works for both MCP and code tools
- Validate context parameter handling

### Validation Criteria
- [ ] `/tools` endpoint lists all available tools
- [ ] `/tools/{tool_name}/run` executes tools correctly
- [ ] Context injection works for all tool types
- [ ] Tool metadata includes parameter information

---

## Phase 4: Enhanced Agent Management (Week 4)

### Overview
Add agent management capabilities and tool permission system for production use.

### Tasks and Timeline

#### Day 1-2: Agent Management Enhancements
**Virtual Agent CRUD Operations**
- Enhance existing agent CRUD endpoints to support virtual agents
- Add virtual agent creation from templates
- Add agent cloning capabilities

#### Day 3-4: Tool Permission System
**Security and Permission Validation**
- Implement tool permission validation
- Add rate limiting and parameter constraints
- Create permission testing framework

**Implementation**:
```python
# src/agents/common/tool_permissions.py
class ToolPermissionValidator:
    @staticmethod
    def validate_and_constrain_parameters(config: Dict, tool_name: str, parameters: Dict):
        tool_config = config.get("tool_config", {})
        enabled_tools = tool_config.get("enabled_tools", [])
        
        # Check if tool is enabled
        if enabled_tools and tool_name not in enabled_tools:
            raise PermissionError(f"Tool {tool_name} not enabled for this agent")
        
        # Apply parameter constraints
        permissions = tool_config.get("tool_permissions", {}).get(tool_name, {})
        if "max_results" in permissions and "max_results" in parameters:
            parameters["max_results"] = min(parameters["max_results"], permissions["max_results"])
        
        return parameters
```

#### Day 5: Production Readiness
**Error Handling and Monitoring**
- Add comprehensive error handling for virtual agents
- Implement logging and monitoring for tool usage
- Add configuration validation and helpful error messages

### Validation Criteria
- [ ] Virtual agents can be created, updated, and deleted via API
- [ ] Tool permissions prevent unauthorized access
- [ ] Parameter constraints work correctly
- [ ] Production-ready error handling and logging

---

## Simple Database Changes Required

### Only Configuration Enhancements (No Schema Changes)

**Existing Schema Works Perfect**:
- `agents.type = "pydanticai"` (unchanged)
- `agents.config` JSON field enhanced:

```json
{
  "agent_source": "virtual",
  "default_model": "openai:gpt-4o",
  "tool_config": {
    "enabled_tools": ["search", "memory", "send_message"],
    "tool_permissions": {
      "search": {"max_results": 10}
    }
  }
}
```

**Migration**: None required! Just start creating virtual agents with enhanced config.

---

## API Changes Required

### New Endpoints (Additive Only)
```python
# Tool management (new)
GET  /tools                    # List available tools
POST /tools/{tool_name}/run    # Execute tool directly

# Agent management (enhanced existing)
POST   /agents                 # Enhanced to support virtual agents
PUT    /agents/{id}            # Enhanced to support virtual agent config
GET    /agents                 # Works for both virtual and code agents
POST   /agent/{name}/run       # Works for both virtual and code agents (unchanged)
```

### No Breaking Changes
- All existing endpoints continue working unchanged
- Virtual agents use same execution path as code agents
- Tool integration leverages existing MCP infrastructure

---

## Resource Requirements

### Development Team
- **Backend Developer**: 4 weeks, 80% time for implementation
- **Testing**: 20% time across all phases for validation

### Infrastructure
- **No Database Migration**: Use existing schema
- **No New Services**: Leverage existing MCP and API infrastructure
- **Enhanced Monitoring**: Add logging for virtual agent tool usage

---

## Risk Mitigation

### Minimal Risk Profile
- **No Database Schema Changes**: Zero risk of data corruption
- **Additive API Changes**: No breaking changes to existing clients
- **Existing Infrastructure**: Build on proven, stable components
- **Gradual Rollout**: Can deploy virtual agents incrementally

### Safety Measures
- **Feature Flags**: Control virtual agent features per environment
- **Backward Compatibility**: All existing agents continue working unchanged
- **Tool Permissions**: Security controls prevent unauthorized access
- **Configuration Validation**: Prevent invalid virtual agent configurations

---

## Success Metrics

### Technical Goals
- [ ] Single-line model selection: `model = "openai:gpt-4o"`
- [ ] Virtual agents created in < 2 minutes
- [ ] Tool discovery finds 100% of available tools
- [ ] Virtual agents perform identically to code agents

### Business Impact
- [ ] 10x faster agent specialization (hours vs weeks)
- [ ] Zero deployment needed for new agent variants
- [ ] Developer satisfaction with simplified model selection
- [ ] Tool testing and validation capabilities

This simplified implementation plan leverages your existing infrastructure while delivering the core benefits of virtual agents and clean model selection with minimal complexity and risk.