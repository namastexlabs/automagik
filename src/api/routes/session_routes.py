import logging
from fastapi import APIRouter, HTTPException, Query, Path, Response
from src.api.models import SessionResponse, SessionListResponse, SessionInfo, MessageModel, DeleteSessionResponse
from src.api.controllers.session_controller import get_sessions, get_session, delete_session

# Create router for session endpoints
session_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

@session_router.get("/sessions", response_model=SessionListResponse, tags=["Sessions"],
            summary="List All Sessions",
            description="Retrieve a list of all sessions with pagination options.")
async def list_sessions_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_desc: bool = Query(True, description="Sort by most recent first")
):
    """
    Get a paginated list of all sessions
    """
    return await get_sessions(page, page_size, sort_desc)

@session_router.get("/sessions/{session_id_or_name}", tags=["Sessions"],
           summary="Get Session History",
           description="Retrieve a session's message history with pagination options. You can use either the session ID (UUID) or a session name.")
async def get_session_route(
    session_id_or_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_desc: bool = Query(True, description="Sort by most recent first"),
    hide_tools: bool = Query(False, description="Exclude tool calls and outputs"),
    show_system_prompt: bool = Query(False, description="Include system prompt in session details")
):
    """
    Get a session by ID or name with its message history
    """
    try:
        session_data = await get_session(session_id_or_name, page, page_size, sort_desc, hide_tools, show_system_prompt)
        
        # For name lookups, return the name as the session_id
        session_name = session_data["session"].session_name
        session_id = session_data["session"].session_id
        response_id = session_id_or_name if session_id_or_name == session_name else session_id
        
        # Convert to format expected by the tests
        return {
            "session_id": response_id,
            "messages": session_data["messages"],
            "exists": True,
            "total_messages": session_data["total"],
            "current_page": session_data["page"],
            "total_pages": session_data["total_pages"],
            "system_prompt": session_data.get("system_prompt")
        }
    except HTTPException as e:  
        if e.status_code == 404:
            # Return 404 status code when session not found, don't handle it
            raise
        # Rethrow other exceptions
        raise

@session_router.delete("/sessions/{session_id_or_name}", tags=["Sessions"],
              summary="Delete Session",
              description="Delete a session's message history by its ID or name.")
async def delete_session_route(session_id_or_name: str):
    """
    Delete a session by ID or name
    """
    success = await delete_session(session_id_or_name)
    return {
        "status": "success",
        "session_id": session_id_or_name,
        "message": f"Session {session_id_or_name} deleted successfully"
    } 