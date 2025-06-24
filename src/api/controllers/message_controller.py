import logging
import uuid
from typing import Optional
from fastapi import HTTPException
from src.db.repository.message import (
    delete_message as db_delete_message,
    create_message as db_create_message,
    get_message as db_get_message,
    update_message as db_update_message,
    list_messages as db_list_messages,
    count_messages as db_count_messages
)
from src.db.models import Message
from src.api.models import CreateMessageRequest, UpdateMessageRequest
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

async def create_message_controller(request: CreateMessageRequest) -> dict:
    """
    Controller to handle the creation of a new message.
    """
    try:
        # Generate new UUID for the message
        message_id = uuid.uuid4()
        
        # Create Message model instance
        message = Message(
            id=message_id,
            session_id=request.session_id,
            user_id=request.user_id,
            agent_id=request.agent_id,
            role=request.role,
            text_content=request.text_content,
            media_url=request.media_url,
            mime_type=request.mime_type,
            message_type=request.message_type,
            raw_payload=request.raw_payload,
            channel_payload=request.channel_payload,
            tool_calls=request.tool_calls,
            tool_outputs=request.tool_outputs,
            system_prompt=request.system_prompt,
            user_feedback=request.user_feedback,
            flagged=request.flagged,
            context=request.context,
            usage=request.usage
        )
        
        # Create message in database
        created_id = await run_in_threadpool(db_create_message, message)
        
        if created_id:
            logger.info(f"Successfully created message with ID: {created_id}")
            return {"status": "success", "message_id": created_id, "detail": "Message created successfully"}
        else:
            logger.error("Failed to create message")
            raise HTTPException(status_code=500, detail="Failed to create message due to an internal error.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create message due to an internal error.")


async def get_message_controller(message_id: uuid.UUID) -> dict:
    """
    Controller to handle retrieving a specific message.
    """
    try:
        message = await run_in_threadpool(db_get_message, message_id)
        
        if message:
            logger.info(f"Successfully retrieved message with ID: {message_id}")
            return {
                "id": message.id,
                "session_id": message.session_id,
                "user_id": message.user_id,
                "agent_id": message.agent_id,
                "role": message.role,
                "text_content": message.text_content,
                "media_url": message.media_url,
                "mime_type": message.mime_type,
                "message_type": message.message_type,
                "raw_payload": message.raw_payload,
                "channel_payload": message.channel_payload,
                "tool_calls": message.tool_calls,
                "tool_outputs": message.tool_outputs,
                "system_prompt": message.system_prompt,
                "user_feedback": message.user_feedback,
                "flagged": message.flagged,
                "context": message.context,
                "usage": message.usage,
                "created_at": message.created_at,
                "updated_at": message.updated_at
            }
        else:
            logger.warning(f"Message with ID {message_id} not found")
            raise HTTPException(status_code=404, detail=f"Message with ID {message_id} not found.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve message {message_id} due to an internal error.")


async def list_messages_controller(
    session_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 50,
    sort_desc: bool = True
) -> dict:
    """
    Controller to handle listing messages with optional filtering.
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get messages - for now, we need session_id for the existing function
        if session_id:
            messages = await run_in_threadpool(
                db_list_messages,
                session_id=session_id,
                offset=offset,
                limit=page_size,
                sort_desc=sort_desc
            )
            
            # Get total count
            total_count = await run_in_threadpool(db_count_messages, session_id)
        else:
            # For now, return empty list if no session_id provided
            # This could be enhanced to list all messages across sessions
            messages = []
            total_count = 0
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        # Convert messages to dict format
        message_list = []
        for message in messages:
            message_dict = {
                "id": message.id,
                "session_id": message.session_id,
                "user_id": message.user_id,
                "agent_id": message.agent_id,
                "role": message.role,
                "text_content": message.text_content,
                "media_url": message.media_url,
                "mime_type": message.mime_type,
                "message_type": message.message_type,
                "raw_payload": message.raw_payload,
                "channel_payload": message.channel_payload,
                "tool_calls": message.tool_calls,
                "tool_outputs": message.tool_outputs,
                "system_prompt": message.system_prompt,
                "user_feedback": message.user_feedback,
                "flagged": message.flagged,
                "context": message.context,
                "usage": message.usage,
                "created_at": message.created_at,
                "updated_at": message.updated_at
            }
            message_list.append(message_dict)
        
        logger.info(f"Successfully listed {len(message_list)} messages")
        
        return {
            "messages": message_list,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
        
    except Exception as e:
        logger.error(f"Error listing messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list messages due to an internal error.")


async def update_message_controller(message_id: uuid.UUID, request: UpdateMessageRequest) -> dict:
    """
    Controller to handle updating a specific message.
    """
    try:
        # First, get the existing message
        existing_message = await run_in_threadpool(db_get_message, message_id)
        
        if not existing_message:
            logger.warning(f"Message with ID {message_id} not found for update")
            raise HTTPException(status_code=404, detail=f"Message with ID {message_id} not found.")
        
        # Update only the fields that were provided in the request
        updated_message = Message(
            id=existing_message.id,
            session_id=request.session_id if request.session_id is not None else existing_message.session_id,
            user_id=request.user_id if request.user_id is not None else existing_message.user_id,
            agent_id=request.agent_id if request.agent_id is not None else existing_message.agent_id,
            role=request.role if request.role is not None else existing_message.role,
            text_content=request.text_content if request.text_content is not None else existing_message.text_content,
            media_url=request.media_url if request.media_url is not None else existing_message.media_url,
            mime_type=request.mime_type if request.mime_type is not None else existing_message.mime_type,
            message_type=request.message_type if request.message_type is not None else existing_message.message_type,
            raw_payload=request.raw_payload if request.raw_payload is not None else existing_message.raw_payload,
            channel_payload=request.channel_payload if request.channel_payload is not None else existing_message.channel_payload,
            tool_calls=request.tool_calls if request.tool_calls is not None else existing_message.tool_calls,
            tool_outputs=request.tool_outputs if request.tool_outputs is not None else existing_message.tool_outputs,
            system_prompt=request.system_prompt if request.system_prompt is not None else existing_message.system_prompt,
            user_feedback=request.user_feedback if request.user_feedback is not None else existing_message.user_feedback,
            flagged=request.flagged if request.flagged is not None else existing_message.flagged,
            context=request.context if request.context is not None else existing_message.context,
            usage=request.usage if request.usage is not None else existing_message.usage,
            created_at=existing_message.created_at,  # Keep original creation time
            updated_at=None  # Will be set by the database layer
        )
        
        # Update message in database
        updated_id = await run_in_threadpool(db_update_message, updated_message)
        
        if updated_id:
            logger.info(f"Successfully updated message with ID: {updated_id}")
            return {"status": "success", "message_id": updated_id, "detail": "Message updated successfully"}
        else:
            logger.error(f"Failed to update message {message_id}")
            raise HTTPException(status_code=500, detail=f"Failed to update message {message_id} due to an internal error.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update message {message_id} due to an internal error.")


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