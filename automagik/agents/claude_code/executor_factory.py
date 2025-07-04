"""Factory for creating Claude Code SDK executor."""

import logging
import os
from pathlib import Path
from typing import Optional

from .executor_base import ExecutorBase

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Factory for creating SDK executor."""
    
    @staticmethod
    def create_executor(**kwargs) -> ExecutorBase:
        """Create SDK executor.
        
        Args:
            **kwargs: Additional arguments for the executor
            
        Returns:
            ClaudeSDKExecutor instance
        """
        logger.debug("Creating SDK executor")
        
        from .sdk_executor import ClaudeSDKExecutor
        
        # Create environment manager if needed
        environment_manager = None
        if kwargs.get('use_environment_manager', True):
            from .cli_environment import CLIEnvironmentManager
            
            workspace_base = kwargs.get('workspace_base', 
                                      os.environ.get("AUTOMAGIK_CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"))
            
            environment_manager = CLIEnvironmentManager(
                base_path=Path(workspace_base)
            )
        
        return ClaudeSDKExecutor(environment_manager=environment_manager)