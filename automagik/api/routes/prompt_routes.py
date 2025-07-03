import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, status, Body

from automagik.api.models import (
    PromptResponse, 
    PromptListResponse, 
    PromptCreateRequest, 
    PromptUpdateRequest
)
from automagik.api.controllers import prompt_controller

# Create router for prompt endpoints
prompt_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

@prompt_router.get(
    "/agent/{agent_id}/prompt",
    response_model=PromptListResponse,
    tags=["Prompts"],
    summary="List Prompts for Agent",
    description="Returns a list of all prompts for the specified agent, optionally filtered by status key."
)
async def list_prompts(
    agent_id: int = Path(..., description="The ID of the agent to list prompts for"),
    status_key: Optional[str] = Query(None, description="Filter prompts by status key")
):
    """
    Get a list of all prompts for an agent, optionally filtered by status key.
    
    Args:
        agent_id: The agent ID
        status_key: Optional status key to filter by
    """
    return await prompt_controller.list_prompts(agent_id, status_key)

@prompt_router.get(
    "/agent/{agent_id}/prompt/{prompt_id}",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Get Prompt by ID",
    description="Returns the details of a specific prompt."
)
async def get_prompt(
    agent_id: int = Path(..., description="The ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to retrieve")
):
    """
    Get a prompt by ID.
    
    Args:
        agent_id: The agent ID (for path consistency)
        prompt_id: The prompt ID
    """
    # Get the prompt
    prompt = await prompt_controller.get_prompt(prompt_id)
    
    # Verify the prompt belongs to the specified agent
    if prompt.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found for agent {agent_id}"
        )
    
    return prompt

@prompt_router.post(
    "/agent/{agent_id}/prompt",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Create New Prompt",
    description="Creates a new prompt for the specified agent.",
    status_code=status.HTTP_201_CREATED
)
async def create_prompt(
    agent_id: int = Path(..., description="The ID of the agent to create a prompt for"),
    prompt_data: PromptCreateRequest = Body(..., description="The prompt data")
):
    """
    Create a new prompt for an agent.
    
    Args:
        agent_id: The agent ID
        prompt_data: The prompt data
    """
    return await prompt_controller.create_prompt(agent_id, prompt_data.model_dump())

@prompt_router.put(
    "/agent/{agent_id}/prompt/{prompt_id}",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Update Prompt",
    description="Updates an existing prompt."
)
async def update_prompt(
    agent_id: int = Path(..., description="The ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to update"),
    prompt_data: PromptUpdateRequest = Body(..., description="The updated prompt data")
):
    """
    Update an existing prompt.
    
    Args:
        agent_id: The agent ID (for path consistency)
        prompt_id: The prompt ID
        prompt_data: The updated prompt data
    """
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_id}"
            )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        raise
    
    return await prompt_controller.update_prompt(prompt_id, prompt_data.model_dump())

@prompt_router.post(
    "/agent/{agent_id}/prompt/{prompt_id}/activate",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Activate Prompt",
    description="Sets a prompt as active for its agent and status key, deactivating other prompts."
)
async def activate_prompt(
    agent_id: int = Path(..., description="The ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to activate")
):
    """
    Set a prompt as active.
    
    Args:
        agent_id: The agent ID (for path consistency)
        prompt_id: The prompt ID
    """
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_id}"
            )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        raise
    
    return await prompt_controller.set_prompt_active(prompt_id, True)

@prompt_router.post(
    "/agent/{agent_id}/prompt/{prompt_id}/deactivate",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Deactivate Prompt",
    description="Sets a prompt as inactive."
)
async def deactivate_prompt(
    agent_id: int = Path(..., description="The ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to deactivate")
):
    """
    Set a prompt as inactive.
    
    Args:
        agent_id: The agent ID (for path consistency)
        prompt_id: The prompt ID
    """
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_id}"
            )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        raise
    
    return await prompt_controller.set_prompt_active(prompt_id, False)

@prompt_router.delete(
    "/agent/{agent_id}/prompt/{prompt_id}",
    tags=["Prompts"],
    summary="Delete Prompt",
    description="Deletes a prompt."
)
async def delete_prompt(
    agent_id: int = Path(..., description="The ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to delete")
):
    """
    Delete a prompt.
    
    Args:
        agent_id: The agent ID (for path consistency)
        prompt_id: The prompt ID
    """
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_id}"
            )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        raise
    
    return await prompt_controller.delete_prompt(prompt_id) 