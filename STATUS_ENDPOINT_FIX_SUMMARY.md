# Status Endpoint Data Extraction Issues - Root Cause Analysis & Fix

## Problem Summary

The Claude Code workflow status endpoint was showing zero/empty fields for critical metrics despite tools being used and workflows completing successfully. The specific issues were:

1. **Turn counting** = 0 (should show actual turns like 19)
2. **Cost calculation** = $0.00 (should show actual cost like $0.112)
3. **Token usage** = 0 (should show actual tokens like 232,933)  
4. **Tool usage count** = 0 (should show actual count)
5. **Execution time** = 0s (should show actual time like 47s)

## Root Cause Analysis

### Issue 1: Status Endpoint Data Source Priority
**File:** `src/api/routes/claude_code_routes.py`

**Problem:** The status endpoint was trying to extract data from multiple sources (SDK executor, logs, session metadata) but was prioritizing unreliable sources over the accurate session metadata.

**Root Cause:** Lines 676-686 tried to get real-time SDK data first, but for completed workflows, this data isn't available. The endpoint then fell back to parsing logs instead of using the rich session metadata that was already stored.

**Evidence:** Database query showed session metadata contained accurate data:
```json
{
  "total_cost_usd": 0.11218940000000001,
  "total_turns": 19, 
  "total_tokens": 232933,
  "tools_used": ["TodoWrite", "Write", "Bash"],
  "execution_time": 47.3
}
```

### Issue 2: SDK Executor Metrics Loss  
**File:** `src/agents/claude_code/sdk_executor.py`

**Problem:** Some workflows (like run 35c8e5fb) had tools captured but zero cost/turns/tokens, indicating the SDK executor was hitting TaskGroup errors and losing the final ResultMessage containing metrics.

**Root Cause:** Lines 238-250 show the SDK streaming would encounter TaskGroup cancellation errors and continue processing without the final metrics. The ResultMessage containing cost/usage data was lost.

**Evidence:** Database showed one run with tools but no metrics:
```json
{
  "tools": "[\"TodoWrite\",\"LS\",\"Read\"]",
  "cost": 0,
  "turns": 0, 
  "tokens": 0,
  "exec_time": 64.4  // Time captured but metrics lost
}
```

### Issue 3: Turn Counting Logic Error
**File:** `src/api/routes/claude_code_routes.py`

**Problem:** Line 881 was counting assistant messages (`len(assistant_messages)`) instead of using the stored `total_turns` from metadata.

**Root Cause:** The turn counting logic wasn't prioritizing the accurate turn count already stored in session metadata.

## Fixes Implemented

### Fix 1: Prioritize Session Metadata in Status Endpoint

**Changed:** Status endpoint now uses session metadata as the primary source for completed workflows:

```python
# NEW: Extract metrics from session metadata (PRIMARY SOURCE) 
execution_results = metadata.get("execution_results", {})
token_details = execution_results.get("token_details", {})

# Primary metrics directly from session metadata (most reliable)
real_cost = metadata.get("total_cost_usd", 0.0)
real_turns = metadata.get("total_turns", 0)
real_total_tokens = metadata.get("total_tokens", 0)
real_input_tokens = metadata.get("input_tokens", token_details.get("input_tokens", 0))
# ... etc
```

**Impact:** Status endpoint now correctly shows cost, turns, tokens for all completed workflows.

### Fix 2: Capture Metrics During SDK Streaming

**Changed:** SDK executor now captures metrics immediately during streaming to prevent loss:

```python
# NEW: Capture final metrics immediately during streaming to avoid loss
if hasattr(message, 'total_cost_usd') and message.total_cost_usd is not None:
    final_metrics = {
        'total_cost_usd': message.total_cost_usd,
        'num_turns': getattr(message, 'num_turns', 0),
        'duration_ms': getattr(message, 'duration_ms', 0),
        'usage': getattr(message, 'usage', {})
    }
```

**Impact:** Future workflows will have accurate metrics even if TaskGroup errors occur.

### Fix 3: Correct Data Source Priority Logic

**Changed:** Status endpoint now properly prioritizes data sources:

```python
# NEW: Use proper priority: session metadata > SDK > stream status
if workflow_status in ["completed", "failed"] or metadata.get("success") is not None:
    # Use session metadata as primary source for completed workflows
    enhanced_response = EnhancedStatusResponse(...)
elif sdk_status_data:
    # Use SDK stream processor data for running workflows  
    enhanced_response = EnhancedStatusResponse(...)
```

**Impact:** Completed workflows show accurate data, running workflows show real-time data.

### Fix 4: Tools and Turn Count from Metadata

**Changed:** Direct extraction from session metadata:

```python
# NEW: Extract tools used from session metadata (primary source)
tools_used = metadata.get("tools_used", metadata.get("tool_names_used", []))

# NEW: Get real turn count from metadata (primary source)
real_turns = metadata.get("total_turns", metadata.get("current_turns", 0))
```

**Impact:** Tool usage and turn counts now display correctly.

## Verification

### Database Evidence Shows Rich Data Exists
```sql
SELECT 
  json_extract(metadata, '$.run_id') as run_id,
  json_extract(metadata, '$.total_cost_usd') as cost,
  json_extract(metadata, '$.total_turns') as turns,
  json_extract(metadata, '$.total_tokens') as tokens,
  json_extract(metadata, '$.tools_used') as tools
FROM sessions WHERE platform = 'claude-code-api' AND json_extract(metadata, '$.run_status') = 'completed'
```

**Results:**
- Run 014a58bc: $0.112, 19 turns, 232K tokens, 3 tools ✅
- Run f9384632: $0.163, 7 turns, 98K tokens, 2 tools ✅  
- Run 35c8e5fb: $0.00, 0 turns, 0 tokens, 3 tools ❌ (metrics lost)

### Expected Status Endpoint Response

After the fix, the status endpoint should show:

```json
{
  "run_id": "014a58bc-528c-4d08-9f28-b794b1b0c663",
  "status": "completed",
  "progress": {
    "turns": 19,
    "completion_percentage": 100.0
  },
  "metrics": {
    "cost_usd": 0.11218940000000001,
    "tokens": {
      "total": 232933,
      "input": 61,
      "output": 1391,
      "cache_created": 5566,
      "cache_read": 225915
    },
    "tools_used": ["TodoWrite", "Write", "Bash"],
    "api_duration_ms": 47307
  },
  "execution_time_seconds": 47.3
}
```

## Files Modified

1. **`src/api/routes/claude_code_routes.py`** - Status endpoint data extraction logic
2. **`src/agents/claude_code/sdk_executor.py`** - Metrics capture during streaming

## Testing Required

1. **New workflows** - Verify new workflows capture and display metrics correctly
2. **Existing completed workflows** - Verify status endpoint shows stored metadata correctly
3. **Running workflows** - Verify real-time data still works for active workflows

The fix addresses both the immediate issue (status endpoint not reading stored data) and the underlying issue (SDK executor losing metrics during TaskGroup errors).