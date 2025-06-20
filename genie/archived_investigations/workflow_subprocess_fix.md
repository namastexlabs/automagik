# 🚨 CRITICAL WORKFLOW SUBPROCESS FIX

**Date**: 2025-06-20  
**Issue**: SURGEON workflow failed to execute due to subprocess Python environment issue

## Problem Identified

The SURGEON workflow failed with error:
```
ERROR - SDK Executor (SUBPROCESS): SDK execution failed: Claude Code not found. Install with:
```

## Root Cause

The subprocess execution in `execution_isolator.py` uses `sys.executable` which may not point to the virtual environment's Python interpreter. When the subprocess starts, it doesn't have access to the installed packages in the virtual environment, including `claude-code-sdk`.

## Evidence

1. The claude-code-sdk IS installed in the venv:
   ```
   claude-code-sdk  0.0.11
   ```

2. The subprocess is launched without venv activation:
   ```python
   process = await asyncio.create_subprocess_exec(
       sys.executable,  # This might not be the venv Python!
       temp_script_path,
       ...
   )
   ```

## Quick Fix

We need to ensure the subprocess uses the virtual environment's Python interpreter. The fix is in `execution_isolator.py`:

```python
# Line 262 - Replace sys.executable with explicit venv Python path
venv_python = Path.cwd() / ".venv" / "bin" / "python"
if not venv_python.exists():
    venv_python = sys.executable  # Fallback

process = await asyncio.create_subprocess_exec(
    str(venv_python),  # Use venv Python explicitly
    temp_script_path,
    ...
)
```

## Alternative Fix

Add environment activation to the subprocess script generation:

```python
def _generate_subprocess_script(self, request, agent_context):
    script = f'''
import sys
import os

# Activate virtual environment
venv_path = "{Path.cwd() / '.venv'}"
if os.path.exists(venv_path):
    activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
    if os.path.exists(activate_this):
        exec(open(activate_this).read(), {{'__file__': activate_this}})
    else:
        # Add venv site-packages to path
        site_packages = os.path.join(venv_path, 'lib', 'python3.12', 'site-packages')
        sys.path.insert(0, site_packages)

# Rest of the script...
'''
```

## Immediate Workaround

Since the workflows are failing, we can:
1. Manually fix the files using the investigation findings
2. Test the fixes locally
3. Redeploy the system

## Next Steps

1. Apply the subprocess Python interpreter fix
2. Test SURGEON workflow again
3. Verify all P0 bugs get fixed
4. Monitor for successful execution