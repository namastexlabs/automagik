"""Tool Wrapper Factory for PydanticAI agents.

This module provides utilities to eliminate duplication in tool wrapper creation
across PydanticAI agents, reducing boilerplate code significantly.
"""
import logging
from typing import Any, Dict, Callable, Optional, List
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


class ToolWrapperFactory:
    """Factory for creating standardized tool wrappers for PydanticAI agents."""
    
    @staticmethod
    def create_context_wrapper(
        func: Callable,
        context: Dict[str, Any],
        preserve_signature: bool = True
    ) -> Callable:
        """Create a context-aware tool wrapper.
        
        Args:
            func: The function to wrap
            context: The agent context to inject
            preserve_signature: Whether to preserve the original function signature
            
        Returns:
            Wrapped function that injects context as first argument
        """
        if preserve_signature:
            # Preserve original signature but inject context
            sig = inspect.signature(func)
            
            @wraps(func)
            async def wrapper(ctx, *args, **kwargs):
                # Inject context as first argument after ctx
                return await func(context, *args, **kwargs)
                
            # Update wrapper signature to match original (minus context param)
            wrapper.__signature__ = sig
        else:
            # Simple wrapper without signature preservation
            async def wrapper(ctx, *args, **kwargs):
                return await func(context, *args, **kwargs)
            
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
        
        return wrapper
    
    @staticmethod
    def create_agent_tool_wrapper(
        agent_func: Callable,
        agent_context: Dict[str, Any],
        input_param: str = "input_text"
    ) -> Callable:
        """Create a wrapper for sub-agent calls.
        
        Args:
            agent_func: The agent function to wrap
            agent_context: The parent agent context
            input_param: Name of the input parameter
            
        Returns:
            Wrapped agent function
        """
        async def wrapper(ctx, **kwargs):
            # Ensure evolution_payload is available in context
            if hasattr(ctx, 'deps') and ctx.deps:
                ctx.deps.set_context(agent_context)
            
            # Extract the input text from kwargs
            input_text = kwargs.get(input_param, "")
            return await agent_func(ctx, input_text)
        
        wrapper.__name__ = agent_func.__name__
        wrapper.__doc__ = agent_func.__doc__
        return wrapper
    
    @staticmethod
    def create_batch_wrappers(
        functions: List[Callable],
        context: Dict[str, Any]
    ) -> Dict[str, Callable]:
        """Create multiple tool wrappers at once.
        
        Args:
            functions: List of functions to wrap
            context: The agent context to inject
            
        Returns:
            Dictionary mapping function names to wrapped functions
        """
        wrappers = {}
        for func in functions:
            wrapper = ToolWrapperFactory.create_context_wrapper(func, context)
            wrappers[func.__name__] = wrapper
        return wrappers
    
    @staticmethod
    def create_api_tool_wrapper(
        api_func: Callable,
        context: Dict[str, Any],
        response_formatter: Optional[Callable] = None
    ) -> Callable:
        """Create a wrapper for API integration tools.
        
        Args:
            api_func: The API function to wrap
            context: The agent context
            response_formatter: Optional function to format the response
            
        Returns:
            Wrapped API function with error handling
        """
        async def wrapper(ctx, **kwargs):
            try:
                result = await api_func(context, **kwargs)
                
                if response_formatter:
                    return response_formatter(result)
                return result
                
            except Exception as e:
                logger.error(f"Error in API tool {api_func.__name__}: {str(e)}")
                return {
                    "error": True,
                    "message": f"Failed to execute {api_func.__name__}: {str(e)}"
                }
        
        wrapper.__name__ = api_func.__name__
        wrapper.__doc__ = api_func.__doc__
        return wrapper
    
    @staticmethod
    def register_tools_from_module(
        tool_registry,
        module,
        context: Dict[str, Any],
        function_filter: Optional[Callable[[str], bool]] = None
    ) -> List[str]:
        """Auto-register all functions from a module as tools.
        
        Args:
            tool_registry: The agent's tool registry
            module: Module containing tool functions
            context: Agent context to inject
            function_filter: Optional filter for function names
            
        Returns:
            List of registered tool names
        """
        registered_tools = []
        
        for name in dir(module):
            if function_filter and not function_filter(name):
                continue
                
            attr = getattr(module, name)
            if callable(attr) and not name.startswith('_'):
                # Create wrapper for the function
                wrapper = ToolWrapperFactory.create_context_wrapper(attr, context)
                tool_registry.register_tool(wrapper)
                registered_tools.append(name)
                logger.debug(f"Auto-registered tool: {name}")
        
        return registered_tools


class ToolRegistrationHelper:
    """Helper class for common tool registration patterns."""
    
    @staticmethod
    def register_evolution_tools(tool_registry, context: Dict[str, Any]) -> None:
        """Register standard Evolution/WhatsApp tools."""
        tool_registry.register_evolution_tools(context)
    
    @staticmethod
    def register_blackpearl_tools(
        tool_registry,
        context: Dict[str, Any],
        tools: Optional[List[str]] = None
    ) -> None:
        """Register BlackPearl integration tools.
        
        Args:
            tool_registry: The agent's tool registry
            context: Agent context
            tools: Optional list of specific tools to register (default: all)
        """
        from automagik.tools.blackpearl import verificar_cnpj
        
        # Standard BlackPearl tools
        blackpearl_tools = {
            'verificar_cnpj': verificar_cnpj
        }
        
        tools_to_register = tools or blackpearl_tools.keys()
        
        for tool_name in tools_to_register:
            if tool_name in blackpearl_tools:
                wrapper = ToolWrapperFactory.create_context_wrapper(
                    blackpearl_tools[tool_name], 
                    context
                )
                tool_registry.register_tool(wrapper)
                logger.debug(f"Registered BlackPearl tool: {tool_name}")
    
    @staticmethod
    def register_specialized_agents(
        tool_registry,
        context: Dict[str, Any],
        agents: Dict[str, Callable]
    ) -> None:
        """Register specialized sub-agents as tools.
        
        Args:
            tool_registry: The agent's tool registry
            context: Agent context
            agents: Dictionary mapping agent names to agent functions
        """
        for agent_name, agent_func in agents.items():
            wrapper = ToolWrapperFactory.create_agent_tool_wrapper(
                agent_func, 
                context
            )
            tool_registry.register_tool(wrapper)
            logger.debug(f"Registered specialized agent: {agent_name}")