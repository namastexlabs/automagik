"""CLI Environment Manager for Claude Code agent.

This module manages isolated CLI execution environments with proper
lifecycle management, configuration copying, and cleanup.
"""

import asyncio
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from .repository_utils import setup_repository
from .utils import get_current_git_branch_with_fallback

logger = logging.getLogger(__name__)




class CLIEnvironmentManager:
    """Manages isolated CLI execution environments."""
    
    def __init__(
        self,
        base_path: str = "/tmp",
        config_source: Optional[Path] = None,
        repository_cache: Optional[Path] = None
    ):
        """Initialize the environment manager.
        
        Args:
            base_path: Base directory for creating workspaces
            config_source: Source directory for configuration files
            repository_cache: Path to cached repository for faster cloning
        """
        self.base_path = Path(base_path)
        self.config_source = config_source or Path(os.environ.get("PWD", "/home/namastex/workspace/am-agents-labs"))
        self.repository_cache = repository_cache
        self.active_workspaces: Dict[str, Path] = {}
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"CLIEnvironmentManager initialized with base path: {self.base_path}")
    
    async def create_workspace(self, run_id: str) -> Path:
        """Create git worktree workspace instead of isolated copy.
        
        Args:
            run_id: Unique identifier for this run
            
        Returns:
            Path to the created worktree workspace
            
        Raises:
            OSError: If worktree creation fails
        """
        # Use main repository's worktrees directory
        repo_root = Path(os.environ.get("PWD", "/home/namastex/workspace/am-agents-labs"))
        worktree_path = repo_root / "worktrees" / f"builder_run_{run_id}"
        
        try:
            # Create worktree with new branch
            branch_name = f"builder/run_{run_id}"
            
            # Create worktree
            process = await asyncio.create_subprocess_exec(
                "git", "worktree", "add", str(worktree_path), "-b", branch_name,
                cwd=str(repo_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise OSError(f"Failed to create worktree: {stderr.decode()}")
            
            # Set proper permissions
            os.chmod(worktree_path, 0o755)
            
            # Track active workspace
            self.active_workspaces[run_id] = worktree_path
            
            logger.info(f"Created worktree workspace: {worktree_path} on branch {branch_name}")
            return worktree_path
            
        except Exception as e:
            logger.error(f"Failed to create worktree workspace for run {run_id}: {e}")
            raise OSError(f"Failed to create worktree workspace: {e}")
    
    async def setup_repository(
        self, 
        workspace: Path, 
        branch: Optional[str],
        repository_url: Optional[str] = None
    ) -> Path:
        """Setup repository in worktree workspace - already configured.
        
        Args:
            workspace: Worktree workspace directory path (already has git repo)
            branch: Git branch (already set during worktree creation)
            repository_url: Repository URL (ignored for worktrees)
            
        Returns:
            Path to the repository (same as workspace for worktrees)
            
        Raises:
            RuntimeError: If repository setup fails
        """
        try:
            # For worktrees, the workspace IS the repository
            # No additional setup needed since worktree creation handles branch setup
            
            if not workspace.exists():
                raise RuntimeError(f"Worktree workspace {workspace} does not exist")
            
            # Verify it's a git repository
            git_dir = workspace / ".git"
            if not git_dir.exists():
                raise RuntimeError(f"Worktree workspace {workspace} is not a git repository")
            
            logger.info(f"Worktree repository ready at {workspace}")
            return workspace
            
        except Exception as e:
            logger.error(f"Failed to setup worktree repository: {e}")
            raise
    
    async def copy_configs(self, workspace: Path, workflow_name: Optional[str] = None) -> None:
        """Copy configuration files to workspace.
        
        Args:
            workspace: Workspace directory path
            workflow_name: Optional workflow name to copy specific configs
        """
        config_files = [
            ".env",
            ".mcp.json",
            "allowed_tools.json",
            ".credentials.json"
        ]
        
        # Copy general configuration files
        for config_file in config_files:
            src = self.config_source / config_file
            dst = workspace / config_file
            
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                    logger.debug(f"Copied {config_file} to workspace")
                except Exception as e:
                    logger.warning(f"Failed to copy {config_file}: {e}")
        
        # Copy workflow-specific configuration if provided
        if workflow_name:
            workflow_src = Path(__file__).parent / "workflows" / workflow_name
            workflow_dst = workspace / "workflow"
            
            if workflow_src.exists():
                try:
                    shutil.copytree(workflow_src, workflow_dst, dirs_exist_ok=True)
                    logger.debug(f"Copied workflow {workflow_name} to workspace")
                    
                    # Also copy workflow-specific configs to workspace root
                    for config_file in config_files:
                        workflow_config = workflow_dst / config_file
                        if workflow_config.exists() and not (workspace / config_file).exists():
                            shutil.copy2(workflow_config, workspace / config_file)
                            
                except Exception as e:
                    logger.warning(f"Failed to copy workflow {workflow_name}: {e}")
    
    async def auto_commit_snapshot(self, workspace: Path, run_id: str, message: str = None) -> bool:
        """Automatically commit all changes as a snapshot in the worktree.
        
        Args:
            workspace: Worktree workspace directory path
            run_id: Run identifier for commit message
            message: Optional custom commit message
            
        Returns:
            True if commit successful, False otherwise
        """
        result = await self.auto_commit_with_options(workspace, run_id, message)
        return result.get('success', False)

    async def auto_commit_with_options(
        self, 
        workspace: Path, 
        run_id: str, 
        message: str = None,
        create_pr: bool = False,
        merge_to_main: bool = False,
        pr_title: str = None,
        pr_body: str = None,
        workflow_name: str = None
    ) -> Dict[str, Any]:
        """Enhanced auto-commit with PR creation and merging options.
        
        Args:
            workspace: Worktree workspace directory path
            run_id: Run identifier for commit message
            message: Optional custom commit message
            create_pr: Whether to create a PR after committing
            merge_to_main: Whether to merge to main branch after committing
            pr_title: Custom PR title
            pr_body: Custom PR body
            workflow_name: Workflow name for better commit/PR messages
            
        Returns:
            Dict with success status and operation results
        """
        result = {
            'success': False,
            'commit_sha': None,
            'pr_url': None,
            'merge_sha': None,
            'operations': []
        }
        
        try:
            if not workspace.exists():
                logger.warning(f"Workspace {workspace} does not exist for auto-commit")
                return result
            
            # Add all changes
            add_process = await asyncio.create_subprocess_exec(
                "git", "add", "-A",
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await add_process.communicate()
            
            # Check if there are changes to commit
            status_process = await asyncio.create_subprocess_exec(
                "git", "status", "--porcelain",
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await status_process.communicate()
            
            if not stdout.decode().strip():
                logger.debug(f"No changes to commit in worktree {workspace}")
                result['success'] = True
                result['operations'].append('no_changes')
                return result
            
            # Create commit message
            workflow_prefix = f"{workflow_name}: " if workflow_name else ""
            commit_msg = message or f"auto-snapshot: {workflow_prefix}workflow progress (run {run_id[:8]})"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"{commit_msg}\n\nAuto-committed at {timestamp} by worktree workflow system"
            
            # Commit changes
            commit_process = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", full_message,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await commit_process.communicate()
            
            if commit_process.returncode != 0:
                logger.warning(f"Auto-commit failed for run {run_id}: {stderr.decode()}")
                return result
            
            # Get commit SHA
            sha_process = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            sha_stdout, _ = await sha_process.communicate()
            result['commit_sha'] = sha_stdout.decode().strip()
            result['operations'].append('commit')
            
            logger.info(f"Auto-committed snapshot for run {run_id}: {commit_msg}")
            
            # Create PR if requested
            if create_pr:
                pr_result = await self._create_pull_request(
                    workspace, run_id, pr_title, pr_body, workflow_name, commit_msg
                )
                if pr_result:
                    result['pr_url'] = pr_result
                    result['operations'].append('pr_created')
                    logger.info(f"Created PR for run {run_id}: {pr_result}")
            
            # Merge to main if requested
            if merge_to_main:
                merge_result = await self._merge_to_main(workspace, run_id)
                if merge_result:
                    result['merge_sha'] = merge_result
                    result['operations'].append('merged_to_main')
                    logger.info(f"Merged to main for run {run_id}: {merge_result}")
            
            result['success'] = True
            return result
                
        except Exception as e:
            logger.error(f"Error during auto-commit with options for run {run_id}: {e}")
            return result

    async def _create_pull_request(
        self, 
        workspace: Path, 
        run_id: str, 
        pr_title: str = None,
        pr_body: str = None,
        workflow_name: str = None,
        commit_msg: str = None
    ) -> Optional[str]:
        """Create a pull request for the current branch.
        
        Args:
            workspace: Worktree workspace directory path
            run_id: Run identifier
            pr_title: Custom PR title
            pr_body: Custom PR body
            workflow_name: Workflow name for default PR content
            commit_msg: Commit message for default PR content
            
        Returns:
            PR URL if successful, None otherwise
        """
        try:
            # Get current branch name
            branch_process = await asyncio.create_subprocess_exec(
                "git", "branch", "--show-current",
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            branch_stdout, _ = await branch_process.communicate()
            current_branch = branch_stdout.decode().strip()
            
            if not current_branch:
                logger.error(f"Could not determine current branch for run {run_id}")
                return None
            
            # Generate PR title and body if not provided
            if not pr_title:
                workflow_prefix = f"{workflow_name}: " if workflow_name else ""
                pr_title = f"{workflow_prefix}Workflow run {run_id}"
            
            if not pr_body:
                changes_summary = commit_msg or "Auto-generated changes from workflow execution"
                pr_body = f"""## Summary
{changes_summary}

## Changes
This PR contains changes generated by the Claude Code workflow system.

**Run ID:** `{run_id}`
**Workflow:** {workflow_name or 'Unknown'}
**Branch:** `{current_branch}`

## Review Notes
- Changes were automatically committed during workflow execution
- Please review all modifications before merging

🤖 Generated with [Claude Code](https://claude.ai/code)"""

            # Create PR using gh CLI
            gh_process = await asyncio.create_subprocess_exec(
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--base", "main",
                "--head", current_branch,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await gh_process.communicate()
            
            if gh_process.returncode == 0:
                pr_url = stdout.decode().strip()
                logger.info(f"Created PR for run {run_id}: {pr_url}")
                return pr_url
            else:
                logger.warning(f"Failed to create PR for run {run_id}: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating PR for run {run_id}: {e}")
            return None

    async def _merge_to_main(self, workspace: Path, run_id: str) -> Optional[str]:
        """Merge the current branch to main branch.
        
        Args:
            workspace: Worktree workspace directory path
            run_id: Run identifier
            
        Returns:
            Merge commit SHA if successful, None otherwise
        """
        try:
            # Get current branch name
            branch_process = await asyncio.create_subprocess_exec(
                "git", "branch", "--show-current",
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            branch_stdout, _ = await branch_process.communicate()
            current_branch = branch_stdout.decode().strip()
            
            if not current_branch or current_branch == "main":
                logger.warning(f"Cannot merge: already on main or no branch detected for run {run_id}")
                return None
            
            # Get main repository path from worktree structure
            # workspace is: /path/to/main_repo/worktrees/builder_run_xxxx
            # main_repo is: /path/to/main_repo
            main_repo_path = workspace.parent.parent
            
            # Verify main repo path is correct
            main_git_dir = main_repo_path / ".git"
            if not main_git_dir.is_dir():
                logger.error(f"Main repository not found at {main_repo_path}")
                return None
            
            logger.info(f"Using main repository at: {main_repo_path}")
            
            # Pull latest changes to ensure we're up-to-date
            pull_process = await asyncio.create_subprocess_exec(
                "git", "pull", "origin", "main",
                cwd=str(main_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            pull_stdout, pull_stderr = await pull_process.communicate()
            if pull_process.returncode != 0:
                logger.error(f"Failed to pull latest changes: {pull_stderr.decode()}")
                return None
            
            # Fetch latest changes from the workflow branch
            fetch_process = await asyncio.create_subprocess_exec(
                "git", "fetch", "origin", current_branch,
                cwd=str(main_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            fetch_stdout, fetch_stderr = await fetch_process.communicate()
            if fetch_process.returncode != 0:
                logger.error(f"Failed to fetch branch {current_branch}: {fetch_stderr.decode()}")
                return None
            
            # Switch to main
            checkout_process = await asyncio.create_subprocess_exec(
                "git", "checkout", "main",
                cwd=str(main_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            checkout_stdout, checkout_stderr = await checkout_process.communicate()
            if checkout_process.returncode != 0:
                logger.error(f"Failed to checkout main branch: {checkout_stderr.decode()}")
                return None
            
            # Merge the workflow branch with --no-ff to preserve branch history
            merge_msg = f"Merge workflow run {run_id} from {current_branch}\n\nAuto-merged by Claude Code workflow system"
            merge_process = await asyncio.create_subprocess_exec(
                "git", "merge", "--no-ff", current_branch, "-m", merge_msg,
                cwd=str(main_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await merge_process.communicate()
            
            if merge_process.returncode == 0:
                # Get merge commit SHA
                sha_process = await asyncio.create_subprocess_exec(
                    "git", "rev-parse", "HEAD",
                    cwd=str(main_repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                sha_stdout, _ = await sha_process.communicate()
                merge_sha = sha_stdout.decode().strip()
                
                logger.info(f"Merged branch {current_branch} to main for run {run_id}: {merge_sha}")
                return merge_sha
            else:
                # Check if merge conflict occurred
                if "CONFLICT" in stderr.decode() or merge_process.returncode == 1:
                    logger.error(f"Merge conflict detected for run {run_id}. Aborting merge.")
                    # Abort the merge
                    abort_process = await asyncio.create_subprocess_exec(
                        "git", "merge", "--abort",
                        cwd=str(main_repo_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await abort_process.communicate()
                    logger.warning(f"Merge aborted for run {run_id} due to conflicts")
                else:
                    logger.error(f"Failed to merge to main for run {run_id}: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error merging to main for run {run_id}: {e}")
            return None
    
    async def cleanup(self, workspace: Path, force: bool = False) -> bool:
        """Remove worktree workspace and all contents.
        
        Args:
            workspace: Worktree workspace directory path
            force: Force cleanup even if processes might be running
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Find run_id from workspace path
            run_id = None
            for rid, ws_path in self.active_workspaces.items():
                if ws_path == workspace:
                    run_id = rid
                    break
            
            # Check if workspace exists
            if not workspace.exists():
                logger.warning(f"Worktree workspace {workspace} does not exist")
                return True
            
            # Remove worktree using git command
            try:
                process = await asyncio.create_subprocess_exec(
                    "git", "worktree", "remove", str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.warning(f"Git worktree remove failed: {stderr.decode()}")
                    if force:
                        # Force remove with shutil as fallback
                        shutil.rmtree(workspace, ignore_errors=True)
                    else:
                        return False
                        
            except Exception as git_error:
                logger.warning(f"Git worktree remove error: {git_error}")
                if force:
                    # Force remove with shutil as fallback
                    shutil.rmtree(workspace, ignore_errors=True)
                else:
                    return False
            
            # Clean up branch if this was a temporary branch
            if run_id:
                branch_name = f"builder/run_{run_id}"
                try:
                    process = await asyncio.create_subprocess_exec(
                        "git", "branch", "-D", branch_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    logger.debug(f"Cleaned up branch: {branch_name}")
                except Exception as branch_error:
                    logger.debug(f"Branch cleanup error (non-critical): {branch_error}")
            
            # Remove from active workspaces
            if run_id:
                del self.active_workspaces[run_id]
            
            logger.info(f"Cleaned up worktree workspace: {workspace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup worktree workspace {workspace}: {e}")
            return False
    
    async def cleanup_all(self, force: bool = False) -> Dict[str, bool]:
        """Clean up all active workspaces.
        
        Args:
            force: Force cleanup even if processes might be running
            
        Returns:
            Dictionary mapping run_id to cleanup success status
        """
        results = {}
        
        for run_id, workspace in list(self.active_workspaces.items()):
            results[run_id] = await self.cleanup(workspace, force)
        
        return results
    
    async def cleanup_by_run_id(self, run_id: str, force: bool = False) -> bool:
        """Clean up workspace by run_id.
        
        Args:
            run_id: The run ID to clean up
            force: Force cleanup even if processes might be running
            
        Returns:
            True if cleanup successful, False otherwise
        """
        workspace = self.active_workspaces.get(run_id)
        if not workspace:
            # Construct workspace path from run_id in case it's not in active_workspaces
            repo_root = Path(os.environ.get("PWD", "/home/namastex/workspace/am-agents-labs"))
            workspace = repo_root / "worktrees" / f"builder_run_{run_id}"
        
        # Ensure workspace is a Path object
        if isinstance(workspace, str):
            workspace = Path(workspace)
        
        return await self.cleanup(workspace, force)
    
    async def get_workspace_info(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a workspace.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Dictionary with workspace information or None if not found
        """
        workspace = self.active_workspaces.get(run_id)
        
        if not workspace or not workspace.exists():
            return None
        
        # Gather workspace information
        info = {
            "run_id": run_id,
            "path": str(workspace),
            "created": datetime.fromtimestamp(workspace.stat().st_ctime).isoformat(),
            "size_bytes": sum(f.stat().st_size for f in workspace.rglob("*") if f.is_file()),
            "file_count": len(list(workspace.rglob("*")))
        }
        
        # Check for repository - find first directory that looks like a git repo
        repo_path = None
        for item in workspace.iterdir():
            if item.is_dir() and (item / ".git").exists():
                repo_path = item
                break
        
        if not repo_path:
            # Fallback to default
            repo_path = workspace / "am-agents-labs"
            
        if repo_path and repo_path.exists():
            try:
                # Get current branch
                process = await asyncio.create_subprocess_exec(
                    "git", "rev-parse", "--abbrev-ref", "HEAD",
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                info["git_branch"] = stdout.decode('utf-8').strip()
                
                # Get commit count
                process = await asyncio.create_subprocess_exec(
                    "git", "rev-list", "--count", "HEAD",
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                info["commit_count"] = int(stdout.decode('utf-8').strip())
                
            except Exception as e:
                logger.warning(f"Failed to get git info: {e}")
        
        return info
    
    def list_active_workspaces(self) -> List[str]:
        """List all active workspace run IDs.
        
        Returns:
            List of active run IDs
        """
        return list(self.active_workspaces.keys())