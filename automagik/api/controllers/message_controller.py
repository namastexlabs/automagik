import logging
import uuid
from typing import Optional
from fastapi import HTTPException
from automagik.db.repository.message import (
    delete_message as db_delete_message,
    create_message as db_create_message,
    get_message as db_get_message,
    update_message as db_update_message,
    list_messages as db_list_messages,
    count_messages as db_count_messages
)
from automagik.db.repository.session import (
    create_branch_session,
    copy_messages_to_branch,
    get_session
)
from automagik.db.models import Message, Session
from automagik.api.models import CreateMessageRequest, UpdateMessageRequest, CreateBranchRequest, AgentRunRequest
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
        
        # Check if we should create a branch instead of updating in-place
        if request.create_branch:
            # Create a branch request with the updated content
            branch_request = CreateBranchRequest(
                edited_message_content=request.text_content if request.text_content is not None else existing_message.text_content,
                branch_name=request.branch_name,
                run_agent=request.run_agent
            )
            
            # Use the branch creation logic
            branch_result = await create_message_branch_controller(message_id, branch_request)
            
            # Return branch-specific response
            return {
                "status": "success",
                "message_id": branch_result["branch_point_message_id"],
                "detail": "Message branch created successfully",
                "branch_session_id": branch_result["branch_session_id"],
                "original_session_id": branch_result["original_session_id"],
                "branch_point_message_id": branch_result["branch_point_message_id"]
            }
        
        # Regular in-place update logic
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


async def create_message_branch_controller(message_id: uuid.UUID, request: CreateBranchRequest) -> dict:
    """
    Controller to handle creating a conversation branch from a message.
    """
    try:
        # Get the original message to get session context
        original_message = await run_in_threadpool(db_get_message, message_id)
        if not original_message:
            logger.warning(f"Message {message_id} not found for branching")
            raise HTTPException(status_code=404, detail=f"Message with ID {message_id} not found.")
        
        # Get the session to ensure it exists
        parent_session = await run_in_threadpool(get_session, original_message.session_id)
        if not parent_session:
            logger.error(f"Parent session {original_message.session_id} not found")
            raise HTTPException(status_code=404, detail="Parent session not found.")
        
        # Create the branch session
        branch_session_id = await run_in_threadpool(
            create_branch_session,
            parent_session_id=original_message.session_id,
            branch_point_message_id=message_id,
            branch_name=request.branch_name,
            branch_type="edit_branch"
        )
        
        if not branch_session_id:
            logger.error(f"Failed to create branch session for message {message_id}")
            raise HTTPException(status_code=500, detail="Failed to create branch session.")
        
        # Copy messages up to the branch point
        copy_success = await run_in_threadpool(
            copy_messages_to_branch,
            parent_session_id=original_message.session_id,
            branch_session_id=branch_session_id,
            branch_point_message_id=message_id
        )
        
        if not copy_success:
            logger.error(f"Failed to copy messages to branch session {branch_session_id}")
            raise HTTPException(status_code=500, detail="Failed to copy conversation history to branch.")
        
        # Update the branch point message with the edited content
        # Create a new message with the edited content
        edited_message = Message(
            id=uuid.uuid4(),
            session_id=branch_session_id,
            user_id=original_message.user_id,
            agent_id=original_message.agent_id,
            role=original_message.role,
            text_content=request.edited_message_content,
            media_url=original_message.media_url,
            mime_type=original_message.mime_type,
            message_type=original_message.message_type,
            raw_payload=original_message.raw_payload,
            channel_payload=original_message.channel_payload,
            tool_calls=original_message.tool_calls,
            tool_outputs=original_message.tool_outputs,
            system_prompt=original_message.system_prompt,
            context=original_message.context,
            usage=original_message.usage
        )
        
        edited_message_id = await run_in_threadpool(db_create_message, edited_message)
        if not edited_message_id:
            logger.error(f"Failed to create edited message in branch {branch_session_id}")
            raise HTTPException(status_code=500, detail="Failed to create edited message in branch.")
        
        # Trigger agent execution if requested
        if request.run_agent:
            logger.info(f"Triggering agent execution for branch session {branch_session_id}")
            await trigger_agent_execution_for_branch(
                branch_session_id=branch_session_id,
                parent_session=parent_session,
                edited_message_content=request.edited_message_content
            )
        
        logger.info(f"Successfully created branch {branch_session_id} from message {message_id}")
        
        return {
            "status": "success",
            "branch_session_id": branch_session_id,
            "original_session_id": original_message.session_id,
            "branch_point_message_id": message_id,
            "detail": "Branch created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message branch: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation branch due to an internal error.")


async def trigger_agent_execution_for_branch(
    branch_session_id: uuid.UUID,
    parent_session: Session,
    edited_message_content: str
) -> None:
    """
    Trigger agent execution for a newly created branch session.
    
    Args:
        branch_session_id: The new branch session ID
        parent_session: The parent session containing agent information
        edited_message_content: The edited message content that started the branch
    """
    try:
        # Import here to avoid circular imports
        from automagik.api.controllers.agent_controller import handle_agent_run
        
        # Determine which agent to run based on parent session
        agent_name = None
        if parent_session.agent_id:
            # Get agent name from database
            from automagik.db import get_agent
            agent = await run_in_threadpool(get_agent, parent_session.agent_id)
            if agent:
                agent_name = agent.name
        
        if not agent_name:
            logger.warning(f"No agent found for parent session {parent_session.id}, skipping agent execution")
            return
        
        # Create agent run request for the branch session
        agent_request = AgentRunRequest(
            message_content=edited_message_content,
            session_id=str(branch_session_id),
            user_id=parent_session.user_id,
            agent_id=parent_session.agent_id,
            message_limit=10,  # Reasonable default for branch context
            session_origin="automagik-agent",  # Use valid session origin
            force_new_session=False  # Use existing branch session
        )
        
        logger.info(f"Executing agent {agent_name} for branch session {branch_session_id}")
        
        # Execute the agent asynchronously
        response = await handle_agent_run(agent_name, agent_request)
        
        if response.get("status") == "success":
            logger.info(f"Agent execution completed successfully for branch {branch_session_id}")
        else:
            logger.warning(f"Agent execution completed with issues for branch {branch_session_id}: {response}")
            
    except Exception as e:
        logger.error(f"Error triggering agent execution for branch {branch_session_id}: {str(e)}")
        # Don't raise the exception - branch creation should succeed even if agent execution fails
        # This prevents branch creation from failing due to agent issues