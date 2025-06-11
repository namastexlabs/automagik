# Technical Decisions: Startup Error Fixes

## Decision Record: MCP Compatibility Layer

**Decision ID**: STARTUP-001
**Date**: 2025-06-11
**Status**: Approved
**Epic**: Startup Error Analysis & Fix

### Context
Sofia agent fails to start due to missing `refresh_mcp_client_manager` function that was removed during MCP refactor (NMSTX-253). We need to maintain backward compatibility while supporting the new simplified MCP architecture.

### Decision
Implement a compatibility layer in `src/mcp/client.py` that provides the expected function signature while delegating to the new MCP manager.

### Rationale
- **Minimal Impact**: Adds 3 lines of code vs rewriting Sofia agent
- **Backward Compatibility**: Preserves existing agent implementations
- **Zero Breaking Changes**: No production client impact
- **Quick Resolution**: Can be implemented immediately
- **Future-Proof**: Easy to remove when Sofia is refactored

### Alternatives Considered
1. **Rewrite Sofia Agent**: Higher risk, more time-consuming
2. **Remove Sofia Temporarily**: Reduces system functionality
3. **Stub Function**: Would hide real errors, chosen approach actually works

### Implementation
```python
async def refresh_mcp_client_manager() -> None:
    """Compatibility function for legacy agents like Sofia."""
    global _mcp_manager
    if _mcp_manager is not None:
        await _mcp_manager.reload_configurations()
```

### Risks
- **LOW**: Function has minimal scope and clear behavior
- **Mitigation**: Function delegates to tested new manager

---

## Decision Record: MCP Server Constructor Fix

**Decision ID**: STARTUP-002
**Date**: 2025-06-11
**Status**: Approved
**Epic**: Startup Error Analysis & Fix

### Context
MCP servers fail to start because `MCPServerStdio` constructor signature changed in PydanticAI. Current code passes `command=[]` but constructor expects `args` as first positional parameter.

### Decision
Update the constructor call to match PydanticAI's expected signature: `MCPServerStdio(args, env=None, timeout=30)`.

### Rationale
- **Standards Compliance**: Matches PydanticAI documentation
- **Error Elimination**: Directly fixes the startup error
- **No Functionality Change**: Same behavior, correct API usage

### Implementation
```python
# BEFORE (broken)
server = MCPServerStdio(
    command=command,
    env=env or None,
    timeout=server_config.get('timeout', 30000) / 1000
)

# AFTER (fixed)
server = MCPServerStdio(
    args=command,  # First positional argument
    env=env or None,
    timeout=server_config.get('timeout', 30000) / 1000
)
```

### Risks
- **NONE**: Direct API compliance fix with no behavior change

---

## Decision Record: Standardized Error Handling

**Decision ID**: STARTUP-003
**Date**: 2025-06-11
**Status**: Approved
**Epic**: Startup Error Analysis & Fix

### Context
Sofia agent's error handler tries to use `PlaceholderAgent` but doesn't import it, causing `NameError`. Other agents may have similar issues.

### Decision
Standardize error handling pattern across all agent factories with proper imports and consistent error handling.

### Rationale
- **Reliability**: Prevents cascading failures during agent initialization
- **Consistency**: Same pattern across all agents
- **Graceful Degradation**: System continues running with placeholder
- **Debug Information**: Proper error logging and context

### Implementation Pattern
```python
def create_agent(config: Dict[str, str]):
    """Factory function with standardized error handling."""
    try:
        from .agent import SpecificAgent
        return SpecificAgent(config)
    except Exception as e:
        logger.error(f"Failed to create SpecificAgent: {e}")
        from src.agents.common.placeholder import PlaceholderAgent
        return PlaceholderAgent({"name": "agent_name_error", "error": str(e)})
```

### Risks
- **LOW**: Improves reliability without changing successful paths
- **Mitigation**: PlaceholderAgent is well-tested fallback

---

## Architecture Patterns Established

### Pattern: MCP Compatibility Functions
When refactoring MCP systems, provide compatibility functions for existing agents rather than forcing immediate updates.

**Benefits**:
- Enables progressive migration
- Reduces system-wide coordination requirements
- Maintains production stability

**Usage**: 
- Add `@deprecated` decorator with migration timeline
- Delegate to new implementation
- Document in architecture decisions

### Pattern: Standardized Agent Error Handling
All agent factory functions should follow the same error handling pattern.

**Benefits**:
- Consistent system behavior
- Graceful degradation
- Better debugging information

**Requirements**:
- Import PlaceholderAgent within try/catch
- Log specific error with context
- Return placeholder with error details

### Pattern: Constructor Signature Updates
When updating to new library versions, check constructor signatures against documentation.

**Process**:
1. Check library documentation for signature changes
2. Update all usage sites simultaneously
3. Test with actual library calls
4. Add compatibility if needed

---

**Risk Assessment**: All decisions are LOW RISK with HIGH CONFIDENCE of success. No breaking changes introduced. Solutions directly address logged error messages.

**Next Actions**: IMPLEMENT workflow should apply these fixes in the order: MCP compatibility → PlaceholderAgent import → MCP constructor signature.