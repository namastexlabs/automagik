# MCP Refactor Technical Decisions

## Decision 1: Single Table with JSON Config

**Decision**: Replace the complex `mcp_servers` + `agent_mcp_servers` junction table with a single `mcp_configs` table storing JSON configuration.

**Rationale**:
- **Simplicity**: Eliminates complex relationships and N+1 queries
- **Flexibility**: JSON allows arbitrary MCP server configurations
- **PydanticAI Alignment**: Matches the PydanticAI MCP server config format
- **Maintenance**: Single table is easier to understand and modify

**Alternatives Considered**:
- Keep existing normalized approach → Rejected due to over-complexity
- NoSQL document store → Rejected to maintain SQL compatibility

**Production Impact**: **BREAKING CHANGE** - Requires data migration
**Rollback Plan**: Keep migration scripts to revert to old schema if needed

---

## Decision 2: .mcp.json as Single Source of Truth

**Decision**: Use `.mcp.json` file at project root as the primary configuration source, with database as sync target.

**Rationale**:
- **Developer Experience**: File-based config is easier to version control
- **PydanticAI Standard**: Follows established MCP configuration patterns
- **Startup Integration**: Already partially implemented in existing system
- **Transparency**: Configuration is visible and auditable

**Alternatives Considered**:
- Database-first with file export → Rejected, harder to manage
- Dual sources of truth → Rejected, creates consistency issues

**Production Impact**: **LOW** - Enhances existing functionality
**Rollback Plan**: Database can function without file if needed

---

## Decision 3: Agent Tool Filtering via JSON Arrays

**Decision**: Use simple JSON arrays for `agent_names` and `allowed_tools` filtering instead of complex permission systems.

**Rationale**:
- **KISS Principle**: Simple array checks are easy to understand
- **Performance**: Fast JSON array operations
- **Wildcard Support**: `["*"]` allows easy "all agents" configuration
- **Tool Granularity**: Per-server tool filtering provides adequate control

**Alternatives Considered**:
- Complex RBAC system → Rejected as over-engineering
- Database-normalized permissions → Rejected for simplicity

**Production Impact**: **BREAKING CHANGE** - Current agent assignments must be migrated
**Rollback Plan**: Export current assignments before migration

---

## Decision 4: PydanticAI Native Integration

**Decision**: Replace custom MCP client manager with PydanticAI's built-in `MCPServerStdio` and `MCPServerHTTP` classes.

**Rationale**:
- **Reduced Code**: Eliminates 500+ lines of custom client management
- **Standard Compliance**: Uses official PydanticAI MCP implementation
- **Maintenance**: Let PydanticAI handle MCP protocol details
- **Features**: Get tool prefixes, server lifecycle management for free

**Alternatives Considered**:
- Keep custom client → Rejected due to maintenance burden
- Hybrid approach → Rejected for complexity

**Production Impact**: **MEDIUM** - Changes agent initialization patterns
**Rollback Plan**: Keep old client code in git history for reference

---

## Decision 5: Simplified API - 4 Endpoints Only

**Decision**: Replace 15+ complex MCP endpoints with 4 simple CRUD operations.

**Rationale**:
- **KISS Principle**: Basic CRUD covers all real use cases
- **Maintenance**: Easier to test and maintain
- **Client Simplicity**: API consumers need only basic operations
- **Focus**: Let PydanticAI handle complex server operations

**API Endpoints**:
- `POST /api/v1/mcp/configs` - Create/update config
- `GET /api/v1/mcp/configs` - List all configs  
- `GET /api/v1/mcp/configs/{name}` - Get specific config
- `DELETE /api/v1/mcp/configs/{name}` - Delete config

**Alternatives Considered**:
- Keep all existing endpoints → Rejected due to complexity
- GraphQL approach → Rejected as overkill for simple CRUD

**Production Impact**: **BREAKING CHANGE** - All current MCP API clients break
**Rollback Plan**: Document exact endpoint mappings for client updates

---

## Decision 6: Hot Reload via Agent Registry

**Decision**: When MCP configs change via API, update database, sync .mcp.json file, and trigger affected agent reloads.

**Rationale**:
- **User Experience**: Changes take effect immediately
- **File Consistency**: Keeps .mcp.json in sync with database
- **Agent Isolation**: Only reload affected agents, not entire system

**Implementation**:
```python
def update_mcp_config(name: str, config: dict):
    # 1. Update database
    update_mcp_config_db(name, config)
    
    # 2. Sync to file
    sync_mcp_json_file()
    
    # 3. Reload affected agents
    affected_agents = get_agents_using_mcp_server(name)
    for agent in affected_agents:
        agent_registry.reload_agent(agent.name)
```

**Alternatives Considered**:
- Require restart for changes → Rejected for poor UX
- Background sync → Rejected for complexity

**Production Impact**: **LOW** - Improves existing functionality
**Rollback Plan**: Can disable hot reload if issues arise

---

## Decision 7: Gradual Migration Strategy

**Decision**: Implement new system alongside old one, then migrate data and clean up.

**Migration Phases**:
1. **Build New System** - Create new table, APIs, PydanticAI integration
2. **Data Migration** - Export old data to new format with validation
3. **Agent Updates** - Modify agent creation to use new system
4. **Cleanup** - Remove old tables, files, and endpoints

**Rationale**:
- **Risk Mitigation**: Can rollback at each phase
- **Testing**: Validate new system before removing old one
- **Zero Downtime**: System remains functional during migration

**Alternatives Considered**:
- Big bang migration → Rejected as too risky
- Parallel systems → Rejected for complexity

**Production Impact**: **PLANNED** - Controlled migration with rollback points
**Rollback Plan**: Each phase has specific rollback procedures

---

## Summary of Breaking Changes

### Database Schema
- `mcp_servers` table → REMOVED
- `agent_mcp_servers` table → REMOVED  
- New `mcp_configs` table → ADDED

### API Endpoints
- 15+ existing MCP endpoints → REMOVED
- 4 new CRUD endpoints → ADDED

### Agent Integration
- Custom MCP client manager → REMOVED
- PydanticAI native integration → ADDED

### Configuration
- Database-only config → CHANGED to file-first approach
- Complex agent assignments → SIMPLIFIED to JSON arrays

## Risk Assessment

### High Risk
- **Data Migration**: Risk of data loss during table consolidation
- **API Breakage**: All current MCP API clients will need updates

### Medium Risk  
- **Agent Behavior**: Changes to MCP integration may affect agent performance
- **Tool Discovery**: Simplified filtering may miss edge cases

### Low Risk
- **File Operations**: .mcp.json loading is additive to existing functionality
- **Performance**: Simplified queries should improve performance

## Mitigation Strategies

1. **Comprehensive Testing**: Test all migration phases in development
2. **Data Backup**: Full database backup before any schema changes
3. **Gradual Rollout**: Implement phases with ability to rollback
4. **Client Communication**: Provide migration guide for API consumers
5. **Monitoring**: Enhanced logging during migration phases