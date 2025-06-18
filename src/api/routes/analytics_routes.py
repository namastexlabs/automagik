"""Analytics API routes for token usage reporting."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.services.token_analytics import TokenAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("/sessions/{session_id}/usage")
async def get_session_usage(session_id: str):
    """Get detailed token usage analytics for a specific session.
    
    Args:
        session_id: The session UUID to analyze
        
    Returns:
        Detailed usage summary grouped by model
    """
    try:
        result = TokenAnalyticsService.get_session_usage_summary(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: str,
    days: Optional[int] = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get token usage analytics for a specific user.
    
    Args:
        user_id: The user UUID to analyze
        days: Number of days to look back (default: 30)
        
    Returns:
        User usage summary across sessions
    """
    try:
        result = TokenAnalyticsService.get_user_usage_summary(user_id, days)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/usage")
async def get_agent_usage(
    agent_id: int,
    days: Optional[int] = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get token usage analytics for a specific agent.
    
    Args:
        agent_id: The agent ID to analyze
        days: Number of days to look back (default: 30)
        
    Returns:
        Agent usage summary across sessions and users
    """
    try:
        result = TokenAnalyticsService.get_agent_usage_summary(agent_id, days)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/top-usage")
async def get_top_usage_sessions(
    limit: Optional[int] = Query(10, description="Number of sessions to return", ge=1, le=100),
    days: Optional[int] = Query(7, description="Number of days to analyze", ge=1, le=365)
):
    """Get sessions with highest token usage.
    
    Args:
        limit: Number of top sessions to return (default: 10)
        days: Number of days to look back (default: 7)
        
    Returns:
        List of sessions ordered by token usage
    """
    try:
        result = TokenAnalyticsService.get_top_usage_sessions(limit, days)
        
        return {
            "sessions": result,
            "limit": limit,
            "days_analyzed": days,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting top usage sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))