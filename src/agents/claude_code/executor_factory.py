"""Factory for creating appropriate executor based on configuration.

This module provides the ExecutorFactory class that creates the appropriate
executor (Docker or Local) based on configuration.
"""

import logging
import os
from typing import Optional

from src.config import settings
from .executor_base import ExecutorBase
from .container import ContainerManager

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Factory for creating appropriate executor based on configuration."""
    
    @staticmethod
    def create_executor(
        mode: Optional[str] = None,
        container_manager: Optional[ContainerManager] = None,
        **kwargs
    ) -> ExecutorBase:
        """Create an executor based on the specified mode.
        
        Args:
            mode: Execution mode ('docker' or 'local'). 
                  If None, reads from CLAUDE_CODE_MODE env var.
            container_manager: Required for Docker mode
            **kwargs: Additional arguments for the executor
            
        Returns:
            ExecutorBase instance
            
        Raises:
            ValueError: If mode is invalid or required args missing
        """
        # Determine execution mode
        if mode is None:
            mode = os.environ.get("CLAUDE_CODE_MODE", "docker")
        
        mode = mode.lower()
        logger.info(f"Creating executor for mode: {mode}")
        
        if mode == "docker":
            # Import here to avoid circular imports
            from .docker_executor import DockerExecutor
            
            if container_manager is None:
                raise ValueError("container_manager is required for Docker mode")
            
            return DockerExecutor(container_manager)
            
        elif mode == "local":
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
            
        else:
            raise ValueError(f"Invalid execution mode: {mode}. Must be 'docker' or 'local'.")