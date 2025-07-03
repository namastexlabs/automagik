"""Tool repository for database operations."""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from automagik.db.connection import execute_query
from automagik.db.models import ToolDB, ToolExecutionDB, ToolCreate, ToolUpdate

logger = logging.getLogger(__name__)


def list_tools(
    tool_type: Optional[str] = None,
    enabled_only: bool = True,
    categories: Optional[List[str]] = None,
    agent_name: Optional[str] = None
) -> List[ToolDB]:
    """List tools with optional filtering."""
    try:
        query = "SELECT * FROM tools WHERE 1=1"
        params = []
        
        if enabled_only:
            query += " AND enabled = %s"
            params.append(True)
            
        if tool_type:
            query += " AND type = %s"
            params.append(tool_type)
            
        if categories:
            # Filter by categories using JSON operations
            query += " AND categories::jsonb ?| %s"
            params.append(categories)
            
        if agent_name:
            # Check if agent is allowed (empty restrictions = all agents allowed)
            query += " AND (agent_restrictions = '[]'::jsonb OR agent_restrictions::jsonb ? %s)"
            params.append(agent_name)
            
        query += " ORDER BY name"
        
        results = execute_query(query, tuple(params))
        return [ToolDB.from_db_row(dict(row)) for row in results]
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        return []


def get_tool_by_name(name: str) -> Optional[ToolDB]:
    """Get tool by name."""
    try:
        result = execute_query(
            "SELECT * FROM tools WHERE name = %s",
            (name,)
        )
        return ToolDB.from_db_row(dict(result[0])) if result else None
    except Exception as e:
        logger.error(f"Error getting tool by name {name}: {str(e)}")
        return None


def get_tool_by_id(tool_id: uuid.UUID) -> Optional[ToolDB]:
    """Get tool by ID."""
    try:
        result = execute_query(
            "SELECT * FROM tools WHERE id = %s",
            (str(tool_id),)
        )
        return ToolDB.from_db_row(dict(result[0])) if result else None
    except Exception as e:
        logger.error(f"Error getting tool by ID {tool_id}: {str(e)}")
        return None


def create_tool(tool_data: ToolCreate) -> Optional[ToolDB]:
    """Create a new tool."""
    try:
        tool_id = uuid.uuid4()
        now = datetime.utcnow()
        
        execute_query(
            """
            INSERT INTO tools (
                id, name, type, description, module_path, function_name,
                mcp_server_name, mcp_tool_name, parameters_schema, capabilities,
                categories, enabled, agent_restrictions, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                str(tool_id),
                tool_data.name,
                tool_data.type,
                tool_data.description,
                tool_data.module_path,
                tool_data.function_name,
                tool_data.mcp_server_name,
                tool_data.mcp_tool_name,
                json.dumps(tool_data.parameters_schema) if tool_data.parameters_schema else None,
                json.dumps(tool_data.capabilities),
                json.dumps(tool_data.categories),
                tool_data.enabled,
                json.dumps(tool_data.agent_restrictions),
                now,
                now
            ),
            fetch=False
        )
        
        return get_tool_by_id(tool_id)
        
    except Exception as e:
        logger.error(f"Error creating tool: {str(e)}")
        return None


def update_tool(name: str, tool_data: ToolUpdate) -> Optional[ToolDB]:
    """Update an existing tool."""
    try:
        # Build dynamic update query
        set_clauses = []
        params = []
        
        if tool_data.description is not None:
            set_clauses.append("description = %s")
            params.append(tool_data.description)
            
        if tool_data.enabled is not None:
            set_clauses.append("enabled = %s")
            params.append(tool_data.enabled)
            
        if tool_data.parameters_schema is not None:
            set_clauses.append("parameters_schema = %s")
            params.append(json.dumps(tool_data.parameters_schema))
            
        if tool_data.capabilities is not None:
            set_clauses.append("capabilities = %s")
            params.append(json.dumps(tool_data.capabilities))
            
        if tool_data.categories is not None:
            set_clauses.append("categories = %s")
            params.append(json.dumps(tool_data.categories))
            
        if tool_data.agent_restrictions is not None:
            set_clauses.append("agent_restrictions = %s")
            params.append(json.dumps(tool_data.agent_restrictions))
        
        if not set_clauses:
            # No updates provided
            return get_tool_by_name(name)
            
        set_clauses.append("updated_at = %s")
        params.append(datetime.utcnow())
        params.append(name)
        
        query = f"""
            UPDATE tools 
            SET {', '.join(set_clauses)}
            WHERE name = %s
        """
        
        execute_query(query, tuple(params), fetch=False)
        return get_tool_by_name(name)
        
    except Exception as e:
        logger.error(f"Error updating tool {name}: {str(e)}")
        return None


def delete_tool(name: str) -> bool:
    """Delete a tool."""
    try:
        execute_query(
            "DELETE FROM tools WHERE name = %s",
            (name,),
            fetch=False
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting tool {name}: {str(e)}")
        return False


def get_tools_by_mcp_server(server_name: str) -> List[ToolDB]:
    """Get all tools for a specific MCP server."""
    try:
        results = execute_query(
            "SELECT * FROM tools WHERE mcp_server_name = %s ORDER BY name",
            (server_name,)
        )
        return [ToolDB.from_db_row(dict(row)) for row in results]
    except Exception as e:
        logger.error(f"Error getting tools for MCP server {server_name}: {str(e)}")
        return []


def get_tools_by_category(category: str) -> List[ToolDB]:
    """Get all tools in a specific category."""
    try:
        results = execute_query(
            "SELECT * FROM tools WHERE categories::jsonb ? %s ORDER BY name",
            (category,)
        )
        return [ToolDB.from_db_row(dict(row)) for row in results]
    except Exception as e:
        logger.error(f"Error getting tools for category {category}: {str(e)}")
        return []


def log_tool_execution(
    tool_id: uuid.UUID,
    agent_name: Optional[str],
    session_id: Optional[str],
    parameters: Optional[Dict[str, Any]],
    context: Optional[Dict[str, Any]],
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> bool:
    """Log tool execution for metrics."""
    try:
        execute_query(
            """
            INSERT INTO tool_executions (
                tool_id, agent_name, session_id, parameters, context,
                status, result, error_message, execution_time_ms, executed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(tool_id),
                agent_name,
                session_id,
                json.dumps(parameters) if parameters else None,
                json.dumps(context) if context else None,
                status,
                json.dumps(result) if result else None,
                error_message,
                execution_time_ms,
                datetime.utcnow()
            ),
            fetch=False
        )
        
        # Update tool execution statistics
        execute_query(
            """
            UPDATE tools 
            SET 
                execution_count = execution_count + 1,
                last_executed_at = %s,
                average_execution_time_ms = CASE 
                    WHEN execution_count = 0 THEN COALESCE(%s, 0)
                    ELSE (average_execution_time_ms * execution_count + COALESCE(%s, 0)) / (execution_count + 1)
                END
            WHERE id = %s
            """,
            (datetime.utcnow(), execution_time_ms, execution_time_ms, str(tool_id)),
            fetch=False
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error logging tool execution: {str(e)}")
        return False


def get_tool_execution_stats(tool_id: uuid.UUID, days: int = 30) -> Dict[str, Any]:
    """Get execution statistics for a tool."""
    try:
        # Import here to avoid circular imports
        from ..providers.factory import get_database_type
        
        # Use database-specific date functions
        db_type = get_database_type()
        if db_type == "postgresql":
            date_condition = "executed_at >= NOW() - INTERVAL '%s days'"
            query_params = (str(tool_id), days)
        else:  # SQLite
            date_condition = "executed_at >= datetime('now', '-%s days')"
            query_params = (str(tool_id), days)
        
        results = execute_query(
            f"""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_executions,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_executions,
                AVG(execution_time_ms) as avg_execution_time,
                MAX(execution_time_ms) as max_execution_time,
                MIN(execution_time_ms) as min_execution_time
            FROM tool_executions 
            WHERE tool_id = ? 
            AND {date_condition}
            """,
            query_params
        )
        
        if results:
            row = dict(results[0])
            return {
                "total_executions": row.get("total_executions", 0),
                "successful_executions": row.get("successful_executions", 0),
                "failed_executions": row.get("failed_executions", 0),
                "success_rate": (
                    row.get("successful_executions", 0) / max(row.get("total_executions", 1), 1)
                ) * 100,
                "avg_execution_time_ms": float(row.get("avg_execution_time", 0) or 0),
                "max_execution_time_ms": row.get("max_execution_time", 0),
                "min_execution_time_ms": row.get("min_execution_time", 0)
            }
        
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "success_rate": 0.0,
            "avg_execution_time_ms": 0.0,
            "max_execution_time_ms": 0,
            "min_execution_time_ms": 0
        }
        
    except Exception as e:
        logger.error(f"Error getting tool execution stats: {str(e)}")
        return {}


def get_tool_categories() -> List[str]:
    """Get all unique tool categories."""
    try:
        # SQLite-compatible version - get all categories and parse JSON in Python
        results = execute_query(
            """
            SELECT DISTINCT categories
            FROM tools 
            WHERE categories IS NOT NULL AND categories != '[]'
            """
        )
        
        categories = set()
        for row in results:
            # execute_query returns dictionaries, so access by column name
            categories_json = row.get('categories')
            if categories_json and categories_json != '[]':
                try:
                    parsed_categories = json.loads(categories_json)
                    if isinstance(parsed_categories, list):
                        categories.update(parsed_categories)
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return sorted(list(categories))
    except Exception as e:
        logger.error(f"Error getting tool categories: {str(e)}")
        return []