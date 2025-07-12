# Claude Code SDK Patches

This directory contains minimal monkey patches for the official `claude-code-sdk` to fix critical production issues.

## Current Patches

### 1. Stderr Memory Limit Patch

**Problem**: The official SDK (as of v0.0.14) reads stderr without any limits, which can cause memory exhaustion if a process outputs large amounts of stderr.

**Solution**: Our patch adds:
- 10MB memory limit for stderr collection
- 30-second timeout for stderr reading
- Proper cleanup when limits are exceeded

**When to remove**: Once the official SDK adds stderr memory limits, this patch can be deleted.

## How It Works

1. The patches are automatically applied when importing `automagik.agents.claude_code`
2. Uses monkey patching to override specific methods
3. No code duplication - we use the official SDK for everything else

## Testing

```bash
# Test that patches load correctly
source .venv/bin/activate
python -c "import automagik.vendors.claude_code_sdk_patches; print('Patches loaded')"
```

## Future Patches

If new critical issues are found, add new patch files here following the same pattern:
1. Create a new `*_patch.py` file
2. Import and apply in `__init__.py`
3. Document the issue and when to remove