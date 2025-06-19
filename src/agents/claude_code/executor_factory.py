"""Factory for creating appropriate executor based on configuration.

This module provides the ExecutorFactory class that creates the appropriate
executor. After SDK migration, defaults to SDK executor with emergency legacy override.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .executor_base import ExecutorBase

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Factory for creating appropriate executor based on configuration."""
    
    @staticmethod
    def create_executor(
        mode: Optional[str] = None,
        **kwargs
    ) -> ExecutorBase:
        """Create an executor based on mode.
        
        Migration complete: Only SDK executor is available.
        
        Args:
            mode: Execution mode (deprecated - ignored, always returns SDK executor). 
            **kwargs: Additional arguments for the executor
            
        Returns:
            ClaudeSDKExecutor instance
        """
        # Migration complete: SDK executor only
        logger.info("Creating SDK executor (post-migration)")
        
        # Import SDK executor
        from .sdk_executor import ClaudeSDKExecutor
        
        # Create environment manager if needed
        environment_manager = None
        if kwargs.get('use_environment_manager', True):
            from .cli_environment import CLIEnvironmentManager
            
            workspace_base = kwargs.get('workspace_base', 
                                      os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"))
            
            environment_manager = CLIEnvironmentManager(
                base_path=Path(workspace_base)
            )
        
        return ClaudeSDKExecutor(environment_manager=environment_manager)