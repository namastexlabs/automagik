# Fix for tools_used Data Persistence Issue

## Problem
The `tools_used` field was not being properly persisted to the database in the workflow_runs table. Investigation revealed a naming inconsistency between the SDK (which uses `tool_names_used` internally) and the API/database layer (which expects `tools_used`).

## Root Cause
1. The SDK stream processors track tool usage in a field called `tool_names_used`
2. The SDK executor was returning this as `tools_used` in some places but not consistently
3. The API routes expected `tools_used` but would fall back to `tool_names_used` if not found
4. This inconsistency caused data to be lost or not properly persisted

## Solution
Added both `tools_used` and `tool_names_used` fields in all relevant places to ensure:
1. The API always has access to `tools_used` (primary field)
2. Backwards compatibility is maintained with `tool_names_used`
3. Data flows correctly from SDK → Agent → Database → API

## Changes Made

### 1. `/src/agents/claude_code/sdk_stream_processor.py`
- Modified `get_status_data()` to include both fields:
```python
"tools_used": self.metrics.tool_names_used,
"tool_names_used": self.metrics.tool_names_used,  # Keep for backwards compatibility
```

### 2. `/src/agents/claude_code/completion_tracker.py`
- Updated metadata construction to handle both field names with fallback:
```python
"tools_used": execution_results.get("tools_used", execution_results.get("tool_names_used", [])),
"tool_names_used": execution_results.get("tool_names_used", execution_results.get("tools_used", [])),
```

### 3. `/src/agents/claude_code/sdk_executor.py`
- Added both fields in two locations:
  - Real-time progress updates (`_update_real_time_progress`)
  - Final execution results (both `execute` and `execute_with_streaming` methods)

## Testing
Created and ran a test script that verified:
- `tools_used` is properly populated in the formatted metrics
- Both `tools_used` and `tool_names_used` are present for compatibility
- The data flows correctly through the SDK stream processor

## Impact
- The API endpoint `/api/v1/claude-code/status/{run_id}` will now correctly show tools used
- Database persistence of tool usage data is fixed
- No breaking changes - maintains backwards compatibility