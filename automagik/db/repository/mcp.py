"""MCP configuration repository functions for database operations.

This module provides repository functions for the new simplified MCP configuration
system using the single mcp_configs table architecture (NMSTX-253 refactor).

Legacy two-table system (mcp_servers + agent_mcp_servers) has been removed.
"""

import json
import logging
from typing import List, Optional

from automagik.db.connection import execute_query
from automagik.db.models import MCPConfig, MCPConfigCreate, MCPConfigUpdate

# Configure logger
logger = logging.getLogger(__name__)


def get_mcp_config(config_id: str) -> Optional[MCPConfig]:
    """Get an MCP config by ID.
    
    Args:
        config_id: The config ID (UUID)
        
    Returns:
        MCPConfig object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM mcp_configs WHERE id = %s",
            (config_id,)
        )
        return MCPConfig.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting MCP config {config_id}: {str(e)}")
        return None


def get_mcp_config_by_name(name: str) -> Optional[MCPConfig]:
    """Get an MCP config by name.
    
    Args:
        name: The config name
        
    Returns:
        MCPConfig object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM mcp_configs WHERE name = %s",
            (name,)
        )
        return MCPConfig.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting MCP config by name {name}: {str(e)}")
        return None


def list_mcp_configs(enabled_only: bool = True, agent_name: Optional[str] = None) -> List[MCPConfig]:
    """List MCP configs.
    
    Args:
        enabled_only: Whether to only include enabled configs
        agent_name: Optional agent name to filter configs assigned to that agent
        
    Returns:
        List of MCPConfig objects
    """
    try:
        # Get all configs first, then filter in Python for SQLite compatibility
        query = "SELECT * FROM mcp_configs ORDER BY name ASC"
        result = execute_query(query, [])
        
        configs = []
        for row in result:
            try:
                config = MCPConfig.from_db_row(row)
                
                # Apply enabled filter
                if enabled_only and not config.is_enabled():
                    continue
                
                # Apply agent filter
                if agent_name and not config.is_assigned_to_agent(agent_name):
                    continue
                
                configs.append(config)
            except Exception as e:
                logger.warning(f"Skipping invalid config row: {str(e)}")
                continue
        
        return configs
    except Exception as e:
        logger.error(f"Error listing MCP configs: {str(e)}")
        return []


def create_mcp_config(config_data: MCPConfigCreate) -> Optional[str]:
    """Create a new MCP config.
    
    Args:
        config_data: The MCP config to create
        
    Returns:
        The created config ID if successful, None otherwise
    """
    try:
        # Check if config with this name already exists
        existing = get_mcp_config_by_name(config_data.name)
        if existing:
            logger.warning(f"MCP config with name {config_data.name} already exists")
            return None
        
        # Validate that the config has required fields
        if not config_data.config.get("server_type"):
            logger.error("MCP config must specify server_type")
            return None
        
        # Generate UUID for SQLite compatibility
        import uuid
        config_id = str(uuid.uuid4())
        
        # Serialize config as JSON
        config_json = json.dumps(config_data.config)
        
        # Insert the config (database agnostic)
        execute_query(
            "INSERT INTO mcp_configs (id, name, config, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())",
            (config_id, config_data.name, config_json),
            fetch=False
        )
        
        logger.info(f"Created MCP config {config_data.name} with ID {config_id}")
        return config_id
    except Exception as e:
        logger.error(f"Error creating MCP config {config_data.name}: {str(e)}")
        return None


def update_mcp_config(config_id: str, update_data: MCPConfigUpdate) -> bool:
    """Update an existing MCP config.
    
    Args:
        config_id: The config ID to update
        update_data: The update data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not update_data.config:
            logger.error("No config data provided for update")
            return False
        
        # Serialize config as JSON
        config_json = json.dumps(update_data.config)
        
        execute_query(
            "UPDATE mcp_configs SET config = %s, updated_at = NOW() WHERE id = %s",
            (config_json, config_id),
            fetch=False
        )
        
        logger.info(f"Updated MCP config with ID {config_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating MCP config {config_id}: {str(e)}")
        return False


def update_mcp_config_by_name(name: str, update_data: MCPConfigUpdate) -> bool:
    """Update an existing MCP config by name.
    
    Args:
        name: The config name to update
        update_data: The update data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not update_data.config:
            logger.error("No config data provided for update")
            return False
        
        # Serialize config as JSON
        config_json = json.dumps(update_data.config)
        
        execute_query(
            "UPDATE mcp_configs SET config = %s, updated_at = NOW() WHERE name = %s",
            (config_json, name),
            fetch=False
        )
        
        logger.info(f"Updated MCP config {name}")
        return True
    except Exception as e:
        logger.error(f"Error updating MCP config {name}: {str(e)}")
        return False


def delete_mcp_config(config_id: str) -> bool:
    """Delete an MCP config.
    
    Args:
        config_id: The config ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM mcp_configs WHERE id = %s",
            (config_id,),
            fetch=False
        )
        logger.info(f"Deleted MCP config with ID {config_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting MCP config {config_id}: {str(e)}")
        return False


def delete_mcp_config_by_name(name: str) -> bool:
    """Delete an MCP config by name.
    
    Args:
        name: The config name to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM mcp_configs WHERE name = %s",
            (name,),
            fetch=False
        )
        logger.info(f"Deleted MCP config {name}")
        return True
    except Exception as e:
        logger.error(f"Error deleting MCP config {name}: {str(e)}")
        return False


def get_agent_mcp_configs(agent_name: str) -> List[MCPConfig]:
    """Get all MCP configs assigned to a specific agent.
    
    Args:
        agent_name: The agent name
        
    Returns:
        List of MCPConfig objects assigned to the agent
    """
    try:
        # Get all enabled configs first, then filter in Python for SQLite compatibility
        result = execute_query(
            "SELECT * FROM mcp_configs ORDER BY name ASC",
            []
        )
        
        configs = []
        for row in result:
            try:
                config = MCPConfig.from_db_row(row)
                
                # Check if enabled and assigned to agent
                if config.is_enabled() and config.is_assigned_to_agent(agent_name):
                    configs.append(config)
            except Exception as e:
                logger.warning(f"Skipping invalid config row: {str(e)}")
                continue
        
        return configs
    except Exception as e:
        logger.error(f"Error getting MCP configs for agent {agent_name}: {str(e)}")
        return []


def get_configs_by_server_type(server_type: str) -> List[MCPConfig]:
    """Get all MCP configs of a specific server type.
    
    Args:
        server_type: The server type ('stdio' or 'http')
        
    Returns:
        List of MCPConfig objects
    """
    try:
        # Get all configs first, then filter in Python for SQLite compatibility
        result = execute_query(
            "SELECT * FROM mcp_configs ORDER BY name ASC",
            []
        )
        
        configs = []
        for row in result:
            try:
                config = MCPConfig.from_db_row(row)
                
                # Check if enabled and matches server type
                if config.is_enabled() and config.get_server_type() == server_type:
                    configs.append(config)
            except Exception as e:
                logger.warning(f"Skipping invalid config row: {str(e)}")
                continue
        
        return configs
    except Exception as e:
        logger.error(f"Error getting MCP configs by server type {server_type}: {str(e)}")
        return []