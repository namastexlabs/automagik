import logging
import uuid
from fastapi import APIRouter, HTTPException, Query, Path
from automagik.api.models import SessionListResponse, SessionBranchesResponse, SessionBranchTreeResponse
from automagik.api.controllers.session_controller import get_sessions, get_session, delete_session, get_session_branches_controller, get_session_branch_tree_controller

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
        
        # Prepare the session details from SessionInfo
        # Use .model_dump() for Pydantic v2, or .dict() for v1
        # Assuming Pydantic v2+ for .model_dump()
        session_details = session_data["session"].model_dump(exclude_none=True)
        
        # Ensure all required fields are strings if they are UUID or datetime
        if 'user_id' in session_details and session_details['user_id'] is not None:
            session_details['user_id'] = str(session_details['user_id'])
        if 'created_at' in session_details and session_details['created_at'] is not None:
            session_details['created_at'] = session_details['created_at'].isoformat()
        if 'last_updated' in session_details and session_details['last_updated'] is not None:
            session_details['last_updated'] = session_details['last_updated'].isoformat()

        # Construct the final response
        response_payload = {
            **session_details, # Spread all fields from SessionInfo
            "session_id": response_id, # Override session_id with the one determined for the route
            "messages": session_data["messages"],
            "exists": True,
            "total_messages": session_data["total"], # This is the same as session_details.get('message_count')
            "current_page": session_data["page"],
            "total_pages": session_data["total_pages"],
            "system_prompt": session_data.get("system_prompt")
        }
        return response_payload
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
    await delete_session(session_id_or_name)
    return {
        "status": "success",
        "session_id": session_id_or_name,
        "message": f"Session {session_id_or_name} deleted successfully"
    }


@session_router.get(
    "/sessions/{session_id}/branches",
    response_model=SessionBranchesResponse,
    tags=["Sessions", "Branching"],
    summary="Get Session Branches",
    description="Retrieve all conversation branches for a specific session."
)
async def get_session_branches_route(
    session_id: uuid.UUID = Path(..., description="The unique identifier of the session.")
):
    """
    Get all conversation branches for a session.
    
    Returns the main session and all its branches, including metadata
    about each branch such as the branch point message and creation time.
    """
    try:
        response_data = await get_session_branches_controller(session_id)
        return SessionBranchesResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_session_branches_route for session_id {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to get session branches.")


@session_router.get(
    "/sessions/{session_id}/branch-tree",
    response_model=SessionBranchTreeResponse,
    tags=["Sessions", "Branching"],
    summary="Get Session Branch Tree",
    description="Retrieve the complete conversation branch tree for a session as a hierarchical structure."
)
async def get_session_branch_tree_route(
    session_id: uuid.UUID = Path(..., description="The unique identifier of the session.")
):
    """
    Get the complete conversation branch tree for a session.
    
    Returns a hierarchical tree structure showing the relationship
    between the main session and all its branches and sub-branches.
    """
    try:
        response_data = await get_session_branch_tree_controller(session_id)
        return SessionBranchTreeResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_session_branch_tree_route for session_id {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to get session branch tree.") 