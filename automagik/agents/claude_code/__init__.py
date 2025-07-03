"""Claude-Code Agent Module.

This module provides local Claude CLI execution capabilities
for long-running, autonomous AI workflows.
"""

from typing import Dict, Optional, Any
import logging

# Setup logging first
logger = logging.getLogger(__name__)

try:
    # Lazy import functions for better startup performance
    def _get_claude_code_agent():
        from .agent import ClaudeCodeAgent
        return ClaudeCodeAgent
    
    def _get_log_manager():
        from .log_manager import LogManager, get_log_manager
        return LogManager, get_log_manager
    
    def _get_models():
        from .models import (
            ClaudeCodeRunRequest,
            ClaudeCodeRunResponse, 
            ClaudeCodeStatusResponse,
            WorkflowInfo,
            ExecutionResult,
            ClaudeCodeConfig,
            ExecutionStatus,
            WorkflowType,
            GitConfig,
            WorkflowConfig,
            ExecutionMetadata,
            ExecutionContext,
            ClaudeCodeError,
            ExecutorError,
            GitError,
            WorkflowError
        )
        return {
            'ClaudeCodeRunRequest': ClaudeCodeRunRequest,
            'ClaudeCodeRunResponse': ClaudeCodeRunResponse,
            'ClaudeCodeStatusResponse': ClaudeCodeStatusResponse,
            'WorkflowInfo': WorkflowInfo,
            'ExecutionResult': ExecutionResult,
            'ClaudeCodeConfig': ClaudeCodeConfig,
            'ExecutionStatus': ExecutionStatus,
            'WorkflowType': WorkflowType,
            'GitConfig': GitConfig,
            'WorkflowConfig': WorkflowConfig,
            'ExecutionMetadata': ExecutionMetadata,
            'ExecutionContext': ExecutionContext,
            'ClaudeCodeError': ClaudeCodeError,
            'ExecutorError': ExecutorError,
            'GitError': GitError,
            'WorkflowError': WorkflowError
        }
    
    # Import essential components immediately
    ClaudeCodeAgent = _get_claude_code_agent()
    LogManager, get_log_manager = _get_log_manager()
    
    # Import SDK executor (optional - may fail if claude_code_sdk not installed)
    try:
        from .sdk_executor import ClaudeSDKExecutor
    except ImportError as e:
        logger.warning(f"ClaudeSDKExecutor not available: {e}")
        ClaudeSDKExecutor = None
    
    # Load models lazily on first access
    _models_cache = None
    def _load_models():
        global _models_cache
        if _models_cache is None:
            _models_cache = _get_models()
        return _models_cache
    
    # Make models available through module-level attributes
    def __getattr__(name):
        if name == 'ClaudeCLIExecutor':
            raise ImportError(
                "ClaudeCLIExecutor has been removed. "
                "Use ClaudeSDKExecutor instead."
            )
        if name in ['ClaudeCodeRunRequest', 'ClaudeCodeRunResponse', 'ClaudeCodeStatusResponse',
                   'WorkflowInfo', 'ExecutionResult', 'ClaudeCodeConfig', 'ExecutionStatus',
                   'WorkflowType', 'GitConfig', 'WorkflowConfig', 'ExecutionMetadata',
                   'ExecutionContext', 'ClaudeCodeError', 'ExecutorError', 'GitError', 'WorkflowError']:
            models = _load_models()
            return models[name]
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    
    from automagik.agents.models.placeholder import PlaceholderAgent
    
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
    import traceback
    logger.error(f"Failed to initialize ClaudeCodeAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Store the error message for use in the placeholder function
    initialization_error = str(e)
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        from automagik.agents.models.placeholder import PlaceholderAgent
        error_config = {"name": "claude-code_error", "error": initialization_error}
        if config:
            error_config.update(config)
        return PlaceholderAgent(error_config)

__all__ = [
    'create_agent',
    'ClaudeCodeAgent',
    'ClaudeSDKExecutor',
    'LogManager',
    'get_log_manager',
    'ClaudeCodeRunRequest',
    'ClaudeCodeRunResponse',
    'ClaudeCodeStatusResponse', 
    'WorkflowInfo',
    'ExecutionResult',
    'ClaudeCodeConfig',
    'ExecutionStatus',
    'WorkflowType',
    'GitConfig',
    'WorkflowConfig',
    'ExecutionMetadata',
    'ExecutionContext',
    'ClaudeCodeError',
    'ExecutorError',
    'GitError',
    'WorkflowError'
]