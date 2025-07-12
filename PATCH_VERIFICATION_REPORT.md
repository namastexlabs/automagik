# Claude Code SDK Patch Verification Report

## Current Situation Analysis

### What We Found:
1. **Official 0.0.14 is installed** and working
2. **JSON buffer fix is ALREADY in official 0.0.14** ✅
3. **Stderr memory issue STILL EXISTS** in official version ⚠️
4. **We're using the SDK through the `query()` function** for workflow execution

## Patches Status Comparison

### 1. ✅ JSON Buffer Fix - NO LONGER NEEDED
**Official 0.0.14 already has:**
```python
_MAX_BUFFER_SIZE = 1024 * 1024  # 1MB buffer limit
json_buffer = ""
# Accumulation logic with size checks
```
**Verdict:** They fixed this! Our patch is obsolete.

### 2. ⚠️ Stderr Memory Leak - STILL NEEDED
**Official 0.0.14 still has unbounded stderr:**
```python
async def read_stderr() -> None:
    """Read stderr in background."""
    if self._stderr_stream:
        try:
            async for line in self._stderr_stream:
                stderr_lines.append(line.strip())  # NO LIMIT!
        except anyio.ClosedResourceError:
            pass
```
**Problem:** If a workflow outputs 10GB to stderr, it will consume 10GB of RAM!

### 3. ❌ Working Directory Check - NOT CRITICAL
Our patch adds better error messages but not essential.

### 4. ❌ MCP Type Extensions - NOT USED
We don't use these extended types anywhere in our codebase.

## Our SDK Usage Analysis

### Primary Usage: `query()` function
```python
from claude_code_sdk import query

# Used in sdk_execution_strategies.py
result = await query(
    prompt=request.message,
    options=options
)
```

### Secondary Usage: Type imports
- `AssistantMessage`, `ToolUseBlock`, `ResultMessage`
- `ClaudeCodeOptions`
- Used for parsing and configuration

## Recommendation: Minimal Stderr Patch Only

### Why We Still Need ONE Patch:
- **Memory Safety**: Workflows can output unlimited stderr
- **Production Risk**: Could crash server with OOM
- **Simple Fix**: Just add limits to stderr collection

### Proposed Minimal Solution:

```python
# automagik/vendors/claude_code_sdk_patches.py
import logging
from claude_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

logger = logging.getLogger(__name__)

# Save original method
_original_receive_messages = SubprocessCLITransport.receive_messages

async def patched_receive_messages(self):
    """Patched version with stderr memory limits."""
    # Constants for safety
    MAX_STDERR_SIZE = 10 * 1024 * 1024  # 10MB
    STDERR_TIMEOUT = 30.0  # 30 seconds
    
    # ... minimal patch for stderr handling only
    # Call original for everything else
    
# Apply patch
SubprocessCLITransport.receive_messages = patched_receive_messages
```

### In our code:
```python
# automagik/agents/claude_code/__init__.py
# Apply patches on import
from automagik.vendors import claude_code_sdk_patches
```

## Benefits of This Approach:
1. **Minimal Code**: ~50 lines instead of 1000s
2. **Easy Updates**: Just `pip install --upgrade claude-code-sdk`
3. **Clear Purpose**: Only fixes the one actual bug
4. **No Duplication**: Uses official SDK for everything else
5. **Easy Removal**: When they fix stderr, delete patch file

## Action Plan:
1. ✅ Keep official 0.0.14 installed
2. ⚠️ Create minimal stderr patch (~50 lines)
3. 🗑️ Delete entire `src/vendors/` folder
4. 📝 Document patch clearly for future removal

Should I proceed with this minimal approach?