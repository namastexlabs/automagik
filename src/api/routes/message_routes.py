import logging
import uuid
from fastapi import APIRouter, HTTPException, Path
from src.api.controllers.message_controller import delete_message_controller
from src.api.models import DeleteMessageResponse

# Create router for message endpoints
message_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

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