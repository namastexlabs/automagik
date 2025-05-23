import logging
import uuid
from fastapi import HTTPException
from src.db.repository.message import delete_message as db_delete_message # Renaming for clarity
from fastapi.concurrency import run_in_threadpool  # NEW

logger = logging.getLogger(__name__)

async def delete_message_controller(message_id: uuid.UUID) -> dict:
    """
    Controller to handle the deletion of a specific message.
    """
    try:
        success = await run_in_threadpool(db_delete_message, message_id=message_id)
        if success:
            logger.info(f"Successfully deleted message with ID: {message_id}")
            # The actual response model will be handled by the route's response_model
            return {"status": "success", "message_id": message_id, "detail": "Message deleted successfully"}
        else:
            logger.warning(f"Attempted to delete message with ID: {message_id}, but it was not found or delete failed.")
            raise HTTPException(status_code=404, detail=f"Message with ID {message_id} not found or could not be deleted.")
    except HTTPException:
        raise # Re-raise HTTPException to let FastAPI handle it
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {str(e)}")
        # Consider if any other specific exception types should be caught and handled differently
        raise HTTPException(status_code=500, detail=f"Failed to delete message {message_id} due to an internal error.") 