# Claude Code SDK Patch Analysis

## What We Found

Comparing our local version in `src/vendors/claude-code-sdk/` vs official 0.0.10:

### File Changes Summary

1. **subprocess_cli.py** - Major patch with error handling improvements
2. **__init__.py** - Only version number change (0.0.10 → 0.0.14)  
3. **client.py** - Minor formatting and result field changes
4. **types.py** - Extended MCP config types and result message changes

## Detailed Patch Analysis

### 1. subprocess_cli.py (CRITICAL PATCH)

**Our additions:**
- Import `logging` module
- Added `logger = logging.getLogger(__name__)`
- Added `_MAX_BUFFER_SIZE = 1024 * 1024  # 1MB buffer limit`
- Enhanced error handling in `connect()` method:
  - Check if working directory exists before CLI path error
  - Better error messages for FileNotFoundError
- Completely rewritten `receive_messages()` method with:
  - Safety constants (max_stderr_size, stderr_timeout)
  - JSON buffer accumulation for partial messages
  - Buffer size limits and overflow protection
  - Timeout protection for stderr reading
  - Memory limits for stderr collection
  - Better error handling with exit codes vs string matching
  - Generator cleanup handling

**Purpose:** Fixes buffering issues, memory leaks, and improves error handling

### 2. client.py (MINOR PATCH)

**Changes:**
- Formatting improvements (consistent indentation)
- Changed `total_cost_usd=data["total_cost"]` to `total_cost_usd=data.get("total_cost_usd")`
- Removed `cost_usd=data["cost_usd"]` from ResultMessage

**Purpose:** Compatibility with newer API response format

### 3. types.py (FEATURE EXTENSION)

**Our additions:**
- Extended MCP server configs:
  - `McpStdioServerConfig` (with optional type field)
  - `McpSSEServerConfig` (for SSE connections)  
  - `McpHttpServerConfig` (for HTTP connections)
  - Union type `McpServerConfig`
- Added dataclass decorations and type hints
- Changed `ResultMessage` to have optional `total_cost_usd` and removed `cost_usd`

**Purpose:** Support for different MCP transport types

### 4. __init__.py (VERSION ONLY)

**Changes:**
- `__version__ = "0.0.10"` → `__version__ = "0.0.14"`

**Purpose:** Version alignment

## Critical Assessment

### Most Important Patch: subprocess_cli.py
This is a **critical production fix** that solves:
- Memory leaks from unbounded stderr collection
- Hanging processes from infinite stderr reads  
- JSON parsing failures from partial messages
- Poor error reporting

### Questionable Changes
- **types.py MCP extensions** - May not be needed if official SDK adds this
- **client.py formatting** - Minor, could be cosmetic

### Official Version Progress
The official SDK has moved from 0.0.10 → 0.0.14, likely including:
- Bug fixes that might overlap with our patches
- New features we may not need
- Breaking changes we need to adapt to

## Recommended Approach

1. **Install official 0.0.14** ✅ (already done)
2. **Apply only critical subprocess_cli.py patches** as a surgical patch
3. **Test if MCP type extensions are still needed** 
4. **Skip cosmetic client.py changes** unless needed
5. **Create minimal patch system** for future updates

Would you like me to proceed with this surgical approach, focusing only on the critical subprocess_cli.py improvements?