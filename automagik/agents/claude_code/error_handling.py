"""Error handling utilities for Claude Code agent.

This module provides standardized error handling patterns and exceptions
to improve code quality and consistency across the codebase.
"""

import logging
import traceback
from typing import Optional, Any, Dict, Union, Type
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeCodeError(Exception):
    """Base exception for Claude Code agent errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class ValidationError(ClaudeCodeError):
    """Exception raised when validation fails."""
    pass


class ConfigurationError(ClaudeCodeError):
    """Exception raised when configuration is invalid."""
    pass


class ExecutionError(ClaudeCodeError):
    """Exception raised during workflow execution."""
    
    def __init__(self, message: str, exit_code: Optional[int] = None, 
                 command: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.exit_code = exit_code
        self.command = command
        super().__init__(message, details)


class ResourceError(ClaudeCodeError):
    """Exception raised when resource operations fail."""
    pass


def handle_exception(exc: Exception, operation: str, 
                    context: Optional[Dict[str, Any]] = None,
                    reraise: bool = False) -> Optional[Dict[str, Any]]:
    """Standardized exception handling with logging.
    
    Args:
        exc: Exception that occurred
        operation: Description of the operation that failed
        context: Additional context information
        reraise: Whether to re-raise the exception after logging
        
    Returns:
        Error details dictionary if not re-raising
        
    Raises:
        Exception: If reraise is True
    """
    context = context or {}
    error_details = {
        "operation": operation,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "context": context
    }
    
    # Log the error with appropriate level
    if isinstance(exc, (ValidationError, ConfigurationError)):
        logger.warning(f"Validation/Config error in {operation}: {exc}")
    elif isinstance(exc, ExecutionError):
        logger.error(f"Execution error in {operation}: {exc}")
    elif isinstance(exc, ResourceError):
        logger.error(f"Resource error in {operation}: {exc}")
    else:
        logger.error(f"Unexpected error in {operation}: {exc}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
    
    if reraise:
        raise exc
    
    return error_details


@contextmanager
def safe_operation(operation_name: str, context: Optional[Dict[str, Any]] = None, 
                  reraise: bool = False):
    """Context manager for safe operation execution with standardized error handling.
    
    Args:
        operation_name: Name of the operation being performed
        context: Additional context for error reporting
        reraise: Whether to re-raise exceptions
        
    Yields:
        None
        
    Example:
        with safe_operation("file_processing", {"file": "test.txt"}):
            # perform risky operations
            process_file("test.txt")
    """
    try:
        yield
    except Exception as exc:
        handle_exception(exc, operation_name, context, reraise)


def validate_path(path: Union[str, Path], must_exist: bool = False, 
                 must_be_file: bool = False, must_be_dir: bool = False) -> Path:
    """Validate and normalize a file system path.
    
    Args:
        path: Path to validate
        must_exist: If True, path must exist
        must_be_file: If True, path must be a file
        must_be_dir: If True, path must be a directory
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        path_obj = Path(path)
        
        if must_exist and not path_obj.exists():
            raise ValidationError(f"Path does not exist: {path}")
        
        if must_be_file and path_obj.exists() and not path_obj.is_file():
            raise ValidationError(f"Path is not a file: {path}")
        
        if must_be_dir and path_obj.exists() and not path_obj.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")
        
        return path_obj
        
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {path}") from e


def validate_config(config: Dict[str, Any], required_keys: list, 
                   optional_keys: Optional[list] = None) -> None:
    """Validate configuration dictionary.
    
    Args:
        config: Configuration to validate
        required_keys: Keys that must be present
        optional_keys: Keys that are allowed but not required
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(config, dict):
        raise ValidationError(f"Configuration must be a dictionary, got {type(config).__name__}")
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValidationError(f"Missing required configuration keys: {missing_keys}")
    
    if optional_keys is not None:
        allowed_keys = set(required_keys + optional_keys)
        unexpected_keys = [key for key in config.keys() if key not in allowed_keys]
        if unexpected_keys:
            logger.warning(f"Unexpected configuration keys (will be ignored): {unexpected_keys}")


def log_performance_metrics(operation: str, duration_ms: float, 
                          metrics: Optional[Dict[str, Any]] = None) -> None:
    """Log performance metrics in a standardized format.
    
    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        metrics: Additional metrics to log
    """
    metrics = metrics or {}
    metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
    
    if duration_ms > 5000:  # > 5 seconds
        logger.warning(f"Slow operation '{operation}': {duration_ms:.1f}ms, {metrics_str}")
    elif duration_ms > 1000:  # > 1 second
        logger.info(f"Operation '{operation}': {duration_ms:.1f}ms, {metrics_str}")
    else:
        logger.debug(f"Operation '{operation}': {duration_ms:.1f}ms, {metrics_str}")


def ensure_cleanup(resource: Any, cleanup_method: str = "close") -> None:
    """Ensure proper cleanup of resources.
    
    Args:
        resource: Resource to clean up
        cleanup_method: Method name to call for cleanup
    """
    if resource is None:
        return
    
    try:
        if hasattr(resource, cleanup_method):
            cleanup_func = getattr(resource, cleanup_method)
            if callable(cleanup_func):
                cleanup_func()
                logger.debug(f"Successfully cleaned up resource: {type(resource).__name__}")
        else:
            logger.warning(f"Resource {type(resource).__name__} has no {cleanup_method} method")
    except Exception as e:
        logger.error(f"Failed to cleanup resource {type(resource).__name__}: {e}")