"""Session management utilities for agents.

This module provides functions for managing agent sessions, user IDs,
agent IDs, and context information.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

def create_session_id() -> str:
    """Create a new session ID.
    
    Returns:
        Unique session ID string
    """
    return f"session-{uuid.uuid4()}"

def create_run_id() -> str:
    """Create a new run ID.
    
    Returns:
        Unique run ID string
    """
    return f"run-{uuid.uuid4()}"

def create_context(agent_id: Optional[Union[int, str]] = None, 
                  user_id: Optional[Union[uuid.UUID, str]] = None,
                  session_id: Optional[str] = None,
                  additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a context dictionary for an agent run.
    
    Args:
        agent_id: Optional agent ID
        user_id: Optional user ID (UUID or string)
        session_id: Optional session ID
        additional_context: Optional dictionary with additional context
        
    Returns:
        Context dictionary
    """
    context = {}
    
    if agent_id is not None:
        context["agent_id"] = agent_id
    
    if user_id is not None:
        context["user_id"] = user_id
    
    if session_id is not None:
        context["session_id"] = session_id
    else:
        context["session_id"] = create_session_id()
    
    context["run_id"] = create_run_id()
    
    if additional_context:
        context.update(additional_context)
    
    return context

def extract_ids_from_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract IDs from context dictionary.
    
    Args:
        context: Context dictionary
        
    Returns:
        Dictionary with extracted IDs
    """
    result = {}
    
    if "agent_id" in context:
        result["agent_id"] = context["agent_id"]
    
    if "user_id" in context:
        result["user_id"] = context["user_id"]
    
    if "session_id" in context:
        result["session_id"] = context["session_id"]
    
    if "run_id" in context:
        result["run_id"] = context["run_id"]
    
    return result

def validate_agent_id(agent_id: Optional[Union[int, str]]) -> Optional[Union[int, str]]:
    """Validate and normalize an agent ID.
    
    Args:
        agent_id: Agent ID to validate
        
    Returns:
        Normalized agent ID or None if invalid
    """
    if agent_id is None:
        return None
    
    if isinstance(agent_id, (int, str)):
        # Convert string to int if it's numeric
        if isinstance(agent_id, str) and agent_id.isdigit():
            return int(agent_id)
        return agent_id
    
    logger.warning(f"Invalid agent_id type: {type(agent_id)}")
    return None

def validate_user_id(user_id: Optional[Union[uuid.UUID, str]]) -> Optional[uuid.UUID]:
    """Validate and normalize a user ID.
    
    Args:
        user_id: User ID to validate (UUID or string)
        
    Returns:
        Normalized user ID (UUID) or None if invalid
    """
    if user_id is None:
        return None
    
    # Accept raw ints
    if isinstance(user_id, int):
        return user_id  # type: ignore[return-value]

    # Accept UUID object directly
    if isinstance(user_id, uuid.UUID):
        return user_id

    # Accept numeric strings and cast to int
    if isinstance(user_id, str) and user_id.isdigit():
        return int(user_id)  # type: ignore[return-value]

    # Finally, attempt to parse UUID strings
    try:
        return uuid.UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Invalid user_id format: {user_id}")
        return None

def extract_multimodal_content(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract multimodal content from context.
    
    Args:
        context: Context dictionary
        
    Returns:
        Multimodal content dictionary or None
    """
    if context and "multimodal_content" in context:
        return context["multimodal_content"]
    return None 