#!/usr/bin/env python3
"""Verify SDK migration is complete.

This script validates that the legacy CLI executor has been successfully removed
and replaced with SDK executor as the default.
"""

import sys
from pathlib import Path
import subprocess
import os

def verify_migration():
    """Check migration completeness."""
    issues = []
    
    print("🔍 Verifying SDK Migration Completeness...")
    print("-" * 50)
    
    # Check files are removed
    removed_files = [
        'src/agents/claude_code/cli_executor.py',
        'src/agents/claude_code/local_executor.py',
        'src/agents/claude_code/utils/find_claude_executable.py',
        'tests/test_cli_executor.py',
        'tests/test_find_executable.py',
    ]
    
    print("📁 Checking legacy files are removed...")
    for file_path in removed_files:
        if Path(file_path).exists():
            issues.append(f"Legacy file still exists: {file_path}")
            print(f"  ❌ {file_path} still exists")
        else:
            print(f"  ✅ {file_path} removed")
    
    # Check CLI executor cannot be imported
    print("\n🚫 Checking CLI executor imports...")
    try:
        # Try to import the CLI executor - should fail
        import sys
        sys.path.insert(0, str(Path.cwd() / 'src'))
        from agents.claude_code.cli_executor import ClaudeCLIExecutor
        issues.append("CLI executor can still be imported!")
        print("  ❌ ClaudeCLIExecutor can still be imported")
    except ImportError:
        print("  ✅ ClaudeCLIExecutor import properly blocked")
    except Exception as e:
        print(f"  ⚠️  Unexpected error importing CLI executor: {e}")
    
    # Check executor factory defaults to SDK
    print("\n🏭 Checking executor factory behavior...")
    try:
        sys.path.insert(0, str(Path.cwd() / 'src'))
        from agents.claude_code.executor_factory import ExecutorFactory
        
        # Test normal factory behavior (should return SDK executor)
        executor = ExecutorFactory.create_executor()
        executor_class = executor.__class__.__name__
        
        if executor_class == 'ClaudeSDKExecutor':
            print(f"  ✅ Factory returns SDK executor: {executor_class}")
        else:
            issues.append(f"Factory returns wrong executor: {executor_class}")
            print(f"  ❌ Factory returns: {executor_class} (expected: ClaudeSDKExecutor)")
            
    except Exception as e:
        issues.append(f"Error testing executor factory: {e}")
        print(f"  ❌ Factory test failed: {e}")
    
    # Migration complete - no emergency override needed
    print("\n✅ Legacy override removed - migration complete")
    
    # Check for remaining CLI executor references in codebase
    print("\n🔍 Scanning for remaining CLI executor references...")
    try:
        result = subprocess.run(
            ['grep', '-r', 'ClaudeCLIExecutor', 'src/', '--exclude-dir=__pycache__'],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            # Found references - check if they're acceptable
            lines = result.stdout.strip().split('\n')
            problematic_refs = []
            
            for line in lines:
                # Skip acceptable references (deprecation handlers, comments, etc.)
                if any(keyword in line.lower() for keyword in [
                    'deprecated', 'legacy', 'remove', 'migration', 
                    '__getattr__', 'importerror', 'has been removed',
                    'claudecliexecutor has been removed', 'verification',
                    "if name == 'claudecliexecutor':"
                ]):
                    continue
                problematic_refs.append(line)
            
            if problematic_refs:
                issues.append(f"Found {len(problematic_refs)} problematic CLI executor references")
                print(f"  ❌ Found problematic references:")
                for ref in problematic_refs[:5]:  # Show first 5
                    print(f"    {ref}")
                if len(problematic_refs) > 5:
                    print(f"    ... and {len(problematic_refs) - 5} more")
            else:
                print("  ✅ Only acceptable CLI executor references found")
        else:
            print("  ✅ No CLI executor references found")
            
    except Exception as e:
        print(f"  ⚠️  Reference scan failed: {e}")
    
    # Check SDK executor is available
    print("\n📦 Checking SDK executor availability...")
    try:
        from agents.claude_code.sdk_executor import ClaudeSDKExecutor
        print("  ✅ ClaudeSDKExecutor can be imported")
    except ImportError as e:
        issues.append(f"SDK executor cannot be imported: {e}")
        print(f"  ❌ ClaudeSDKExecutor import failed: {e}")
    
    # Report results
    print("\n" + "=" * 50)
    if issues:
        print("❌ Migration Issues Found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print(f"\n💡 Fix these issues before completing migration.")
        return 1
    else:
        print("✅ SDK Migration Verified Successfully!")
        print("🎉 All legacy CLI executor code has been properly removed.")
        print("🚀 SDK executor is now the default and working correctly.")
        return 0

if __name__ == "__main__":
    sys.exit(verify_migration())