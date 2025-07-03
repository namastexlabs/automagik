"""Tool management API routes."""

import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
from automagik.db.repository.tool import (
    list_tools as db_list_tools,
    get_tool_by_name,
    create_tool,
    update_tool,
    delete_tool,
    get_tools_by_category,
    get_tool_categories,
    get_tool_execution_stats,
    log_tool_execution
)
from automagik.db.models import ToolCreate, ToolUpdate
from automagik.services.tool_execution import execute_tool
from automagik.api.models import ToolInfo, ToolExecuteRequest, ToolExecuteResponse

logger = logging.getLogger(__name__)

# Create router
tool_router = APIRouter(prefix="/tools", tags=["Tools"])


# Response models
class ToolListResponse(BaseModel):
    """Response for listing tools."""
    tools: List[ToolInfo]
    total_count: int
    filtered_count: int
    categories: List[str]
    

class ToolDetailResponse(BaseModel):
    """Response for tool details."""
    tool: ToolInfo
    stats: Optional[Dict[str, Any]] = None


class ToolCreateResponse(BaseModel):
    """Response for tool creation."""
    status: str = "success"
    tool: ToolInfo
    message: str


class ToolUpdateResponse(BaseModel):
    """Response for tool update."""
    status: str = "success"
    tool: ToolInfo
    message: str


class ToolDeleteResponse(BaseModel):
    """Response for tool deletion."""
    status: str = "success"
    message: str




# Main endpoints
@tool_router.get("/", response_model=ToolListResponse)
async def list_tools(
    tool_type: Optional[str] = Query(None, description="Filter by tool type: code, mcp, hybrid"),
    enabled_only: bool = Query(True, description="Show only enabled tools"),
    category: Optional[str] = Query(None, description="Filter by category"),
    agent_name: Optional[str] = Query(None, description="Filter by agent restrictions"),
    search: Optional[str] = Query(None, description="Search in tool names and descriptions")
):
    """List all available tools with filtering options."""
    try:
        logger.info(f"Listing tools with filters: type={tool_type}, category={category}, agent={agent_name}")
        
        # Get tools from database
        if category:
            tools_db = get_tools_by_category(category)
        else:
            categories_filter = [category] if category else None
            tools_db = db_list_tools(
                tool_type=tool_type,
                enabled_only=enabled_only,
                categories=categories_filter,
                agent_name=agent_name
            )
        
        # Convert to API format and apply search filter
        tools = []
        for tool_db in tools_db:
            # Apply search filter
            if search:
                search_text = f"{tool_db.name} {tool_db.description or ''}".lower()
                if search.lower() not in search_text:
                    continue
            
            tool_info = ToolInfo(
                name=tool_db.name,
                type=tool_db.type,
                description=tool_db.description or "",
                server_name=tool_db.mcp_server_name,
                module=tool_db.module_path,
                context_signature="RunContext[Dict]",
                parameters=_convert_schema_to_parameters(tool_db.parameters_schema)
            )
            tools.append(tool_info)
        
        # Get all categories
        all_categories = get_tool_categories()
        
        logger.info(f"Found {len(tools)} tools matching filters")
        
        return ToolListResponse(
            tools=tools,
            total_count=len(db_list_tools(enabled_only=False)),
            filtered_count=len(tools),
            categories=all_categories
        )
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@tool_router.get("/{tool_name}", response_model=ToolDetailResponse)
async def get_tool_details(tool_name: str = Path(..., description="Tool name")):
    """Get detailed information about a specific tool."""
    try:
        logger.info(f"Getting details for tool: {tool_name}")
        
        tool_db = get_tool_by_name(tool_name)
        if not tool_db:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Convert to API format
        tool_info = ToolInfo(
            name=tool_db.name,
            type=tool_db.type,
            description=tool_db.description or "",
            server_name=tool_db.mcp_server_name,
            module=tool_db.module_path,
            context_signature="RunContext[Dict]",
            parameters=_convert_schema_to_parameters(tool_db.parameters_schema)
        )
        
        # Get execution statistics
        stats = get_tool_execution_stats(tool_db.id)
        
        return ToolDetailResponse(tool=tool_info, stats=stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool details: {str(e)}")


@tool_router.post("/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool_endpoint(
    tool_name: str = Path(..., description="Tool name"),
    request: ToolExecuteRequest = Body(..., description="Execution request")
):
    """Execute a specific tool."""
    try:
        logger.info(f"Executing tool: {tool_name}")
        start_time = time.time()
        
        # Get tool from database
        tool_db = get_tool_by_name(tool_name)
        if not tool_db:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        if not tool_db.enabled:
            raise HTTPException(status_code=403, detail=f"Tool '{tool_name}' is disabled")
        
        # Execute the tool
        result = await execute_tool(tool_db, request.context, request.parameters)
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log execution
        log_tool_execution(
            tool_id=tool_db.id,
            agent_name=request.context.get("agent_name"),
            session_id=request.context.get("session_id"),
            parameters=request.parameters,
            context=request.context,
            status="success",
            result=result,
            execution_time_ms=execution_time_ms
        )
        
        logger.info(f"Successfully executed tool {tool_name} in {execution_time_ms}ms")
        
        return ToolExecuteResponse(
            status="success",
            result=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        
        # Log failed execution
        if 'tool_db' in locals():
            log_tool_execution(
                tool_id=tool_db.id,
                agent_name=request.context.get("agent_name"),
                session_id=request.context.get("session_id"),
                parameters=request.parameters,
                context=request.context,
                status="error",
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
            )
        
        return ToolExecuteResponse(
            status="error",
            error=str(e)
        )


class MCPToolCreateRequest(BaseModel):
    """Request for creating MCP tool."""
    name: str = Field(..., description="Tool name")
    command: str = Field(..., description="Command to run (e.g., 'npx')")
    args: List[str] = Field(..., description="Command arguments")
    agent_names: List[str] = Field(default=["*"], description="Agents that can use this tool")
    tools: Dict[str, List[str]] = Field(default={"include": ["*"]}, description="Tool filters")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    description: Optional[str] = Field(None, description="Tool description")
    categories: List[str] = Field(default_factory=list, description="Tool categories")
    enabled: bool = Field(True, description="Whether tool is enabled")


class MCPServerCreateResponse(BaseModel):
    """Response for MCP server creation."""
    status: str = "success"
    server_name: str
    message: str
    tools_will_be_discovered: bool = True


@tool_router.post("/create/mcp", response_model=MCPServerCreateResponse)
async def create_mcp_server_endpoint(server_data: MCPToolCreateRequest = Body(..., description="MCP server creation data")):
    """Create a new MCP server configuration."""
    try:
        logger.info(f"Creating new MCP server: {server_data.name}")
        
        # Read current .mcp.json
        import json
        import os
        
        mcp_config_path = ".mcp.json"
        if os.path.exists(mcp_config_path):
            with open(mcp_config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"mcpServers": {}}
        
        # Check if server already exists
        if server_data.name in config.get("mcpServers", {}):
            raise HTTPException(status_code=409, detail=f"MCP server '{server_data.name}' already exists")
        
        # Create server configuration
        server_config = {
            "command": server_data.command,
            "args": server_data.args,
            "agent_names": server_data.agent_names,
            "tools": server_data.tools
        }
        
        # Add environment variables if provided
        if server_data.env:
            server_config["env"] = server_data.env
        
        # Add to configuration
        config["mcpServers"][server_data.name] = server_config
        
        # Write back to .mcp.json
        with open(mcp_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Successfully created MCP server: {server_data.name}")
        
        return MCPServerCreateResponse(
            server_name=server_data.name,
            message=f"MCP server '{server_data.name}' added to .mcp.json configuration. Restart the application to initialize the server and discover its tools."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MCP server: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create MCP server: {str(e)}")


@tool_router.put("/{tool_name}", response_model=ToolUpdateResponse)
async def update_tool_endpoint(
    tool_name: str = Path(..., description="Tool name"),
    tool_data: ToolUpdate = Body(..., description="Tool update data")
):
    """Update an existing tool."""
    try:
        logger.info(f"Updating tool: {tool_name}")
        
        # Check if tool exists
        existing_tool = get_tool_by_name(tool_name)
        if not existing_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Update the tool
        updated_tool = update_tool(tool_name, tool_data)
        if not updated_tool:
            raise HTTPException(status_code=500, detail="Failed to update tool")
        
        # Convert to API format
        tool_info = ToolInfo(
            name=updated_tool.name,
            type=updated_tool.type,
            description=updated_tool.description or "",
            server_name=updated_tool.mcp_server_name,
            module=updated_tool.module_path,
            context_signature="RunContext[Dict]",
            parameters=_convert_schema_to_parameters(updated_tool.parameters_schema)
        )
        
        logger.info(f"Successfully updated tool: {tool_name}")
        
        return ToolUpdateResponse(
            tool=tool_info,
            message=f"Tool '{tool_name}' updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update tool: {str(e)}")


@tool_router.delete("/{tool_name}", response_model=ToolDeleteResponse)
async def delete_tool_endpoint(tool_name: str = Path(..., description="Tool name")):
    """Delete a tool."""
    try:
        logger.info(f"Deleting tool: {tool_name}")
        
        # Check if tool exists
        existing_tool = get_tool_by_name(tool_name)
        if not existing_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Delete the tool
        success = delete_tool(tool_name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete tool")
        
        logger.info(f"Successfully deleted tool: {tool_name}")
        
        return ToolDeleteResponse(message=f"Tool '{tool_name}' deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {str(e)}")


@tool_router.get("/categories/list", response_model=List[str])
async def list_tool_categories():
    """Get all available tool categories."""
    try:
        categories = get_tool_categories()
        return categories
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")


class MCPServerInfo(BaseModel):
    """Information about available MCP servers."""
    name: str = Field(..., description="Server name")
    type: str = Field(..., description="Server type (stdio/sse)")
    command: Optional[str] = Field(None, description="Command for stdio servers")
    url: Optional[str] = Field(None, description="URL for SSE servers")
    agent_names: List[str] = Field(..., description="Agents that can use this server")


class MCPServersResponse(BaseModel):
    """Response for listing MCP servers."""
    servers: List[MCPServerInfo]
    total_count: int
    configured_in: str = ".mcp.json"


@tool_router.get("/mcp/servers", response_model=MCPServersResponse)
async def list_mcp_servers():
    """Get available MCP servers from .mcp.json configuration."""
    try:
        import json
        import os
        
        mcp_config_path = ".mcp.json"
        if not os.path.exists(mcp_config_path):
            return MCPServersResponse(servers=[], total_count=0)
        
        with open(mcp_config_path, 'r') as f:
            config = json.load(f)
        
        servers = []
        mcp_servers = config.get("mcpServers", {})
        
        for server_name, server_config in mcp_servers.items():
            # Determine server type
            if "command" in server_config:
                server_type = "stdio"
                command = f"{server_config['command']} {' '.join(server_config.get('args', []))}"
                url = None
            elif "url" in server_config:
                server_type = "sse"
                command = None
                url = server_config["url"]
            else:
                server_type = "unknown"
                command = None
                url = None
            
            servers.append(MCPServerInfo(
                name=server_name,
                type=server_type,
                command=command,
                url=url,
                agent_names=server_config.get("agent_names", ["*"])
            ))
        
        return MCPServersResponse(
            servers=servers,
            total_count=len(servers)
        )
        
    except Exception as e:
        logger.error(f"Error listing MCP servers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list MCP servers: {str(e)}")



# Helper functions
def _convert_schema_to_parameters(schema: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert JSON schema to parameter list format."""
    if not schema or not isinstance(schema, dict):
        return []
    
    parameters = []
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    for param_name, param_info in properties.items():
        parameters.append({
            "name": param_name,
            "type": param_info.get("type", "string"),
            "description": param_info.get("description", ""),
            "required": param_name in required
        })
    
    return parameters