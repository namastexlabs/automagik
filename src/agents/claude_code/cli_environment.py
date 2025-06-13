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

from .repository_utils import setup_repository, get_current_git_branch

logger = logging.getLogger(__name__)


async def get_current_git_branch_fallback() -> str:
    """Get the current git branch with fallback.
    
    Returns:
        Current git branch name, or 'main' as fallback
    """
    try:
        branch = await get_current_git_branch()
        return branch if branch else "main"
    except Exception as e:
        logger.warning(f"Failed to get current git branch: {e}, defaulting to 'main'")
        return "main"


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
        """Create isolated workspace in /tmp.
        
        Args:
            run_id: Unique identifier for this run
            
        Returns:
            Path to the created workspace
            
        Raises:
            OSError: If workspace creation fails
        """
        workspace_path = self.base_path / f"claude-code-{run_id}"
        
        try:
            # Create workspace directory
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Set proper permissions
            os.chmod(workspace_path, 0o755)
            
            # Track active workspace
            self.active_workspaces[run_id] = workspace_path
            
            logger.info(f"Created workspace: {workspace_path}")
            return workspace_path
            
        except Exception as e:
            logger.error(f"Failed to create workspace for run {run_id}: {e}")
            raise OSError(f"Failed to create workspace: {e}")
    
    async def setup_repository(
        self, 
        workspace: Path, 
        branch: Optional[str],
        repository_url: Optional[str] = None
    ) -> Path:
        """Setup repository in workspace - copy local or clone remote.
        
        Args:
            workspace: Workspace directory path
            branch: Git branch to checkout (defaults to current branch if None)
            repository_url: Repository URL to clone (defaults to local copy if None)
            
        Returns:
            Path to the repository in workspace
            
        Raises:
            RuntimeError: If repository setup fails
        """
        try:
            # Use the new setup_repository function from repository_utils
            repo_path = await setup_repository(
                workspace=workspace,
                branch=branch,
                repository_url=repository_url
            )
            
            logger.info(f"Repository setup complete at {repo_path}")
            return repo_path
            
        except Exception as e:
            logger.error(f"Failed to setup repository: {e}")
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
    
    async def cleanup(self, workspace: Path, force: bool = False) -> bool:
        """Remove workspace and all contents.
        
        Args:
            workspace: Workspace directory path
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
                logger.warning(f"Workspace {workspace} does not exist")
                return True
            
            # Remove workspace
            shutil.rmtree(workspace, ignore_errors=force)
            
            # Remove from active workspaces
            if run_id:
                del self.active_workspaces[run_id]
            
            logger.info(f"Cleaned up workspace: {workspace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup workspace {workspace}: {e}")
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