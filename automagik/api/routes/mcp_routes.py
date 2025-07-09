"""Streamlined API routes for MCP configuration management."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ValidationError, Field

from automagik.auth import verify_api_key
from automagik.db.repository.mcp import (
    get_mcp_config_by_name,
    list_mcp_configs,
    create_mcp_config,
    update_mcp_config_by_name,
    delete_mcp_config_by_name,
    get_agent_mcp_configs
)
from automagik.db.models import MCPConfig, MCPConfigCreate, MCPConfigUpdate
from automagik.mcp.client import get_mcp_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


# Request/Response Models
class MCPConfigRequest(BaseModel):
    """Request model for creating/updating MCP configurations."""
    name: str = Field(..., description="Unique server identifier")
    server_type: str = Field(..., description="Server type: 'stdio' or 'http'")
    command: Optional[List[str]] = Field(None, description="Command array for stdio servers")
    url: Optional[str] = Field(None, description="URL for HTTP servers")
    agents: List[str] = Field(default=["*"], description="List of agent names or ['*'] for all")
    tools: Optional[Dict[str, List[str]]] = Field(default={"include": ["*"]}, description="Tool filters with include/exclude lists")
    environment: Optional[Dict[str, str]] = Field(default={}, description="Environment variables")
    timeout: Optional[int] = Field(default=30000, description="Timeout in milliseconds")
    retry_count: Optional[int] = Field(default=3, description="Maximum retry attempts")
    enabled: Optional[bool] = Field(default=True, description="Whether the server is enabled")
    auto_start: Optional[bool] = Field(default=True, description="Whether to auto-start the server")

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to configuration dictionary for storage."""
        config = {
            "name": self.name,
            "server_type": self.server_type,
            "agents": self.agents,
            "tools": self.tools or {"include": ["*"]},
            "environment": self.environment or {},
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "enabled": self.enabled,
            "auto_start": self.auto_start
        }
        
        if self.server_type == "stdio" and self.command:
            config["command"] = self.command
        elif self.server_type == "http" and self.url:
            config["url"] = self.url
            
        return config


class MCPConfigResponse(BaseModel):
    """Response model for MCP configurations."""
    id: str
    name: str
    config: Dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_mcp_config(cls, mcp_config: MCPConfig) -> "MCPConfigResponse":
        """Create response from MCPConfig model."""
        return cls(
            id=str(mcp_config.id),
            name=mcp_config.name,
            config=mcp_config.config,
            created_at=mcp_config.created_at.isoformat(),
            updated_at=mcp_config.updated_at.isoformat()
        )


class MCPConfigListResponse(BaseModel):
    """Response model for listing MCP configurations."""
    configs: List[MCPConfigResponse]
    total: int
    filtered_by_agent: Optional[str] = None


async def trigger_hot_reload():
    """Trigger MCP hot reload after configuration changes."""
    try:
        mcp_manager = await get_mcp_manager()
        if mcp_manager.is_hot_reload_enabled():
            await mcp_manager.hot_reload_config()
            logger.info("🔄 Triggered MCP hot reload after API change")
        else:
            logger.debug("Hot reload is disabled, skipping reload trigger")
    except Exception as e:
        logger.warning(f"⚠️ Failed to trigger hot reload: {e}")
        # Don't raise - hot reload failure shouldn't break API operations


def validate_mcp_config_request(config_request: MCPConfigRequest) -> None:
    """Validate MCP configuration request against architecture requirements.
    
    Args:
        config_request: The configuration request to validate
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate server type
    if config_request.server_type not in ["stdio", "http"]:
        raise HTTPException(
            status_code=400,
            detail="server_type must be 'stdio' or 'http'"
        )
    
    # Validate type-specific requirements
    if config_request.server_type == "stdio":
        if not config_request.command:
            raise HTTPException(
                status_code=400,
                detail="command is required for stdio servers"
            )
        if not isinstance(config_request.command, list) or len(config_request.command) == 0:
            raise HTTPException(
                status_code=400,
                detail="command must be a non-empty array for stdio servers"
            )
    elif config_request.server_type == "http":
        if not config_request.url:
            raise HTTPException(
                status_code=400,
                detail="url is required for http servers"
            )
        # Basic URL validation
        if not config_request.url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="url must be a valid HTTP/HTTPS URL"
            )
    
    # Validate name format (alphanumeric, hyphens, underscores only)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', config_request.name):
        raise HTTPException(
            status_code=400,
            detail="name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    # Validate agents list
    if not config_request.agents:
        raise HTTPException(
            status_code=400,
            detail="agents list cannot be empty"
        )
    
    # Validate agent names (wildcard or valid agent names)
    for agent in config_request.agents:
        if agent != "*" and not re.match(r'^[a-zA-Z0-9_-]+$', agent):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent name '{agent}'. Use '*' for wildcard or alphanumeric names."
            )
    
    # Validate tools configuration
    if config_request.tools:
        if not isinstance(config_request.tools, dict):
            raise HTTPException(
                status_code=400,
                detail="tools must be a dictionary with 'include' and/or 'exclude' keys"
            )
        
        for key in config_request.tools.keys():
            if key not in ["include", "exclude"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tools key '{key}'. Only 'include' and 'exclude' are allowed."
                )
        
        # Validate tool patterns
        for filter_type, patterns in config_request.tools.items():
            if not isinstance(patterns, list):
                raise HTTPException(
                    status_code=400,
                    detail=f"tools.{filter_type} must be a list of tool patterns"
                )
    
    # Validate timeout and retry values
    if config_request.timeout is not None:
        if config_request.timeout < 1000 or config_request.timeout > 300000:
            raise HTTPException(
                status_code=400,
                detail="timeout must be between 1000ms (1s) and 300000ms (5m)"
            )
    
    if config_request.retry_count is not None:
        if config_request.retry_count < 0 or config_request.retry_count > 10:
            raise HTTPException(
                status_code=400,
                detail="retry_count must be between 0 and 10"
            )
    
    # Validate environment variables
    if config_request.environment:
        if not isinstance(config_request.environment, dict):
            raise HTTPException(
                status_code=400,
                detail="environment must be a dictionary of key-value pairs"
            )
        
        for key, value in config_request.environment.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise HTTPException(
                    status_code=400,
                    detail="environment variables must be string key-value pairs"
                )


@router.get("/configs", response_model=MCPConfigListResponse)
async def list_mcp_configs_endpoint(
    agent_name: Optional[str] = Query(None, description="Filter configs by agent name"),
    enabled_only: bool = Query(True, description="Only return enabled configurations"),
    _: bool = Depends(verify_api_key)
):
    """List all MCP configurations.
    
    Args:
        agent_name: Optional agent name to filter configurations
        enabled_only: Whether to only return enabled configurations
        api_key: API key for authentication
        
    Returns:
        List of MCP configurations
    """
    try:
        configs = list_mcp_configs(enabled_only=enabled_only, agent_name=agent_name)
        
        response_configs = [
            MCPConfigResponse.from_mcp_config(config) 
            for config in configs
        ]
        
        logger.info(f"Listed {len(response_configs)} MCP configs (agent_filter={agent_name}, enabled_only={enabled_only})")
        
        return MCPConfigListResponse(
            configs=response_configs,
            total=len(response_configs),
            filtered_by_agent=agent_name
        )
        
    except Exception as e:
        logger.error(f"Failed to list MCP configs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list configurations: {str(e)}")


@router.post("/configs", response_model=MCPConfigResponse, status_code=201)
async def create_mcp_config_endpoint(
    config_request: MCPConfigRequest,
    _: bool = Depends(verify_api_key)
):
    """Create a new MCP configuration.
    
    Args:
        config_request: The MCP configuration to create
        api_key: API key for authentication
        
    Returns:
        The created MCP configuration
    """
    try:
        # Validate the request
        validate_mcp_config_request(config_request)
        
        # Check if config with this name already exists
        existing = get_mcp_config_by_name(config_request.name)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"MCP configuration with name '{config_request.name}' already exists"
            )
        
        # Create the configuration
        config_data = MCPConfigCreate(
            name=config_request.name,
            config=config_request.to_config_dict()
        )
        
        config_id = create_mcp_config(config_data)
        if not config_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create MCP configuration"
            )
        
        # Retrieve and return the created config
        created_config = get_mcp_config_by_name(config_request.name)
        if not created_config:
            raise HTTPException(
                status_code=500,
                detail="Configuration created but not found"
            )
        
        logger.info(f"Created MCP config '{config_request.name}' with ID {config_id}")
        
        # Trigger hot reload to apply the new configuration
        await trigger_hot_reload()
        
        return MCPConfigResponse.from_mcp_config(created_config)
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create MCP config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create configuration: {str(e)}")


@router.put("/configs/{name}", response_model=MCPConfigResponse)
async def update_mcp_config_endpoint(
    name: str,
    config_request: MCPConfigRequest,
    _: bool = Depends(verify_api_key)
):
    """Update an existing MCP configuration.
    
    Args:
        name: Name of the configuration to update
        config_request: The updated MCP configuration
        api_key: API key for authentication
        
    Returns:
        The updated MCP configuration
    """
    try:
        # Validate the request
        validate_mcp_config_request(config_request)
        
        # Check if config exists
        existing_config = get_mcp_config_by_name(name)
        if not existing_config:
            raise HTTPException(
                status_code=404,
                detail=f"MCP configuration '{name}' not found"
            )
        
        # Ensure name consistency (can't change name via this endpoint)
        if config_request.name != name:
            raise HTTPException(
                status_code=400,
                detail="Cannot change configuration name via update. Name in URL must match name in payload."
            )
        
        # Update the configuration
        update_data = MCPConfigUpdate(
            config=config_request.to_config_dict()
        )
        
        success = update_mcp_config_by_name(name, update_data)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update MCP configuration"
            )
        
        # Retrieve and return the updated config
        updated_config = get_mcp_config_by_name(name)
        if not updated_config:
            raise HTTPException(
                status_code=500,
                detail="Configuration updated but not found"
            )
        
        logger.info(f"Updated MCP config '{name}'")
        
        # Trigger hot reload to apply configuration changes
        await trigger_hot_reload()
        
        return MCPConfigResponse.from_mcp_config(updated_config)
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update MCP config '{name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/configs/{name}", response_model=MCPConfigResponse)
async def get_mcp_config_endpoint(
    name: str,
    _: bool = Depends(verify_api_key)
):
    """Get a specific MCP configuration by name.
    
    Args:
        name: Name of the configuration to retrieve
        api_key: API key for authentication
        
    Returns:
        The MCP configuration
    """
    try:
        config = get_mcp_config_by_name(name)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"MCP configuration '{name}' not found"
            )
        
        logger.info(f"Retrieved MCP config '{name}'")
        return MCPConfigResponse.from_mcp_config(config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP config '{name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve configuration: {str(e)}")


@router.get("/agents/{agent_name}/configs", response_model=MCPConfigListResponse)
async def get_agent_mcp_configs_endpoint(
    agent_name: str,
    enabled_only: bool = Query(True, description="Only return enabled configurations"),
    _: bool = Depends(verify_api_key)
):
    """Get all MCP configurations assigned to a specific agent.
    
    Args:
        agent_name: Name of the agent to get configurations for
        enabled_only: Whether to only return enabled configurations  
        api_key: API key for authentication
        
    Returns:
        List of MCP configurations assigned to the agent
    """
    try:
        configs = get_agent_mcp_configs(agent_name)
        
        # Apply enabled filter if requested
        if enabled_only:
            configs = [config for config in configs if config.is_enabled()]
        
        response_configs = [
            MCPConfigResponse.from_mcp_config(config) 
            for config in configs
        ]
        
        logger.info(f"Retrieved {len(response_configs)} MCP configs for agent '{agent_name}' (enabled_only={enabled_only})")
        
        return MCPConfigListResponse(
            configs=response_configs,
            total=len(response_configs),
            filtered_by_agent=agent_name
        )
        
    except Exception as e:
        logger.error(f"Failed to get MCP configs for agent '{agent_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent configurations: {str(e)}")


@router.delete("/configs/{name}", status_code=204)
async def delete_mcp_config_endpoint(
    name: str,
    _: bool = Depends(verify_api_key)
):
    """Delete an MCP configuration.
    
    Args:
        name: Name of the configuration to delete
        api_key: API key for authentication
        
    Returns:
        No content (204) on successful deletion
    """
    try:
        # Check if config exists
        existing_config = get_mcp_config_by_name(name)
        if not existing_config:
            raise HTTPException(
                status_code=404,
                detail=f"MCP configuration '{name}' not found"
            )
        
        # Delete the configuration
        success = delete_mcp_config_by_name(name)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete MCP configuration"
            )
        
        logger.info(f"Deleted MCP config '{name}'")
        
        # Trigger hot reload to remove the configuration from active servers
        await trigger_hot_reload()
        
        # Return 204 No Content (no response body)
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete MCP config '{name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {str(e)}")
