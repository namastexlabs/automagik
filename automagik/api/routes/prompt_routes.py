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
from automagik.db.repository import agent as agent_repo
from automagik.db.models import Agent

# Create router for prompt endpoints
prompt_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)


def resolve_agent_by_identifier(identifier: str) -> Optional[Agent]:
    """Resolve an agent by either name or ID.
    
    Args:
        identifier: Either agent name (string) or agent ID (numeric string)
        
    Returns:
        Agent object if found, None otherwise
    """
    # Try to parse as integer ID first
    try:
        agent_id = int(identifier)
        agent = agent_repo.get_agent(agent_id)
        if agent:
            return agent
    except ValueError:
        # Not a numeric ID, continue to name lookup
        pass
    
    # Try to find by name
    return agent_repo.get_agent_by_name(identifier)

@prompt_router.get(
    "/agent/{agent_identifier}/prompt",
    response_model=PromptListResponse,
    tags=["Prompts"],
    summary="List Prompts for Agent",
    description="Returns a list of all prompts for the specified agent, optionally filtered by status key."
)
async def list_prompts(
    agent_identifier: str = Path(..., description="The name or ID of the agent to list prompts for"),
    status_key: Optional[str] = Query(None, description="Filter prompts by status key")
):
    """
    Get a list of all prompts for an agent, optionally filtered by status key.
    
    Args:
        agent_identifier: The agent name or ID
        status_key: Optional status key to filter by
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    return await prompt_controller.list_prompts(agent.id, status_key)

@prompt_router.get(
    "/agent/{agent_identifier}/prompt/{prompt_id}",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Get Prompt by ID",
    description="Returns the details of a specific prompt."
)
async def get_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to retrieve")
):
    """
    Get a prompt by ID.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_id: The prompt ID
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    # Get the prompt
    prompt = await prompt_controller.get_prompt(prompt_id)
    
    # Verify the prompt belongs to the specified agent
    if prompt.agent_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found for agent {agent_identifier}"
        )
    
    return prompt

@prompt_router.post(
    "/agent/{agent_identifier}/prompt",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Create New Prompt",
    description="Creates a new prompt for the specified agent.",
    status_code=status.HTTP_201_CREATED
)
async def create_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent to create a prompt for"),
    prompt_data: PromptCreateRequest = Body(..., description="The prompt data")
):
    """
    Create a new prompt for an agent.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_data: The prompt data
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    return await prompt_controller.create_prompt(agent.id, prompt_data.model_dump())

@prompt_router.put(
    "/agent/{agent_identifier}/prompt/{prompt_id}",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Update Prompt",
    description="Updates an existing prompt."
)
async def update_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to update"),
    prompt_data: PromptUpdateRequest = Body(..., description="The updated prompt data")
):
    """
    Update an existing prompt.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_id: The prompt ID
        prompt_data: The updated prompt data
    """
    logger.debug(f"Updating prompt {prompt_id} for agent {agent_identifier}")
    logger.debug(f"Prompt data received: {prompt_data}")
    
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_identifier}"
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
    "/agent/{agent_identifier}/prompt/{prompt_id}/activate",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Activate Prompt",
    description="Sets a prompt as active for its agent and status key, deactivating other prompts."
)
async def activate_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to activate")
):
    """
    Set a prompt as active.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_id: The prompt ID
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_identifier}"
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
    "/agent/{agent_identifier}/prompt/{prompt_id}/deactivate",
    response_model=PromptResponse,
    tags=["Prompts"],
    summary="Deactivate Prompt",
    description="Sets a prompt as inactive."
)
async def deactivate_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to deactivate")
):
    """
    Set a prompt as inactive.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_id: The prompt ID
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_identifier}"
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
    "/agent/{agent_identifier}/prompt/{prompt_id}",
    tags=["Prompts"],
    summary="Delete Prompt",
    description="Deletes a prompt."
)
async def delete_prompt(
    agent_identifier: str = Path(..., description="The name or ID of the agent"),
    prompt_id: int = Path(..., description="The ID of the prompt to delete")
):
    """
    Delete a prompt.
    
    Args:
        agent_identifier: The agent name or ID
        prompt_id: The prompt ID
    """
    # Resolve agent by identifier
    agent = resolve_agent_by_identifier(agent_identifier)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_identifier}' not found"
        )
    
    # First get the prompt to check if it belongs to this agent
    try:
        existing_prompt = await prompt_controller.get_prompt(prompt_id)
        if existing_prompt.agent_id != agent.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found for agent {agent_identifier}"
            )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )
        raise
    
    return await prompt_controller.delete_prompt(prompt_id) 