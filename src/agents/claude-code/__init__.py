"""Claude-Code Agent Module.

This module provides containerized Claude CLI execution capabilities
for long-running, autonomous AI workflows.
"""

from typing import Dict, Optional, Any
import logging
import traceback

# Setup logging first
logger = logging.getLogger(__name__)

try:
    from .agent import ClaudeCodeAgent
    from .container import ContainerManager
    from .executor import ClaudeExecutor
    from .models import (
        ClaudeCodeRunRequest,
        ClaudeCodeRunResponse, 
        ClaudeCodeStatusResponse,
        WorkflowInfo,
        ContainerInfo,
        ExecutionResult,
        ClaudeCodeConfig,
        ContainerStatus,
        ExecutionStatus,
        WorkflowType,
        ContainerConfig,
        GitConfig,
        WorkflowConfig,
        ExecutionMetadata,
        ExecutionContext,
        ContainerStats,
        ClaudeCodeError,
        ContainerError,
        ExecutorError,
        GitError,
        WorkflowError
    )
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function for AgentFactory discovery
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a ClaudeCodeAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            ClaudeCodeAgent instance or PlaceholderAgent if disabled
        """
        if config is None:
            config = {}
        
        # Check if claude-code is enabled via feature flag
        from src.config import settings
        if not getattr(settings, 'AM_ENABLE_CLAUDE_CODE', False):
            logger.info("Claude-Code agent is disabled via AM_ENABLE_CLAUDE_CODE setting")
            return PlaceholderAgent({
                "name": "claude-code_disabled", 
                "error": "Claude-Code agent disabled via feature flag"
            })
        
        return ClaudeCodeAgent(config)

except Exception as e:
    logger.error(f"Failed to initialize ClaudeCodeAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent({"name": "claude-code_error", "error": str(e)})

__all__ = [
    'create_agent',
    'ClaudeCodeAgent',
    'ContainerManager',
    'ClaudeExecutor',
    'ClaudeCodeRunRequest',
    'ClaudeCodeRunResponse',
    'ClaudeCodeStatusResponse', 
    'WorkflowInfo',
    'ContainerInfo',
    'ExecutionResult',
    'ClaudeCodeConfig',
    'ContainerStatus',
    'ExecutionStatus',
    'WorkflowType',
    'ContainerConfig',
    'GitConfig',
    'WorkflowConfig',
    'ExecutionMetadata',
    'ExecutionContext',
    'ContainerStats',
    'ClaudeCodeError',
    'ContainerError',
    'ExecutorError',
    'GitError',
    'WorkflowError'
]