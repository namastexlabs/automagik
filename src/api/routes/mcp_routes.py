"""API routes for MCP server management."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import ValidationError

from src.auth import get_api_key as verify_api_key
from src.mcp.client import get_mcp_client_manager, refresh_mcp_client_manager
from src.mcp.models import (
    MCPServerConfig,
    MCPServerCreateRequest,
    MCPServerUpdateRequest,
    MCPServerListResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPResourceAccessRequest,
    MCPResourceAccessResponse,
    MCPHealthResponse,
    MCPServerState,
    MCPServerType
)
from src.mcp.exceptions import MCPError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.post("/configure", response_model=MCPServerListResponse)
async def configure_mcp_servers(
    servers_config: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """Configure multiple MCP servers using the mcpServers format.
    
    Accepts JSON in the format:
    {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
            },
            "weather": {
                "command": "node",
                "args": ["weather-server.js"]
            }
        }
    }
    """
    try:
        client_manager = await get_mcp_client_manager()
        
        # Extract mcpServers from the config
        mcp_servers = servers_config.get("mcpServers", {})
        
        created_servers = []
        
        for server_name, server_config in mcp_servers.items():
            # Convert the simplified format to MCPServerConfig
            command = []
            
            # Handle command and args format
            if "command" in server_config:
                base_command = server_config["command"]
                args = server_config.get("args", [])
                
                # Fix for npx and other shell commands that need proper environment
                if base_command in ["npx", "npm", "yarn", "node"] or base_command.endswith("npx"):
                    # Wrap with bash to ensure proper shell environment
                    full_command = f"{base_command} {' '.join(args)}"
                    command = ["/usr/bin/bash", "-c", full_command]
                    logger.info(f"Wrapped {base_command} command with bash for server {server_name}: {command}")
                else:
                    # Use original format for other commands
                    command.append(base_command)
                    command.extend(args)
            
            # Create MCPServerConfig
            config = MCPServerConfig(
                name=server_name,
                server_type=MCPServerType.STDIO,
                description=server_config.get("description", f"MCP server {server_name}"),
                command=command,
                env=server_config.get("env", {}),
                auto_start=server_config.get("auto_start", True),
                max_retries=server_config.get("max_retries", 3),
                timeout_seconds=server_config.get("timeout_seconds", 30),
                tags=server_config.get("tags", []),
                priority=server_config.get("priority", 0),
                agent_names=server_config.get("agent_names", [])
            )
            
            # Add server if it doesn't exist, update if it does
            try:
                await client_manager.add_server(config)
                logger.info(f"Added MCP server: {server_name}")
            except MCPError as e:
                if "already exists" in str(e):
                    # Update existing server
                    existing_server = client_manager.get_server(server_name)
                    if existing_server:
                        # Stop if running
                        if existing_server.is_running:
                            await existing_server.stop()
                        
                        # Update config
                        existing_server.config = config
                        await client_manager._save_server_config(config)
                        
                        # Start if auto_start
                        if config.auto_start:
                            await existing_server.start()
                        
                        logger.info(f"Updated MCP server: {server_name}")
                else:
                    raise
            
            # Get server state
            server = client_manager.get_server(server_name)
            if server:
                created_servers.append(server.state)
        
        return MCPServerListResponse(
            servers=created_servers,
            total=len(created_servers)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to configure MCP servers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to configure servers: {str(e)}")


@router.get("/health", response_model=MCPHealthResponse)
async def get_mcp_health():
    """Get health status of MCP system."""
    try:
        client_manager = await get_mcp_client_manager()
        return await client_manager.get_health()
    except Exception as e:
        logger.error(f"Failed to get MCP health: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    api_key: str = Depends(verify_api_key)
):
    """List all MCP servers and their states."""
    try:
        client_manager = await get_mcp_client_manager()
        servers = client_manager.list_servers()
        
        return MCPServerListResponse(
            servers=servers,
            total=len(servers)
        )
    except Exception as e:
        logger.error(f"Failed to list MCP servers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list servers: {str(e)}")


@router.post("/servers", response_model=MCPServerState)
async def create_mcp_server(
    request: MCPServerCreateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new MCP server configuration."""
    try:
        client_manager = await get_mcp_client_manager()
        
        # Create server config from request
        config = MCPServerConfig(**request.model_dump())
        
        # Add server
        await client_manager.add_server(config)
        
        # Get and return server state
        server = client_manager.get_server(config.name)
        if not server:
            raise HTTPException(status_code=500, detail="Server created but not found")
        
        return server.state
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create MCP server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create server: {str(e)}")


@router.get("/servers/{server_name}", response_model=MCPServerState)
async def get_mcp_server(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """Get details of a specific MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        server = client_manager.get_server(server_name)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        
        return server.state
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get server: {str(e)}")


@router.put("/servers/{server_name}", response_model=MCPServerState)
async def update_mcp_server(
    server_name: str,
    request: MCPServerUpdateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update an MCP server configuration."""
    try:
        client_manager = await get_mcp_client_manager()
        server = client_manager.get_server(server_name)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        
        # Update configuration
        update_data = request.model_dump(exclude_none=True)
        for key, value in update_data.items():
            if hasattr(server.config, key):
                setattr(server.config, key, value)
        
        # Save updated configuration to database
        await client_manager._save_server_config(server.config)
        
        # Restart server if it was running to apply changes
        if server.is_running:
            await server.restart()
        
        # Refresh client manager to reload configurations
        await refresh_mcp_client_manager()
        
        return server.state
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update server: {str(e)}")


@router.delete("/servers/{server_name}")
async def delete_mcp_server(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        await client_manager.remove_server(server_name)
        
        return {"status": "success", "message": f"Server {server_name} deleted successfully"}
        
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete server: {str(e)}")


@router.post("/servers/{server_name}/start")
async def start_mcp_server(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """Start an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        await client_manager.start_server(server_name)
        
        return {"status": "success", "message": f"Server {server_name} started successfully"}
        
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start server: {str(e)}")


@router.post("/servers/{server_name}/stop")
async def stop_mcp_server(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """Stop an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        await client_manager.stop_server(server_name)
        
        return {"status": "success", "message": f"Server {server_name} stopped successfully"}
        
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop server: {str(e)}")


@router.post("/servers/{server_name}/restart")
async def restart_mcp_server(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """Restart an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        await client_manager.restart_server(server_name)
        
        return {"status": "success", "message": f"Server {server_name} restarted successfully"}
        
    except MCPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restart MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to restart server: {str(e)}")


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(
    request: MCPToolCallRequest,
    api_key: str = Depends(verify_api_key)
):
    """Call a tool on an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        
        import time
        start_time = time.time()
        
        result = await client_manager.call_tool(
            server_name=request.server_name,
            tool_name=request.tool_name,
            arguments=request.arguments
        )
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return MCPToolCallResponse(
            success=True,
            result=result,
            execution_time_ms=execution_time,
            tool_name=request.tool_name,
            server_name=request.server_name
        )
        
    except MCPError as e:
        return MCPToolCallResponse(
            success=False,
            error=str(e),
            tool_name=request.tool_name,
            server_name=request.server_name
        )
    except Exception as e:
        logger.error(f"Failed to call MCP tool {request.tool_name}: {str(e)}")
        return MCPToolCallResponse(
            success=False,
            error=f"Tool call failed: {str(e)}",
            tool_name=request.tool_name,
            server_name=request.server_name
        )


@router.post("/resources/access", response_model=MCPResourceAccessResponse)
async def access_mcp_resource(
    request: MCPResourceAccessRequest,
    api_key: str = Depends(verify_api_key)
):
    """Access a resource on an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        
        result = await client_manager.access_resource(
            server_name=request.server_name,
            uri=request.uri
        )
        
        # Extract content and mime type from result
        content = None
        mime_type = None
        
        if isinstance(result, dict):
            content = result.get('content')
            mime_type = result.get('mime_type')
        elif isinstance(result, str):
            content = result
        else:
            content = str(result)
        
        return MCPResourceAccessResponse(
            success=True,
            content=content,
            mime_type=mime_type,
            uri=request.uri,
            server_name=request.server_name
        )
        
    except MCPError as e:
        return MCPResourceAccessResponse(
            success=False,
            error=str(e),
            uri=request.uri,
            server_name=request.server_name
        )
    except Exception as e:
        logger.error(f"Failed to access MCP resource {request.uri}: {str(e)}")
        return MCPResourceAccessResponse(
            success=False,
            error=f"Resource access failed: {str(e)}",
            uri=request.uri,
            server_name=request.server_name
        )


@router.get("/servers/{server_name}/tools")
async def list_mcp_server_tools(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """List tools available on an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        server = client_manager.get_server(server_name)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        
        return {
            "server_name": server_name,
            "tools": server.tools,
            "total": len(server.tools)
        }
        
    except Exception as e:
        logger.error(f"Failed to list tools for MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.get("/servers/{server_name}/resources")
async def list_mcp_server_resources(
    server_name: str,
    api_key: str = Depends(verify_api_key)
):
    """List resources available on an MCP server."""
    try:
        client_manager = await get_mcp_client_manager()
        server = client_manager.get_server(server_name)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        
        return {
            "server_name": server_name,
            "resources": server.resources,
            "total": len(server.resources)
        }
        
    except Exception as e:
        logger.error(f"Failed to list resources for MCP server {server_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list resources: {str(e)}")


@router.get("/agents/{agent_name}/tools")
async def list_agent_mcp_tools(
    agent_name: str,
    api_key: str = Depends(verify_api_key)
):
    """List MCP tools available to a specific agent."""
    try:
        client_manager = await get_mcp_client_manager()
        servers = client_manager.get_servers_for_agent(agent_name)
        
        tools = []
        for server in servers:
            if server.is_running:
                for tool in server.tools:
                    tools.append({
                        "server_name": server.name,
                        "tool_name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "output_schema": tool.output_schema
                    })
        
        return {
            "agent_name": agent_name,
            "tools": tools,
            "total": len(tools),
            "servers": [s.name for s in servers]
        }
        
    except Exception as e:
        logger.error(f"Failed to list MCP tools for agent {agent_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list agent tools: {str(e)}")