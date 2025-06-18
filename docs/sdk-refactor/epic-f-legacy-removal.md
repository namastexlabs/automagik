# Epic F - Legacy Removal & Rollout

## Owner: @surgeon-workflow
## Branch: feature/sdk-migration (after all tests pass)
## Priority: SIXTH - Only after full validation

## Objective
Remove all legacy CLI executor code and complete the migration to SDK-only implementation.

## ⚠️ CRITICAL: Pre-removal Checklist
Before starting this epic, verify:
- [ ] All SDK tests are passing
- [ ] Performance benchmarks acceptable
- [ ] Production validation completed
- [ ] Team sign-off received
- [ ] Rollback plan documented (despite policy)

## Detailed Implementation Steps

### F1. Hard Switch Implementation

Update all imports to use SDK executor:

```python
# In /src/agents/claude_code/executor_factory.py

import os
from pathlib import Path
from .sdk_executor import ClaudeSDKExecutor
from .cli_environment import CLIEnvironmentManager

def get_executor(environment_manager: CLIEnvironmentManager):
    """
    Get the Claude executor instance.
    
    Migration complete: Only SDK executor is available.
    Emergency override: Set FORCE_LEGACY_EXECUTOR=1 (temporary)
    """
    # Emergency escape hatch (remove after stability confirmed)
    if os.getenv("FORCE_LEGACY_EXECUTOR") == "1":
        import warnings
        warnings.warn(
            "FORCE_LEGACY_EXECUTOR is set - this is deprecated and will be removed!",
            DeprecationWarning,
            stacklevel=2
        )
        # Legacy import kept temporarily
        try:
            from .cli_executor import ClaudeCLIExecutor
            return ClaudeCLIExecutor(environment_manager)
        except ImportError:
            raise RuntimeError("Legacy executor no longer available")
    
    # Standard path: SDK executor
    return ClaudeSDKExecutor(environment_manager)
```

### F2. Update All Import Sites

Search and replace across codebase:

```python
# Find all imports
# OLD: from agents.claude_code.cli_executor import ClaudeCLIExecutor
# NEW: from agents.claude_code.sdk_executor import ClaudeSDKExecutor

# Update locations:
# - /src/agents/claude_agent.py
# - /src/agents/local_agent.py
# - /src/workflow/executor.py
# - Any test files still using direct imports
```

### F3. Remove Legacy Files

Delete the following files after confirming no dependencies:

```bash
# Files to remove
rm src/agents/claude_code/cli_executor.py
rm src/agents/claude_code/utils/find_claude_executable.py
rm tests/test_cli_executor.py
rm tests/test_find_executable.py

# Files to update (remove CLI-specific code)
# - src/agents/claude_code/cli_environment.py (keep only shared functionality)
# - src/agents/claude_code/__init__.py (remove CLI exports)
```

### F4. Clean Up Environment Manager

Remove CLI-specific code from environment manager:

```python
# In cli_environment.py, remove:
# - get_cli_args() method
# - _build_cli_flags() method
# - Any CLI-specific flag generation

# Keep:
# - as_dict() method (for SDK)
# - Git worktree management
# - Session management
# - File copying logic
```

### F5. Update Package Exports

Clean up package exports:

```python
# In /src/agents/claude_code/__init__.py

from .sdk_executor import ClaudeSDKExecutor
from .cli_environment import CLIEnvironmentManager

__all__ = [
    'ClaudeSDKExecutor',
    'CLIEnvironmentManager',
    # Remove: 'ClaudeCLIExecutor'
]

# Add deprecation notice for old import
def __getattr__(name):
    if name == 'ClaudeCLIExecutor':
        raise ImportError(
            "ClaudeCLIExecutor has been removed. "
            "Use ClaudeSDKExecutor instead."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### F6. CI Enforcement

Add regression test to prevent legacy code reintroduction:

```python
# tests/test_no_legacy.py

import pytest
import importlib

def test_cli_executor_removed():
    """Ensure CLI executor cannot be imported."""
    with pytest.raises(ImportError):
        from agents.claude_code.cli_executor import ClaudeCLIExecutor

def test_no_cli_executor_in_codebase():
    """Ensure no references to CLI executor remain."""
    import subprocess
    
    # Search for any remaining references
    result = subprocess.run(
        ['grep', '-r', 'ClaudeCLIExecutor', 'src/', '--exclude-dir=__pycache__'],
        capture_output=True,
        text=True
    )
    
    # Should only find the deprecation handler
    assert result.returncode != 0 or 'deprecation' in result.stdout.lower()

def test_executor_factory_returns_sdk():
    """Ensure factory returns SDK executor."""
    from agents.claude_code.executor_factory import get_executor
    from agents.claude_code.sdk_executor import ClaudeSDKExecutor
    
    executor = get_executor(Mock())
    assert isinstance(executor, ClaudeSDKExecutor)
```

### F7. Migration Verification Script

Create verification script:

```python
# scripts/verify_sdk_migration.py

#!/usr/bin/env python3
"""Verify SDK migration is complete."""

import sys
from pathlib import Path

def verify_migration():
    """Check migration completeness."""
    issues = []
    
    # Check files are removed
    removed_files = [
        'src/agents/claude_code/cli_executor.py',
        'src/agents/claude_code/utils/find_claude_executable.py',
    ]
    
    for file_path in removed_files:
        if Path(file_path).exists():
            issues.append(f"Legacy file still exists: {file_path}")
    
    # Check imports
    try:
        from agents.claude_code.cli_executor import ClaudeCLIExecutor
        issues.append("CLI executor can still be imported!")
    except ImportError:
        pass  # Expected
    
    # Check executor factory
    from agents.claude_code.executor_factory import get_executor
    executor = get_executor(None)
    if not executor.__class__.__name__ == 'ClaudeSDKExecutor':
        issues.append(f"Factory returns wrong executor: {executor.__class__}")
    
    # Report results
    if issues:
        print("❌ Migration Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✅ SDK Migration Verified Successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(verify_migration())
```

## Rollback Procedure (Emergency Only)

If critical issues discovered post-deployment:

1. **Set emergency flag**: `export FORCE_LEGACY_EXECUTOR=1`
2. **Restore from git**:
   ```bash
   git checkout origin/main -- src/agents/claude_code/cli_executor.py
   git checkout origin/main -- src/agents/claude_code/utils/
   ```
3. **Deploy hotfix** with restored files
4. **Investigate** SDK issues
5. **Plan fix** and retry migration

## Success Criteria
- [ ] All legacy executor files deleted
- [ ] No imports of ClaudeCLIExecutor remain
- [ ] executor_factory returns SDK executor
- [ ] All tests pass with SDK only
- [ ] Verification script passes
- [ ] No performance regressions in production
- [ ] Emergency override works (then remove it)

## Post-Migration Cleanup (1 week later)
- [ ] Remove FORCE_LEGACY_EXECUTOR check
- [ ] Delete any remaining legacy test fixtures
- [ ] Update all documentation
- [ ] Close migration epic in Linear

## Communication Plan
1. Announce migration start to team
2. Monitor error rates closely for 24 hours
3. Daily updates for first week
4. Document any issues discovered
5. Final migration report

## Files to Modify/Delete
- DELETE: `/src/agents/claude_code/cli_executor.py`
- DELETE: `/src/agents/claude_code/utils/find_claude_executable.py`
- MODIFY: `/src/agents/claude_code/executor_factory.py`
- MODIFY: `/src/agents/claude_code/__init__.py`
- MODIFY: `/src/agents/claude_code/cli_environment.py`
- CREATE: `/tests/test_no_legacy.py`
- CREATE: `/scripts/verify_sdk_migration.py`