# Session Name Epic Association Pattern

## Overview

The Automagik Agents platform uses `session_name` to associate workflow runs with epics, providing a clean way to track related workflows without requiring additional database fields or API endpoints.

## Pattern Format

```
epic:{epic_id}:{task_name}
```

### Components

- **epic:** - Fixed prefix indicating this session is part of an epic
- **{epic_id}** - The Linear epic identifier (e.g., `NMSTX-123`)
- **{task_name}** - Human-readable task description

### Examples

```bash
# Epic session names
epic:NMSTX-123:implement-user-auth
epic:NMSTX-456:add-dark-mode-toggle
epic:NMSTX-789:optimize-database-queries

# Regular session names (non-epic)
fix-login-bug
update-documentation
refactor-api-endpoints
```

## Usage in Workflow API

When creating a workflow run, use the `session_name` parameter to associate it with an epic:

```bash
# Create workflow run associated with epic
curl -X POST "/api/v1/workflows/claude-code/run/implement" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Implement JWT authentication system",
    "session_name": "epic:NMSTX-123:implement-user-auth",
    "max_turns": 50
  }'
```

## Querying Epic-Associated Workflows

### Using Existing Endpoints

The pattern integrates seamlessly with existing workflow_runs table queries:

```python
# Get all workflows for a specific epic
from src.db.repository.workflow_run import list_workflow_runs

epic_workflows, total = list_workflow_runs(
    filters={
        'session_name': 'epic:NMSTX-123:%'  # SQL LIKE pattern
    }
)

# Or using the existing session_name field in API queries
```

### Database Queries

```sql
-- Get all workflows for an epic
SELECT * FROM workflow_runs 
WHERE session_name LIKE 'epic:NMSTX-123:%'
ORDER BY created_at DESC;

-- Get epic summary statistics
SELECT 
    SUBSTR(session_name, 6, INSTR(session_name || ':', ':', 6) - 6) as epic_id,
    COUNT(*) as workflow_count,
    SUM(cost_estimate) as total_cost,
    AVG(duration_seconds) as avg_duration
FROM workflow_runs 
WHERE session_name LIKE 'epic:%'
GROUP BY epic_id;
```

## Benefits

1. **No Schema Changes** - Uses existing `session_name` field
2. **No New Endpoints** - Works with existing API structure  
3. **Backward Compatible** - Non-epic workflows continue to work normally
4. **Flexible Queries** - Can filter by exact epic or pattern matching
5. **Human Readable** - Session names remain descriptive and useful

## Implementation Notes

- The pattern is **optional** - workflows without epic association use regular session names
- Epic IDs should follow Linear ticket format (e.g., `NMSTX-XXX`)
- Task names should use kebab-case for consistency
- The pattern enables future epic-specific tooling without API changes

## Migration from Metadata Approach

If epic association was previously stored in metadata:

```python
# Old approach (metadata)
metadata = {"epic_id": "NMSTX-123", "task": "implement-user-auth"}

# New approach (session_name)
session_name = "epic:NMSTX-123:implement-user-auth"
```

The session_name approach is simpler and more queryable than metadata storage.