"""API routes for Genie orchestrator."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from src.agents.pydanticai.genie.agent import GenieAgent
from src.agents.pydanticai.genie.models import EpicRequest
from src.auth import get_api_key as verify_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global agent instance (will be moved to proper dependency injection)
_genie_agent: Optional[GenieAgent] = None


def get_genie_agent() -> GenieAgent:
    """Get or create the Genie agent instance."""
    global _genie_agent
    if _genie_agent is None:
        config = {
            "agent_id": "genie",
            "agent_name": "Genie Orchestrator",
            "session_id": "genie-api"
        }
        _genie_agent = GenieAgent(config)
    return _genie_agent


class CreateEpicRequest(BaseModel):
    """Request to create a new epic."""
    message: str = Field(..., description="Natural language epic description")
    budget_limit: float = Field(50.0, description="Maximum budget in USD")
    require_tests: bool = Field(True, description="Whether to require test workflow")
    require_pr: bool = Field(True, description="Whether to require PR workflow")
    approval_mode: str = Field("auto", description="Approval mode: 'auto' or 'manual'")


class EpicResponse(BaseModel):
    """Response from epic creation."""
    epic_id: str
    title: str
    status: str
    planned_workflows: List[str]
    estimated_cost: float
    approval_required: bool
    tracking_url: str


class EpicStatusResponse(BaseModel):
    """Epic status response."""
    epic_id: str
    title: str
    phase: str
    current_workflow: Optional[str]
    completed_workflows: List[str]
    cost_accumulated: float
    cost_limit: float
    pending_approvals: List[str]
    error_count: int
    updated_at: Optional[str]


class ApprovalRequest(BaseModel):
    """Approval decision request."""
    decision: str = Field(..., description="Decision: 'approve', 'deny', or 'rollback'")
    comments: Optional[str] = Field(None, description="Optional comments")


@router.post("/run", response_model=EpicResponse)
async def create_epic(
    request: CreateEpicRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
) -> EpicResponse:
    """Create and execute a new development epic.
    
    This endpoint accepts a natural language description of a development task
    and orchestrates the appropriate Claude Code workflows to complete it.
    """
    try:
        agent = get_genie_agent()
        
        # Create the epic request
        epic_request = EpicRequest(
            message=request.message,
            context={"api_key": api_key},
            budget_limit=request.budget_limit,
            require_tests=request.require_tests,
            require_pr=request.require_pr,
            approval_mode=request.approval_mode
        )
        
        # Use the agent's create_epic tool
        result = await agent.agent.arun(
            f"Create an epic: {request.message}",
            deps=agent.dependencies,
            tool_calls={
                "create_epic": {
                    "request": request.message,
                    "budget_limit": request.budget_limit,
                    "require_tests": request.require_tests,
                    "require_pr": request.require_pr,
                    "approval_mode": request.approval_mode
                }
            }
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return EpicResponse(
            epic_id=result["epic_id"],
            title=result["title"],
            status=result["status"],
            planned_workflows=result["planned_workflows"],
            estimated_cost=result["estimated_cost"],
            approval_required=result["approval_required"],
            tracking_url=result["tracking_url"]
        )
        
    except Exception as e:
        logger.error(f"Error creating epic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{epic_id}", response_model=EpicStatusResponse)
async def get_epic_status(
    epic_id: str,
    api_key: str = Depends(verify_api_key)
) -> EpicStatusResponse:
    """Get the current status of an epic."""
    try:
        agent = get_genie_agent()
        
        # Use the agent's get_epic_status tool
        result = await agent.agent.arun(
            f"Get status of epic {epic_id}",
            deps=agent.dependencies,
            tool_calls={
                "get_epic_status": {
                    "epic_id": epic_id
                }
            }
        )
        
        if "error" in result:
            if result.get("status") == "not_found":
                raise HTTPException(status_code=404, detail=f"Epic {epic_id} not found")
            raise HTTPException(status_code=400, detail=result["error"])
            
        return EpicStatusResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting epic status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{epic_id}/{approval_id}")
async def approve_epic_step(
    epic_id: str,
    approval_id: str,
    request: ApprovalRequest,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Approve or deny a pending epic approval."""
    try:
        agent = get_genie_agent()
        
        # Use the agent's approve_epic_step tool
        result = await agent.agent.arun(
            f"Process approval for epic {epic_id}",
            deps=agent.dependencies,
            tool_calls={
                "approve_epic_step": {
                    "epic_id": epic_id,
                    "approval_id": approval_id,
                    "decision": request.decision,
                    "comments": request.comments
                }
            }
        )
        
        if "error" in result:
            if result.get("status") == "not_found":
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_active_epics(
    api_key: str = Depends(verify_api_key)
) -> List[Dict[str, Any]]:
    """List all active epics."""
    try:
        agent = get_genie_agent()
        
        # Use the agent's list_active_epics tool
        result = await agent.agent.arun(
            "List all active epics",
            deps=agent.dependencies,
            tool_calls={
                "list_active_epics": {}
            }
        )
        
        return result if isinstance(result, list) else []
        
    except Exception as e:
        logger.error(f"Error listing epics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{epic_id}")
async def stop_epic(
    epic_id: str,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, str]:
    """Stop a running epic."""
    try:
        agent = get_genie_agent()
        
        # Check if epic exists
        status_result = await agent.agent.arun(
            f"Get status of epic {epic_id}",
            deps=agent.dependencies,
            tool_calls={
                "get_epic_status": {
                    "epic_id": epic_id
                }
            }
        )
        
        if "error" in status_result:
            raise HTTPException(status_code=404, detail=f"Epic {epic_id} not found")
        
        # For now, just mark as cancelled
        # TODO: Implement actual workflow stopping via Claude Code API
        agent.active_epics[epic_id]["phase"] = "cancelled"
        
        return {
            "status": "stopped",
            "epic_id": epic_id,
            "message": f"Epic {epic_id} has been stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping epic: {e}")
        raise HTTPException(status_code=500, detail=str(e))