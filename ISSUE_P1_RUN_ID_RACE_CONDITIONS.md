# ⚠️ P1 HIGH: Run ID Race Conditions & Duplicate Records

## Issue Summary
**Workflow run record creation has race conditions causing duplicate record warnings and potential database inconsistencies.**

## Evidence
```bash
# Pattern appears in EVERY workflow launch:
WARNING: Failed to create workflow run record: Workflow run with run_id 'cd2ad1be-d1ca-4114-b2b5-37c584abca72' already exists
WARNING: Failed to create workflow run record: Workflow run with run_id '2dd481d7-818e-42a9-b296-e112daca8dcd' already exists
```

## Root Cause Analysis
```bash
# SEQUENCE OF EVENTS:
1. API endpoint creates workflow run record (SUCCESS)
2. Background agent tries to create same record (DUPLICATE WARNING)
3. Both processes continue with potentially inconsistent data
```

## Affected Systems
- **Database integrity**: Potential data corruption from race conditions
- **Logging clarity**: Warning noise in every workflow execution  
- **Monitoring confidence**: Suggests underlying coordination issues
- **Debugging difficulty**: Harder to identify real vs false warnings

## Technical Details
```python
# File: src/api/routes/claude_code_routes.py
# Line: Creates initial workflow run record
Created workflow run record {record_id} for run_id {run_id}

# File: src/agents/claude_code/agent.py  
# Line: Background agent attempts duplicate creation
Failed to create workflow run record: Workflow run with run_id '{run_id}' already exists
```

## Business Impact
- **MEDIUM**: Database consistency concerns
- **LOW**: Operational noise in logs
- **LOW**: Potential future scaling issues

## Proposed Fix
1. **Check-then-create pattern**: Verify record existence before creation
2. **Coordinator pattern**: Single source of truth for record creation
3. **Idempotent operations**: Make record creation safely repeatable

## Investigation Areas
- `src/api/routes/claude_code_routes.py` - API record creation
- `src/agents/claude_code/agent.py` - Background record creation
- `src/db/repository/workflow_run.py` - Database operations
- Timing between API response and background agent startup

## Suggested Solutions
```python
# Option 1: Skip duplicate creation in background agent
if not workflow_run_exists(run_id):
    create_workflow_run_record(run_id)

# Option 2: Make creation idempotent  
create_or_update_workflow_run_record(run_id)

# Option 3: Coordinate via message queue
enqueue_workflow_run_creation(run_id)
```

## Acceptance Criteria
- [ ] No duplicate record warnings in logs
- [ ] Single workflow run record per run_id
- [ ] Consistent data between API and background agent
- [ ] Clean logs without warning noise
- [ ] Race condition-free record creation

## Risk Level: HIGH ⚠️
**Could lead to data inconsistencies and scaling issues.**