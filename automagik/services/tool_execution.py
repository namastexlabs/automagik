"""Tool execution service for code and MCP tools."""

import asyncio
import importlib
import logging
from typing import Dict, Any, Optional

try:
    from pydantic_ai import RunContext
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    # Define a minimal fallback for when pydantic_ai is not available
    class RunContext:
        def __init__(self, deps, model=None, usage=None, prompt=None):
            self.deps = deps
            self.model = model
            self.usage = usage  
            self.prompt = prompt

from automagik.db.models import ToolDB
from automagik.mcp import get_mcp_manager

logger = logging.getLogger(__name__)


async def execute_tool(
    tool: ToolDB,
    context: Dict[str, Any],
    parameters: Dict[str, Any]
) -> Any:
    """Execute a tool (code or MCP) with given context and parameters."""
    logger.info(f"Executing {tool.type} tool: {tool.name}")
    
    if tool.type == "code":
        return await _execute_code_tool(tool, context, parameters)
    elif tool.type == "mcp":
        return await _execute_mcp_tool(tool, context, parameters)
    elif tool.type == "hybrid":
        # Try code first, fallback to MCP
        try:
            return await _execute_code_tool(tool, context, parameters)
        except Exception as e:
            logger.warning(f"Code execution failed for hybrid tool {tool.name}, trying MCP: {e}")
            return await _execute_mcp_tool(tool, context, parameters)
    else:
        raise ValueError(f"Unknown tool type: {tool.type}")


async def _execute_code_tool(
    tool: ToolDB,
    context: Dict[str, Any],
    parameters: Dict[str, Any]
) -> Any:
    """Execute a code-based tool."""
    try:
        if not tool.module_path or not tool.function_name:
            raise ValueError(f"Missing module_path or function_name for code tool {tool.name}")
        
        # Import the module
        module = importlib.import_module(tool.module_path)
        
        # Get the function
        if not hasattr(module, tool.function_name):
            raise ValueError(f"Function {tool.function_name} not found in module {tool.module_path}")
        
        func = getattr(module, tool.function_name)
        
        # Create RunContext with proper parameters
        # Extract or create the required parameters for RunContext
        model = context.get('model') or None
        usage = context.get('usage') or None  
        prompt = context.get('prompt') or None
        
        # Create RunContext with all required parameters
        run_context = RunContext(
            deps=context,  # Pass the full context as dependencies
            model=model,
            usage=usage,
            prompt=prompt
        )
        
        # Call the function
        if asyncio.iscoroutinefunction(func):
            result = await func(run_context, **parameters)
        else:
            result = func(run_context, **parameters)
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing code tool {tool.name}: {e}")
        raise RuntimeError(f"Code tool execution failed: {str(e)}")


async def _execute_mcp_tool(
    tool: ToolDB,
    context: Dict[str, Any],
    parameters: Dict[str, Any]
) -> Any:
    """Execute an MCP tool."""
    try:
        if not tool.mcp_server_name or not tool.mcp_tool_name:
            raise ValueError(f"Missing mcp_server_name or mcp_tool_name for MCP tool {tool.name}")
        
        # Get MCP manager
        mcp_manager = await get_mcp_manager()
        if not mcp_manager:
            raise RuntimeError("MCP client manager not available")
        
        # Execute the tool via MCP
        result = await mcp_manager.call_tool(
            server_name=tool.mcp_server_name,
            tool_name=tool.mcp_tool_name,
            arguments=parameters
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing MCP tool {tool.name}: {e}")
        raise RuntimeError(f"MCP tool execution failed: {str(e)}")


async def validate_tool_parameters(
    tool: ToolDB,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate tool parameters against schema."""
    if not tool.parameters_schema:
        return parameters
    
    try:
        from jsonschema import validate, ValidationError
        
        validate(instance=parameters, schema=tool.parameters_schema)
        return parameters
        
    except ImportError:
        logger.warning("jsonschema not available, skipping parameter validation")
        return parameters
    except ValidationError as e:
        raise ValueError(f"Parameter validation failed: {e.message}")
    except Exception as e:
        logger.warning(f"Parameter validation error: {e}")
        return parameters