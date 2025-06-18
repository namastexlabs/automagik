"""Factory for creating appropriate executor based on configuration.

This module provides the ExecutorFactory class that creates the appropriate
executor (Local or SDK mode) based on configuration.
"""

import logging
import os
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
        
        Args:
            mode: Execution mode ('local' or 'sdk'). 
                  If None, defaults to 'local'.
            **kwargs: Additional arguments for the executor
            
        Returns:
            LocalExecutor or ClaudeSDKExecutor instance
            
        Raises:
            ValueError: If mode is not 'local' or 'sdk'
        """
        # Determine execution mode
        if mode is None:
            mode = os.environ.get("CLAUDE_CODE_MODE", "local")
        
        mode = mode.lower()
        logger.info(f"Creating executor for mode: {mode}")
        
        if mode == "local" or mode is None:
            # Import here to avoid circular imports
            from .local_executor import LocalExecutor
            
            # Extract local mode specific kwargs
            workspace_base = kwargs.get('workspace_base', 
                                      os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"))
            cleanup_on_complete = kwargs.get('cleanup_on_complete',
                                           os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true")
            git_cache_enabled = kwargs.get('git_cache_enabled',
                                         os.environ.get("CLAUDE_LOCAL_GIT_CACHE", "false").lower() == "true")
            
            return LocalExecutor(
                workspace_base=workspace_base,
                cleanup_on_complete=cleanup_on_complete,
                git_cache_enabled=git_cache_enabled
            )
        
        elif mode == "sdk":
            # Import SDK executor
            from .sdk_executor import ClaudeSDKExecutor
            
            # Create environment manager if needed
            environment_manager = None
            if kwargs.get('use_environment_manager', True):
                from .local_executor import LocalEnvironmentManager
                
                workspace_base = kwargs.get('workspace_base', 
                                          os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"))
                cleanup_on_complete = kwargs.get('cleanup_on_complete',
                                               os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true")
                git_cache_enabled = kwargs.get('git_cache_enabled',
                                             os.environ.get("CLAUDE_LOCAL_GIT_CACHE", "false").lower() == "true")
                
                environment_manager = LocalEnvironmentManager(
                    workspace_base=workspace_base,
                    cleanup_on_complete=cleanup_on_complete,
                    git_cache_enabled=git_cache_enabled
                )
            
            return ClaudeSDKExecutor(environment_manager=environment_manager)
            
        else:
            raise ValueError(f"Invalid execution mode: {mode}. Only 'local' or 'sdk' modes are supported.")