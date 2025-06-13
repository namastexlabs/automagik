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
    from .docker_executor import DockerExecutor
    from .log_manager import LogManager, get_log_manager
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
        
        # Check if claude CLI is available by looking for credentials
        from pathlib import Path
        claude_credentials = Path.home() / ".claude" / ".credentials.json"
        
        if not claude_credentials.exists():
            logger.info(f"Claude-Code agent disabled: credentials not found at {claude_credentials}")
            return PlaceholderAgent({
                "name": "claude-code_disabled", 
                "error": f"Claude CLI not configured (no credentials at {claude_credentials})"
            })
        
        return ClaudeCodeAgent(config)

except Exception as e:
    logger.error(f"Failed to initialize ClaudeCodeAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Store the error message for use in the placeholder function
    initialization_error = str(e)
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        from src.agents.models.placeholder import PlaceholderAgent
        error_config = {"name": "claude-code_error", "error": initialization_error}
        if config:
            error_config.update(config)
        return PlaceholderAgent(error_config)

__all__ = [
    'create_agent',
    'ClaudeCodeAgent',
    'ContainerManager',
    'DockerExecutor',
    'LogManager',
    'get_log_manager',
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