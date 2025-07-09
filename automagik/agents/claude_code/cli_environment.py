"""CLI Environment Manager for Claude Code agent.

This module manages isolated CLI execution environments with proper
lifecycle management, configuration copying, and cleanup.
"""

import asyncio
import os
import shutil
import logging
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime


logger = logging.getLogger(__name__)




class CLIEnvironmentManager:
    """Manages isolated CLI execution environments with thread-safe operations."""
    
    # Class-level lock for worktree creation to prevent race conditions
    _worktree_creation_lock = asyncio.Lock()
    
    def __init__(
        self,
        base_path: str = "/tmp",
        config_source: Optional[Path] = None,
        repository_cache: Optional[Path] = None,
        session_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
        api_base_url: Optional[str] = None,
        auth_tokens: Optional[Dict[str, str]] = None,
        mcp_endpoints: Optional[Dict[str, str]] = None,
        enable_citations: bool = True,
        enable_artifacts: bool = True,
        workspace_root: Optional[Path] = None,
        git_info: Optional[Any] = None
    ):
        """Initialize the environment manager.
        
        Args:
            base_path: Base directory for creating workspaces
            config_source: Source directory for configuration files
            repository_cache: Path to cached repository for faster cloning
            session_id: Claude session ID
            workflow_name: Name of the workflow being executed
            workflow_run_id: Unique ID for this workflow run
            api_base_url: Base URL for API endpoints
            auth_tokens: Authentication tokens for various services
            mcp_endpoints: MCP server endpoints
            enable_citations: Whether to enable citations feature
            enable_artifacts: Whether to enable artifacts feature
            workspace_root: Root workspace directory
            git_info: Git repository information
        """
        self.base_path = Path(base_path)
        self.config_source = config_source or Path(os.environ.get("PWD", "/home/namastex/workspace/am-agents-labs"))
        self.repository_cache = repository_cache
        self.active_workspaces: Dict[str, Path] = {}
        
        # Environment context
        self.session_id = session_id
        self.workflow_name = workflow_name
        self.workflow_run_id = workflow_run_id
        self.api_base_url = api_base_url
        self.auth_tokens = auth_tokens or {}
        self.mcp_endpoints = mcp_endpoints or {}
        self.enable_citations = enable_citations
        self.enable_artifacts = enable_artifacts
        self.workspace_root = workspace_root or self.config_source
        self.git_info = git_info
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"CLIEnvironmentManager initialized with base path: {self.base_path}")
    
    async def create_workspace(self, run_id: str, workflow_name: Optional[str] = None, persistent: bool = True, git_branch: Optional[str] = None) -> Path:
        """Create git worktree workspace with race condition protection.
        
        Args:
            run_id: Unique identifier for this run
            workflow_name: Optional workflow name for persistent workspaces
            persistent: Whether to create a persistent workspace (default: True)
            git_branch: Optional git branch to checkout
            
        Returns:
            Path to the created worktree workspace
            
        Raises:
            OSError: If worktree creation fails
        """
        # Use lock to prevent concurrent worktree creation race conditions
        async with CLIEnvironmentManager._worktree_creation_lock:
            # Use main repository's worktrees directory
            repo_root = Path(os.environ.get("PWD", "/home/namastex/workspace/am-agents-labs"))
        
        # Use custom branch if provided
        if git_branch:
            branch_name = git_branch
        else:
            # Default branch naming logic - hierarchical structure
            current_branch = await self._get_current_branch(repo_root)
            if workflow_name and persistent:
                # For persistent: include run_id to ensure unique branch names
                # This prevents "already used by worktree" errors
                branch_name = f"{current_branch}-{workflow_name}-{run_id[:8]}"
            else:
                # For temporary: feat/NMSTX-500-test-feature-builder-runuuid
                branch_name = f"{current_branch}-{workflow_name or 'temp'}-{run_id[:8]}"
        
        # If workflow_name is provided, create persistent or temp worktree based on parameter
        if workflow_name:
            if persistent:
                # For persistent: include a short run_id suffix to ensure uniqueness
                # This prevents database constraint violations while keeping paths readable
                safe_branch_name = branch_name.replace("/", "-")
                worktree_path = repo_root / "worktrees" / f"{safe_branch_name}-{run_id[:8]}"
            else:
                # For temporary: use branch name as directory (feat-NMSTX-500-test-feature-builder-runuuid)
                safe_branch_name = branch_name.replace("/", "-")
                worktree_path = repo_root / "worktrees" / safe_branch_name
        else:
            # Fallback to original behavior if no workflow name
            worktree_path = repo_root / "worktrees" / f"builder_run_{run_id}"
        
            # Check if persistent worktree already exists
            if worktree_path.exists() and workflow_name and persistent:
                logger.info(f"Reusing existing persistent worktree: {worktree_path}")
                # Switch to the requested branch if different
                if git_branch:
                    await self._checkout_branch_in_worktree(worktree_path, git_branch)
                # Track active workspace
                self.active_workspaces[run_id] = worktree_path
                return worktree_path
            
            # For non-persistent workspaces, check if the path already exists (race condition)
            if worktree_path.exists() and not persistent:
                # Add a unique suffix to avoid conflicts
                import time
                timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
                safe_branch_name = branch_name.replace("/", "-")
                worktree_path = repo_root / "worktrees" / f"{safe_branch_name}-{timestamp}"
                logger.warning(f"Worktree path already exists, using alternative: {worktree_path}")
        
        try:
            # For temporary workspaces or when a specific branch is requested, create new worktree
            if not persistent or git_branch:
                # Create worktree with new branch
                process = await asyncio.create_subprocess_exec(
                    "git", "worktree", "add", str(worktree_path), "-b", branch_name,
                    cwd=str(repo_root),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    # If branch already exists, use it without -b flag
                    if "already exists" in stderr.decode():
                        process = await asyncio.create_subprocess_exec(
                            "git", "worktree", "add", str(worktree_path), branch_name,
                            cwd=str(repo_root),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            raise OSError(f"Failed to create worktree: {stderr.decode()}")
                    else:
                        raise OSError(f"Failed to create worktree: {stderr.decode()}")
            else:
                # For persistent workspaces without custom branch, always create new branch
                process = await asyncio.create_subprocess_exec(
                    "git", "worktree", "add", str(worktree_path), "-b", branch_name,
                    cwd=str(repo_root),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    # If branch already exists, use it without -b flag
                    if "already exists" in stderr.decode():
                        process = await asyncio.create_subprocess_exec(
                            "git", "worktree", "add", str(worktree_path), branch_name,
                            cwd=str(repo_root),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            raise OSError(f"Failed to create worktree: {stderr.decode()}")
                    else:
                        raise OSError(f"Failed to create worktree: {stderr.decode()}")
            
            # Set proper permissions
            os.chmod(worktree_path, 0o755)
            
            # Track active workspace
            self.active_workspaces[run_id] = worktree_path
            
            logger.info(f"Created worktree workspace: {worktree_path} on branch {branch_name}")
            return worktree_path
            
        except Exception as e:
            # Check if it's a "already exists" error from concurrent creation
            error_msg = str(e).lower()
            if "already exists" in error_msg and worktree_path.exists():
                logger.warning(f"Worktree already created by concurrent process for run {run_id}, using existing")
                # Track active workspace
                self.active_workspaces[run_id] = worktree_path
                return worktree_path
            
            logger.error(f"Failed to create worktree workspace for run {run_id}: {e}")
            raise OSError(f"Failed to create worktree workspace: {e}")
    
    async def _get_current_branch(self, repo_root: Path) -> str:
        """Get the current git branch name.
        
        Args:
            repo_root: Path to the repository root
            
        Returns:
            Current branch name, defaults to 'main' if unable to determine
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--abbrev-ref", "HEAD",
                cwd=str(repo_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                branch = stdout.decode().strip()
                return branch if branch else "main"
            else:
                logger.warning(f"Failed to get current branch: {stderr.decode()}")
                return "main"
        except Exception as e:
            logger.warning(f"Error getting current branch: {e}")
            return "main"
    
    async def _checkout_branch_in_worktree(self, worktree_path: Path, branch: str) -> None:
        """Checkout a specific branch in the worktree.
        
        Args:
            worktree_path: Path to the worktree
            branch: Branch name to checkout
        """
        try:
            # First, try to checkout the branch
            process = await asyncio.create_subprocess_exec(
                "git", "checkout", branch,
                cwd=str(worktree_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                # If branch doesn't exist locally, try to create it from origin
                if "did not match any" in stderr.decode() or "pathspec" in stderr.decode():
                    # Try to checkout from origin
                    process = await asyncio.create_subprocess_exec(
                        "git", "checkout", "-b", branch, f"origin/{branch}",
                        cwd=str(worktree_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        # If that fails, create a new branch
                        process = await asyncio.create_subprocess_exec(
                            "git", "checkout", "-b", branch,
                            cwd=str(worktree_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            logger.warning(f"Failed to checkout branch {branch}: {stderr.decode()}")
                else:
                    logger.warning(f"Failed to checkout branch {branch}: {stderr.decode()}")
            else:
                logger.info(f"Checked out branch {branch} in worktree")
                
        except Exception as e:
            logger.warning(f"Error checking out branch {branch}: {e}")
    
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
                    
                    # SURGICAL FIX: Copy prompt.md to workspace root where SDK expects it
                    workflow_prompt = workflow_dst / "prompt.md"
                    root_prompt = workspace / "prompt.md" 
                    if workflow_prompt.exists():
                        shutil.copy2(workflow_prompt, root_prompt)
                        logger.info("Copied prompt.md to workspace root for SDK")
                    
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
            # Check if this is a persistent worktree (ends with _persistent)
            is_persistent = str(workspace).endswith("_persistent")
            
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
            
            # Cleanup logic:
            # - persistent=true: keep workspace
            # - persistent=false: delete workspace
            if is_persistent:
                logger.info(f"Keeping persistent worktree: {workspace}")
                # Remove from active workspaces tracking but keep the workspace
                if run_id:
                    del self.active_workspaces[run_id]
                return True
            else:
                logger.info(f"Deleting non-persistent worktree: {workspace}")
                # Continue to removal code below
            
            # Use centralized worktree cleanup service
            try:
                from .utils.worktree_cleanup import get_cleanup_service
                cleanup_service = get_cleanup_service(self.workspace_root)
                
                # Try to find run_id for this workspace
                found_run_id = run_id
                if not found_run_id:
                    # Extract from workspace path if possible
                    workspace_name = workspace.name
                    if "run_" in workspace_name:
                        # Extract run_id from patterns like "builder_run_xxx" or "workflow-run-xxx"
                        parts = workspace_name.split("run_")
                        if len(parts) > 1:
                            found_run_id = parts[1].split("-")[0].split("_")[0]
                
                if found_run_id:
                    success = await cleanup_service.cleanup_on_workflow_completion(found_run_id, force)
                else:
                    # Fallback to direct worktree cleanup
                    success = await cleanup_service._cleanup_worktree(workspace)
                
                if not success and force:
                    # Force remove with shutil as fallback
                    shutil.rmtree(workspace, ignore_errors=True)
                    success = True
                
                return success
                        
            except Exception as cleanup_error:
                logger.warning(f"Worktree cleanup service error: {cleanup_error}")
                if force:
                    # Force remove with shutil as fallback
                    shutil.rmtree(workspace, ignore_errors=True)
                    return True
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
    
    async def prepare_workspace(
        self,
        repository_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        session_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """Prepare a workspace for execution.
        
        This method creates a complete workspace environment including:
        1. Creating the workspace (worktree)
        2. Setting up the repository
        3. Copying configuration files
        
        Args:
            repository_url: Git repository URL (optional for worktrees)
            git_branch: Git branch to use
            session_id: Session identifier for workspace naming
            workflow_name: Optional workflow name for persistent workspaces
            
        Returns:
            Dictionary containing workspace information
        """
        try:
            # Use session_id as run_id for workspace creation
            run_id = session_id or f"session_{int(time.time())}"
            
            # DEBUG: Log repository_url to diagnose the issue
            logger.info(f"🔍 PREPARE_WORKSPACE DEBUG: repository_url='{repository_url}', git_branch='{git_branch}', session_id='{session_id}'")
            
            # External repository handling - completely different flow
            if repository_url:
                # For external repositories, git_branch is mandatory
                if not git_branch:
                    raise ValueError("git_branch is mandatory when repository_url is provided")
                
                # Create separate directory for external repositories (NOT in worktrees)
                external_repos_base = self.base_path.parent / "external_repos"
                external_repos_base.mkdir(parents=True, exist_ok=True)
                
                # Extract repository name from URL
                safe_repo_name = repository_url.rstrip('/').split('/')[-1]
                if safe_repo_name.endswith('.git'):
                    safe_repo_name = safe_repo_name[:-4]
                
                # Create workspace name based on persistence
                if persistent and workflow_name:
                    # Persistent: reusable workspace name
                    workspace_name = f"{safe_repo_name}-{workflow_name}"
                    workspace_path = external_repos_base / workspace_name
                    
                    # Check if persistent external repo workspace already exists
                    if workspace_path.exists():
                        repo_path = workspace_path / safe_repo_name
                        if repo_path.exists() and (repo_path / ".git").exists():
                            logger.info(f"Reusing existing external repository workspace: {repo_path}")
                            # Track external repository workspace for auto-commit
                            self.active_workspaces[run_id] = repo_path
                            # Still copy configs and return early
                            await self.copy_configs(repo_path, workflow_name)
                            return {
                                'workspace_path': str(repo_path),
                                'repository_path': str(repo_path),
                                'run_id': run_id,
                                'session_id': session_id,
                                'git_branch': git_branch,
                                'workflow_name': workflow_name
                            }
                else:
                    # Temporary: unique workspace name with run_id
                    workspace_name = f"{safe_repo_name}-{workflow_name or 'workflow'}-{run_id[:8]}"
                    workspace_path = external_repos_base / workspace_name
                
                # Import and use repository_utils for external cloning
                from .repository_utils import setup_repository as repo_setup_repository
                repo_path = await repo_setup_repository(
                    workspace=workspace_path,
                    branch=git_branch,
                    repository_url=repository_url
                )
                
                logger.info(f"Cloned external repository {repository_url} to {repo_path} (separate from worktrees)")
                
                # Track external repository workspace for auto-commit
                self.active_workspaces[run_id] = repo_path
                
            else:
                # Local repository handling - use worktree system
                workspace_path = await self.create_workspace(
                    run_id=run_id, 
                    workflow_name=workflow_name,
                    persistent=persistent,
                    git_branch=git_branch
                )
                
                # Setup repository (for worktrees, this mainly validates)
                repo_path = await self.setup_repository(
                    workspace=workspace_path,
                    branch=git_branch,
                    repository_url=None
                )
            
            # Copy configuration files
            await self.copy_configs(repo_path, workflow_name)
            
            logger.info(f"Prepared workspace at {repo_path} for session {session_id}")
            
            return {
                'workspace_path': str(repo_path),
                'repository_path': str(repo_path),
                'run_id': run_id,
                'session_id': session_id,
                'git_branch': git_branch,
                'workflow_name': workflow_name
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare workspace for session {session_id}: {e}")
            raise RuntimeError(f"Workspace preparation failed: {e}")

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
    
    def as_dict(self, workspace: Path) -> Dict[str, str]:
        """Return environment variables to inject into subprocess.
        
        This replaces the old CLI flag generation with pure data
        that can be used by the SDK executor.
        
        Args:
            workspace: Path to the workspace directory
            
        Returns:
            Dictionary of environment variables to inject
        """
        env = {}
        
        # Core Claude environment
        env['CLAUDE_WORKSPACE'] = str(workspace)
        env['CLAUDE_SESSION_ID'] = self.session_id or ''
        
        # Git information
        if self.git_info:
            if hasattr(self.git_info, 'repo_path'):
                env['CLAUDE_GIT_REPO'] = str(self.git_info.repo_path)
            if hasattr(self.git_info, 'current_branch'):
                env['CLAUDE_GIT_BRANCH'] = self.git_info.current_branch
            if hasattr(self.git_info, 'current_commit'):
                env['CLAUDE_GIT_COMMIT'] = self.git_info.current_commit
        
        # Workflow context
        if self.workflow_name:
            env['CLAUDE_WORKFLOW'] = self.workflow_name
            env['CLAUDE_WORKFLOW_RUN_ID'] = self.workflow_run_id or ''
        
        # API endpoints (if configured)
        if self.api_base_url:
            env['CLAUDE_API_BASE'] = self.api_base_url
        
        # Authentication tokens
        if self.auth_tokens:
            for key, value in self.auth_tokens.items():
                env[f'CLAUDE_AUTH_{key.upper()}'] = value
        
        # MCP server endpoints
        if self.mcp_endpoints:
            env['CLAUDE_MCP_SERVERS'] = json.dumps(self.mcp_endpoints)
        
        # Feature flags
        env['CLAUDE_ENABLE_CITATIONS'] = str(self.enable_citations).lower()
        env['CLAUDE_ENABLE_ARTIFACTS'] = str(self.enable_artifacts).lower()
        
        # Workspace metadata
        env['CLAUDE_WORKSPACE_ROOT'] = str(self.workspace_root)
        env['CLAUDE_TEMP_DIR'] = str(workspace / '.claude-temp')
        
        return env
    
    def list_active_workspaces(self) -> List[str]:
        """List all active workspace run IDs.
        
        Returns:
            List of active run IDs
        """
        return list(self.active_workspaces.keys())
    
    async def cleanup_workspace(self, workspace_path: Any, force: bool = False) -> bool:
        """Clean up a workspace by path (wrapper for cleanup method).
        
        This method provides backward compatibility for code that expects
        a cleanup_workspace method instead of the cleanup method.
        
        Args:
            workspace_path: Path to workspace (can be str or Path object)
            force: Force cleanup even if processes might be running
            
        Returns:
            True if cleanup successful, False otherwise
        """
        # Convert workspace_path to Path object if it's a string
        if isinstance(workspace_path, str):
            workspace_path = Path(workspace_path)
        elif not isinstance(workspace_path, Path):
            # Handle other types by converting to string first, then Path
            workspace_path = Path(str(workspace_path))
        
        return await self.cleanup(workspace_path, force)
    
    async def create_temp_workspace(self, user_id: str, run_id: str) -> Path:
        """Create a temporary workspace without git integration.
        
        Args:
            user_id: User identifier for organization
            run_id: Unique run identifier
            
        Returns:
            Path to the created temporary workspace
        """
        # Create path structure: /tmp/claude-code-temp/{user_id}/workspace_{run_id}
        temp_base = Path("/tmp/claude-code-temp")
        user_dir = temp_base / user_id
        workspace_dir = user_dir / f"workspace_{run_id}"
        
        # Create directories
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Track this as an active workspace
        self.active_workspaces[run_id] = workspace_dir
        
        logger.info(f"Created temporary workspace: {workspace_dir}")
        return workspace_dir
    
    async def cleanup_temp_workspace(self, workspace_path: Path) -> bool:
        """Clean up temporary workspace.
        
        Args:
            workspace_path: Path to the temporary workspace
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Safety check: only clean up paths under /tmp/claude-code-temp
            if str(workspace_path).startswith("/tmp/claude-code-temp/"):
                if workspace_path.exists():
                    # Get the parent user directory before removing workspace
                    user_dir = workspace_path.parent
                    
                    # Remove the workspace directory
                    shutil.rmtree(workspace_path, ignore_errors=True)
                    logger.info(f"Cleaned up temporary workspace: {workspace_path}")
                    
                    # Clean up empty parent user directory if it's empty
                    if user_dir.exists() and user_dir != Path("/tmp/claude-code-temp"):
                        try:
                            # Check if directory is empty (only remove if empty)
                            if not any(user_dir.iterdir()):
                                user_dir.rmdir()
                                logger.info(f"Removed empty user directory: {user_dir}")
                        except OSError:
                            # Directory not empty or permission error, ignore
                            pass
                    
                return True
            else:
                logger.warning(f"Refusing to clean up non-temp workspace: {workspace_path}")
                return False
        except Exception as e:
            logger.error(f"Error cleaning up temp workspace {workspace_path}: {e}")
            return False