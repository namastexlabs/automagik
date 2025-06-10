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
        branch: str,
        repository_url: str = "https://github.com/namastexlabs/am-agents-labs.git"
    ) -> Path:
        """Clone and checkout branch in workspace.
        
        Args:
            workspace: Workspace directory path
            branch: Git branch to checkout
            repository_url: Repository URL to clone
            
        Returns:
            Path to the cloned repository
            
        Raises:
            subprocess.CalledProcessError: If git operations fail
        """
        repo_path = workspace / "am-agents-labs"
        
        try:
            # Use repository cache if available for faster cloning
            if self.repository_cache and self.repository_cache.exists():
                logger.info(f"Using repository cache from {self.repository_cache}")
                clone_cmd = [
                    "git", "clone", 
                    "--reference", str(self.repository_cache),
                    "--dissociate",
                    repository_url,
                    str(repo_path)
                ]
            else:
                # Standard clone with depth limit for performance
                clone_cmd = [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", branch,
                    repository_url,
                    str(repo_path)
                ]
            
            # Execute clone
            process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8')
                logger.error(f"Git clone failed: {error_msg}")
                raise RuntimeError(f"Git clone failed: {error_msg}")
            
            # If we cloned with --depth 1, we need to fetch the branch
            if "--depth" in clone_cmd:
                # Fetch the specific branch with full history
                fetch_cmd = ["git", "fetch", "origin", f"{branch}:{branch}"]
                process = await asyncio.create_subprocess_exec(
                    *fetch_cmd,
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                # Checkout the branch
                checkout_cmd = ["git", "checkout", branch]
                process = await asyncio.create_subprocess_exec(
                    *checkout_cmd,
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8')
                    logger.error(f"Git checkout failed: {error_msg}")
                    raise RuntimeError(f"Git checkout failed: {error_msg}")
            
            # Configure git user for commits
            git_config_cmds = [
                ["git", "config", "user.name", "Claude Code Agent"],
                ["git", "config", "user.email", "claude@automagik-agents.com"],
                ["git", "config", "commit.gpgsign", "false"]
            ]
            
            for cmd in git_config_cmds:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            logger.info(f"Repository setup complete at {repo_path} on branch {branch}")
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
                    shutil.copytree(workflow_src, workflow_dst)
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
        
        # Check for repository
        repo_path = workspace / "am-agents-labs"
        if repo_path.exists():
            try:
                # Get current branch
                process = await asyncio.create_subprocess_exec(
                    "git", "branch", "--show-current",
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