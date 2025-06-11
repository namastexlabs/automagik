# NMSTX-258 Technical Decision Records

## Decision 1: Configuration Validation Strategy

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: MCP startup failures due to invalid configurations in database

### Decision
Implement **graceful degradation** validation strategy where invalid configurations are **skipped with warnings** rather than failing the entire startup process.

### Rationale
- **Production Safety**: System continues to function with valid configurations
- **Debugging Friendly**: Clear warnings identify problematic configurations
- **Non-Breaking**: Existing valid configurations remain unaffected
- **Incremental Fix**: Allows gradual cleanup of invalid data

### Alternatives Considered
1. **Fail-Fast Validation**: Reject startup if any invalid configs exist
   - ❌ Too disruptive for production systems
   - ❌ Single bad config could break entire system
2. **Silent Skip**: Skip invalid configs without logging
   - ❌ Hides problems, makes debugging difficult
3. **Auto-Fix**: Attempt to repair invalid configurations
   - ❌ Risk of unintended side effects
   - ❌ Complex logic for edge cases

### Implementation
```python
# Skip invalid configs with structured warnings
if not config.validate_config():
    logger.warning(f"Skipping invalid config: {config.name}", 
                  extra={"validation_errors": config.get_validation_errors()})
    continue
```

**Success Metrics**:
- Zero startup failures due to configuration issues
- Clear diagnostic information in logs
- All valid configurations continue to load successfully

---

## Decision 2: Database Configuration Cleanup Approach

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: Invalid test configurations in production database

### Decision
Implement **manual cleanup with audit trail** for removing invalid configurations from the database.

### Rationale
- **Safety First**: Manual process prevents accidental data loss
- **Audit Trail**: Track what was removed and why
- **Reversible**: Configurations can be restored if needed
- **Transparent**: Clear logging of cleanup operations

### Alternatives Considered
1. **Automatic Cleanup**: Remove invalid configs during startup
   - ❌ Risk of removing configurations that might be fixable
   - ❌ No human oversight for edge cases
2. **Leave Invalid Configs**: Keep them but skip during loading
   - ❌ Database pollution grows over time
   - ❌ Confusing for administrators

### Implementation
```python
async def cleanup_invalid_configurations(audit_mode=True) -> dict:
    """Remove invalid configurations with audit trail."""
    # Audit first, then cleanup with confirmation
    # Log all actions with timestamps and reasons
    # Return detailed cleanup report
```

**Target Configurations for Removal**:
- `manual-test`: Missing required command field
- Any other configs failing validation

**Success Metrics**:
- Clean database with only valid configurations
- Detailed audit log of cleanup actions
- No impact on valid server operations

---

## Decision 3: Dual-Source Configuration Priority

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: Conflicting configurations between .mcp.json file and database

### Decision
Establish **file-first priority** where `.mcp.json` configurations override database configurations for the same server name.

### Rationale
- **Developer Experience**: File configs are easier to version control and modify
- **Deployment Flexibility**: Environment-specific configs via files
- **Override Capability**: Allows temporary overrides without database changes
- **Clear Precedence**: Eliminates ambiguity in configuration source

### Alternatives Considered
1. **Database-First Priority**: Database configs override file configs
   - ❌ Less flexible for development and deployment
   - ❌ Requires database access for configuration changes
2. **Merge Strategy**: Attempt to merge configurations
   - ❌ Complex logic for conflicting values
   - ❌ Unpredictable results for complex configurations
3. **Exclusive Sources**: Only one source active at a time
   - ❌ Reduces flexibility
   - ❌ Requires configuration migration

### Implementation
```python
# Load database configs first
await self._load_database_configs()

# Override with file configs
if config_file_exists:
    file_configs = await self._load_mcp_json_file()
    for name, config in file_configs.items():
        self._config_cache[name] = config  # Override database config
```

**Configuration Sources Priority** (highest to lowest):
1. `.mcp.json` file configurations
2. Database `mcp_configs` table
3. Legacy database configurations (deprecated)

**Success Metrics**:
- Predictable configuration resolution
- Clear logging of source priority decisions
- Smooth development and deployment workflows

---

## Decision 4: MCPServerStdio Parameter Handling

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: Constructor parameter mismatch between command array and expected parameters

### Decision
Implement **command array splitting** where the first element becomes the command parameter and remaining elements become the args parameter.

### Rationale
- **Standards Compliance**: Aligns with PydanticAI MCPServerStdio expectations
- **Backward Compatibility**: Maintains existing configuration format
- **Clear Separation**: Explicit distinction between executable and arguments
- **Error Prevention**: Prevents parameter type mismatches

### Implementation
```python
# Split command array correctly
if not command or len(command) == 0:
    raise MCPError(f"Server {name}: 'command' is required for stdio servers")

main_command = command[0]  # Executable
args = command[1:] if len(command) > 1 else []  # Arguments

server = MCPServerStdio(
    command=main_command,  # str
    args=args,            # List[str]
    env=env or {}
)
```

**Configuration Format**:
```json
{
  "command": ["python", "-m", "myserver", "--verbose"],
  // Becomes: command="python", args=["-m", "myserver", "--verbose"]
}
```

**Success Metrics**:
- No parameter type errors during server creation
- All stdio servers start successfully
- Maintain compatibility with existing configurations

---

## Decision 5: Validation Error Reporting Strategy

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: Need for detailed diagnostic information during configuration validation

### Decision
Implement **structured validation reporting** with detailed error messages and suggested fixes.

### Rationale
- **Debugging Efficiency**: Clear error messages reduce troubleshooting time
- **User Experience**: Helpful suggestions for fixing configurations
- **Automation Friendly**: Structured format enables automated analysis
- **Progressive Disclosure**: Basic warnings with detailed info available

### Implementation
```python
def get_validation_errors(self) -> List[str]:
    """Return detailed validation errors with suggestions."""
    errors = []
    
    if self.server_type == "stdio" and not self.get_command():
        errors.append("STDIO servers require 'command' field. Example: ['python', '-m', 'myserver']")
    
    return errors

# Structured logging
logger.warning("Invalid configuration detected", extra={
    "config_name": config.name,
    "validation_errors": config.get_validation_errors(),
    "suggestion": "Remove from database or fix configuration"
})
```

**Error Categories**:
- **CRITICAL**: Missing required fields
- **WARNING**: Suboptimal but functional configurations  
- **INFO**: Configuration suggestions and best practices

**Success Metrics**:
- Reduced time to diagnose configuration issues
- Clear documentation of all validation requirements
- Improved developer and operator experience

---

## Decision 6: Startup Health Check Architecture

**Status**: APPROVED  
**Date**: 2025-06-11  
**Context**: Need for comprehensive startup diagnostics and health monitoring

### Decision
Implement **multi-phase startup health checks** with detailed reporting and graceful failure handling.

### Rationale
- **Production Reliability**: Early detection of configuration and startup issues
- **Operational Visibility**: Clear status reporting for system administrators
- **Graceful Degradation**: System functions with partial configurations
- **Diagnostic Information**: Detailed health reports for troubleshooting

### Architecture Phases
```python
# Phase 1: Pre-startup audit
audit = await self.audit_configurations()

# Phase 2: Startup with validation
await self.initialize_with_validation()

# Phase 3: Post-startup verification
status = await self.verify_startup_health()

# Phase 4: Ongoing health monitoring
await self.schedule_health_checks()
```

### Health Check Components
1. **Configuration Validation**: Check all configs before startup
2. **Server Connectivity**: Verify servers can be reached
3. **Tool Discovery**: Confirm tools are available
4. **Resource Access**: Test resource accessibility
5. **Performance Baseline**: Measure startup times and response times

**Success Metrics**:
- Complete startup health visibility
- Early detection of configuration issues
- Reduced mean time to resolution for startup problems
- Comprehensive health monitoring dashboard

---

## Implementation Priority

### Phase 1: Critical Path (Immediate)
1. ✅ **Decision 1**: Configuration validation with graceful degradation
2. ✅ **Decision 2**: Manual cleanup of invalid configurations
3. ✅ **Decision 4**: MCPServerStdio parameter handling

### Phase 2: Enhanced Reliability (Next Sprint)
4. **Decision 5**: Structured validation error reporting
5. **Decision 3**: Dual-source configuration priority
6. **Decision 6**: Startup health check architecture

### Success Criteria
- ✅ MCP startup error resolved
- ✅ No breaking changes introduced
- ✅ Improved diagnostic capabilities
- ✅ Foundation for robust configuration management

## Rollback Strategy

All decisions include rollback mechanisms:
- **Configuration validation**: Can be disabled via feature flag
- **Database cleanup**: Audit trail allows restoration
- **Parameter handling**: Backward compatible with existing configs
- **Health checks**: Optional enhancement, can be disabled

**Risk Assessment**: **LOW** - All changes are additive and include fallback mechanisms.