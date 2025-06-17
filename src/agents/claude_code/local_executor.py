"""Local execution implementation for Claude Code agent.

This module provides the LocalExecutor class that executes Claude CLI
directly on the host system without Docker containers.
"""

import time
from typing import Dict, Any
from pathlib import Path

from .executor_base import ExecutorBase
from .models import ClaudeCodeRunRequest
from .cli_environment import CLIEnvironmentManager
from .cli_executor import ClaudeCLIExecutor, CLIResult

import logging
logger = logging.getLogger(__name__)


class LocalExecutor(ExecutorBase):
    """Executes Claude CLI directly on the host system."""
    
    def __init__(
        self, 
        workspace_base: str = "/tmp/claude-workspace",
        cleanup_on_complete: bool = True,
        git_cache_enabled: bool = False,
        timeout: int = 7200,
        max_concurrent: int = 5
    ):
        """Initialize the local executor.
        
        Args:
            workspace_base: Base directory for workspaces
            cleanup_on_complete: Whether to cleanup after execution
            git_cache_enabled: Whether to cache git repositories
            timeout: Default timeout in seconds
            max_concurrent: Maximum concurrent executions
        """
        self.cleanup_on_complete = cleanup_on_complete
        self.git_cache_enabled = git_cache_enabled
        
        # Initialize CLI components
        self.env_manager = CLIEnvironmentManager(
            base_path=Path(workspace_base)
        )
        self.cli_executor = ClaudeCLIExecutor(
            timeout=timeout,
            max_concurrent=max_concurrent,
            env_manager=self.env_manager
        )
        
        logger.info(f"LocalExecutor initialized with workspace base: {workspace_base}")
    
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude CLI task locally.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results
        """
        run_id = agent_context.get('run_id', str(int(time.time())))
        
        try:
            # Create workspace using environment manager
            workspace_path = await self.env_manager.create_workspace(run_id)
            
            # Setup repository
            await self.env_manager.setup_repository(
                workspace_path,
                request.git_branch,
                request.repository_url  # Pass repository URL from request
            )
            
            # Copy workflow configs
            await self.env_manager.copy_configs(workspace_path, request.workflow_name)
            
            # Execute Claude CLI using full execution method (not early response)
            result: CLIResult = await self.cli_executor.execute(
                workflow=request.workflow_name,
                message=request.message,
                workspace=workspace_path,
                session_id=request.session_id,
                max_turns=request.max_turns,
                timeout=request.timeout,
                run_id=run_id
            )
            
            # Auto-commit and merge back to main (unless workflow uses current workspace)
            try:
                commit_message = f"feat: {request.workflow_name} workflow completed (run {run_id[:8]})"
                
                # Check if this workflow uses current workspace (no git operations)
                workflow_uses_current_workspace = await self._workflow_uses_current_workspace(request.workflow_name)
                
                if not workflow_uses_current_workspace:
                    # Default: auto-commit and merge to main
                    # PR creation only if explicitly requested via UI
                    create_pr = getattr(request, 'create_pr_on_success', False)
                    pr_title = getattr(request, 'pr_title', None)
                    pr_body = getattr(request, 'pr_body', None)
                    
                    git_ops_result = await self.env_manager.auto_commit_with_options(
                        workspace_path, 
                        run_id, 
                        commit_message,
                        create_pr=create_pr,
                        merge_to_main=True,  # Always merge back to main
                        pr_title=pr_title,
                        pr_body=pr_body,
                        workflow_name=request.workflow_name
                    )
                    
                    if git_ops_result['success']:
                        logger.info(f"Auto-committed and merged to main for run {run_id}")
                        if git_ops_result.get('pr_url'):
                            logger.info(f"Created PR: {git_ops_result['pr_url']}")
                        
                        # Store git operation results in the result
                        result.auto_commit_sha = git_ops_result.get('commit_sha')
                        result.pr_url = git_ops_result.get('pr_url')
                        result.merge_sha = git_ops_result.get('merge_sha')
                else:
                    logger.info(f"Skipping git operations for {request.workflow_name} (uses current workspace)")
                    
            except Exception as commit_error:
                logger.warning(f"Auto-commit failed for run {run_id}: {commit_error}")
            
            # Cleanup if configured
            if self.cleanup_on_complete and result.success:
                await self.env_manager.cleanup_by_run_id(run_id)
            
            # Convert CLIResult to expected format
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Error executing local Claude task: {str(e)}")
            # Cleanup on error
            if self.cleanup_on_complete:
                try:
                    await self.env_manager.cleanup_by_run_id(run_id)
                except Exception as cleanup_error:
                    logger.error(f"Cleanup error: {cleanup_error}")
            
            return {
                'success': False,
                'session_id': request.session_id,
                'result': '',
                'exit_code': -1,
                'execution_time': 0,
                'logs': '',
                'error': str(e),
                'git_commits': [],
                'workspace_path': None
            }
    
    async def execute_until_first_response(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude CLI and return after first response.
        
        This method starts execution but returns early after Claude's first response.
        The execution continues in the background.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with first response data
        """
        run_id = agent_context.get('run_id', str(int(time.time())))
        
        try:
            # Create workspace using environment manager  
            workspace_path = await self.env_manager.create_workspace(run_id)
            
            # Setup repository
            await self.env_manager.setup_repository(
                workspace_path,
                request.git_branch,
                request.repository_url
            )
            
            # Copy workflow configs
            await self.env_manager.copy_configs(workspace_path, request.workflow_name)
            
            # Start Claude CLI execution and capture first response
            # This is the key difference - we don't wait for completion
            first_response_data = await self.cli_executor.execute_until_first_response(
                workflow=request.workflow_name,
                message=request.message,
                workspace=workspace_path,
                session_id=request.session_id,
                max_turns=request.max_turns,
                timeout=request.timeout,
                run_id=run_id
            )
            
            # Auto-commit initial snapshot (workflow may continue in background)
            try:
                commit_message = f"auto-snapshot: {request.workflow_name} workflow started (run {run_id[:8]})"
                await self.env_manager.auto_commit_snapshot(workspace_path, run_id, commit_message)
                logger.info(f"Auto-committed initial snapshot for run {run_id}")
            except Exception as commit_error:
                logger.warning(f"Initial auto-commit failed for run {run_id}: {commit_error}")
            
            return first_response_data
            
        except Exception as e:
            logger.error(f"Error in execute_until_first_response: {str(e)}")
            return {
                'session_id': request.session_id,
                'first_response': f"Error starting execution: {str(e)}",
                'streaming_started': False
            }
    
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Session ID for local execution
            
        Returns:
            Execution logs as string
        """
        # Try to get logs from log manager if available
        try:
            from .log_manager import get_log_manager
            log_manager = get_log_manager()
            if log_manager:
                log_path = log_manager.get_log_path(execution_id)
                if log_path and log_path.exists():
                    return log_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Could not retrieve logs from log manager: {e}")
        
        return f"Logs for session {execution_id} not available"
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Run ID or session ID for local execution
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            # Try to cancel using CLI executor
            return await self.cli_executor.cancel_execution(execution_id)
        except Exception as e:
            logger.error(f"Error cancelling execution {execution_id}: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            # Clean up CLI executor
            await self.cli_executor.cleanup()
            
            # Clean up environment manager (this will clean up all workspaces)
            # Note: env_manager doesn't have a cleanup method yet
            # We might need to add one later
            
            logger.info("LocalExecutor cleanup completed")
        except Exception as e:
            logger.error(f"Error during LocalExecutor cleanup: {str(e)}")

    async def _workflow_uses_current_workspace(self, workflow_name: str) -> bool:
        """Check if a workflow uses current workspace (no worktree git operations)."""
        try:
            from pathlib import Path
            workflow_env_path = Path(__file__).parent / "workflows" / workflow_name / ".env"
            
            if workflow_env_path.exists():
                with open(workflow_env_path, 'r') as f:
                    content = f.read()
                    return 'current_workspace=true' in content
            
            return False
        except Exception as e:
            logger.warning(f"Error checking workflow env for {workflow_name}: {e}")
            return False
