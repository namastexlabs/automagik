import logging
import math
from fastapi import HTTPException
from src.db import list_sessions, get_session as db_get_session, get_session_by_name
from src.db.connection import safe_uuid
from src.memory.message_history import MessageHistory
from src.api.models import SessionResponse, SessionListResponse, SessionInfo, MessageModel, DeleteSessionResponse
from src.db.repository.session import get_system_prompt
from typing import List, Optional, Dict, Any
import uuid
from fastapi.concurrency import run_in_threadpool

# Get our module's logger
logger = logging.getLogger(__name__)

async def get_sessions(page: int, page_size: int, sort_desc: bool) -> SessionListResponse:
    """
    Get a paginated list of sessions
    """
    try:
        sessions, total_count = await run_in_threadpool(list_sessions,
            page=page,
            page_size=page_size,
            sort_desc=sort_desc)
        
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

async def get_session(session_id_or_name: str, page: int, page_size: int, sort_desc: bool, hide_tools: bool, show_system_prompt: bool) -> Dict[str, Any]:
    """
    Get a session by ID or name with its message history
    """
    try:
        # Check if we're dealing with a UUID or a name
        session_id = None
        session = None
        
        # First try to get session by name regardless of UUID format
        session = await run_in_threadpool(get_session_by_name, session_id_or_name)
        if session:
            session_id = str(session.id)
            logger.info(f"Found session with name '{session_id_or_name}', id: {session_id}")
        # If not found by name, try as UUID if it looks like one
        elif safe_uuid(session_id_or_name):
            try:
                session = await run_in_threadpool(db_get_session, uuid.UUID(session_id_or_name))
                if session:
                    session_id = str(session.id)
                    logger.info(f"Found session with id: {session_id}")
            except ValueError as e:
                logger.error(f"Error parsing session identifier as UUID: {str(e)}")
        
        if not session_id:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id_or_name}")
        
        # Create message history with the session_id
        message_history = await run_in_threadpool(lambda: MessageHistory(session_id=session_id))
        
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
        
        # Get system prompt only if requested
        system_prompt = None
        if show_system_prompt:
            system_prompt = await run_in_threadpool(get_system_prompt, uuid.UUID(session_id))

        # Get messages with pagination
        messages, total_count = await run_in_threadpool(
            message_history.get_messages,
            page, page_size, sort_desc
        )
        
        # If hide_tools is True, filter out tool calls and outputs from the messages
        if hide_tools:
            for message in messages:
                if "tool_calls" in message:
                    del message["tool_calls"]
                if "tool_outputs" in message:
                    del message["tool_outputs"]
        
        # Create response as a dictionary that can be converted to SessionResponse
        response_data = {
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

        # Conditionally add system_prompt to the response data
        if show_system_prompt:
            response_data["system_prompt"] = system_prompt
            
        return response_data
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
        session = await run_in_threadpool(get_session_by_name, session_id_or_name)
        if session:
            session_id = str(session.id)
            logger.info(f"Found session with name '{session_id_or_name}', id: {session_id}")
        # If not found by name, try as UUID if it looks like one
        elif safe_uuid(session_id_or_name):
            try:
                session = await run_in_threadpool(db_get_session, uuid.UUID(session_id_or_name))
                if session:
                    session_id = str(session.id)
                    logger.info(f"Found session with id: {session_id}")
            except ValueError as e:
                logger.error(f"Error parsing session identifier as UUID: {str(e)}")
        
        if not session_id:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id_or_name}")
        
        # Create message history with the session_id
        message_history = await run_in_threadpool(lambda: MessageHistory(session_id=session_id))
        
        # Delete the session
        success = await run_in_threadpool(message_history.delete_session)
        if not success:
            raise HTTPException(status_code=404, detail=f"Session not found or failed to delete: {session_id_or_name}")
        
        return success
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}") 