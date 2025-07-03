import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query, status
from automagik.api.controllers.message_controller import (
    create_message_controller,
    get_message_controller,
    list_messages_controller,
    update_message_controller,
    delete_message_controller,
    create_message_branch_controller
)
from automagik.api.models import (
    CreateMessageRequest,
    CreateMessageResponse,
    MessageResponse,
    MessageListResponse,
    UpdateMessageRequest,
    UpdateMessageResponse,
    DeleteMessageResponse,
    CreateBranchRequest,
    CreateBranchResponse
)

# Create router for message endpoints
message_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

@message_router.post(
    "/messages",
    response_model=CreateMessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Messages"],
    summary="Create New Message",
    description="Creates a new message in the system."
)
async def create_message_route(
    request: CreateMessageRequest
):
    """
    Endpoint to create a new message.
    """
    try:
        response_data = await create_message_controller(request)
        return CreateMessageResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in create_message_route: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to create the message.")


@message_router.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    tags=["Messages"],
    summary="Get Message by ID",
    description="Retrieves a specific message from the system by its unique ID."
)
async def get_message_route(
    message_id: uuid.UUID = Path(..., description="The unique identifier of the message to retrieve.")
):
    """
    Endpoint to get a specific message by its ID.
    """
    try:
        response_data = await get_message_controller(message_id)
        return MessageResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_message_route for message_id {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to retrieve the message.")


@message_router.get(
    "/messages",
    response_model=MessageListResponse,
    tags=["Messages"],
    summary="List Messages",
    description="Retrieves a list of messages with optional filtering and pagination."
)
async def list_messages_route(
    session_id: Optional[uuid.UUID] = Query(None, description="Filter messages by session ID"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter messages by user ID"),
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of messages per page (max 100)"),
    sort_desc: bool = Query(True, description="Sort by creation date descending (newest first)")
):
    """
    Endpoint to list messages with optional filtering and pagination.
    """
    try:
        response_data = await list_messages_controller(
            session_id=session_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_desc=sort_desc
        )
        return MessageListResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in list_messages_route: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to list messages.")


@message_router.put(
    "/messages/{message_id}",
    response_model=UpdateMessageResponse,
    tags=["Messages"],
    summary="Update Message by ID",
    description="Updates a specific message in the system by its unique ID."
)
async def update_message_route(
    message_id: uuid.UUID = Path(..., description="The unique identifier of the message to update."),
    request: UpdateMessageRequest = ...
):
    """
    Endpoint to update a specific message by its ID.
    """
    try:
        response_data = await update_message_controller(message_id, request)
        return UpdateMessageResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in update_message_route for message_id {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to update the message.")


@message_router.delete(
    "/messages/{message_id}", 
    response_model=DeleteMessageResponse, 
    tags=["Messages"],
    summary="Delete Message by ID",
    description="Deletes a specific message from the system by its unique ID."
)
async def delete_message_route(
    message_id: uuid.UUID = Path(..., description="The unique identifier of the message to delete.")
):
    """
    Endpoint to delete a specific message by its ID.
    """
    try:
        # The controller already returns a dict that matches DeleteMessageResponse
        # or raises appropriate HTTPErrors.
        response_data = await delete_message_controller(message_id=message_id)
        return DeleteMessageResponse(**response_data) # Construct the response model instance
    except HTTPException as e:
        # Re-raise if controller raised an HTTPException (like 404 or 500)
        raise e
    except Exception as e:
        # Catch any other unexpected errors from the controller or this level
        logger.error(f"Unexpected error in delete_message_route for message_id {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to delete the message.")


@message_router.post(
    "/messages/{message_id}/branch",
    response_model=CreateBranchResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Messages", "Branching"],
    summary="Create Conversation Branch from Message",
    description="Creates a new conversation branch starting from a specific message with edited content."
)
async def create_message_branch_route(
    message_id: uuid.UUID = Path(..., description="The unique identifier of the message to branch from."),
    request: CreateBranchRequest = ...
):
    """
    Endpoint to create a conversation branch from a specific message.
    
    This allows users to:
    1. Edit a message in the conversation history
    2. Create a new conversation branch from that point
    3. Optionally re-run the agent from the edited message
    
    The original conversation remains unchanged, and the new branch
    becomes a separate conversation thread that can be developed independently.
    """
    try:
        response_data = await create_message_branch_controller(message_id, request)
        return CreateBranchResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in create_message_branch_route for message_id {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while trying to create the conversation branch.") 