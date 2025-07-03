#!/usr/bin/env python3
"""Test script for worktree cleanup functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from automagik.agents.claude_code.utils.worktree_cleanup import get_cleanup_service


async def main():
    """Test worktree cleanup functionality."""
    print("Testing worktree cleanup service...")
    
    service = get_cleanup_service()
    
    # List current worktrees
    worktrees = await service._list_git_worktrees()
    print(f"\nFound {len(worktrees)} worktrees:")
    for wt in worktrees:
        print(f"  - {wt['path']} (branch: {wt.get('branch', 'unknown')})")
    
    # Run orphaned worktree detection in dry-run mode
    print("\nRunning orphaned worktree detection (dry-run)...")
    results = await service.cleanup_orphaned_worktrees(max_age_hours=24, dry_run=True)
    
    print(f"\nResults:")
    print(f"  Total worktrees: {results['total_worktrees']}")
    print(f"  Orphaned: {len(results['orphaned'])}")
    print(f"  Would clean up: {len(results['orphaned']) if results['dry_run'] else len(results['cleaned_up'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    
    if results['orphaned']:
        print("\nOrphaned worktrees:")
        for orphan in results['orphaned']:
            print(f"  - {orphan['path']} (age: {orphan['age_hours']:.1f}h)")
    
    if results['skipped']:
        print("\nSkipped worktrees:")
        for skip in results['skipped'][:5]:  # Show first 5
            print(f"  - {skip['path']} (reason: {skip['reason']})")


if __name__ == "__main__":
    asyncio.run(main())