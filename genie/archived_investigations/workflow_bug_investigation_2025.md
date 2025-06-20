# Workflow System Bug Investigation - January 2025

## 🚨 Critical Issues Summary

Based on previous investigations, the main issues are:
1. **Workspace paths are created but never persisted to database** (NULL in db)
2. **Key mismatch between storage and retrieval** (run_id vs claude_session_id)
3. **Status reporting uses wrong field** (shows false failures)

## API vs MCP Tool Comparison

### API Endpoints (http://localhost:28881/api/v1/)
```
Key Claude Code endpoints:
- POST /api/v1/workflows/claude-code/run/{workflow_name}
- GET  /api/v1/workflows/claude-code/run/{run_id}/status
- POST /api/v1/workflows/claude-code/run/{run_id}/kill
- GET  /api/v1/workflows/claude-code/runs (list with filtering)
- GET  /api/v1/workflows/claude-code/workflows (list available)
- GET  /api/v1/workflows/claude-code/health
```

### MCP Workflow Tools
```
- mcp__automagik-workflows__run_workflow
- mcp__automagik-workflows__list_workflows  
- mcp__automagik-workflows__list_recent_runs
- mcp__automagik-workflows__get_workflow_status
- mcp__automagik-workflows__kill_workflow
```

### Feature Comparison

| Feature | API | MCP Tool | Notes |
|---------|-----|----------|-------|
| Run workflow | ✅ `/run/{workflow_name}` | ✅ `run_workflow` | Both support |
| Get status | ✅ `/run/{run_id}/status` | ✅ `get_workflow_status` | Both support |
| Kill workflow | ✅ `/run/{run_id}/kill` | ✅ `kill_workflow` | Both support |
| List workflows | ✅ `/workflows` | ✅ `list_workflows` | Both support |
| List runs | ✅ `/runs` | ✅ `list_recent_runs` | Both support |
| Health check | ✅ `/health` | ❌ | API only |
| Auto-merge option | ✅ query param | ❌ | API only |
| Persistent option | ✅ query param | ✅ parameter | Both support |

## Missing Testing Features

1. **Direct Database Query Tool** - Need to query workflow_runs table directly
2. **Workspace Inspection Tool** - Need to verify workspace creation
3. **Log Streaming Tool** - Real-time log monitoring beyond `make logs`
4. **Process Monitoring Tool** - Check subprocess execution

## Investigation Plan

1. Deploy test workflow and monitor complete execution
2. Check database state at each stage
3. Verify workspace creation and path storage
4. Trace subprocess execution
5. Monitor API responses vs actual state