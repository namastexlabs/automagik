"""Session repository functions for database operations."""

import uuid
import json
import logging
from typing import List, Optional, Union, Tuple

from automagik.db.connection import execute_query
from automagik.db.models import Session

# Configure logger
logger = logging.getLogger(__name__)


def get_session(session_id: uuid.UUID) -> Optional[Session]:
    """Get a session by ID.
    
    Args:
        session_id: The session ID
        
    Returns:
        Session object if found, None otherwise
    """
    try:
        query = """
            SELECT
                s.*,
                a.name AS agent_name
            FROM
                sessions s
            LEFT JOIN
                agents a ON s.agent_id = a.id
            WHERE
                s.id = %s
        """
        result = execute_query(
            query,
            (str(session_id),)
        )
        return Session.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        return None


def get_session_by_name(name: str) -> Optional[Session]:
    """Get a session by name.
    
    Args:
        name: The session name
        
    Returns:
        Session object if found, None otherwise
    """
    try:
        query = """
            SELECT
                s.*,
                a.name AS agent_name
            FROM
                sessions s
            LEFT JOIN
                agents a ON s.agent_id = a.id
            WHERE
                s.name = %s
        """
        result = execute_query(
            query,
            (name,)
        )
        return Session.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting session by name {name}: {str(e)}")
        return None


def list_sessions(
    user_id: Optional[uuid.UUID] = None, 
    agent_id: Optional[int] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_desc: bool = True
) -> Union[List[Session], Tuple[List[Session], int]]:
    """List sessions with optional filtering and pagination.
    
    Args:
        user_id: Filter by user ID (UUID)
        agent_id: Filter by agent ID
        page: Page number (1-based, optional)
        page_size: Number of items per page (optional)
        sort_desc: Sort by most recent first if True
        
    Returns:
        If pagination is requested (page and page_size provided):
            Tuple of (list of Session objects, total count)
        Otherwise:
            List of Session objects
    """
    try:
        count_query = "SELECT COUNT(*) as count FROM sessions s"
        
        # Modified query to include message count and agent_name
        query = """
            SELECT
                s.*,
                a.name AS agent_name,
                COUNT(m.id) as message_count 
            FROM
                sessions s
            LEFT JOIN
                agents a ON s.agent_id = a.id
            LEFT JOIN
                messages m ON s.id = m.session_id
        """
        
        params = []
        conditions = []
        
        if user_id is not None:
            conditions.append("s.user_id = %s")
            params.append(str(user_id) if isinstance(user_id, uuid.UUID) else user_id)
        
        if agent_id is not None:
            conditions.append("s.agent_id = %s")
            params.append(agent_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            count_query += " WHERE " + " AND ".join(conditions)
        
        # Need to group by all selected columns from sessions table and agent_name
        # Assuming s.id is the primary key of sessions table.
        # For portability, listing all s.* columns explicitly in GROUP BY or ensuring functional dependency is key.
        # Most modern SQL DBs (like PostgreSQL) are fine with GROUP BY s.id, a.name if s.id is PK.
        # For broader compatibility, we might list all s columns, but let's try with s.id, a.name first for conciseness.
        # All columns from s are functionally dependent on s.id. So, s.id and a.name should be sufficient.
        query += " GROUP BY s.id, a.name" # Added a.name to GROUP BY
        
        # Add sorting
        sort_direction = "DESC" if sort_desc else "ASC"
        query += f" ORDER BY s.updated_at {sort_direction}, s.created_at {sort_direction}"
        
        # Get total count for pagination
        count_result = execute_query(count_query, tuple(params) if params else None)
        total_count = count_result[0]['count'] if count_result else 0
        
        # Add pagination if requested
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query += " LIMIT %s OFFSET %s"
            params.append(page_size)
            params.append(offset)
        
        result = execute_query(query, tuple(params) if params else None)
        
        # Create Session objects with message_count
        sessions = []
        for row in result:
            # Create Session object from the main session fields
            session = Session.from_db_row({k: v for k, v in row.items() if k != 'message_count'})
            
            # Attach message_count as an attribute
            session.message_count = row.get('message_count', 0)
            
            sessions.append(session)
        
        # Return with count for pagination or just the list
        if page is not None and page_size is not None:
            return sessions, total_count
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        if page is not None and page_size is not None:
            return [], 0
        return []


def create_session(session: Session) -> Optional[uuid.UUID]:
    """Create a new session.
    
    Args:
        session: The session to create
        
    Returns:
        The created session ID if successful, None otherwise
    """
    try:
        # Check if a session with this name already exists
        if session.name:
            existing = get_session_by_name(session.name)
            if existing:
                # Update existing session
                session.id = existing.id
                return update_session(session)
        
        # Ensure session has an ID
        if session.id is None:
            session.id = uuid.uuid4()
            logger.info(f"Generated new UUID for session: {session.id}")
        
        # Prepare session data
        metadata_json = json.dumps(session.metadata) if session.metadata else None
        
        # Use provided ID or let the database generate one
        session_id_param = str(session.id) if session.id else None
        
        # Insert the session
        result = execute_query(
            """
            INSERT INTO sessions (
                id, user_id, agent_id, name, platform,
                metadata, created_at, updated_at, run_finished_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, NOW(), NOW(), %s
            ) RETURNING id
            """,
            (
                session_id_param,
                session.user_id,
                session.agent_id,
                session.name,
                session.platform,
                metadata_json,
                session.run_finished_at
            )
        )
        
        session_id = uuid.UUID(result[0]["id"]) if result else None
        logger.info(f"Created session with ID {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return None


def update_session(session: Session) -> Optional[uuid.UUID]:
    """Update an existing session.
    
    Args:
        session: The session to update
        
    Returns:
        The updated session ID if successful, None otherwise
    """
    try:
        if not session.id:
            if session.name:
                existing = get_session_by_name(session.name)
                if existing:
                    session.id = existing.id
                else:
                    return create_session(session)
            else:
                return create_session(session)
        
        metadata_json = json.dumps(session.metadata) if session.metadata else None
        
        execute_query(
            """
            UPDATE sessions SET 
                user_id = %s,
                agent_id = %s,
                name = %s,
                platform = %s,
                metadata = %s,
                updated_at = NOW(),
                run_finished_at = %s
            WHERE id = %s
            """,
            (
                session.user_id,
                session.agent_id,
                session.name,
                session.platform,
                metadata_json,
                session.run_finished_at,
                str(session.id)
            ),
            fetch=False
        )
        
        logger.info(f"Updated session with ID {session.id}")
        return session.id
    except Exception as e:
        logger.error(f"Error updating session {session.id}: {str(e)}")
        return None


def delete_session(session_id: uuid.UUID) -> bool:
    """Delete a session.
    
    Args:
        session_id: The session ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM sessions WHERE id = %s",
            (str(session_id),),
            fetch=False
        )
        logger.info(f"Deleted session with ID {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        return False


def finish_session(session_id: uuid.UUID) -> bool:
    """Mark a session as finished.
    
    Args:
        session_id: The session ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "UPDATE sessions SET run_finished_at = NOW(), updated_at = NOW() WHERE id = %s",
            (str(session_id),),
            fetch=False
        )
        logger.info(f"Marked session {session_id} as finished")
        return True
    except Exception as e:
        logger.error(f"Error finishing session {session_id}: {str(e)}")
        return False


def get_system_prompt(session_id: uuid.UUID) -> Optional[str]:
    """Get the system prompt for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The system prompt if found, None otherwise
    """
    try:
        # First check if system prompt is stored in session metadata
        session_result = execute_query(
            """
            SELECT metadata FROM sessions 
            WHERE id = %s
            """,
            (str(session_id),)
        )
        
        if session_result and session_result[0]["metadata"]:
            metadata = session_result[0]["metadata"]
            
            # Log metadata format for debugging
            logger.debug(f"Session metadata type: {type(metadata)}")
            
            if isinstance(metadata, dict) and "system_prompt" in metadata:
                system_prompt = metadata["system_prompt"]
                logger.debug(f"Found system prompt in session metadata (dict): {system_prompt[:50]}...")
                return system_prompt
            elif isinstance(metadata, str):
                try:
                    metadata_dict = json.loads(metadata)
                    if "system_prompt" in metadata_dict:
                        system_prompt = metadata_dict["system_prompt"]
                        logger.debug(f"Found system prompt in session metadata (string->dict): {system_prompt[:50]}...")
                        return system_prompt
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse session metadata as JSON: {metadata[:100]}...")
                    # Continue to fallback
            
            # If we got here but couldn't find a system prompt, log the metadata for debugging
            logger.debug(f"No system_prompt found in metadata: {str(metadata)[:100]}...")
        
        # Fallback: look for a system role message
        logger.debug("Falling back to system role message search")
        result = execute_query(
            """
            SELECT text_content FROM messages 
            WHERE session_id = %s AND role = 'system'
            ORDER BY created_at DESC, updated_at DESC
            LIMIT 1
            """,
            (str(session_id),)
        )
        
        if result and result[0]["text_content"]:
            system_prompt = result[0]["text_content"]
            logger.debug(f"Found system prompt in system role message: {system_prompt[:50]}...")
            return system_prompt
        
        logger.warning(f"No system prompt found for session {session_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting system prompt for session {session_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def update_session_name_if_empty(session_id: uuid.UUID, new_name: str) -> bool:
    """Updates a session's name only if it's currently empty or None.
    
    Args:
        session_id: Session ID
        new_name: New session name to set if current name is empty
        
    Returns:
        True if update was performed, False if not needed or failed
    """
    try:
        # Get current session
        session = get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False
            
        # Check if name is empty or None
        if not session.name:
            # Update the session name
            session.name = new_name
            updated_id = update_session(session)
            if updated_id:
                logger.info(f"Updated session {session_id} name to '{new_name}'")
                return True
            else:
                logger.error(f"Failed to update session {session_id} name")
                return False
            
        # No update needed
        logger.debug(f"Session {session_id} already has name '{session.name}', no update needed")
        return False
    except Exception as e:
        logger.error(f"Error updating session name: {str(e)}")
        return False


# Session branching functions
def create_branch_session(
    parent_session_id: uuid.UUID,
    branch_point_message_id: uuid.UUID,
    branch_name: Optional[str] = None,
    branch_type: str = "edit_branch"
) -> Optional[uuid.UUID]:
    """Create a new session as a branch from an existing session.
    
    Args:
        parent_session_id: The ID of the parent session
        branch_point_message_id: The message where the branch starts
        branch_name: Optional name for the branch session
        branch_type: Type of branch ('edit_branch' or 'manual_branch')
        
    Returns:
        The new session ID if successful, None otherwise
    """
    try:
        # Get the parent session to copy basic info
        parent_session = get_session(parent_session_id)
        if not parent_session:
            logger.error(f"Parent session {parent_session_id} not found")
            return None
        
        # Generate new session ID
        new_session_id = uuid.uuid4()
        
        # Generate branch name if not provided
        if not branch_name:
            branch_name = f"{parent_session.name or 'Session'} - Branch"
        
        # Insert the new branch session
        result = execute_query(
            """
            INSERT INTO sessions (
                id, user_id, agent_id, name, platform, metadata,
                parent_session_id, branch_point_message_id, branch_type, is_main_branch,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW(), NOW()
            ) RETURNING id
            """,
            (
                str(new_session_id),
                parent_session.user_id,
                parent_session.agent_id,
                branch_name,
                parent_session.platform,
                json.dumps(parent_session.metadata) if parent_session.metadata else None,
                str(parent_session_id),
                str(branch_point_message_id),
                branch_type,
                False  # is_main_branch
            )
        )
        
        if result:
            session_id = uuid.UUID(result[0]["id"])
            logger.info(f"Created branch session {session_id} from parent {parent_session_id}")
            return session_id
        else:
            logger.error("Failed to create branch session - no result returned")
            return None
            
    except Exception as e:
        logger.error(f"Error creating branch session: {str(e)}")
        return None


def copy_messages_to_branch(
    parent_session_id: uuid.UUID,
    branch_session_id: uuid.UUID,
    branch_point_message_id: uuid.UUID
) -> bool:
    """Copy messages from parent session to branch session up to the branch point.
    
    Args:
        parent_session_id: The parent session ID
        branch_session_id: The new branch session ID
        branch_point_message_id: The message where the branch starts
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Copy messages created before or at the branch point
        execute_query(
            """
            INSERT INTO messages (
                id, session_id, user_id, agent_id, role, text_content,
                media_url, mime_type, message_type, raw_payload, channel_payload,
                tool_calls, tool_outputs, system_prompt, user_feedback, flagged,
                context, usage, created_at, updated_at
            )
            SELECT 
                uuid_generate_v4(), %s, user_id, agent_id, role, text_content,
                media_url, mime_type, message_type, raw_payload, channel_payload,
                tool_calls, tool_outputs, system_prompt, user_feedback, flagged,
                context, usage, created_at, updated_at
            FROM messages 
            WHERE session_id = %s 
            AND created_at <= (
                SELECT created_at FROM messages WHERE id = %s
            )
            ORDER BY created_at ASC
            """,
            (str(branch_session_id), str(parent_session_id), str(branch_point_message_id)),
            fetch=False
        )
        
        logger.info(f"Copied messages to branch session {branch_session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error copying messages to branch: {str(e)}")
        return False


def get_session_branches(session_id: uuid.UUID) -> List[Session]:
    """Get all branch sessions for a given session.
    
    Args:
        session_id: The session ID (main or branch)
        
    Returns:
        List of branch sessions
    """
    try:
        # First find the root session
        root_session_query = """
            WITH RECURSIVE find_root AS (
                SELECT id, parent_session_id, 0 as level
                FROM sessions 
                WHERE id = %s
                
                UNION ALL
                
                SELECT s.id, s.parent_session_id, fr.level + 1
                FROM sessions s
                INNER JOIN find_root fr ON s.id = fr.parent_session_id
                WHERE fr.level < 10  -- Prevent infinite recursion
            )
            SELECT id FROM find_root WHERE parent_session_id IS NULL LIMIT 1
        """
        
        root_result = execute_query(root_session_query, (str(session_id),))
        if not root_result:
            logger.warning(f"Could not find root session for {session_id}")
            return []
        
        root_session_id = root_result[0]["id"]
        
        # Get all branches from the root (exclude the root itself)
        query = """
            WITH RECURSIVE session_branches AS (
                SELECT 
                    s.id, s.user_id, s.agent_id, s.name, s.platform, s.metadata,
                    s.created_at, s.updated_at, s.run_finished_at, s.message_count,
                    s.parent_session_id, s.branch_point_message_id, s.branch_type, s.is_main_branch,
                    a.name AS agent_name,
                    0 as depth
                FROM sessions s
                LEFT JOIN agents a ON s.agent_id = a.id
                WHERE s.id = %s
                
                UNION ALL
                
                SELECT 
                    s.id, s.user_id, s.agent_id, s.name, s.platform, s.metadata,
                    s.created_at, s.updated_at, s.run_finished_at, s.message_count,
                    s.parent_session_id, s.branch_point_message_id, s.branch_type, s.is_main_branch,
                    a.name AS agent_name,
                    sb.depth + 1
                FROM sessions s
                LEFT JOIN agents a ON s.agent_id = a.id
                INNER JOIN session_branches sb ON s.parent_session_id = sb.id
                WHERE sb.depth < 10  -- Prevent infinite recursion
            )
            SELECT * FROM session_branches
            WHERE depth > 0
            ORDER BY created_at ASC
        """
        
        result = execute_query(query, (root_session_id,))
        
        branches = []
        for row in result:
            session = Session.from_db_row(row)
            branches.append(session)
        
        logger.info(f"Found {len(branches)} branches for session {session_id}")
        return branches
        
    except Exception as e:
        logger.error(f"Error getting session branches: {str(e)}")
        return []


def get_session_branch_tree(session_id: uuid.UUID) -> Optional[Session]:
    """Get the complete branch tree for a session as a hierarchical structure.
    
    Args:
        session_id: The session ID (main or branch)
        
    Returns:
        Root session with branch hierarchy, None if not found
    """
    try:
        # First find the root session
        root_query = """
            WITH RECURSIVE find_root AS (
                SELECT id, parent_session_id, 0 as level
                FROM sessions 
                WHERE id = %s
                
                UNION ALL
                
                SELECT s.id, s.parent_session_id, fr.level + 1
                FROM sessions s
                INNER JOIN find_root fr ON s.id = fr.parent_session_id
                WHERE fr.level < 10  -- Prevent infinite recursion
            )
            SELECT id FROM find_root WHERE parent_session_id IS NULL LIMIT 1
        """
        
        root_result = execute_query(root_query, (str(session_id),))
        if not root_result:
            logger.warning(f"Could not find root session for {session_id}")
            return None
        
        root_session_id = root_result[0]["id"]
        
        # Get the root session details using raw query
        session_query = """
            SELECT s.*, a.name as agent_name
            FROM sessions s
            LEFT JOIN agents a ON s.agent_id = a.id
            WHERE s.id = %s
        """
        
        session_result = execute_query(session_query, (root_session_id,))
        if not session_result:
            logger.warning(f"Root session {root_session_id} not found")
            return None
        
        root_session = Session.from_db_row(session_result[0])
        
        logger.info(f"Built session tree with root session {root_session_id}")
        return root_session
        
    except Exception as e:
        logger.error(f"Error getting session branch tree: {str(e)}")
        return None
