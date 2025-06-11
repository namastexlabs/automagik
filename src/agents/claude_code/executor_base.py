"""Base executor abstract class for Claude Code agent.

This module defines the abstract base class that all executors must implement
to ensure compatibility with the ClaudeCodeAgent.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from .models import ClaudeCodeRunRequest


class ExecutorBase(ABC):
    """Abstract base class for Claude executors.
    
    All executors must implement these methods to ensure compatibility
    with the ClaudeCodeAgent.
    """
    
    @abstractmethod
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude CLI task.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results:
            {
                'success': bool,
                'session_id': str,
                'result': str,
                'exit_code': int,
                'execution_time': float,
                'logs': str,
                'error': Optional[str],
                'git_commits': List[str],
                'container_id': Optional[str],  # Only for Docker
                'workspace_path': Optional[str]  # Only for Local
            }
        """
        pass
    
    @abstractmethod
    async def execute_until_first_response(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude CLI and return after first response.
        
        This method starts execution and returns as soon as Claude provides
        the first substantial response, rather than waiting for completion.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with first response data:
            {
                'session_id': str,
                'first_response': str,
                'streaming_started': bool
            }
        """
        pass
    
    @abstractmethod
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Container ID (Docker) or Session ID (Local)
            
        Returns:
            Execution logs as string
        """
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Container ID (Docker) or Session ID (Local)
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up all resources."""
        pass