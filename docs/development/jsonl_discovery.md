# JSONL Discovery: The Key to Async-Code UI Pattern

## 🔍 Critical Discovery

While investigating why we have both `.log` and `_stream.jsonl` files in our logs directory, we discovered the **secret sauce** of async-code's UI pattern.

## The Discovery

**Two Types of Log Files:**

1. **`.log` files** - Structured event logs with timestamps and metadata (for debugging)
2. **`_stream.jsonl` files** - Line-delimited JSON conversation streams (for UI display)

## Why This Matters

**The JSONL files are exactly what async-code UI reads for real-time progress!**

### Async-Code Pattern:
- UI polls for `_stream.jsonl` files every 2 seconds
- Reads line-by-line to show conversation flow
- Displays tool calls, responses, file changes, results
- No WebSocket complexity needed - just simple file polling

### Example JSONL Structure:
```json
{"type": "system", "subtype": "init", "cwd": "/path", "tools": [...]}
{"type": "assistant", "message": {"content": "I'll help you..."}}
{"type": "tool_use", "name": "Edit", "input": {"file_path": "..."}}
{"type": "tool_result", "content": "Applied 3 edits..."}
```

## Implementation Impact

### ✅ What This Simplifies:
- **No WebSocket needed** - just HTTP polling + file reading
- **No streaming complexity** - async-code already solved this
- **No real-time infrastructure** - files are the interface
- **Copy exact UI patterns** - proven approach

### 🎯 Our Implementation:
1. Ensure all workflows create `_stream.jsonl` files
2. Copy async-code's file polling mechanism
3. Use same UI components for progress display
4. Adapt data format (task → workflow)

## Files Generated

**Successful Workflows Create:**
- `run_{uuid}.log` - Debug/monitoring logs
- `run_{uuid}_stream.jsonl` - UI display data

**Our Recent Workflows:**
- `run_f36af3d9...` - UI copy workflow (has .log, making progress)
- `run_a5e09cd0...` - Backend API workflow (has .log, making progress)

## Next Steps

1. **Finish UI Conversion** - Complete task→workflow terminology
2. **API Compatibility** - Map /tasks endpoints to /workflows
3. **JSONL Integration** - Ensure UI reads our workflow JSONL files
4. **Test Pattern** - Validate async-code polling works with our data

## Success Criteria

- [ ] Workflows generate proper `_stream.jsonl` files
- [ ] UI can read and display workflow progress from JSONL
- [ ] 2-second polling shows real-time updates
- [ ] All based on proven async-code patterns

---

**Date**: 2025-06-17  
**Discovered by**: GENIE autonomous analysis  
**Impact**: Eliminates need for complex WebSocket implementation