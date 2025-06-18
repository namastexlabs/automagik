"""Tool management API routes."""

import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field

from src.auth import get_api_key
from src.db.repository.tool import (
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
from src.db.models import ToolCreate, ToolUpdate
from src.services.tool_discovery import get_tool_discovery_service
from src.services.tool_execution import execute_tool
from src.api.models import ToolInfo, ToolExecuteRequest, ToolExecuteResponse

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


class ToolDiscoveryResponse(BaseModel):
    """Response for tool discovery."""
    status: str = "success"
    discovered: Dict[str, List[Dict[str, Any]]]
    sync_stats: Dict[str, int]
    message: str


class MCPServerCreateRequest(BaseModel):
    """Request for creating MCP server configuration."""
    name: str = Field(..., description="Server name")
    server_type: str = Field(..., description="Server type: stdio or http")
    config: Dict[str, Any] = Field(..., description="Server configuration")
    auto_discover: bool = Field(True, description="Auto-discover tools")


class MCPServerCreateResponse(BaseModel):
    """Response for MCP server creation."""
    status: str = "success"
    server_name: str
    tools_discovered: List[str]
    message: str


# Main endpoints
@tool_router.get("/", response_model=ToolListResponse, dependencies=[Depends(get_api_key)])
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


@tool_router.get("/{tool_name}", response_model=ToolDetailResponse, dependencies=[Depends(get_api_key)])
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


@tool_router.post("/{tool_name}/execute", response_model=ToolExecuteResponse, dependencies=[Depends(get_api_key)])
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


@tool_router.post("/", response_model=ToolCreateResponse, dependencies=[Depends(get_api_key)])
async def create_tool_endpoint(tool_data: ToolCreate = Body(..., description="Tool creation data")):
    """Create a new tool."""
    try:
        logger.info(f"Creating new tool: {tool_data.name}")
        
        # Check if tool already exists
        existing_tool = get_tool_by_name(tool_data.name)
        if existing_tool:
            raise HTTPException(status_code=409, detail=f"Tool '{tool_data.name}' already exists")
        
        # Create the tool
        created_tool = create_tool(tool_data)
        if not created_tool:
            raise HTTPException(status_code=500, detail="Failed to create tool")
        
        # Convert to API format
        tool_info = ToolInfo(
            name=created_tool.name,
            type=created_tool.type,
            description=created_tool.description or "",
            server_name=created_tool.mcp_server_name,
            module=created_tool.module_path,
            context_signature="RunContext[Dict]",
            parameters=_convert_schema_to_parameters(created_tool.parameters_schema)
        )
        
        logger.info(f"Successfully created tool: {tool_data.name}")
        
        return ToolCreateResponse(
            tool=tool_info,
            message=f"Tool '{tool_data.name}' created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {str(e)}")


@tool_router.put("/{tool_name}", response_model=ToolUpdateResponse, dependencies=[Depends(get_api_key)])
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


@tool_router.delete("/{tool_name}", response_model=ToolDeleteResponse, dependencies=[Depends(get_api_key)])
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


@tool_router.get("/categories/list", response_model=List[str], dependencies=[Depends(get_api_key)])
async def list_tool_categories():
    """Get all available tool categories."""
    try:
        categories = get_tool_categories()
        return categories
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")


@tool_router.post("/discover", response_model=ToolDiscoveryResponse, dependencies=[Depends(get_api_key)])
async def discover_tools():
    """Discover and sync all available tools."""
    try:
        logger.info("Starting tool discovery and sync")
        
        discovery_service = get_tool_discovery_service()
        
        # Discover all tools
        discovered = await discovery_service.discover_all_tools(force_refresh=True)
        
        # Sync to database
        sync_stats = await discovery_service.sync_tools_to_database()
        
        logger.info(f"Tool discovery completed: {sync_stats}")
        
        return ToolDiscoveryResponse(
            discovered=discovered,
            sync_stats=sync_stats,
            message=f"Discovered and synced {sync_stats['total']} tools"
        )
        
    except Exception as e:
        logger.error(f"Error during tool discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Tool discovery failed: {str(e)}")


# MCP server management endpoints
@tool_router.post("/mcp/servers", response_model=MCPServerCreateResponse, dependencies=[Depends(get_api_key)])
async def create_mcp_server(request: MCPServerCreateRequest = Body(..., description="MCP server creation request")):
    """Create a new MCP server configuration and discover its tools."""
    try:
        logger.info(f"Creating MCP server: {request.name}")
        
        # Import MCP repository here to avoid circular imports
        from src.db.repository.mcp import create_mcp_config, MCPConfigRequest
        
        # Create MCP server configuration
        mcp_config_request = MCPConfigRequest(
            name=request.name,
            server_type=request.server_type,
            config=request.config
        )
        
        created_config = create_mcp_config(mcp_config_request)
        if not created_config:
            raise HTTPException(status_code=500, detail="Failed to create MCP server configuration")
        
        tools_discovered = []
        
        if request.auto_discover:
            try:
                # Discover tools from the new server
                discovery_service = get_tool_discovery_service()
                discovered = await discovery_service._discover_mcp_tools()
                
                # Filter tools from this server
                server_tools = [
                    tool for tool in discovered 
                    if tool.get("server_name") == request.name
                ]
                
                # Sync server tools to database
                for tool_data in server_tools:
                    try:
                        tool_create = ToolCreate(
                            name=tool_data["name"],
                            type="mcp",
                            description=tool_data["description"],
                            mcp_server_name=tool_data["mcp_server_name"],
                            mcp_tool_name=tool_data["mcp_tool_name"],
                            parameters_schema=tool_data.get("parameters_schema"),
                            capabilities=tool_data.get("capabilities", []),
                            categories=tool_data.get("categories", [])
                        )
                        
                        created_tool = create_tool(tool_create)
                        if created_tool:
                            tools_discovered.append(created_tool.name)
                            
                    except Exception as e:
                        logger.warning(f"Failed to create tool {tool_data['name']}: {e}")
                        
            except Exception as e:
                logger.warning(f"Failed to auto-discover tools for server {request.name}: {e}")
        
        logger.info(f"Successfully created MCP server {request.name} with {len(tools_discovered)} tools")
        
        return MCPServerCreateResponse(
            server_name=request.name,
            tools_discovered=tools_discovered,
            message=f"MCP server '{request.name}' created with {len(tools_discovered)} tools discovered"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MCP server: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create MCP server: {str(e)}")


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