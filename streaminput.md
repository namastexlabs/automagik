# Stream Input Implementation Guide

## Discovery: The Hidden `--input-format stream-json` Feature

After deep investigation, we discovered that Claude Code **already supports** real-time streaming input through the `--input-format stream-json` flag. The custom `/inject-message` endpoint was unnecessary overengineering - the functionality already exists in the CLI!

## How Stream-JSON Input Works

### CLI Flag
```bash
claudecode --input-format stream-json --output-format stream-json
```

### Format Specification
Stream-JSON uses **line-delimited JSON** (JSONL) where each line is a complete JSON object:

```json
{"type": "user", "message": "Add error handling to the calculator"}
{"type": "user", "message": "Also add a history feature"}
{"type": "system", "message": "Focus on the error handling first"}
```

### Current Implementation Location
- **CLI Argument**: Defined in `src/agents/claude_code/cli.py`
- **Stream Processing**: `src/agents/claude_code/stream_utils.py`
- **Execution Strategy**: `src/agents/claude_code/sdk_execution_strategies.py`

## The Problem

Currently, `--input-format stream-json` is defined but **not connected** to the execution flow. The stdin reading logic exists but isn't activated when the flag is set.

## KISS Implementation Plan

### Step 1: Connect the Existing Pieces (30 minutes)

**File**: `src/agents/claude_code/sdk_execution_strategies.py`

```python
# In ClaudeCodeSDKExecutionStrategy.execute()
async def execute(self, request: WorkflowExecutionRequest) -> WorkflowExecutionResult:
    # Add this check at the beginning
    if request.input_format == "stream-json":
        return await self._execute_with_stream_input(request)
    
    # ... existing execution logic

async def _execute_with_stream_input(self, request: WorkflowExecutionRequest):
    """Execute workflow with real-time stdin monitoring"""
    import sys
    import asyncio
    from .stream_utils import parse_stream_json_line
    
    # Start the workflow process
    process = await self._start_claude_process(request)
    
    # Monitor stdin for new messages
    async def stdin_monitor():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            line = await reader.readline()
            if not line:
                break
                
            try:
                message = parse_stream_json_line(line.decode())
                if message.get("type") == "user":
                    # Send to Claude process stdin
                    process.stdin.write(line)
                    await process.stdin.drain()
            except Exception:
                continue  # Skip malformed lines
    
    # Run workflow and stdin monitor concurrently
    await asyncio.gather(
        self._monitor_process(process, request),
        stdin_monitor()
    )
```

### Step 2: Enable in Workflow Execution (15 minutes)

**File**: `src/api/controllers/workflow_controller.py`

```python
# Pass input_format from API request
async def execute_claude_code_workflow(self, request: WorkflowRequest):
    execution_request = WorkflowExecutionRequest(
        # ... existing fields
        input_format=request.input_format or "text",  # Add this
    )
```

### Step 3: Simple Test Script (10 minutes)

**File**: `test_stream_input.py`

```python
#!/usr/bin/env python3
import json
import time
import sys

# Start a workflow
print(json.dumps({"type": "user", "message": "Create a simple counter app"}))
sys.stdout.flush()

# Wait for initial implementation
time.sleep(5)

# Add new requirement
print(json.dumps({"type": "user", "message": "Add a reset button"}))
sys.stdout.flush()

# Add another requirement
time.sleep(3)
print(json.dumps({"type": "user", "message": "Make the counter persistent"}))
sys.stdout.flush()
```

**Usage**:
```bash
python test_stream_input.py | claudecode --input-format stream-json --output-format stream-json
```

## Why This is Better Than `/inject-message`

1. **No Additional Infrastructure**: Uses existing stdin/stdout pipes
2. **No File Polling**: Direct process communication
3. **No State Management**: Claude Code handles conversation context
4. **Standard Unix Pattern**: Follows pipes philosophy
5. **Already Implemented**: Just needs connection

## Minimal API Integration

If we need HTTP endpoint support, wrap the stream functionality:

```python
@router.post("/workflows/claude-code/run-interactive")
async def run_interactive_workflow(request: WorkflowRequest):
    """Start workflow that accepts streaming input"""
    # Return workflow ID and streaming endpoint
    workflow_id = str(uuid.uuid4())
    
    # Start process with stream-json input
    process = subprocess.Popen(
        ["claudecode", "--input-format", "stream-json"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Store process reference
    active_workflows[workflow_id] = process
    
    return {
        "workflow_id": workflow_id,
        "message_endpoint": f"/workflows/{workflow_id}/send-message",
        "stream_endpoint": f"/workflows/{workflow_id}/stream"
    }

@router.post("/workflows/{workflow_id}/send-message")
async def send_message(workflow_id: str, message: str):
    """Send message to running workflow"""
    process = active_workflows.get(workflow_id)
    if not process:
        raise HTTPException(404, "Workflow not found")
    
    # Send message via stdin
    message_json = json.dumps({"type": "user", "message": message})
    process.stdin.write(message_json + "\n")
    process.stdin.flush()
    
    return {"status": "sent"}
```

## Implementation Priority

1. **Phase 1** (1 hour): Connect `--input-format stream-json` to stdin monitoring
2. **Phase 2** (30 min): Test with manual stdin input
3. **Phase 3** (optional): Add simple HTTP wrapper if needed

## Key Insight

The entire `/inject-message` endpoint and file-based queue system was unnecessary. Claude Code was designed to handle streaming input from the start - we just need to activate it!

## Next Steps

1. Implement `_execute_with_stream_input()` method
2. Test with piped input
3. Document usage examples
4. Remove unnecessary injection code

This approach follows the KISS principle by using what's already there instead of building new complexity.