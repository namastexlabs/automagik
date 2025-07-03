import logging
import math
from fastapi import HTTPException
from automagik.db import list_sessions, get_session as db_get_session, get_session_by_name
from automagik.db.connection import safe_uuid

def _is_valid_uuid_string(value: str) -> bool:
    """Check if a string can be parsed as a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False
from automagik.memory.message_history import MessageHistory
from automagik.api.models import SessionListResponse, SessionInfo, BranchInfo
from automagik.db.repository.session import get_system_prompt, get_session_branches, get_session_branch_tree
from automagik.db.repository.session import get_session as get_session_by_id
from automagik.db import list_session_messages
from typing import Dict, Any, List
import uuid
import json
from datetime import datetime
from fastapi.concurrency import run_in_threadpool

# Get our module's logger
logger = logging.getLogger(__name__)


def _extract_usage_from_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper function to extract and aggregate usage data from messages."""
    total_tokens = 0
    total_requests = 0
    models = {}
    message_count = 0
    
    for message in messages:
        usage = message.get('usage')
        if not usage:
            continue
        
        # Parse usage data if it's a string
        if isinstance(usage, str):
            try:
                usage = json.loads(usage)
            except:
                continue
        
        if not isinstance(usage, dict):
            continue
            
        message_count += 1
            
        model = usage.get('model', 'unknown')
        framework = usage.get('framework', 'unknown')
        key = f"{model}_{framework}"
        
        if key not in models:
            models[key] = {
                "model": model,
                "framework": framework,
                "message_count": 0,
                "total_requests": 0,
                "request_tokens": 0,
                "response_tokens": 0,
                "total_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0
            }
        
        models[key]["message_count"] += 1
        models[key]["total_requests"] += usage.get('total_requests', 0)
        models[key]["request_tokens"] += usage.get('request_tokens', 0)
        models[key]["response_tokens"] += usage.get('response_tokens', 0)
        models[key]["total_tokens"] += usage.get('total_tokens', 0)
        models[key]["cache_creation_tokens"] += usage.get('cache_creation_tokens', 0)
        models[key]["cache_read_tokens"] += usage.get('cache_read_tokens', 0)
        
        total_tokens += usage.get('total_tokens', 0)
        total_requests += usage.get('total_requests', 0)
    
    return {
        "session_id": None,  # Will be set by caller
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "models": list(models.values()),
        "summary": {
            "message_count": message_count,
            "unique_models": len(models),
            "total_request_tokens": sum(m["request_tokens"] for m in models.values()),
            "total_response_tokens": sum(m["response_tokens"] for m in models.values()),
            "total_cache_tokens": sum(m["cache_creation_tokens"] + m["cache_read_tokens"] for m in models.values()),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    }

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
        elif _is_valid_uuid_string(session_id_or_name):
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
        
        # Add token usage analytics for the session
        try:
            session_uuid = safe_uuid(session_id)
            if session_uuid:
                messages, _ = await run_in_threadpool(list_session_messages, session_uuid)
                token_analytics = _extract_usage_from_messages(messages)
                token_analytics["session_id"] = session_id
                response_data["token_analytics"] = token_analytics
            else:
                response_data["token_analytics"] = None
        except Exception as e:
            logger.warning(f"Failed to get token analytics for session {session_id}: {e}")
            response_data["token_analytics"] = None
            
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
        elif _is_valid_uuid_string(session_id_or_name):
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


async def get_session_branches_controller(session_id: uuid.UUID) -> dict:
    """
    Controller to get all branches for a session.
    """
    try:
        # Get the main session
        main_session = await run_in_threadpool(get_session_by_id, session_id)
        if not main_session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
        
        # Get all branches
        branches = await run_in_threadpool(get_session_branches, session_id)
        
        # Convert to BranchInfo objects
        main_branch_info = BranchInfo(
            session_id=main_session.id,
            session_name=main_session.name,
            branch_type=main_session.branch_type,
            branch_point_message_id=main_session.branch_point_message_id,
            is_main_branch=main_session.is_main_branch,
            created_at=main_session.created_at,
            message_count=main_session.message_count
        )
        
        branch_infos = []
        for branch in branches:
            branch_info = BranchInfo(
                session_id=branch.id,
                session_name=branch.name,
                branch_type=branch.branch_type,
                branch_point_message_id=branch.branch_point_message_id,
                is_main_branch=branch.is_main_branch,
                created_at=branch.created_at,
                message_count=branch.message_count
            )
            branch_infos.append(branch_info)
        
        logger.info(f"Found {len(branch_infos)} branches for session {session_id}")
        
        return {
            "main_session": main_branch_info,
            "branches": branch_infos,
            "total_branches": len(branch_infos)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session branches: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session branches due to an internal error.")


async def get_session_branch_tree_controller(session_id: uuid.UUID) -> dict:
    """
    Controller to get the complete branch tree for a session.
    """
    try:
        # Get the root session with tree structure
        root_session = await run_in_threadpool(get_session_branch_tree, session_id)
        if not root_session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
        
        # For now, we'll return a simplified tree structure
        # The repository function returns just the root; we'd need to enhance it
        # to build the full hierarchical structure with children
        
        from automagik.api.models import BranchTreeNode
        
        root_node = BranchTreeNode(
            session_id=root_session.id,
            session_name=root_session.name,
            branch_type=root_session.branch_type,
            branch_point_message_id=root_session.branch_point_message_id,
            is_main_branch=root_session.is_main_branch,
            created_at=root_session.created_at,
            message_count=root_session.message_count,
            children=[]  # TODO: Build actual tree structure
        )
        
        logger.info(f"Built branch tree for session {session_id}")
        
        return {
            "root": root_node,
            "total_sessions": 1  # TODO: Count actual sessions in tree
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session branch tree: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session branch tree due to an internal error.") 