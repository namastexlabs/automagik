import logging
from typing import Optional

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool

from automagik.api.models import PromptResponse, PromptListResponse
from automagik.db.models import PromptCreate, PromptUpdate
from automagik.db.repository import prompt as prompt_repo

# Configure logger
logger = logging.getLogger(__name__)

async def list_prompts(agent_id: int, status_key: Optional[str] = None) -> PromptListResponse:
    """
    List all prompts for an agent, optionally filtered by status key.
    
    Args:
        agent_id: The agent ID
        status_key: Optional status key to filter by
        
    Returns:
        PromptListResponse with the list of prompts
    """
    try:
        prompts = await run_in_threadpool(prompt_repo.get_prompts_by_agent_id, agent_id, status_key)
        
        # Convert DB models to API response models
        prompt_responses = [
            PromptResponse(
                id=prompt.id,
                agent_id=prompt.agent_id,
                prompt_text=prompt.prompt_text,
                version=prompt.version,
                is_active=prompt.is_active,
                is_default_from_code=prompt.is_default_from_code,
                status_key=prompt.status_key,
                name=prompt.name,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at
            )
            for prompt in prompts
        ]
        
        return PromptListResponse(
            prompts=prompt_responses,
            total=len(prompt_responses),
            agent_id=agent_id
        )
    except Exception as e:
        logger.error(f"Error listing prompts for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompts: {str(e)}"
        )

async def get_prompt(prompt_id: int) -> PromptResponse:
    """
    Get a prompt by ID.
    
    Args:
        prompt_id: The prompt ID
        
    Returns:
        PromptResponse with the prompt details
    """
    try:
        prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        
        return PromptResponse(
            id=prompt.id,
            agent_id=prompt.agent_id,
            prompt_text=prompt.prompt_text,
            version=prompt.version,
            is_active=prompt.is_active,
            is_default_from_code=prompt.is_default_from_code,
            status_key=prompt.status_key,
            name=prompt.name,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt: {str(e)}"
        )

async def create_prompt(agent_id: int, prompt_data: dict) -> PromptResponse:
    """
    Create a new prompt for an agent.
    
    Args:
        agent_id: The agent ID
        prompt_data: The prompt data
        
    Returns:
        PromptResponse with the created prompt details
    """
    try:
        # Create a PromptCreate object
        create_data = PromptCreate(
            agent_id=agent_id,
            prompt_text=prompt_data["prompt_text"],
            status_key=prompt_data.get("status_key", "default"),
            name=prompt_data.get("name"),
            is_active=prompt_data.get("is_active", False),
            version=prompt_data.get("version", 1),
            is_default_from_code=False  # API-created prompts are never default from code
        )
        
        # Create the prompt
        prompt_id = await run_in_threadpool(prompt_repo.create_prompt, create_data)
        
        if not prompt_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create prompt"
            )
        
        # Get the created prompt
        prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        return PromptResponse(
            id=prompt.id,
            agent_id=prompt.agent_id,
            prompt_text=prompt.prompt_text,
            version=prompt.version,
            is_active=prompt.is_active,
            is_default_from_code=prompt.is_default_from_code,
            status_key=prompt.status_key,
            name=prompt.name,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prompt for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prompt: {str(e)}"
        )

async def update_prompt(prompt_id: int, prompt_data: dict) -> PromptResponse:
    """
    Update an existing prompt.
    
    Args:
        prompt_id: The prompt ID
        prompt_data: The updated prompt data
        
    Returns:
        PromptResponse with the updated prompt details
    """
    try:
        # Get the existing prompt
        existing_prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        if not existing_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        
        # Create an update object
        update_data = PromptUpdate(
            prompt_text=prompt_data.get("prompt_text"),
            name=prompt_data.get("name"),
            is_active=prompt_data.get("is_active")
        )
        
        # Update the prompt
        success = await run_in_threadpool(prompt_repo.update_prompt, prompt_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update prompt"
            )
        
        # Get the updated prompt
        updated_prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        return PromptResponse(
            id=updated_prompt.id,
            agent_id=updated_prompt.agent_id,
            prompt_text=updated_prompt.prompt_text,
            version=updated_prompt.version,
            is_active=updated_prompt.is_active,
            is_default_from_code=updated_prompt.is_default_from_code,
            status_key=updated_prompt.status_key,
            name=updated_prompt.name,
            created_at=updated_prompt.created_at,
            updated_at=updated_prompt.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt: {str(e)}"
        )

async def set_prompt_active(prompt_id: int, is_active: bool = True) -> PromptResponse:
    """
    Set a prompt as active or inactive.
    
    Args:
        prompt_id: The prompt ID
        is_active: Whether to set as active
        
    Returns:
        PromptResponse with the updated prompt details
    """
    try:
        # Get the existing prompt
        existing_prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        if not existing_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        
        # Set the prompt active status
        success = await run_in_threadpool(prompt_repo.set_prompt_active, prompt_id, is_active)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set prompt {prompt_id} active status to {is_active}"
            )
        
        # Get the updated prompt
        updated_prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        return PromptResponse(
            id=updated_prompt.id,
            agent_id=updated_prompt.agent_id,
            prompt_text=updated_prompt.prompt_text,
            version=updated_prompt.version,
            is_active=updated_prompt.is_active,
            is_default_from_code=updated_prompt.is_default_from_code,
            status_key=updated_prompt.status_key,
            name=updated_prompt.name,
            created_at=updated_prompt.created_at,
            updated_at=updated_prompt.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting prompt {prompt_id} active status to {is_active}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set prompt active status: {str(e)}"
        )

async def delete_prompt(prompt_id: int) -> dict:
    """
    Delete a prompt.
    
    Args:
        prompt_id: The prompt ID
        
    Returns:
        Success message
    """
    try:
        # Get the existing prompt
        existing_prompt = await run_in_threadpool(prompt_repo.get_prompt_by_id, prompt_id)
        
        if not existing_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        
        # Delete the prompt
        success = await run_in_threadpool(prompt_repo.delete_prompt, prompt_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete prompt {prompt_id}"
            )
        
        return {
            "status": "success",
            "detail": f"Prompt with ID {prompt_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete prompt: {str(e)}"
        ) 