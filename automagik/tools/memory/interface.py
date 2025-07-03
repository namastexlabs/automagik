"""Memory tool interface helpers.

This module provides helper functions and decorators for memory tools.
"""
from typing import Any, Callable
import logging
import re
from functools import wraps

logger = logging.getLogger(__name__)

def invalidate_memory_cache(func: Callable) -> Callable:
    """Decorator that invalidates the memory cache after the function is called.
    
    This ensures that any memory updates are immediately reflected in
    subsequent system prompt generation.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Call the original function
        result = await func(*args, **kwargs)
        
        # Get the memory provider
        from automagik.tools.memory.provider import get_memory_provider_for_agent
        
        # Try to extract agent_id from args/kwargs
        agent_id = None
        
        # Check if first argument might be a context with dependencies
        if args and hasattr(args[0], 'deps'):
            deps = args[0].deps
            if hasattr(deps, '_agent_id_numeric'):
                agent_id = deps._agent_id_numeric
                logger.debug(f"Extracted agent_id={agent_id} from args[0].deps._agent_id_numeric")
        
        # Check for context object with dict-like access
        if args and agent_id is None and hasattr(args[0], 'get') and callable(getattr(args[0], 'get')):
            try:
                if args[0].get('agent_id'):
                    agent_id = args[0].get('agent_id')
                    logger.debug(f"Extracted agent_id={agent_id} from args[0].get('agent_id')")
            except Exception as e:
                logger.debug(f"Error accessing context dict: {str(e)}")
        
        # Check if first argument is a dict
        if args and agent_id is None and isinstance(args[0], dict) and 'agent_id' in args[0]:
            agent_id = args[0]['agent_id']
            logger.debug(f"Extracted agent_id={agent_id} from args[0]['agent_id'] direct access")
        
        # Check if context.deps is a dict-like object
        if args and agent_id is None and hasattr(args[0], 'deps') and hasattr(args[0].deps, 'get') and callable(getattr(args[0].deps, 'get')):
            try:
                if args[0].deps.get('agent_id'):
                    agent_id = args[0].deps.get('agent_id')
                    logger.debug(f"Extracted agent_id={agent_id} from args[0].deps.get('agent_id')")
            except Exception as e:
                logger.debug(f"Error accessing deps dict: {str(e)}")
        
        # Check if agent_id is in kwargs
        if agent_id is None and 'agent_id' in kwargs:
            agent_id = kwargs['agent_id']
            logger.debug(f"Extracted agent_id={agent_id} from kwargs['agent_id']")
        
        # Try to extract from the result of the function
        if agent_id is None and isinstance(result, dict) and 'agent_id' in result:
            agent_id = result['agent_id']
            logger.debug(f"Extracted agent_id={agent_id} from result['agent_id']")
        
        # Try to extract the user_id from the context and look up the agent_id
        if agent_id is None and args:
            user_id = None
            
            # Check if context has user_id
            if hasattr(args[0], 'deps') and hasattr(args[0].deps, '_user_id'):
                user_id = args[0].deps._user_id
                logger.debug(f"Found user_id={user_id} from args[0].deps._user_id")
            
            # Try context as dict-like
            if user_id is None and hasattr(args[0], 'get') and callable(getattr(args[0], 'get')):
                try:
                    if args[0].get('user_id'):
                        user_id = args[0].get('user_id')
                        logger.debug(f"Found user_id={user_id} from args[0].get('user_id')")
                except Exception:
                    pass
            
            # Try kwargs
            if user_id is None and 'user_id' in kwargs:
                user_id = kwargs['user_id']
                logger.debug(f"Found user_id={user_id} from kwargs")
            
            # If we found user_id, try to find the current agent for this user
            if user_id:
                try:
                    # Import here to avoid circular imports
                    from automagik.context import get_current_agent_id
                    current_agent_id = get_current_agent_id(user_id)
                    if current_agent_id:
                        agent_id = current_agent_id
                        logger.debug(f"Found agent_id={agent_id} from current agent for user_id={user_id}")
                except Exception as e:
                    logger.debug(f"Error getting current agent ID: {str(e)}")
        
        # If we found an agent_id, invalidate its cache
        if agent_id:
            provider = get_memory_provider_for_agent(agent_id)
            if provider:
                provider.invalidate_cache()
                logger.info(f"Invalidated memory cache for agent {agent_id}")
            else:
                logger.warning(f"No memory provider found for agent {agent_id}")
        else:
            logger.warning(f"Could not determine agent_id for cache invalidation in {func.__name__}")
        
        return result
    
    return wrapper


def validate_memory_name(name: str) -> bool:
    """Validate that a memory name contains only allowed characters.
    
    Args:
        name: Memory name to validate
        
    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))

def format_memory_content(content: Any) -> str:
    """Format memory content for storage.
    
    Args:
        content: Memory content to format
        
    Returns:
        Formatted string representation
    """
    if isinstance(content, str):
        return content
    
    # For other types, convert to string representation
    try:
        import json
        return json.dumps(content)
    except Exception:
        return str(content) 