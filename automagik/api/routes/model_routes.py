"""API routes for model management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import logging

from automagik.services.model_discovery import ModelDiscoveryService
from automagik.db import get_agent_by_name, execute_query
from automagik.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


class ModelUpdate(BaseModel):
    """Request body for updating agent model."""
    model: str  # e.g. "openai:gpt-4" or "anthropic:claude-3-5-sonnet"


@router.get("/models")
async def list_available_models(api_key: str = Depends(verify_api_key)) -> dict:
    """Get all available models based on configured API keys."""
    try:
        service = ModelDiscoveryService()
        models = await service.get_available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available models")


@router.get("/agents/{agent_name}/model")
async def get_agent_model(agent_name: str, api_key: str = Depends(verify_api_key)) -> dict:
    """Get current model for an agent."""
    agent = get_agent_by_name(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Return current model or default
    model = agent.model or "gpt-4.1-mini"
    return {"agent": agent_name, "model": model}


@router.put("/agents/{agent_name}/model")
async def update_agent_model(
    agent_name: str, 
    request: ModelUpdate,
    _: bool = Depends(verify_api_key)
) -> dict:
    """Update model for an agent."""
    agent = get_agent_by_name(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    try:
        # Update model in database
        execute_query(
            "UPDATE agents SET model = %s, updated_at = CURRENT_TIMESTAMP WHERE name = %s",
            (request.model, agent_name)
        )
        
        logger.info(f"Updated model for agent '{agent_name}' to '{request.model}'")
        return {"agent": agent_name, "model": request.model, "updated": True}
    except Exception as e:
        logger.error(f"Error updating model for agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update agent model")