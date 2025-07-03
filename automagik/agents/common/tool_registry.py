"""Tool registry for agent implementations.

This module handles tool registration and management for all agent implementations.
"""
import logging
from typing import Dict, Any, Optional, Callable, List

from pydantic_ai.tools import Tool as PydanticTool

# Setup logging
logger = logging.getLogger(__name__)

# Import memory tools but delay actual import until needed to avoid circular imports
memory_tools_imported = False
get_memory_tool = None
store_memory_tool = None
read_memory = None
create_memory = None
update_memory = None
list_memories_tool = None

def _import_memory_tools():
    """Import memory tools to avoid circular imports."""
    global memory_tools_imported, get_memory_tool, store_memory_tool, read_memory, create_memory, update_memory, list_memories_tool
    if not memory_tools_imported:
        from automagik.tools.memory.tool import get_memory_tool as _get_memory_tool
        from automagik.tools.memory.tool import store_memory_tool as _store_memory_tool
        from automagik.tools.memory.tool import read_memory as _read_memory
        from automagik.tools.memory.tool import create_memory as _create_memory
        from automagik.tools.memory.tool import update_memory as _update_memory
        from automagik.tools.memory.tool import list_memories_tool as _list_memories_tool
        
        get_memory_tool = _get_memory_tool
        store_memory_tool = _store_memory_tool
        read_memory = _read_memory
        create_memory = _create_memory
        update_memory = _update_memory
        list_memories_tool = _list_memories_tool
        
        memory_tools_imported = True

class ToolRegistry:
    """Class for registering and managing tools for agent implementations."""
    
    def __init__(self):
        """Initialize the tool registry."""
        self._registered_tools: Dict[str, Callable] = {}
    
    def register_tool(self, tool_func: Callable) -> None:
        """Register a tool with the registry.
        
        Args:
            tool_func: The tool function to register
        """
        # Handle PydanticAI Tool objects properly
        if isinstance(tool_func, PydanticTool):
            name = tool_func.name
        else:
            name = getattr(tool_func, "__name__", str(tool_func))
        self._registered_tools[name] = tool_func
    
    def register_tool_with_context(self, tool_func: Callable, context: Dict[str, Any]) -> None:
        """Register a tool with the registry, automatically injecting context.
        
        This method is useful for tools that require a context parameter. It automatically
        creates a wrapper function that injects the provided context as the first parameter.
        
        Args:
            tool_func: The tool function to register
            context: Context to inject into the tool
        """
        # Handle PydanticAI Tool objects properly
        if isinstance(tool_func, PydanticTool):
            name = tool_func.name
        else:
            name = getattr(tool_func, "__name__", str(tool_func))
        
        # Special handling for verificar_cnpj which has caused issues
        if name == "verificar_cnpj":
            # Create a dedicated wrapper for verificar_cnpj with explicit signature
            async def verificar_cnpj_wrapper(cnpj: str) -> Dict[str, Any]:
                """Verify a CNPJ number in the Blackpearl API.
                
                This tool validates a CNPJ (Brazilian company registration number) and returns
                information about the company if the CNPJ is valid.
                
                Args:
                    cnpj: The CNPJ number to verify (format: xx.xxx.xxx/xxxx-xx or clean numbers)
                    
                Returns:
                    CNPJ verification result containing company information if valid
                """
                return await tool_func(context, cnpj)
            
            # Register the wrapper
            self._registered_tools[name] = verificar_cnpj_wrapper
            logger.info(f"Registered custom wrapper for {name}")
            return
        
        # For other tools, use the regular approach
        # Get the original function's signature
        import inspect
        sig = inspect.signature(tool_func)
        params = list(sig.parameters.values())
        
        # Check if the first parameter is likely for context
        if params and params[0].name in ['ctx', 'context']:
            # Create a generic wrapper that passes context
            async def wrapped_tool(*args, **kwargs):
                """Wrapped version of the original tool with context injection."""
                return await tool_func(context, *args, **kwargs)
                
            # Copy over metadata
            wrapped_tool.__name__ = name
            wrapped_tool.__doc__ = tool_func.__doc__
            
            # Register the wrapped version
            self._registered_tools[name] = wrapped_tool
            logger.info(f"Registered tool with context injection: {name}")
        else:
            # Register the original if it doesn't need context
            self._registered_tools[name] = tool_func
            logger.info(f"Registered tool without context injection: {name}")
    
    def register_agent_as_tool(self, agent, context: Dict[str, Any]) -> None:
        """A simpler method specifically for registering agents as tools with context.
        
        This is a convenience method that handles the common case of registering 
        specialized agents as tools, ensuring they have the proper context.
        
        Args:
            agent: The agent to register as a tool
            context: Context to inject into the agent's tool functions
        """
        # Handle PydanticAI Tool objects properly
        if isinstance(agent, PydanticTool):
            agent_name = agent.name
        else:
            agent_name = getattr(agent, "__name__", str(agent))
        
        # Register the agent with context
        self.register_tool_with_context(agent, context)
        logger.info(f"Registered agent {agent_name} as tool with context")
    
    def register_default_tools(self, context: Dict[str, Any]) -> None:
        """Register the default set of tools for the agent.
        
        Args:
            context: Context dictionary for tool execution
        """
        # Import date/time tools (use raw functions, not Tool instances)
        from automagik.tools.datetime.tool import get_current_date, get_current_time, format_date
        
        # Register date/time tools
        self.register_tool(get_current_date)
        self.register_tool(get_current_time)
        self.register_tool(format_date)
        
        # Import and register memory tools
        _import_memory_tools()
        
        if context:
            # Import RunContext for proper PydanticAI annotations
            from pydantic_ai import RunContext
            
            # Create and register wrapper for store_memory_tool that includes the context
            async def store_memory_wrapper(ctx: RunContext[Dict], key: str, content: str) -> str:
                """Store a memory with the given key.
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    key: The key to store the memory under
                    content: The memory content to store
                    
                Returns:
                    Confirmation message
                """
                return await store_memory_tool(context, key, content)
            
            # Create and register wrapper for get_memory_tool that includes the context
            async def get_memory_wrapper(ctx: RunContext[Dict], key: str) -> Any:
                """Retrieve a memory with the given key.
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    key: The key to retrieve the memory with
                    
                Returns:
                    The memory content if found, else an error message
                """
                return await get_memory_tool(context, key)
            
            # Create and register wrapper for list_memories_tool
            async def list_memories_wrapper(ctx: RunContext[Dict], prefix: Optional[str] = None) -> str:
                """List all available memories, optionally filtered by prefix.
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    prefix: Optional prefix to filter memory keys
                    
                Returns:
                    List of memory keys as a string
                """
                # Extract the agent_id from the context to filter memories by agent
                agent_id = context.get("agent_id") if context else None
                user_id = context.get("user_id") if context else None
                
                try:
                    logger.info(f"Listing memories with agent_id={agent_id}, user_id={user_id}, prefix={prefix}")
                    
                    # Use the imported list_memories_tool directly
                    return await list_memories_tool(prefix)
                except Exception as e:
                    error_msg = f"Error listing memories: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            
            # Register the wrappers instead of the originals
            self.register_tool(store_memory_wrapper)
            self.register_tool(get_memory_wrapper)
            self.register_tool(list_memories_wrapper)
        else:
            # If no context provided, register the original tools
            self.register_tool(store_memory_tool)
            self.register_tool(get_memory_tool)
            self.register_tool(list_memories_tool)
            
        logger.debug("Default tools registered")
    
    def register_evolution_tools(self, context: Dict[str, Any]) -> None:
        """Register Evolution WhatsApp tools.
        
        Args:
            context: Agent context containing necessary information
        """
        try:
            # Import Evolution tools
            from automagik.tools.evolution.tool import send_reaction as _send_reaction, send_message as _send_message
            from pydantic_ai import RunContext
            
            # Create context-aware wrappers
            async def send_reaction(ctx: RunContext[Dict], remote_jid: str, message_id: str, emoji: str = "👍") -> Dict[str, Any]:
                """Send a reaction emoji to a specific message.
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    remote_jid: The remote JID (WhatsApp chat ID)
                    message_id: The ID of the message to react to
                    emoji: The emoji to send as reaction
                    
                Returns:
                    Dictionary with success status and result/error info
                """
                try:
                    result = await _send_reaction(ctx, remote_jid, message_id, emoji)
                    return result if isinstance(result, dict) else {"success": True, "message": "Reaction sent successfully"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            async def send_text_message(ctx: RunContext[Dict], phone: str, message: str) -> Dict[str, Any]:
                """Send a text message via Evolution API.
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    phone: Phone number to send message to
                    message: Message content
                    
                Returns:
                    Dictionary with success status and result/error info
                """
                try:
                    result = await _send_message(ctx, phone, message)
                    return result if isinstance(result, dict) else {"success": True, "message": "Message sent successfully"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Register the wrappers
            self.register_tool(send_reaction)
            self.register_tool(send_text_message)
            
            # Also register with alias that tests expect  
            async def send_text_to_user(ctx: RunContext[Dict], phone: str, message: str) -> Dict[str, Any]:
                """Send a text message to user via Evolution API (alias for send_text_message).
                
                Args:
                    ctx: PydanticAI run context (required for PydanticAI tools)
                    phone: Phone number to send message to
                    message: Message content
                    
                Returns:
                    Dictionary with success status and result/error info
                """
                return await send_text_message(ctx, phone, message)
            
            self.register_tool(send_text_to_user)
            
            logger.debug("Evolution tools registered")
            
        except ImportError as e:
            logger.warning(f"Could not import Evolution tools: {e}")
        except Exception as e:
            logger.error(f"Error registering Evolution tools: {e}")
    
    async def register_mcp_tools(self, agent_name: str) -> None:
        """Register MCP tools for a specific agent.
        
        Simple approach: Try to get MCP client manager, if it's not ready yet, just skip.
        This handles the timing issue without complex dependency injection.
        
        Args:
            agent_name: Name of the agent to register MCP tools for
        """
        try:
            # Try to get MCP client manager - if it's not ready, this will fail gracefully
            from automagik.mcp.client import get_mcp_manager
            mcp_client_manager = await get_mcp_manager()
            
            # Get MCP tools for this agent (returns List[PydanticTool])
            mcp_tools = mcp_client_manager.get_tools_for_agent(agent_name)
            
            # Register each MCP tool - they're already PydanticTool objects
            for tool in mcp_tools:
                if isinstance(tool, PydanticTool):
                    # Register the PydanticTool directly
                    tool_name = getattr(tool, 'name', f"mcp_tool_{len(self._registered_tools)}")
                    self._registered_tools[tool_name] = tool
                    logger.debug(f"Registered MCP PydanticTool: {tool_name}")
                else:
                    logger.warning(f"Unexpected MCP tool type: {type(tool)}")
            
            if mcp_tools:
                logger.info(f"Registered {len(mcp_tools)} MCP tools for agent {agent_name}")
            else:
                logger.debug(f"No MCP tools found for agent {agent_name}")
                
        except Exception as e:
            # MCP client manager not ready yet or other error - just skip MCP tools for now
            logger.debug(f"MCP tools not available for agent {agent_name}: {str(e)}")
            # Don't raise exception to avoid breaking agent initialization
    
    def get_registered_tools(self) -> Dict[str, Callable]:
        """Get all registered tools.
        
        Returns:
            Dictionary of registered tools
        """
        return self._registered_tools
        
    def convert_to_pydantic_tools(self) -> List[PydanticTool]:
        """Convert registered tools to PydanticAI tools.
        
        Returns:
            List of PydanticAI tools
        """
        tools = []
        for name, func in self._registered_tools.items():
            try:
                if isinstance(func, PydanticTool):
                    # If it's already a PydanticTool instance, use it directly
                    tools.append(func)
                    logger.debug(f"Added existing PydanticTool: {name}")
                elif hasattr(func, "get_pydantic_tool"):
                    # Use the PydanticAI tool definition if available
                    tool = func.get_pydantic_tool()
                    tools.append(tool)
                    logger.debug(f"Converted to PydanticAI tool: {name}")
                elif hasattr(func, "__doc__") and callable(func):
                    # Create a basic wrapper for regular functions
                    doc = func.__doc__ or f"Tool for {name}"
                    # Create a simple PydanticTool
                    tool = PydanticTool(
                        name=name,
                        description=doc,
                        function=func,
                        max_retries=6
                    )
                    tools.append(tool)
                    logger.debug(f"Created PydanticTool for function: {name}")
                else:
                    logger.warning(f"Could not convert tool {name}: not a function or missing documentation")
            except Exception as e:
                logger.error(f"Error converting tool {name}: {str(e)}")
                
        logger.debug(msg=f"Converted {len(tools)} tools to PydanticAI tools")
        return tools

    def update_context(self, new_context: Dict[str, Any]) -> None:
        """Update the context used by tools.
        
        This method updates the context for tools that need it, particularly
        memory tools which require agent_id and user_id for proper operation.
        
        Args:
            new_context: Dictionary with context key-value pairs
        """
        if not new_context:
            logger.warning("Empty context provided to update_context")
            return
            
        # Re-register the memory tools with the updated context
        # This is needed because memory tools need the context for operation
        
        # First make sure memory tools are imported
        _import_memory_tools()
        
        # Re-register wrappers for memory tools with the updated context
        if store_memory_tool and get_memory_tool and list_memories_tool:
            # Import RunContext for proper type annotation
            from pydantic_ai import RunContext
            
            # Create wrapper for store_memory_tool with proper RunContext annotation
            async def store_memory_wrapper(ctx: RunContext[Dict], key: str, content: str) -> str:
                """Store a memory with the given key.
                
                Args:
                    ctx: The run context
                    key: The key to store the memory under
                    content: The memory content to store
                    
                Returns:
                    Confirmation message
                """
                return await store_memory_tool(new_context, key, content)
                
            # Create wrapper for get_memory_tool with proper RunContext annotation
            async def get_memory_wrapper(ctx: RunContext[Dict], key: str) -> Any:
                """Retrieve a memory with the given key.
                
                Args:
                    ctx: The run context
                    key: The key to retrieve the memory with
                    
                Returns:
                    The memory content if found, else an error message
                """
                return await get_memory_tool(new_context, key)
            
            # Create wrapper for list_memories_tool with proper RunContext annotation
            async def list_memories_wrapper(ctx: RunContext[Dict], prefix: Optional[str] = None) -> str:
                """List all available memories, optionally filtered by prefix.
                
                Args:
                    prefix: Optional prefix to filter memory keys
                    
                Returns:
                    List of memory keys as a string
                """
                # Extract the agent_id from the context to filter memories by agent
                agent_id = new_context.get("agent_id") if new_context else None
                user_id = new_context.get("user_id") if new_context else None
                
                try:
                    logger.info(f"Listing memories with agent_id={agent_id}, user_id={user_id}, prefix={prefix}")
                    
                    # Use the imported list_memories_tool directly
                    return await list_memories_tool(prefix)
                except Exception as e:
                    error_msg = f"Error listing memories: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            
            # Re-register all memory tool wrappers
            self.register_tool(store_memory_wrapper)
            self.register_tool(get_memory_wrapper)
            self.register_tool(list_memories_wrapper)
            # Sanitize context for logging
            from automagik.api.controllers.agent_controller import _sanitize_multimodal_content_for_logging
            sanitized_context = _sanitize_multimodal_content_for_logging(new_context)
            logger.info(f"Updated memory tools with new context: {sanitized_context}")
        else:
            logger.warning("Could not update memory tools: not imported")
        
        logger.info("Tool context updated") 