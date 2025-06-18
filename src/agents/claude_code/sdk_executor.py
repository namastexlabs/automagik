"""SDK Executor for Claude Code agent using the official SDK.

This module provides an executor that uses the Claude Code SDK instead of
directly calling the CLI. It includes environment variable injection support.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .executor_base import ExecutorBase
from .models import ClaudeCodeRunRequest
from .cli_environment import CLIEnvironmentManager
from .sdk_transport import EnvironmentAwareTransport, SDKEnvironmentInjector

logger = logging.getLogger(__name__)

# Check if SDK is available
try:
    from claude_code import ClaudeCode, ClaudeCodeOptions, query
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    logger.warning("Claude Code SDK not available. Install with: pip install claude-code")


@dataclass
class SDKResult:
    """Result from SDK execution."""
    success: bool
    session_id: Optional[str]
    messages: List[Dict[str, Any]]
    exit_code: int
    execution_time: float
    logs: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by agent."""
        return {
            'success': self.success,
            'session_id': self.session_id,
            'result': '\n'.join(str(msg) for msg in self.messages),
            'exit_code': self.exit_code,
            'execution_time': self.execution_time,
            'logs': self.logs,
            'error': self.error,
            'messages': self.messages
        }


class ClaudeSDKExecutor(ExecutorBase):
    """Executor that uses the Claude Code SDK with environment injection."""
    
    def __init__(
        self,
        environment_manager: CLIEnvironmentManager,
        workspace_base: str = "/tmp/claude-workspace",
        cleanup_on_complete: bool = True,
        timeout: int = 7200,
        max_concurrent: int = 5
    ):
        """Initialize the SDK executor.
        
        Args:
            environment_manager: CLIEnvironmentManager instance
            workspace_base: Base directory for workspaces
            cleanup_on_complete: Whether to cleanup after execution
            timeout: Default timeout in seconds
            max_concurrent: Maximum concurrent executions
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("Claude Code SDK is not installed")
            
        self.env_mgr = environment_manager
        self.workspace_base = Path(workspace_base)
        self.cleanup_on_complete = cleanup_on_complete
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.env_injector = SDKEnvironmentInjector(environment_manager)
        
        # Initialize SDK client
        self._claude = ClaudeCode()
        
        logger.info(f"ClaudeSDKExecutor initialized with workspace base: {workspace_base}")
    
    def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
        """Build SDK options for execution.
        
        Args:
            workspace: Workspace directory path
            **kwargs: Additional options
            
        Returns:
            ClaudeCodeOptions configured for execution
        """
        options = ClaudeCodeOptions()
        
        # Set workspace directory
        options.cwd = str(workspace)
        
        # Set timeout if provided
        if 'timeout' in kwargs:
            options.timeout = kwargs['timeout'] * 1000  # Convert to milliseconds
        
        # Set max turns if provided
        if 'max_turns' in kwargs:
            options.max_turns = kwargs['max_turns']
        
        # Set allowed tools
        if 'allowed_tools' in kwargs:
            options.allowed_tools = kwargs['allowed_tools']
        else:
            # Default tools for workflows
            options.allowed_tools = [
                "Bash", "LS", "Read", "Write", "Edit", 
                "Glob", "Grep", "Task"
            ]
        
        # Set permission mode to avoid prompts
        options.permission_mode = "acceptEdits"
        
        # Enable verbose mode for better debugging
        options.verbose = True
        
        # NOTE: When SDK supports custom_env, add it here:
        # options.custom_env = self.env_mgr.as_dict(workspace)
        
        return options
    
    async def _create_subprocess_with_env(
        self, 
        options: ClaudeCodeOptions,
        workspace: Path
    ) -> ClaudeCodeOptions:
        """Enhance options with custom environment variables.
        
        NOTE: This is a workaround until SDK supports custom env injection.
        
        Args:
            options: SDK options to enhance
            workspace: Workspace directory path
            
        Returns:
            Enhanced options (currently unchanged as we use process injection)
        """
        # Get environment variables
        custom_env = self.env_mgr.as_dict(workspace)
        
        # TODO: When SDK supports custom env, use:
        # options.custom_env = custom_env
        # 
        # For now, we'll use the workaround in execute methods
        
        return options
    
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude task using the SDK.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results
        """
        import time
        start_time = time.time()
        run_id = agent_context.get('run_id', str(int(time.time())))
        
        try:
            # Create workspace
            workspace_path = await self.env_mgr.create_workspace(run_id)
            
            # Setup repository
            await self.env_mgr.setup_repository(
                workspace_path,
                request.git_branch,
                request.repository_url
            )
            
            # Copy configs
            await self.env_mgr.copy_configs(workspace_path, request.workflow_name)
            
            # Build SDK options
            options = self._build_options(
                workspace_path,
                timeout=request.timeout,
                max_turns=request.max_turns
            )
            
            # Execute with environment injection
            messages = []
            session_id = request.session_id
            
            # Use environment injection workaround
            transport = self.env_injector.create_transport(workspace_path)
            
            try:
                # Inject environment variables
                transport.inject_environment()
                
                # Execute query using SDK
                async for message in query(request.message, options):
                    messages.append(message)
                    
                    # Extract session ID from first message if available
                    if not session_id and isinstance(message, dict):
                        session_id = message.get('session_id', session_id)
                
                success = True
                exit_code = 0
                error = None
                
            except Exception as e:
                logger.error(f"SDK execution failed: {e}")
                success = False
                exit_code = 1
                error = str(e)
                
            finally:
                # Restore environment
                transport.restore_environment()
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Build result
            result = SDKResult(
                success=success,
                session_id=session_id,
                messages=messages,
                exit_code=exit_code,
                execution_time=execution_time,
                logs='\n'.join(str(msg) for msg in messages),
                error=error
            )
            
            # Handle cleanup if configured
            if self.cleanup_on_complete and success:
                await self.env_mgr.cleanup_by_run_id(run_id)
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Error in SDK executor: {e}")
            
            # Cleanup on error
            if self.cleanup_on_complete:
                try:
                    await self.env_mgr.cleanup_by_run_id(run_id)
                except Exception as cleanup_error:
                    logger.error(f"Cleanup error: {cleanup_error}")
            
            return {
                'success': False,
                'session_id': None,
                'result': '',
                'exit_code': 1,
                'execution_time': time.time() - start_time,
                'logs': '',
                'error': str(e)
            }
    
    async def execute_until_first_response(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute and return after first substantial response.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with first response data
        """
        import time
        run_id = agent_context.get('run_id', str(int(time.time())))
        
        try:
            # Create workspace
            workspace_path = await self.env_mgr.create_workspace(run_id)
            
            # Setup repository
            await self.env_mgr.setup_repository(
                workspace_path,
                request.git_branch,
                request.repository_url
            )
            
            # Copy configs
            await self.env_mgr.copy_configs(workspace_path, request.workflow_name)
            
            # Build SDK options
            options = self._build_options(
                workspace_path,
                timeout=request.timeout,
                max_turns=1  # Only get first response
            )
            
            # Use environment injection
            async with self.env_injector.execute_with_env(
                workspace_path,
                self._get_first_response,
                request.message,
                options
            ) as first_response:
                return {
                    'session_id': first_response.get('session_id'),
                    'first_response': str(first_response),
                    'streaming_started': True
                }
                
        except Exception as e:
            logger.error(f"Error getting first response: {e}")
            return {
                'session_id': None,
                'first_response': '',
                'streaming_started': False,
                'error': str(e)
            }
    
    async def _get_first_response(self, message: str, options: ClaudeCodeOptions) -> Dict[str, Any]:
        """Helper to get first response from SDK.
        
        Args:
            message: User message to send
            options: SDK options
            
        Returns:
            First response from SDK
        """
        async for response in query(message, options):
            # Return first substantial response
            if response and isinstance(response, dict):
                return response
        
        return {}
    
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Session ID
            
        Returns:
            Execution logs as string
        """
        # SDK doesn't provide direct log access
        # Would need to implement log storage during execution
        logger.warning("Log retrieval not implemented for SDK executor")
        return "Log retrieval not available for SDK executor"
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Session ID
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        # SDK doesn't provide direct cancellation
        # Would need to track running tasks and cancel them
        logger.warning("Execution cancellation not implemented for SDK executor")
        return False
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Clean up all active workspaces
        await self.env_mgr.cleanup_all(force=True)