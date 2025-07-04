"""Utilities for simplifying tool creation in external agents.

This module provides decorators and utilities to reduce boilerplate
when creating tools for external agents.
"""
import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from inspect import signature, Parameter

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Callable[..., Any])


def external_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    auto_context: bool = True
) -> Callable[[T], T]:
    """Decorator to simplify external tool creation.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)
        auto_context: Whether to automatically inject context parameter
        
    Example:
        @external_tool(description="Get user data from API")
        async def get_user_data(user_id: str) -> dict:
            # Tool implementation
            pass
    """
    def decorator(func: T) -> T:
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or "").strip().split('\n')[0]
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # If auto_context is enabled and context is not provided,
            # try to get it from the first positional argument
            if auto_context and 'context' not in kwargs:
                sig = signature(func)
                params = list(sig.parameters.keys())
                if params and params[0] == 'context' and len(args) > 0:
                    # Context is already in args
                    pass
                elif 'context' in params and 'context' not in kwargs:
                    # Add empty context if needed
                    kwargs['context'] = {}
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Tool '{tool_name}' executed successfully")
                return result
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {str(e)}")
                raise
        
        # Add metadata for tool registration
        wrapper.tool_name = tool_name
        wrapper.tool_description = tool_description
        wrapper.is_external_tool = True
        
        return cast(T, wrapper)
    
    return decorator


class ToolRegistry:
    """Enhanced tool registry for external agents."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
    
    def register(self, tool: Callable) -> None:
        """Register a tool, automatically detecting metadata."""
        if hasattr(tool, 'is_external_tool'):
            name = tool.tool_name
            self.tools[name] = tool
            logger.debug(f"Registered external tool: {name}")
        else:
            # Fallback to function name
            name = tool.__name__
            self.tools[name] = tool
            logger.debug(f"Registered tool: {name}")
    
    def register_all(self, tools: list) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> list:
        """List all registered tool names."""
        return list(self.tools.keys())


# Example of creating a simplified tool
@external_tool(description="Get user preferences from memory")
async def get_user_preferences(user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get user preferences from memory system.
    
    Args:
        user_id: User identifier
        context: Agent context
        
    Returns:
        User preferences dictionary
    """
    # Implementation would go here
    return {"theme": "dark", "language": "pt-BR"}