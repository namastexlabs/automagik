import logging
import math
from fastapi import HTTPException
from src.db import list_sessions, get_session as db_get_session, get_session_by_name
from src.db.connection import safe_uuid
from src.memory.message_history import MessageHistory
from src.api.models import SessionResponse, SessionListResponse, SessionInfo, MessageModel, DeleteSessionResponse
from typing import List, Optional, Dict, Any
import uuid

# Get our module's logger
logger = logging.getLogger(__name__)

async def get_sessions(page: int, page_size: int, sort_desc: bool) -> SessionListResponse:
    """
    Get a paginated list of sessions
    """
    try:
        sessions, total_count = list_sessions(
            page=page, 
            page_size=page_size, 
            sort_desc=sort_desc
        )
        
        # Convert Session objects to SessionInfo objects
        session_infos = []
        for session in sessions:
            session_infos.append(SessionInfo(
                session_id=str(session.id),
                session_name=session.name,
                created_at=session.created_at,
                last_updated=session.updated_at,
                message_count=session.message_count,  # Use the actual message count from the session
                user_id=session.user_id,
                agent_id=session.agent_id,
                agent_name=session.agent_name
            ))
        
        return SessionListResponse(
            sessions=session_infos,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

async def get_session(session_id_or_name: str, page: int, page_size: int, sort_desc: bool, hide_tools: bool) -> Dict[str, Any]:
    """
    Get a session by ID or name with its message history
    """
    try:
        # Check if we're dealing with a UUID or a name
        session_id = None
        session = None
        
        # First try to get session by name regardless of UUID format
        session = get_session_by_name(session_id_or_name)
        if session:
            session_id = str(session.id)
            logger.info(f"Found session with name '{session_id_or_name}', id: {session_id}")
        # If not found by name, try as UUID if it looks like one
        elif safe_uuid(session_id_or_name):
            try:
                session = db_get_session(uuid.UUID(session_id_or_name))
                if session:
                    session_id = str(session.id)
                    logger.info(f"Found session with id: {session_id}")
            except ValueError as e:
                logger.error(f"Error parsing session identifier as UUID: {str(e)}")
        
        if not session_id:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id_or_name}")
        
        # Create message history with the session_id
        message_history = MessageHistory(session_id=session_id)
        
        # Get session info
        session_info = {
            "id": str(session.id),
            "name": session.name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "user_id": session.user_id,
            "agent_id": session.agent_id,
            "agent_name": getattr(session, 'agent_name', None),
            "session_origin": getattr(session, 'platform', None)
        }
        
        # Get messages with pagination
        messages, total_count = message_history.get_messages(
            page=page, 
            page_size=page_size, 
            sort_desc=sort_desc
        )
        
        # If hide_tools is True, filter out tool calls and outputs from the messages
        if hide_tools:
            for message in messages:
                if "tool_calls" in message:
                    del message["tool_calls"]
                if "tool_outputs" in message:
                    del message["tool_outputs"]
        
        # Create response as a dictionary that can be converted to SessionResponse
        return {
            "session": SessionInfo(
                session_id=session_info["id"],
                session_name=session_info["name"],
                created_at=session_info["created_at"],
                last_updated=session_info["updated_at"],
                message_count=total_count,
                user_id=session_info.get("user_id"),
                agent_id=session_info.get("agent_id"),
                agent_name=session_info.get("agent_name"),
                session_origin=session_info.get("session_origin")
            ),
            "messages": messages,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total_count / page_size) if page_size > 0 else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

async def delete_session(session_id_or_name: str) -> bool:
    """
    Delete a session by ID or name
    """
    try:
        # Check if we're dealing with a UUID or a name
        session_id = None
        session = None
        
        # First try to get session by name regardless of UUID format
        session = get_session_by_name(session_id_or_name)
        if session:
            session_id = str(session.id)
            logger.info(f"Found session with name '{session_id_or_name}', id: {session_id}")
        # If not found by name, try as UUID if it looks like one
        elif safe_uuid(session_id_or_name):
            try:
                session = db_get_session(uuid.UUID(session_id_or_name))
                if session:
                    session_id = str(session.id)
                    logger.info(f"Found session with id: {session_id}")
            except ValueError as e:
                logger.error(f"Error parsing session identifier as UUID: {str(e)}")
        
        if not session_id:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id_or_name}")
        
        # Create message history with the session_id
        message_history = MessageHistory(session_id=session_id)
        
        # Delete the session
        success = message_history.delete_session()
        if not success:
            raise HTTPException(status_code=404, detail=f"Session not found or failed to delete: {session_id_or_name}")
        
        return success
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}") 