"""Context management for agent execution.

This module provides thread-local and global context management for
agent execution, including user identification and agent state tracking.
"""
import threading
import logging
from typing import Optional, Dict, Any, Union
from uuid import UUID
from contextvars import ContextVar
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Context variables for async-safe storage
_current_user_id: ContextVar[Optional[Union[str, UUID]]] = ContextVar('current_user_id', default=None)
_current_agent_id: ContextVar[Optional[Union[str, int]]] = ContextVar('current_agent_id', default=None)
_current_session_id: ContextVar[Optional[Union[str, UUID]]] = ContextVar('current_session_id', default=None)


@dataclass
class ThreadContext:
    """Thread-local context for agent execution."""
    user_id: Optional[Union[str, UUID]] = None
    agent_id: Optional[Union[str, int]] = None
    session_id: Optional[Union[str, UUID]] = None
    additional_data: Optional[Dict[str, Any]] = None


def set_current_user_id(user_id: Optional[Union[str, UUID]]) -> None:
    """Set the current user ID in context.
    
    Args:
        user_id: User ID to set
    """
    _current_user_id.set(user_id)
    logger.debug(f"Set current user_id: {user_id}")


def get_current_user_id() -> Optional[Union[str, UUID]]:
    """Get the current user ID from context.
    
    Returns:
        Current user ID or None if not set
    """
    user_id = _current_user_id.get()
    logger.debug(f"Retrieved current user_id: {user_id}")
    return user_id


def set_current_agent_id(agent_id: Optional[Union[str, int]]) -> None:
    """Set the current agent ID in context.
    
    Args:
        agent_id: Agent ID to set
    """
    _current_agent_id.set(agent_id)
    logger.debug(f"Set current agent_id: {agent_id}")


def get_current_agent_id(user_id: Optional[Union[str, UUID]] = None) -> Optional[Union[str, int]]:
    """Get the current agent ID from context.
    
    Args:
        user_id: Optional user ID (for compatibility, not used in current implementation)
        
    Returns:
        Current agent ID or None if not set
    """
    agent_id = _current_agent_id.get()
    logger.debug(f"Retrieved current agent_id: {agent_id}")
    return agent_id


def set_current_session_id(session_id: Optional[Union[str, UUID]]) -> None:
    """Set the current session ID in context.
    
    Args:
        session_id: Session ID to set
    """
    _current_session_id.set(session_id)
    logger.debug(f"Set current session_id: {session_id}")


def get_current_session_id() -> Optional[Union[str, UUID]]:
    """Get the current session ID from context.
    
    Returns:
        Current session ID or None if not set
    """
    session_id = _current_session_id.get()
    logger.debug(f"Retrieved current session_id: {session_id}")
    return session_id


def set_thread_context(context: ThreadContext) -> None:
    """Set thread-local context (for backward compatibility).
    
    Args:
        context: ThreadContext object to set
    """
    current_thread = threading.current_thread()
    current_thread._context = context
    
    # Also set in context vars for consistency
    if context.user_id:
        set_current_user_id(context.user_id)
    if context.agent_id:
        set_current_agent_id(context.agent_id)
    if context.session_id:
        set_current_session_id(context.session_id)
    
    logger.debug(f"Set thread context: {context}")


def get_thread_context() -> Optional[ThreadContext]:
    """Get thread-local context (for backward compatibility).
    
    Returns:
        ThreadContext object or None if not set
    """
    current_thread = threading.current_thread()
    context = getattr(current_thread, '_context', None)
    logger.debug(f"Retrieved thread context: {context}")
    return context


def clear_context() -> None:
    """Clear all context variables."""
    _current_user_id.set(None)
    _current_agent_id.set(None)
    _current_session_id.set(None)
    
    # Also clear thread-local context
    current_thread = threading.current_thread()
    if hasattr(current_thread, '_context'):
        delattr(current_thread, '_context')
    
    logger.debug("Cleared all context variables")


def create_execution_context(
    user_id: Optional[Union[str, UUID]] = None,
    agent_id: Optional[Union[str, int]] = None,
    session_id: Optional[Union[str, UUID]] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> ThreadContext:
    """Create and set execution context for agent operations.
    
    Args:
        user_id: User ID for the execution
        agent_id: Agent ID for the execution
        session_id: Session ID for the execution
        additional_data: Additional context data
        
    Returns:
        Created ThreadContext object
    """
    context = ThreadContext(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        additional_data=additional_data or {}
    )
    
    set_thread_context(context)
    logger.info(f"Created execution context: user_id={user_id}, agent_id={agent_id}, session_id={session_id}")
    
    return context


# Context manager for temporary context
class ExecutionContext:
    """Context manager for setting execution context temporarily."""
    
    def __init__(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        agent_id: Optional[Union[str, int]] = None,
        session_id: Optional[Union[str, UUID]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.agent_id = agent_id
        self.session_id = session_id
        self.additional_data = additional_data or {}
        
        # Store previous context to restore later
        self.previous_user_id = None
        self.previous_agent_id = None
        self.previous_session_id = None
        self.previous_thread_context = None
    
    def __enter__(self) -> ThreadContext:
        """Enter the context manager."""
        # Store previous context
        self.previous_user_id = get_current_user_id()
        self.previous_agent_id = get_current_agent_id()
        self.previous_session_id = get_current_session_id()
        self.previous_thread_context = get_thread_context()
        
        # Set new context
        context = create_execution_context(
            user_id=self.user_id,
            agent_id=self.agent_id,
            session_id=self.session_id,
            additional_data=self.additional_data
        )
        
        return context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and restore previous context."""
        # Restore previous context
        set_current_user_id(self.previous_user_id)
        set_current_agent_id(self.previous_agent_id)
        set_current_session_id(self.previous_session_id)
        
        if self.previous_thread_context:
            set_thread_context(self.previous_thread_context)
        else:
            current_thread = threading.current_thread()
            if hasattr(current_thread, '_context'):
                delattr(current_thread, '_context')
        
        logger.debug("Restored previous execution context")