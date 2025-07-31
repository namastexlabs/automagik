# Streaming Endpoint Implementation Plan

## Current State Analysis

### What We Have:
1. Backend can accept `input_format: "stream-json"` in requests
2. JSONL parsing functionality (`parse_stream_json_line`)
3. Model validation for input formats
4. Basic infrastructure for stream execution (but not functional)

### What's Missing:
1. Cannot actually send messages to running workflows
2. No WebSocket/SSE endpoint for real-time communication
3. No output streaming to frontend
4. Current implementation tries to use stdin (won't work in API context)

### Important Discovery:
- Claude SDK already uses `--output-format stream-json` 
- The workflow output is in JSONL format from the SDK
- We need to capture and relay this stream to the frontend

## Correct Implementation Plan

### Phase 1: Fix Core Execution Strategy

The current `_execute_with_stream_input` is flawed. We need to:

1. **Remove stdin monitoring** - doesn't work in API context
2. **Create a message queue** for the workflow
3. **Use the existing file-based approach** OR implement proper IPC

### Phase 2: Create Streaming Endpoint

#### Option A: Server-Sent Events (SSE) - Recommended
```python
@router.get("/workflows/{run_id}/stream")
async def stream_workflow_output(run_id: str):
    """Stream workflow output in real-time."""
    async def event_generator():
        # Read from workflow's _stream.jsonl file
        workspace_path = get_workspace_for_run(run_id)
        stream_file = Path(workspace_path) / "_stream.jsonl"
        
        async with aiofiles.open(stream_file, 'r') as f:
            while True:
                line = await f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    await asyncio.sleep(0.1)
                    
                # Check if workflow is still running
                if not is_workflow_running(run_id):
                    break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

#### Option B: WebSocket - More Complex
```python
@router.websocket("/workflows/{run_id}/ws")
async def workflow_websocket(websocket: WebSocket, run_id: str):
    await websocket.accept()
    
    # Handle bidirectional communication
    # - Receive messages from frontend
    # - Send workflow output to frontend
```

### Phase 3: Message Input Mechanism

Since we can't directly pipe to Claude process stdin, we need:

1. **Message Queue File** in workspace (similar to old injection)
2. **Polling Mechanism** in workflow to check for new messages
3. **OR use MCP tools** for message passing

### Phase 4: Frontend Integration

Update `FRONTEND_INTEGRATION.md` with:

```javascript
// Connect to output stream
const eventSource = new EventSource(`/api/v1/workflows/${runId}/stream`);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Update chat view with new output
};

// Send message to workflow (needs new endpoint)
async function sendMessage(runId, message) {
    await fetch(`/api/v1/workflows/${runId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ message })
    });
}
```

## Recommended Approach

### 1. Start with Output Streaming (Read-Only)
- Implement SSE endpoint to stream `_stream.jsonl` content
- This provides immediate value for real-time chat view
- No workflow modifications needed

### 2. Add Message Input Later
- Could use a simplified version of the old message queue
- OR investigate if Claude SDK supports message injection
- OR use workflow restarts with context

### 3. True Bidirectional Streaming
- WebSocket implementation if needed
- More complex but allows real-time bidirectional communication

## Implementation Priority

1. **SSE Output Streaming** (2-3 hours)
   - `/workflows/{run_id}/stream` endpoint
   - Read from `_stream.jsonl` file
   - Frontend can display real-time output

2. **Message Queue Input** (2-3 hours)
   - `/workflows/{run_id}/messages` POST endpoint
   - Simple file-based queue (like old system but simpler)
   - Workflow polls for messages

3. **Frontend Updates** (1-2 hours)
   - Update integration guide
   - Add example code for streaming
   - Test with real chat view

## Key Insights

1. **Don't use stdin** - not available in API context
2. **Start with output streaming** - provides immediate value
3. **Message input can be added incrementally**
4. **Use existing _stream.jsonl files** - already being written by workflows
5. **Keep it simple** - SSE is easier than WebSockets for output-only

This approach provides real value quickly while avoiding the complexity of full bidirectional streaming initially.