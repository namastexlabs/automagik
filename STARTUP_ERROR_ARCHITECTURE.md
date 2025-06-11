# Startup Error Architecture Solution

## Epic: Fix MCP & Sofia Agent Startup Errors

### Problem Statement
The application fails to start cleanly due to:
1. Missing `refresh_mcp_client_manager` function causing Sofia agent import failure
2. Undefined `PlaceholderAgent` in error handlers
3. MCP server startup failures due to constructor signature mismatches

### Root Cause Analysis

#### Issue 1: Sofia Agent Import Error
```
ImportError: cannot import name 'refresh_mcp_client_manager' from 'src.mcp.client'
```

**Root Cause**: Sofia agent imports a function that was removed during MCP refactor
- File: `src/agents/pydanticai/sofia/agent.py:28`
- Expected: `refresh_mcp_client_manager` function
- Reality: Function doesn't exist in new MCP architecture

#### Issue 2: PlaceholderAgent Undefined
```
NameError: name 'PlaceholderAgent' is not defined
```

**Root Cause**: Missing import in Sofia's error handler
- File: `src/agents/pydanticai/sofia/__init__.py:42`
- Missing: `from src.agents.common.placeholder import PlaceholderAgent`

#### Issue 3: MCP Server Constructor Mismatch
```
MCPServerStdio.__init__() missing 1 required positional argument: 'args'
```

**Root Cause**: MCP client using old constructor signature
- File: `src/mcp/client.py:314`
- Issue: `MCPServerStdio(command=command, ...)` missing `args` parameter
- PydanticAI expects `MCPServerStdio(args, env=None, timeout=30)`

### Architecture Solution

#### Solution 1: MCP Client Compatibility Layer
Add compatibility functions to MCP client module:

```python
# src/mcp/client.py - Add compatibility functions
async def refresh_mcp_client_manager() -> None:
    """Compatibility function for legacy Sofia agent."""
    global _mcp_manager
    if _mcp_manager is not None:
        await _mcp_manager.reload_configurations()

# Update MCPServerStdio constructor call
server = MCPServerStdio(
    args=command,  # First positional argument
    env=env or None,
    timeout=server_config.get('timeout', 30000) / 1000
)
```

#### Solution 2: Sofia Agent Import Fix
Update Sofia agent imports:

```python
# src/agents/pydanticai/sofia/__init__.py - Add missing import
from src.agents.common.placeholder import PlaceholderAgent

# src/agents/pydanticai/sofia/agent.py - Update import
from src.mcp.client import get_mcp_manager  # Instead of refresh_mcp_client_manager
```

#### Solution 3: Error Handler Standardization
Implement consistent error handling pattern across all agents:

```python
def create_agent(config: Dict[str, str]):
    """Factory function with standardized error handling."""
    try:
        from .agent import SofiaAgent
        return SofiaAgent(config)
    except Exception as e:
        logger.error(f"Failed to create SofiaAgent: {e}")
        from src.agents.common.placeholder import PlaceholderAgent
        return PlaceholderAgent({"name": "sofia_agent_error", "error": str(e)})
```

### Implementation Strategy

#### Phase 1: Quick Fixes (IMMEDIATE)
1. Add `refresh_mcp_client_manager` compatibility function
2. Fix PlaceholderAgent import in Sofia
3. Fix MCP server constructor calls

#### Phase 2: Architecture Cleanup (FOLLOW-UP)
1. Update Sofia agent to use new MCP patterns
2. Standardize error handling across all agents
3. Add compatibility tests

### Breaking Changes Assessment
- **NONE**: All fixes are backward compatible
- Solution adds compatibility functions without removing existing functionality
- No API contract changes required

### Risk Assessment
- **LOW RISK**: Minimal changes to core functionality
- **HIGH CONFIDENCE**: Solutions address exact error messages
- **QUICK IMPLEMENTATION**: All fixes can be completed in single session

### Success Criteria
1. Application starts without import errors
2. Sofia agent initializes successfully (or fails gracefully with PlaceholderAgent)
3. MCP servers start without constructor errors
4. All 11 agents initialize successfully

### Next Workflow
- **IMPLEMENT**: Apply the architectural fixes
- **TEST**: Verify startup succeeds and basic functionality works
- **REVIEW**: Ensure fixes are complete and robust

### Dependencies
- No external dependencies required
- No database schema changes needed
- No breaking changes to existing APIs

---

**Architect Decision**: Implement compatibility layer approach to maintain backward compatibility while supporting new MCP architecture.