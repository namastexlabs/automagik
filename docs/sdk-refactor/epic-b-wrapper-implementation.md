# Epic B - Thin Wrapper Implementation

## Owner: @builder-workflow
## Branch: feature/sdk-migration (after Epic A merged)
## Priority: SECOND - Depends on Epic A

## Objective
Create `ClaudeSDKExecutor` that provides a drop-in replacement for `ClaudeCLIExecutor` using the official SDK.

## Detailed Implementation Steps

### B1. Create SDK Executor Skeleton
Create `/src/agents/claude_code/sdk_executor.py`:

```python
from pathlib import Path
from typing import Optional, AsyncIterator, Dict, Any
import asyncio
from claude_code import ClaudeCode, ClaudeCodeOptions, query
from .cli_executor import CLIResult  # Reuse existing result type
from .cli_environment import CLIEnvironmentManager

class ClaudeSDKExecutor:
    """Drop-in replacement for ClaudeCLIExecutor using official SDK."""
    
    def __init__(self, environment_manager: CLIEnvironmentManager):
        self.env_mgr = environment_manager
        self._claude = ClaudeCode()
    
    async def execute(
        self,
        prompt: str,
        *,
        workspace: Path,
        max_tokens: Optional[int] = None,
        max_thinking_tokens: Optional[int] = None,
        model: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> CLIResult:
        """Execute prompt and return complete result."""
        # Implementation here
        pass
    
    async def execute_until_first_response(
        self,
        prompt: str,
        *,
        workspace: Path,
        **kwargs
    ) -> tuple[list[dict], asyncio.Task]:
        """Execute until first assistant response for UI streaming."""
        # Implementation here
        pass
```

### B2. Option Mapping Helper
```python
def _build_options(
    self,
    workspace: Path,
    max_tokens: Optional[int] = None,
    max_thinking_tokens: Optional[int] = None,
    model: Optional[str] = None,
    resume_session_id: Optional[str] = None,
) -> ClaudeCodeOptions:
    """Build SDK options from parameters and workspace files."""
    options = ClaudeCodeOptions()
    
    # Core options
    if max_tokens:
        options.max_tokens = max_tokens
    if max_thinking_tokens:
        options.max_thinking_tokens = max_thinking_tokens
    if model:
        options.model = model
    if resume_session_id:
        options.continue_session = resume_session_id
    
    # Working directory
    options.cwd = str(workspace)
    
    # Load prompt.md if exists (NEW: system_prompt, not append)
    prompt_file = workspace / "prompt.md"
    if prompt_file.exists():
        options.system_prompt = prompt_file.read_text().strip()
    
    # Load MCP configuration
    mcp_file = workspace / ".mcp.json"
    if mcp_file.exists():
        import json
        with open(mcp_file) as f:
            mcp_config = json.load(f)
            options.mcp_servers = mcp_config.get("servers", {})
    
    # Load allowed tools
    tools_file = workspace / "allowed_tools.json"
    if tools_file.exists():
        import json
        with open(tools_file) as f:
            options.allowed_tools = json.load(f)
    
    return options
```

### B3. Streaming Integration
```python
async def execute(self, prompt: str, *, workspace: Path, timeout: Optional[float] = None, **kwargs) -> CLIResult:
    """Execute prompt with full streaming support."""
    options = self._build_options(workspace, **kwargs)
    
    messages = []
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Apply timeout if specified
        if timeout:
            async with asyncio.timeout(timeout):
                async for message in query(prompt, options):
                    messages.append(message)
        else:
            async for message in query(prompt, options):
                messages.append(message)
    except asyncio.TimeoutError:
        # Handle timeout gracefully
        return CLIResult(
            success=False,
            messages=messages,
            exit_code=1,
            execution_time=asyncio.get_event_loop().time() - start_time,
            error="Execution timed out"
        )
    
    return CLIResult(
        success=True,
        messages=messages,
        exit_code=0,
        execution_time=asyncio.get_event_loop().time() - start_time
    )
```

### B4. Early Return Feature
```python
async def execute_until_first_response(
    self, prompt: str, *, workspace: Path, **kwargs
) -> tuple[list[dict], asyncio.Task]:
    """Stream until first assistant response, return consumed + continuation task."""
    options = self._build_options(workspace, **kwargs)
    consumed = []
    
    # Create a queue for message passing
    queue = asyncio.Queue()
    
    async def stream_messages():
        """Stream all messages to queue."""
        try:
            async for message in query(prompt, options):
                await queue.put(message)
        finally:
            await queue.put(None)  # Sentinel
    
    # Start streaming task
    stream_task = asyncio.create_task(stream_messages())
    
    # Consume until first assistant response
    while True:
        message = await queue.get()
        if message is None:  # Stream ended
            break
        consumed.append(message)
        if message.get('role') == 'assistant' and message.get('content'):
            break
    
    # Create continuation task
    async def continue_stream():
        """Continue consuming from queue."""
        remaining = []
        while True:
            message = await queue.get()
            if message is None:
                break
            remaining.append(message)
        await stream_task  # Ensure task completes
        return consumed + remaining
    
    continuation_task = asyncio.create_task(continue_stream())
    return consumed, continuation_task
```

### B5. Environment Integration
```python
# Extend _build_options to support environment variables
def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
    options = super()._build_options(workspace, **kwargs)
    
    # Get environment variables from manager
    env_vars = self.env_mgr.as_dict(workspace)
    
    # The SDK will need to support env injection in subprocess
    # For now, document this as a gap that needs SDK enhancement
    # TODO: Implement when SDK supports custom env
    
    return options
```

## Success Criteria
- [ ] ClaudeSDKExecutor class created with identical API to ClaudeCLIExecutor
- [ ] execute() method returns CLIResult with proper streaming
- [ ] execute_until_first_response() returns early for UI optimization
- [ ] Workspace files (prompt.md, .mcp.json, allowed_tools.json) are loaded
- [ ] system_prompt used instead of append_system_prompt
- [ ] Timeout handling works correctly
- [ ] All existing tests pass with new executor

## Testing Approach
```python
# Create test file: tests/test_sdk_executor.py
import pytest
from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor

@pytest.mark.asyncio
async def test_basic_execution(tmp_path):
    """Test basic prompt execution."""
    executor = ClaudeSDKExecutor(mock_env_manager)
    result = await executor.execute(
        "What is 2+2?",
        workspace=tmp_path
    )
    assert result.success
    assert any(msg['role'] == 'assistant' for msg in result.messages)

@pytest.mark.asyncio
async def test_system_prompt_loading(tmp_path):
    """Test prompt.md loads as system_prompt."""
    (tmp_path / "prompt.md").write_text("You are a helpful assistant.")
    # Test that system_prompt is set correctly
```

## Files to Create/Modify
- `/src/agents/claude_code/sdk_executor.py` (new)
- `/src/agents/claude_code/__init__.py` (export new class)
- `/tests/test_sdk_executor.py` (new)

## Integration Notes
- Maintain backward compatibility with CLIResult
- Preserve all existing method signatures
- Document any SDK limitations encountered
- Keep streaming behavior identical to CLI version