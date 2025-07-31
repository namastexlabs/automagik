# Git Worktree Cleanup Documentation

## Overview

The worktree cleanup system automatically manages git worktrees created during Claude Code workflow execution. It ensures that temporary worktrees are cleaned up after workflow completion while preserving persistent workspaces.

## Features

### 1. Automatic Cleanup on Workflow Completion
- Cleans up non-persistent worktrees when workflows complete (successfully or with errors)
- Preserves persistent worktrees for ongoing development
- Updates the database to track cleanup status

### 2. Cleanup on Workflow Termination
- Automatically cleans up worktrees when workflows are killed/cancelled
- Prevents accumulation of orphaned worktrees from interrupted workflows

### 3. Periodic Orphaned Worktree Cleanup
- Identifies worktrees not associated with active workflows
- Respects age thresholds (default: 48 hours)
- Provides dry-run mode for safety
- Handles edge cases where manual deletion left orphaned git references

### 4. Git Worktree Pruning
- Automatically runs `git worktree prune` to clean up stale references
- Handles cases where worktree directories were manually deleted

## Implementation Details

### Core Components

1. **WorktreeCleanupService** (`src/agents/claude_code/utils/worktree_cleanup.py`)
   - Main service class for worktree management
   - Thread-safe cleanup operations
   - Integration with workflow database

2. **Automatic Cleanup Integration**
   - SDK execution strategies: Cleanup on success/failure
   - Process manager: Cleanup when workflows are killed
   - CLI environment: Cleanup logic in workflow lifecycle

3. **Cleanup Script** (`scripts/cleanup_orphaned_worktrees.py`)
   - Standalone script for periodic cleanup
   - Can be run via cron or scheduled tasks
   - Supports dry-run mode for safety

### Database Integration

The cleanup system integrates with the `workflow_runs` table:
- `workspace_path`: Tracks the worktree location
- `workspace_persistent`: Indicates if workspace should be preserved
- `workspace_cleaned_up`: Tracks cleanup status

### Cleanup Rules

1. **Never clean up**:
   - Persistent workspaces (marked with `persistent=true`)
   - Active workflows (status: running/pending)
   - Worktrees less than 1 hour old (safety buffer)
   - Main/master branch worktrees

2. **Always clean up**:
   - Non-persistent worktrees after workflow completion
   - Killed/cancelled workflow worktrees
   - Orphaned worktrees older than threshold (default: 48h)

## Usage

### Manual Cleanup Script

```bash
# Dry run - see what would be cleaned up
python scripts/cleanup_orphaned_worktrees.py --dry-run

# Clean up worktrees older than 24 hours
python scripts/cleanup_orphaned_worktrees.py --max-age-hours=24

# Verbose mode for debugging
python scripts/cleanup_orphaned_worktrees.py --verbose --dry-run
```

### Programmatic Usage

```python
from src.agents.claude_code.utils.worktree_cleanup import cleanup_workflow_worktree

# Clean up a specific workflow's worktree
await cleanup_workflow_worktree(run_id="workflow-run-123")

# Clean up orphaned worktrees
from src.agents.claude_code.utils.worktree_cleanup import cleanup_orphaned_worktrees
results = await cleanup_orphaned_worktrees(max_age_hours=48, dry_run=False)
```

### Scheduled Cleanup (Cron)

Add to crontab for periodic cleanup:

```bash
# Run cleanup daily at 2 AM
0 2 * * * /path/to/python /path/to/automagik/scripts/cleanup_orphaned_worktrees.py --max-age-hours=48
```

## Configuration

### Environment Variables

- `WORKTREE_CLEANUP_AGE_HOURS`: Default age threshold (default: 48)
- `WORKTREE_CLEANUP_ENABLED`: Enable/disable automatic cleanup (default: true)

### Persistent Workspace Patterns

Workspaces are considered persistent if they:
- Have a `.persistent` marker file
- Contain "persistent", "main", "permanent", or "long-term" in the name
- Are the main/master branch worktree

## Troubleshooting

### Common Issues

1. **"fatal: '<path>' is not a working tree"**
   - The worktree was manually deleted
   - Solution: The cleanup system will run `git worktree prune` automatically

2. **"fatal: '<path>' is a main working tree"**
   - Attempting to remove the main repository
   - Solution: Main worktrees are automatically skipped

3. **Cleanup fails with permission errors**
   - Insufficient permissions to remove directories
   - Solution: Ensure the cleanup process runs with appropriate permissions

### Monitoring

Check cleanup logs:
```bash
# View recent cleanup operations
grep "worktree cleanup" logs/claude_code.log

# Check for cleanup errors
grep -i "cleanup.*error" logs/claude_code.log
```

## Best Practices

1. **Use persistent workspaces for long-running development**
   - Set `persistent=true` when creating workflows
   - Persistent workspaces won't be auto-cleaned

2. **Run periodic cleanup**
   - Schedule the cleanup script to run daily
   - Monitor disk usage in the worktrees directory

3. **Handle cleanup failures gracefully**
   - Cleanup failures don't fail the workflow
   - Check logs for cleanup issues

4. **Test cleanup in dry-run mode first**
   - Always test with `--dry-run` before actual cleanup
   - Verify the correct worktrees are identified

## Future Enhancements

1. **Configurable cleanup policies**
   - Per-workflow cleanup settings
   - Custom age thresholds by workflow type

2. **Cleanup metrics**
   - Track disk space reclaimed
   - Monitor cleanup performance

3. **Integration with monitoring**
   - Alerts for cleanup failures
   - Disk usage warnings