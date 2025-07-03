#!/usr/bin/env python3
"""Script to clean up orphaned git worktrees.

This script can be run periodically (e.g., via cron) to clean up any orphaned
worktrees that weren't properly cleaned up after workflow completion.

Usage:
    python scripts/cleanup_orphaned_worktrees.py [--dry-run] [--max-age-hours=48]
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from automagik.agents.claude_code.utils.worktree_cleanup import cleanup_orphaned_worktrees

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned git worktrees from Claude Code workflows"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be cleaned up, don't actually clean"
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=48,
        help="Maximum age in hours before considering a worktree orphaned (default: 48)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting orphaned worktree cleanup (dry_run={args.dry_run}, max_age={args.max_age_hours}h)")
    
    try:
        # Run cleanup
        results = await cleanup_orphaned_worktrees(
            max_age_hours=args.max_age_hours,
            dry_run=args.dry_run
        )
        
        # Report results
        logger.info(f"Total worktrees found: {results['total_worktrees']}")
        logger.info(f"Orphaned worktrees: {len(results['orphaned'])}")
        
        if results['orphaned']:
            logger.info("Orphaned worktrees details:")
            for orphan in results['orphaned']:
                logger.info(f"  - {orphan['path']} (branch: {orphan['branch']}, age: {orphan['age_hours']:.1f}h)")
        
        if not args.dry_run:
            logger.info(f"Successfully cleaned up: {len(results['cleaned_up'])}")
            if results['cleaned_up']:
                for path in results['cleaned_up']:
                    logger.info(f"  - Removed: {path}")
            
            if results['failed']:
                logger.warning(f"Failed to clean up: {len(results['failed'])}")
                for path in results['failed']:
                    logger.warning(f"  - Failed: {path}")
        
        if results['skipped']:
            logger.info(f"Skipped {len(results['skipped'])} worktrees:")
            reason_counts = {}
            for skip in results['skipped']:
                reason = skip['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            for reason, count in reason_counts.items():
                logger.info(f"  - {reason}: {count}")
        
        # Exit with appropriate code
        if results['failed'] and not args.dry_run:
            sys.exit(1)  # Some cleanups failed
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        logger.error(f"Cleanup failed with error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())