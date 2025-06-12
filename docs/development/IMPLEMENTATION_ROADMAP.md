# MCP Refactor Implementation Roadmap

## Overview

This roadmap outlines the step-by-step implementation of the MCP refactor, transitioning from the over-engineered multi-table system to a simplified single-table approach with PydanticAI integration.

## Phase 1: Foundation (New System Alongside Old)

### Phase 1.1: Database Layer
**Duration**: 1 day
**Risk**: Low - Additive only

**Tasks**:
1. **Create new table migration**
   ```sql
   -- File: src/db/migrations/YYYYMMDD_HHMMSS_create_mcp_configs_table.sql
   CREATE TABLE IF NOT EXISTS mcp_configs (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL UNIQUE,
       config JSONB NOT NULL,
       agent_names JSONB DEFAULT '[]',
       allowed_tools JSONB DEFAULT '[]',
       enabled BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **Create new models**
   ```python
   # File: src/mcp/config_models.py
   class MCPConfig(BaseModel):
       name: str
       config: Dict[str, Any]
       agent_names: List[str] = []
       allowed_tools: List[str] = []
       enabled: bool = True
   ```

3. **Create simple repository**
   ```python
   # File: src/db/repository/mcp_config.py
   def get_mcp_config(name: str) -> Optional[MCPConfig]: ...
   def list_mcp_configs(agent_name: Optional[str] = None) -> List[MCPConfig]: ...
   def create_or_update_mcp_config(config: MCPConfig) -> bool: ...
   def delete_mcp_config(name: str) -> bool: ...
   ```

**Validation**:
- [ ] New table created successfully
- [ ] Basic CRUD operations working
- [ ] No impact on existing system

### Phase 1.2: Configuration Loader
**Duration**: 1 day
**Risk**: Low - Read-only operations

**Tasks**:
1. **Create .mcp.json loader**
   ```python
   # File: src/mcp/config_loader.py
   def load_mcp_json(file_path: str = ".mcp.json") -> Dict[str, Any]:
       """Load and validate .mcp.json configuration."""
   
   def sync_to_database(mcp_config: Dict[str, Any]) -> bool:
       """Sync .mcp.json to mcp_configs table."""
   ```

2. **Add startup integration**
   ```python
   # File: src/main.py (add to startup)
   @app.on_event("startup")
   async def load_mcp_configs():
       if os.path.exists(".mcp.json"):
           config = load_mcp_json()
           sync_to_database(config)
   ```

3. **Create example .mcp.json**
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
         "agent_names": ["simple"],
         "allowed_tools": ["read_file", "list_directory"]
       }
     }
   }
   ```

**Validation**:
- [ ] .mcp.json loads on startup
- [ ] Configuration syncs to database
- [ ] Invalid configs are rejected with helpful errors

### Phase 1.3: Simple API
**Duration**: 1 day
**Risk**: Low - New endpoints only

**Tasks**:
1. **Create simple CRUD API**
   ```python
   # File: src/api/routes/mcp_config_routes.py
   @router.get("/configs")
   @router.get("/configs/{name}")
   @router.post("/configs") 
   @router.delete("/configs/{name}")
   ```

2. **Add to main routes**
   ```python
   # File: src/api/routes/__init__.py
   from .mcp_config_routes import router as mcp_config_router
   app.include_router(mcp_config_router, prefix="/api/v1/mcp")
   ```

3. **Add file sync on changes**
   ```python
   # Auto-sync database changes back to .mcp.json
   def sync_to_file(file_path: str = ".mcp.json") -> bool: ...
   ```

**Validation**:
- [ ] 4 CRUD endpoints working
- [ ] Changes sync back to .mcp.json file
- [ ] API documentation updated

## Phase 2: PydanticAI Integration

### Phase 2.1: Agent MCP Integration
**Duration**: 2 days
**Risk**: Medium - Changes agent behavior

**Tasks**:
1. **Create PydanticAI adapter**
   ```python
   # File: src/mcp/pydantic_adapter.py
   def create_mcp_servers_for_agent(agent_name: str) -> List[Union[MCPServerStdio, MCPServerHTTP]]:
       """Create PydanticAI MCP servers for specific agent."""
       configs = get_mcp_configs_for_agent(agent_name)
       servers = []
       
       for config in configs:
           if config.config.get("command"):
               server = MCPServerStdio(
                   config.config["command"],
                   args=config.config.get("args", []),
                   env=config.config.get("env", {}),
                   tool_prefix=config.config.get("tool_prefix")
               )
           else:
               server = MCPServerHTTP(
                   url=config.config["http_url"],
                   tool_prefix=config.config.get("tool_prefix")
               )
           servers.append(server)
       
       return servers
   ```

2. **Update agent creation**
   ```python
   # File: src/agents/models/automagik_agent.py
   def __init__(self, config: Dict[str, str], framework_type: str = "pydanticai") -> None:
       # ... existing initialization
       
       # Add MCP servers for this agent
       mcp_servers = create_mcp_servers_for_agent(self.agent_name)
       
       # Create PydanticAI agent with MCP servers
       self.pydantic_agent = Agent(
           model=self.model,
           mcp_servers=mcp_servers,
           system_prompt=self._code_prompt_text
       )
   ```

3. **Add tool filtering logic**
   ```python
   def filter_tools_for_agent(agent_name: str, server_config: MCPConfig) -> List[str]:
       """Filter tools based on allowed_tools configuration."""
       if not server_config.allowed_tools:
           return []  # No filtering, all tools allowed
       return server_config.allowed_tools
   ```

**Validation**:
- [ ] Agents created with PydanticAI MCP integration
- [ ] Tool filtering works correctly
- [ ] Agent behavior unchanged for existing functionality

### Phase 2.2: Hot Reload Implementation
**Duration**: 1 day  
**Risk**: Medium - Runtime configuration changes

**Tasks**:
1. **Agent registry for tracking**
   ```python
   # File: src/agents/registry.py
   class AgentRegistry:
       def __init__(self):
           self._agents: Dict[str, AutomagikAgent] = {}
           
       def register_agent(self, agent: AutomagikAgent):
           self._agents[agent.agent_name] = agent
           
       def reload_agent(self, agent_name: str):
           """Reload agent with updated MCP configuration."""
           if agent_name in self._agents:
               # Recreate agent with new MCP servers
               old_agent = self._agents[agent_name]
               new_agent = create_agent_with_updated_mcp(old_agent)
               self._agents[agent_name] = new_agent
   ```

2. **Update API to trigger reloads**
   ```python
   @router.post("/configs")
   async def create_or_update_mcp_config(config: MCPConfigRequest):
       # Update database
       success = create_or_update_mcp_config(config)
       
       # Sync to file
       sync_to_file()
       
       # Reload affected agents
       affected_agents = get_agents_using_mcp_server(config.name)
       for agent_name in affected_agents:
           agent_registry.reload_agent(agent_name)
       
       return {"success": success}
   ```

**Validation**:
- [ ] Configuration changes trigger agent reloads
- [ ] .mcp.json stays in sync with database
- [ ] No service interruption during reloads

## Phase 3: Data Migration

### Phase 3.1: Export Current Data
**Duration**: 1 day
**Risk**: Low - Read-only operations

**Tasks**:
1. **Create migration script**
   ```python
   # File: scripts/migrate_mcp_data.py
   def export_current_mcp_data() -> Dict[str, Any]:
       """Export current mcp_servers and agent_mcp_servers to new format."""
       
   def validate_migration_data(data: Dict[str, Any]) -> bool:
       """Validate exported data meets new schema requirements."""
       
   def create_backup() -> str:
       """Create full database backup before migration."""
   ```

2. **Generate .mcp.json from current data**
   ```python
   def generate_mcp_json_from_current_data():
       servers = get_all_mcp_servers()  # Current system
       config = {"mcpServers": {}}
       
       for server in servers:
           agents = get_server_agents(server.id)
           config["mcpServers"][server.name] = {
               "command": server.command[0] if server.command else None,
               "args": server.command[1:] if len(server.command) > 1 else [],
               "http_url": server.http_url,
               "env": server.env or {},
               "agent_names": [agent.name for agent in agents],
               "allowed_tools": []  # Default to no filtering
           }
   ```

**Validation**:
- [ ] All current MCP data exported successfully
- [ ] Generated .mcp.json validates against new schema
- [ ] Database backup created

### Phase 3.2: Execute Migration
**Duration**: 1 day
**Risk**: High - Data manipulation

**Tasks**:
1. **Apply migration SQL**
   ```sql
   -- File: src/db/migrations/YYYYMMDD_HHMMSS_migrate_mcp_data.sql
   
   -- Create backup table with current data
   CREATE TABLE mcp_migration_backup AS 
   SELECT s.*, array_agg(a.name) as agent_names
   FROM mcp_servers s
   LEFT JOIN agent_mcp_servers ams ON s.id = ams.mcp_server_id
   LEFT JOIN agents a ON ams.agent_id = a.id
   GROUP BY s.id;
   
   -- Migrate to new simplified format
   INSERT INTO mcp_configs (name, config, agent_names, enabled)
   SELECT 
       name,
       json_build_object(...),  -- Build new config format
       COALESCE(agent_names, ARRAY[]::text[]),
       enabled
   FROM mcp_migration_backup;
   ```

2. **Validation queries**
   ```sql
   -- Verify data integrity
   SELECT 
       COUNT(*) as old_servers,
       (SELECT COUNT(*) FROM mcp_configs) as new_configs,
       COUNT(DISTINCT ams.agent_id) as old_assignments
   FROM mcp_servers s
   LEFT JOIN agent_mcp_servers ams ON s.id = ams.mcp_server_id;
   ```

**Validation**:
- [ ] All servers migrated to new table
- [ ] Agent assignments preserved
- [ ] Data integrity verified
- [ ] Rollback script prepared

## Phase 4: System Transition

### Phase 4.1: Switch to New System
**Duration**: 1 day
**Risk**: High - System behavior change

**Tasks**:
1. **Update all agent creation calls**
   ```python
   # Update everywhere agents are created
   # From: create_agent(name, type, config)
   # To: create_agent_with_mcp(name, type, config)  # Uses new system
   ```

2. **Feature flag for safety**
   ```python
   # Environment variable to control which system to use
   USE_NEW_MCP_SYSTEM = os.getenv("USE_NEW_MCP_SYSTEM", "false").lower() == "true"
   
   def create_agent_with_mcp_config(agent_name: str):
       if USE_NEW_MCP_SYSTEM:
           return create_agent_with_new_mcp(agent_name)
       else:
           return create_agent_with_old_mcp(agent_name)
   ```

3. **Comprehensive testing**
   ```python
   # Test suite comparing old vs new behavior
   def test_mcp_functionality_parity():
       old_agent = create_agent_with_old_mcp("simple")
       new_agent = create_agent_with_new_mcp("simple") 
       
       # Compare available tools
       # Compare agent behavior
       # Compare performance
   ```

**Validation**:
- [ ] All agents work with new MCP system
- [ ] No functionality regression
- [ ] Performance equal or better
- [ ] Feature flag allows quick rollback

### Phase 4.2: Production Validation
**Duration**: 2 days
**Risk**: Medium - Production testing

**Tasks**:
1. **Staged rollout**
   - Enable new system for 10% of requests
   - Monitor for errors and performance issues
   - Gradually increase to 100%

2. **Performance monitoring**
   - Compare query performance (old vs new)
   - Monitor agent creation time
   - Track API response times

3. **Error handling validation**
   - Test invalid .mcp.json configurations
   - Test database connectivity issues
   - Test PydanticAI MCP server failures

**Validation**:
- [ ] Production system stable with new MCP implementation
- [ ] Performance metrics within acceptable range
- [ ] Error handling works correctly
- [ ] Monitoring and alerts functional

## Phase 5: Cleanup

### Phase 5.1: Remove Old System
**Duration**: 1 day
**Risk**: Low - Dead code removal

**Tasks**:
1. **Drop old tables**
   ```sql
   -- After confirming new system is stable
   DROP TABLE IF EXISTS agent_mcp_servers;
   DROP TABLE IF EXISTS mcp_servers;
   ```

2. **Remove old code files**
   - `src/db/repository/mcp.py` (600 lines)
   - `src/api/routes/mcp_routes.py` (578 lines)
   - MCP classes from `src/mcp/models.py`

3. **Update imports throughout codebase**
   ```python
   # Remove all references to old MCP system
   # Update import statements
   # Remove feature flags
   ```

**Validation**:
- [ ] Old tables dropped successfully
- [ ] No broken imports or references
- [ ] System continues to function normally

### Phase 5.2: Documentation and Communication
**Duration**: 1 day
**Risk**: Low - Documentation only

**Tasks**:
1. **Update API documentation**
   - Remove old MCP endpoints from docs
   - Document new 4-endpoint API
   - Update example configurations

2. **Create migration guide for API consumers**
   ```markdown
   # MCP API Migration Guide
   
   ## Old vs New Endpoints
   - OLD: POST /api/v1/mcp/servers → NEW: POST /api/v1/mcp/configs
   - OLD: GET /api/v1/mcp/servers → NEW: GET /api/v1/mcp/configs
   ```

3. **Update internal documentation**
   - Update CLAUDE.md with new patterns
   - Update architecture documentation
   - Update development commands

**Validation**:
- [ ] All documentation updated
- [ ] API consumers notified of changes
- [ ] Internal teams trained on new system

## Risk Mitigation Strategies

### Phase 1-2 (Low Risk)
- **Parallel Implementation**: New system runs alongside old
- **Feature Flags**: Easy rollback if issues found
- **Comprehensive Testing**: Validate each component before proceeding

### Phase 3-4 (High Risk)  
- **Database Backups**: Full backup before any data changes
- **Staged Rollout**: Gradual transition with monitoring
- **Rollback Scripts**: Prepared rollback for each migration step
- **24/7 Monitoring**: Enhanced alerting during transition

### Phase 5 (Low Risk)
- **Code Review**: Multiple reviewers for cleanup changes
- **Testing**: Comprehensive testing after cleanup
- **Documentation**: Clear communication of changes

## Success Metrics

### Quantitative Goals
- **90% Code Reduction**: From 2000+ lines to ~300 lines
- **Query Performance**: 50%+ improvement in MCP-related queries
- **API Simplification**: From 15+ endpoints to 4 endpoints
- **Startup Time**: No degradation in application startup time

### Qualitative Goals
- **Developer Experience**: Easier MCP configuration and debugging
- **Maintainability**: Reduced complexity for future development
- **Standards Compliance**: Full PydanticAI compatibility
- **File-First Config**: Improved configuration management

This roadmap provides a safe, incremental path from the current over-engineered system to the simplified, maintainable approach while minimizing risk and ensuring all functionality is preserved.