# Breaking Changes Analysis

## Overview

This document identifies all breaking changes introduced by the Model Selection and Virtual Agents architecture, provides migration paths, and establishes backward compatibility strategies.

**⚠️ CRITICAL**: Multiple breaking changes require careful migration planning and stakeholder coordination.

---

## Breaking Changes Summary

| Change Category | Impact Level | Affected Components | Migration Effort |
|----------------|--------------|-------------------|------------------|
| Model Selection API | HIGH | All agents using config-based models | Medium |
| Virtual Agent Database Schema | CRITICAL | Database, migrations, backups | High |
| Framework Integration | MEDIUM | PydanticAI, Claude Code adapters | Medium |
| Tool Access Patterns | MEDIUM | Agents using MCP servers | Low |
| API Endpoint Structure | LOW | External API clients | Low |

---

## 1. Model Selection API Changes

### Breaking Change: Model Configuration Pattern

#### Current Implementation (BEFORE):
```python
# Complex multi-layer model configuration
class FlashinhoPro(AutomagikAgent):
    def __init__(self, config):
        self.pro_model = "google-gla:gemini-2.5-pro-preview-05-06"
        self.free_model = "google-gla:gemini-2.5-flash-preview-05-20"
        config.setdefault("model", self.pro_model)
        super().__init__(config)
        
        # Complex model switching in runtime methods
        if self._is_pro_user:
            self.model_name = self.pro_model
            if hasattr(self, 'llm_client'):
                self.llm_client.model = self.pro_model
            if hasattr(self, 'dependencies'):
                self.dependencies.model_name = self.pro_model
```

#### New Implementation (AFTER):
```python
# Clean single-line model selection
class FlashinhoPro(AutomagikAgent):
    def _select_model(self, context):
        return "google-gla:gemini-2.5-pro-preview-05-06" if context.user.is_pro else "google-gla:gemini-2.5-flash-preview-05-20"
    
    model = _select_model  # Single line model definition!
    
    def __init__(self, config):
        super().__init__(config)
        # Rest of initialization without model complexity
```

### Impact Assessment:
- **Affected Files**: All agent classes with custom model selection
- **Code Changes Required**: Refactor model initialization patterns
- **Configuration Changes**: Model config validation may change
- **Runtime Behavior**: Model switching happens through descriptor

### Migration Strategy:

#### Phase 1: Parallel Implementation (2 weeks)
```python
# Agents can use both patterns during migration
class FlashinhoPro(AutomagikAgent):
    # New pattern (preferred)
    model = lambda self, ctx: "pro-model" if ctx.user.is_pro else "free-model"
    
    def __init__(self, config):
        # Old pattern still works for backward compatibility
        if not hasattr(self.__class__, 'model'):
            config.setdefault("model", self._legacy_model_selection())
        super().__init__(config)
```

#### Phase 2: Deprecation Period (4 weeks)
- Add deprecation warnings for old model selection patterns
- Provide automated migration tools for common patterns
- Update documentation with migration examples

#### Phase 3: Legacy Removal (2 weeks)
- Remove backward compatibility code
- Clean up deprecated configuration patterns
- Update all internal agents to new pattern

### Automated Migration Tool:
```python
# migration/model_selection_migrator.py
class ModelSelectionMigrator:
    """Automated migration tool for agent model selection patterns."""
    
    def migrate_agent_file(self, file_path: str) -> List[str]:
        """Migrate an agent file to new model selection pattern."""
        changes = []
        
        # Detect complex model initialization patterns
        # Generate new model selection function
        # Create backup of original file
        # Apply transformations
        
        return changes
```

---

## 2. Database Schema Breaking Changes

### Breaking Change: Virtual Agents Table Structure

#### Current Schema (BEFORE):
```sql
-- Simple agent storage
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    model TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',
    system_prompt TEXT,
    active BOOLEAN DEFAULT TRUE
);
```

#### New Schema (AFTER):
```sql
-- Enhanced schema with virtual agent support
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    model TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',  -- Now contains virtual_agent configuration
    system_prompt TEXT,
    active BOOLEAN DEFAULT TRUE
);

-- New virtual agent tables
CREATE TABLE virtual_agents (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    endpoint_path TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 60,
    max_concurrent_sessions INTEGER DEFAULT 10,
    created_at TEXT NOT NULL DEFAULT datetime('now'),
    updated_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE agent_runtime_configs (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    config_key TEXT NOT NULL,
    config_value TEXT NOT NULL,
    config_type TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT datetime('now'),
    updated_at TEXT NOT NULL DEFAULT datetime('now'),
    UNIQUE(agent_id, config_key)
);
```

### Impact Assessment:
- **Data Migration Required**: All existing agent configurations
- **Backup Necessity**: Full database backup before migration
- **Downtime Required**: 2-4 hour maintenance window
- **Rollback Complexity**: Requires full database restore

### Migration Procedure:

#### Pre-Migration Safety (1 week before):
```bash
#!/bin/bash
# pre_migration_safety.sh

# 1. Full database backup with verification
pg_dump automagik_agents > backup_pre_virtual_agents_$(date +%Y%m%d).sql
pg_restore --dry-run backup_pre_virtual_agents_$(date +%Y%m%d).sql

# 2. Export critical data to JSON
python scripts/export_agent_configs.py --output agents_backup_$(date +%Y%m%d).json

# 3. Validate backup integrity
python scripts/validate_backup.py --backup agents_backup_$(date +%Y%m%d).json

# 4. Test migration on copy
scripts/test_migration_on_copy.sh
```

#### Migration Execution:
```sql
-- migration/001_add_virtual_agents.sql
BEGIN;

-- Step 1: Create new tables
CREATE TABLE virtual_agents (...);
CREATE TABLE agent_runtime_configs (...);

-- Step 2: Migrate existing configurations
INSERT INTO virtual_agents (agent_id, endpoint_path, is_active)
SELECT id, '/virtual/' || LOWER(REPLACE(name, ' ', '-')), active
FROM agents 
WHERE active = TRUE;

-- Step 3: Validate data integrity
SELECT COUNT(*) FROM agents;
SELECT COUNT(*) FROM virtual_agents;

-- Step 4: Add indexes and constraints
CREATE INDEX idx_virtual_agents_endpoint ON virtual_agents (endpoint_path);
CREATE INDEX idx_agent_runtime_configs ON agent_runtime_configs (agent_id, config_type);

COMMIT;
```

#### Rollback Procedure:
```bash
#!/bin/bash
# rollback_virtual_agents.sh

echo "EMERGENCY ROLLBACK: Virtual Agents Migration"
echo "This will restore database to pre-migration state"
read -p "Are you sure? Type 'ROLLBACK' to confirm: " confirmation

if [ "$confirmation" = "ROLLBACK" ]; then
    # Stop all services
    systemctl stop automagik-agents
    
    # Restore database
    dropdb automagik_agents
    createdb automagik_agents
    pg_restore backup_pre_virtual_agents_$(date +%Y%m%d).sql
    
    # Restart services
    systemctl start automagik-agents
    
    echo "Rollback completed. Verify system functionality."
else
    echo "Rollback cancelled."
fi
```

---

## 3. Framework Integration Changes

### Breaking Change: Framework Adapter Pattern

#### Current Implementation (BEFORE):
```python
# Direct framework instantiation in AutomagikAgent
class AutomagikAgent:
    def __init__(self, config, framework_type=None):
        if framework_type == 'pydanticai':
            self.ai_framework = PydanticAIFramework(self, config)
        elif framework_type == 'claude_code':
            # Direct framework usage
            pass
```

#### New Implementation (AFTER):
```python
# Framework adapters provide unified interface
class AutomagikAgent:
    def __init__(self, config, framework_type=None):
        self.ai_framework = FrameworkAdapterRegistry.create_adapter(
            framework_type or config.get('framework_type', 'pydanticai'),
            agent=self,
            config=config
        )
```

### Impact Assessment:
- **Custom Framework Integrations**: Need adapter implementation
- **Framework-Specific Code**: Requires refactoring through adapters
- **Configuration Validation**: Framework configs validated differently

### Migration Strategy:

#### Phase 1: Adapter Implementation
```python
# Create adapters for existing frameworks
class PydanticAIAdapter(FrameworkAdapter):
    """Adapter for existing PydanticAI integration."""
    
    def __init__(self, agent, config):
        self.agent = agent
        self.config = config
        self._framework = self._create_pydantic_framework()
    
    def _create_pydantic_framework(self):
        # Wrap existing PydanticAIFramework
        return PydanticAIFramework(self.agent, self.config)
    
    async def execute(self, input_text, **kwargs):
        # Delegate to existing framework
        return await self._framework.run_agent(input_text, **kwargs)
```

#### Phase 2: Gradual Migration
- Update agents one by one to use adapter pattern
- Maintain direct framework access for backward compatibility
- Add deprecation warnings for direct framework usage

---

## 4. Tool Access Pattern Changes

### Breaking Change: Capability-Based Tool Access

#### Current Implementation (BEFORE):
```python
# Direct MCP server access
async def setup_tools(self):
    mcp_servers = await get_agent_mcp_servers(self.id)
    for server in mcp_servers:
        await self.connect_mcp_server(server)
```

#### New Implementation (AFTER):
```python
# Capability-based tool access with permissions
async def setup_tools(self):
    tool_manager = VirtualAgentToolManager(self.config)
    await tool_manager.initialize_tools()
    self.available_tools = await tool_manager.get_available_tools()
```

### Impact Assessment:
- **Tool Access Control**: More restrictive by default
- **MCP Server Integration**: Requires capability declarations
- **Permission Validation**: Added overhead for tool execution

### Migration Strategy:

#### Auto-Migration for Existing Agents:
```python
# migration/tool_access_migrator.py
def migrate_tool_access(agent_config):
    """Auto-migrate existing tool access to capability-based."""
    
    # Extract current MCP server associations
    mcp_servers = get_agent_mcp_servers(agent_config['id'])
    
    # Generate permissive capability configuration
    tool_config = {
        "tool_access": {
            "enabled_tools": ["*"],  # Allow all tools initially
            "restricted_tools": [],
            "mcp_server_ids": [server.id for server in mcp_servers],
            "tool_permissions": {}  # No restrictions initially
        }
    }
    
    # Update agent configuration
    agent_config['config']['virtual_agent'] = tool_config
    return agent_config
```

---

## 5. API Endpoint Structure Changes

### Breaking Change: Virtual Agent Endpoints

#### New Endpoints Added:
```python
# New virtual agent endpoints
POST /virtual/{agent_path}/run          # Execute virtual agent
GET  /virtual/agents                    # List virtual agents
POST /virtual/agents                    # Create virtual agent
PUT  /virtual/agents/{id}/config        # Update agent config
```

### Impact Assessment:
- **New API Structure**: Additional endpoints for virtual agent management
- **Authentication**: May require new authentication for virtual endpoints
- **Rate Limiting**: Different rate limits for virtual vs regular agents

### Migration Strategy:
- **Additive Changes**: New endpoints don't break existing functionality
- **Gradual Adoption**: Virtual agents can be added without affecting existing agents
- **Documentation**: Update API documentation with new endpoint examples

---

## Backward Compatibility Strategy

### 1. Model Selection Compatibility

```python
class AutomagikAgent:
    def __init__(self, config, framework_type=None):
        # Support both old and new patterns
        if hasattr(self.__class__, 'model'):
            # New descriptor pattern
            self.model = self.__class__.model
        else:
            # Legacy config-based pattern
            self.model = config.get('model', DEFAULT_MODEL)
```

### 2. Database Compatibility

```sql
-- Maintain old table structure alongside new
-- Use views for backward compatibility
CREATE VIEW agents_legacy AS 
SELECT id, name, type, model, description, 
       config::text as config, system_prompt, active
FROM agents;
```

### 3. API Compatibility

```python
# Maintain existing endpoints during transition
@router.post("/agents/{agent_id}/run")  # Existing endpoint
@router.post("/virtual/{agent_path}/run")  # New endpoint
```

---

## Migration Timeline

### Week 1-2: Preparation Phase
- [ ] Backup procedures tested and validated
- [ ] Migration scripts developed and tested
- [ ] Rollback procedures documented and tested
- [ ] Stakeholder communication and approval

### Week 3: Database Migration
- [ ] Maintenance window scheduled
- [ ] Database migration executed
- [ ] Data integrity validated
- [ ] System functionality verified

### Week 4-6: Code Migration
- [ ] Agent model selection patterns updated
- [ ] Framework adapters implemented
- [ ] Tool access patterns migrated
- [ ] Comprehensive testing completed

### Week 7-8: Cleanup and Documentation
- [ ] Legacy code removed
- [ ] Documentation updated
- [ ] Migration tools archived
- [ ] Lessons learned documented

---

## Communication Plan

### Stakeholder Notifications:

#### 2 Weeks Before Migration:
- **Development Team**: Detailed technical briefing
- **Operations Team**: Deployment and monitoring plan
- **Product Team**: Feature impact and timeline

#### 1 Week Before Migration:
- **All Teams**: Final migration plan and emergency contacts
- **External Partners**: API changes and maintenance window

#### Day of Migration:
- **Real-time Updates**: Migration progress and any issues
- **Go/No-Go Decision**: Final approval before irreversible changes

#### Post-Migration:
- **Success Confirmation**: All systems validated and functional
- **Lessons Learned**: Migration retrospective and improvements

This breaking changes analysis ensures all stakeholders understand the scope of changes and have clear migration paths to maintain system stability during the architectural evolution.