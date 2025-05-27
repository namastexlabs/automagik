"""MCP server repository functions for database operations."""

import json
import logging
from typing import List, Optional

from src.db.connection import execute_query
from src.db.models import MCPServerDB, AgentMCPServerDB

# Configure logger
logger = logging.getLogger(__name__)


def get_mcp_server(server_id: int) -> Optional[MCPServerDB]:
    """Get an MCP server by ID.
    
    Args:
        server_id: The server ID
        
    Returns:
        MCPServerDB object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM mcp_servers WHERE id = %s",
            (server_id,)
        )
        return MCPServerDB.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting MCP server {server_id}: {str(e)}")
        return None


def get_mcp_server_by_name(name: str) -> Optional[MCPServerDB]:
    """Get an MCP server by name.
    
    Args:
        name: The server name
        
    Returns:
        MCPServerDB object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM mcp_servers WHERE name = %s",
            (name,)
        )
        return MCPServerDB.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting MCP server by name {name}: {str(e)}")
        return None


def list_mcp_servers(enabled_only: bool = True, status_filter: Optional[str] = None) -> List[MCPServerDB]:
    """List MCP servers.
    
    Args:
        enabled_only: Whether to only include enabled servers
        status_filter: Optional status to filter by
        
    Returns:
        List of MCPServerDB objects
    """
    try:
        query = "SELECT * FROM mcp_servers"
        params = []
        conditions = []
        
        if enabled_only:
            conditions.append("enabled = TRUE")
        
        if status_filter:
            conditions.append("status = %s")
            params.append(status_filter)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY priority DESC, name ASC"
        
        result = execute_query(query, params)
        return [MCPServerDB.from_db_row(row) for row in result]
    except Exception as e:
        logger.error(f"Error listing MCP servers: {str(e)}")
        return []


def create_mcp_server(server: MCPServerDB) -> Optional[int]:
    """Create a new MCP server.
    
    Args:
        server: The MCP server to create
        
    Returns:
        The created server ID if successful, None otherwise
    """
    try:
        # Check if server with this name already exists
        existing = get_mcp_server_by_name(server.name)
        if existing:
            logger.warning(f"MCP server with name {server.name} already exists")
            return None
        
        # Serialize JSON fields
        command_json = json.dumps(server.command) if server.command else None
        env_json = json.dumps(server.env) if server.env else '{}'
        tags_json = json.dumps(server.tags) if server.tags else '[]'
        tools_json = json.dumps(server.tools_discovered) if server.tools_discovered else '[]'
        resources_json = json.dumps(server.resources_discovered) if server.resources_discovered else '[]'
        
        # Insert the server
        result = execute_query(
            """
            INSERT INTO mcp_servers (
                name, server_type, description, command, env, http_url,
                auto_start, max_retries, timeout_seconds, tags, priority,
                status, enabled, tools_discovered, resources_discovered,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW(), NOW()
            ) RETURNING id
            """,
            (
                server.name,
                server.server_type,
                server.description,
                command_json,
                env_json,
                server.http_url,
                server.auto_start,
                server.max_retries,
                server.timeout_seconds,
                tags_json,
                server.priority,
                server.status,
                server.enabled,
                tools_json,
                resources_json
            )
        )
        
        server_id = result[0]["id"] if result else None
        logger.info(f"Created MCP server {server.name} with ID {server_id}")
        return server_id
    except Exception as e:
        logger.error(f"Error creating MCP server {server.name}: {str(e)}")
        return None


def update_mcp_server(server: MCPServerDB) -> bool:
    """Update an existing MCP server.
    
    Args:
        server: The MCP server to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not server.id:
            logger.error("Cannot update MCP server without ID")
            return False
        
        # Serialize JSON fields
        command_json = json.dumps(server.command) if server.command else None
        env_json = json.dumps(server.env) if server.env else '{}'
        tags_json = json.dumps(server.tags) if server.tags else '[]'
        tools_json = json.dumps(server.tools_discovered) if server.tools_discovered else '[]'
        resources_json = json.dumps(server.resources_discovered) if server.resources_discovered else '[]'
        
        execute_query(
            """
            UPDATE mcp_servers SET 
                name = %s,
                server_type = %s,
                description = %s,
                command = %s,
                env = %s,
                http_url = %s,
                auto_start = %s,
                max_retries = %s,
                timeout_seconds = %s,
                tags = %s,
                priority = %s,
                status = %s,
                enabled = %s,
                tools_discovered = %s,
                resources_discovered = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                server.name,
                server.server_type,
                server.description,
                command_json,
                env_json,
                server.http_url,
                server.auto_start,
                server.max_retries,
                server.timeout_seconds,
                tags_json,
                server.priority,
                server.status,
                server.enabled,
                tools_json,
                resources_json,
                server.id
            ),
            fetch=False
        )
        
        logger.info(f"Updated MCP server {server.name} with ID {server.id}")
        return True
    except Exception as e:
        logger.error(f"Error updating MCP server {server.name}: {str(e)}")
        return False


def update_mcp_server_status(server_id: int, status: str, error_message: Optional[str] = None) -> bool:
    """Update MCP server status and error information.
    
    Args:
        server_id: The server ID
        status: New status
        error_message: Optional error message
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if status == "running":
            # Clear error info when status is running
            execute_query(
                """
                UPDATE mcp_servers SET 
                    status = %s,
                    started_at = CASE WHEN status != 'running' THEN NOW() ELSE started_at END,
                    last_error = NULL,
                    last_ping = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, server_id),
                fetch=False
            )
        elif status == "error":
            # Increment error count and set error message
            execute_query(
                """
                UPDATE mcp_servers SET 
                    status = %s,
                    last_error = %s,
                    error_count = error_count + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, error_message, server_id),
                fetch=False
            )
        elif status == "stopped":
            # Set stopped timestamp
            execute_query(
                """
                UPDATE mcp_servers SET 
                    status = %s,
                    last_stopped = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, server_id),
                fetch=False
            )
        else:
            # General status update
            execute_query(
                """
                UPDATE mcp_servers SET 
                    status = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, server_id),
                fetch=False
            )
        
        logger.info(f"Updated MCP server {server_id} status to {status}")
        return True
    except Exception as e:
        logger.error(f"Error updating MCP server {server_id} status: {str(e)}")
        return False


def update_mcp_server_discovery(server_id: int, tools: List[str], resources: List[str]) -> bool:
    """Update MCP server discovery results.
    
    Args:
        server_id: The server ID
        tools: List of discovered tool names
        resources: List of discovered resource URIs
        
    Returns:
        True if successful, False otherwise
    """
    try:
        tools_json = json.dumps(tools)
        resources_json = json.dumps(resources)
        
        execute_query(
            """
            UPDATE mcp_servers SET 
                tools_discovered = %s,
                resources_discovered = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (tools_json, resources_json, server_id),
            fetch=False
        )
        
        logger.info(f"Updated discovery results for MCP server {server_id}: {len(tools)} tools, {len(resources)} resources")
        return True
    except Exception as e:
        logger.error(f"Error updating discovery results for MCP server {server_id}: {str(e)}")
        return False


def increment_connection_attempts(server_id: int) -> bool:
    """Increment the connection attempts counter for a server.
    
    Args:
        server_id: The server ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            """
            UPDATE mcp_servers SET 
                connection_attempts = connection_attempts + 1,
                updated_at = NOW()
            WHERE id = %s
            """,
            (server_id,),
            fetch=False
        )
        return True
    except Exception as e:
        logger.error(f"Error incrementing connection attempts for server {server_id}: {str(e)}")
        return False


def delete_mcp_server(server_id: int) -> bool:
    """Delete an MCP server and all its agent assignments.
    
    Args:
        server_id: The server ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Delete agent assignments first (handled by CASCADE)
        execute_query(
            "DELETE FROM mcp_servers WHERE id = %s",
            (server_id,),
            fetch=False
        )
        logger.info(f"Deleted MCP server with ID {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting MCP server {server_id}: {str(e)}")
        return False


# Agent-Server Assignment Functions

def assign_agent_to_server(agent_id: int, server_id: int) -> bool:
    """Assign an agent to an MCP server.
    
    Args:
        agent_id: The agent ID
        server_id: The server ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if assignment already exists
        existing = execute_query(
            "SELECT id FROM agent_mcp_servers WHERE agent_id = %s AND mcp_server_id = %s",
            (agent_id, server_id)
        )
        
        if existing:
            logger.info(f"Agent {agent_id} already assigned to MCP server {server_id}")
            return True
        
        # Create new assignment
        execute_query(
            """
            INSERT INTO agent_mcp_servers (agent_id, mcp_server_id, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            """,
            (agent_id, server_id),
            fetch=False
        )
        
        logger.info(f"Assigned agent {agent_id} to MCP server {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error assigning agent {agent_id} to MCP server {server_id}: {str(e)}")
        return False


def remove_agent_from_server(agent_id: int, server_id: int) -> bool:
    """Remove an agent's assignment from an MCP server.
    
    Args:
        agent_id: The agent ID
        server_id: The server ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM agent_mcp_servers WHERE agent_id = %s AND mcp_server_id = %s",
            (agent_id, server_id),
            fetch=False
        )
        logger.info(f"Removed agent {agent_id} assignment from MCP server {server_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing agent {agent_id} from MCP server {server_id}: {str(e)}")
        return False


def get_agent_servers(agent_id: int) -> List[MCPServerDB]:
    """Get all MCP servers assigned to an agent.
    
    Args:
        agent_id: The agent ID
        
    Returns:
        List of MCPServerDB objects assigned to the agent
    """
    try:
        result = execute_query(
            """
            SELECT s.* FROM mcp_servers s
            JOIN agent_mcp_servers ams ON s.id = ams.mcp_server_id
            WHERE ams.agent_id = %s AND s.enabled = TRUE
            ORDER BY s.priority DESC, s.name ASC
            """,
            (agent_id,)
        )
        return [MCPServerDB.from_db_row(row) for row in result]
    except Exception as e:
        logger.error(f"Error getting servers for agent {agent_id}: {str(e)}")
        return []


def get_server_agents(server_id: int) -> List[int]:
    """Get all agent IDs assigned to an MCP server.
    
    Args:
        server_id: The server ID
        
    Returns:
        List of agent IDs assigned to the server
    """
    try:
        result = execute_query(
            "SELECT agent_id FROM agent_mcp_servers WHERE mcp_server_id = %s",
            (server_id,)
        )
        return [row["agent_id"] for row in result]
    except Exception as e:
        logger.error(f"Error getting agents for server {server_id}: {str(e)}")
        return []


def get_agent_server_assignments(agent_id: Optional[int] = None, server_id: Optional[int] = None) -> List[AgentMCPServerDB]:
    """Get agent-server assignments with optional filtering.
    
    Args:
        agent_id: Optional agent ID to filter by
        server_id: Optional server ID to filter by
        
    Returns:
        List of AgentMCPServerDB objects
    """
    try:
        query = "SELECT * FROM agent_mcp_servers"
        params = []
        conditions = []
        
        if agent_id is not None:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        
        if server_id is not None:
            conditions.append("mcp_server_id = %s")
            params.append(server_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        result = execute_query(query, params)
        return [AgentMCPServerDB.from_db_row(row) for row in result]
    except Exception as e:
        logger.error(f"Error getting agent-server assignments: {str(e)}")
        return []