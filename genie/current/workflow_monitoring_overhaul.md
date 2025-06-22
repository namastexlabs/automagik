# Workflow Monitoring System Overhaul Epic

## Epic Context
**CRITICAL SYSTEM BREAKDOWN DISCOVERED** - Status endpoints completely broken, session continuation missing, data priority chaos

## Root Cause Analysis Complete ✅

### Status Endpoint Data Pipeline BROKEN:
1. **SDK Status Data (PRIMARY)** - Stream processors deleted after completion → `None`
2. **Database Updates (SECONDARY)** - `update_workflow_run_by_run_id()` silently fails → All `0` values  
3. **Session Metadata (FALLBACK)** - Only contains request params → No execution metrics

### Perfect Session Continuation Case:
- **Session ID**: `8b99235a-e9ee-447c-a529-ea6c13de5c3d`
- **Cost**: $1.4468734 (HIGH VALUE)
- **Turns**: 30/30 (MAX REACHED)
- **Status**: `error_max_turns` but work INCOMPLETE
- **Need**: Continue same session with more turns

## Architecture Decisions

### New Data Flow System:
```
SDK Stream Processor (Real-time) 
    ↓ 
Workflow Tables (THE SOURCE)
    ↓
API Status Endpoint (reads workflow tables ONLY)
```

**CRITICAL**: API reads whatever is in workflow tables - NOT as fallback but as THE way to extract real-time workflow data. Workflow tables ARE the real-time data source.

### Workflow Tables First Strategy:
- **STOP using**: `sessions` and `messages` tables for workflow data
- **START using**: `workflow_runs` and `workflow_processes` tables exclusively
- **All workflow fields available**: run_id, session_id, workspace_path, metadata, cost_estimate, total_tokens, etc.

## Implementation Strategy

### Phase 1: Database Persistence Fix (CRITICAL)
- Fix `update_workflow_run_by_run_id()` silent failures
- Add transaction error handling and retries
- Ensure SDK metrics actually persist to database
- Add database update validation

### Phase 2: Status Endpoint Overhaul 
- Rewrite data source priority logic
- Remove dependency on session/messages tables
- Use workflow_runs as primary source
- Add real-time SDK fallback for active workflows

### Phase 3: Session Continuation Feature
- Add `continue_session` API endpoint
- Support same session_id with additional turns
- Preserve workspace and context
- Increment turn limits dynamically

### Phase 4: Stream Processor Persistence
- Keep stream processors alive after completion
- Add LRU cache for recent workflow data
- Provide real-time status for completed workflows
- Add cleanup after configurable TTL

## Success Criteria

✅ **Database Updates Work**: Real metrics persist to workflow_runs
✅ **Status Endpoint Accurate**: Shows real turns, tokens, cost
✅ **Session Continuation**: Can resume max_turns workflows
✅ **Real-time Monitoring**: Active workflows show live progress
✅ **Data Consistency**: Single source of truth in workflow tables

## Technical Specifications

### Session Continuation API:
```python
POST /api/v1/workflows/claude-code/run/{workflow_name}/continue
{
    "session_id": "8b99235a-e9ee-447c-a529-ea6c13de5c3d",
    "additional_turns": 20,
    "message": "Continue the cleanup task from where you left off"
}
```

### Database Schema Validation:
```sql
-- Ensure workflow_runs has all needed fields:
-- run_id, session_id, session_name, workspace_path
-- total_tokens, input_tokens, output_tokens, cost_estimate
-- duration_seconds, metadata, status, error_message
-- created_at, completed_at, updated_at
```

### Stream Processor Lifecycle:
- **Create**: On workflow start
- **Update**: During execution with real metrics  
- **Persist**: On completion to database
- **Cache**: Keep in memory for status queries
- **Cleanup**: After TTL or memory pressure

## File Structure Updates

```
src/agents/claude_code/
├── monitoring/
│   ├── database_persistence.py    # Fix DB updates
│   ├── status_data_aggregator.py  # New data priority system
│   └── session_continuation.py    # Resume workflows
├── api/
│   └── enhanced_status_endpoint.py # Rewritten status logic
└── persistence/
    └── workflow_table_manager.py   # Workflow tables interface
```

## Risk Mitigation

### High Priority Risks:
- **Data Loss**: Backup existing session data before migration
- **API Breaking**: Maintain response format compatibility  
- **Performance**: Stream processor memory usage
- **Concurrency**: Multiple workflows updating same records

### Mitigation Strategies:
- **Gradual Rollout**: Feature flags for new endpoints
- **Data Validation**: Compare old vs new data sources
- **Monitoring**: Real-time metrics on data accuracy
- **Rollback Plan**: Keep legacy endpoints as backup

## Dependencies

### Critical Path:
1. Fix database persistence (blocking everything)
2. Rewrite status endpoint (blocking monitoring)
3. Add session continuation (blocking user value)
4. Stream processor persistence (performance optimization)

### External Dependencies:
- Workflow tables schema validation
- MCP workflow monitoring tools updates
- Agent memory integration for learned patterns
- Linear integration for epic tracking

## Timeline Estimate

**Phase 1 (Critical)**: 1-2 sessions - Database persistence fix
**Phase 2 (Core)**: 2-3 sessions - Status endpoint rewrite  
**Phase 3 (Value)**: 1-2 sessions - Session continuation
**Phase 4 (Polish)**: 1-2 sessions - Stream processor persistence

**Total**: 5-9 focused coding sessions

This epic will transform the workflow monitoring system from broken to production-ready with session continuation as a key differentiator.