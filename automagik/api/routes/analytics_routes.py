"""Analytics API routes for token usage reporting using repository pattern."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List, Any
import logging
import uuid
from datetime import datetime, timedelta

from automagik.db import list_session_messages, list_sessions
from automagik.db.connection import safe_uuid

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


def _extract_usage_from_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper function to extract and aggregate enhanced usage data from messages."""
    total_tokens = 0
    total_requests = 0
    models = {}
    message_count = 0
    total_estimated_cost = 0.0
    global_content_types = set()
    total_processing_time = 0.0
    
    for message in messages:
        usage = message.get('usage')
        if not usage:
            continue
        
        # Parse usage data if it's a string
        if isinstance(usage, str):
            try:
                import json
                usage = json.loads(usage)
            except:
                continue
        
        if not isinstance(usage, dict):
            continue
            
        message_count += 1
            
        model = usage.get('model', 'unknown')
        framework = usage.get('framework', 'unknown')
        key = f"{model}_{framework}"
        
        if key not in models:
            models[key] = {
                "model": model,
                "framework": framework,
                "message_count": 0,
                "total_requests": 0,
                "request_tokens": 0,
                "response_tokens": 0,
                "total_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                # Enhanced usage tracking fields
                "content_types": set(),
                "processing_time_ms": 0.0,
                "estimated_cost_usd": 0.0,
                "cost_breakdown": {},
                "media_costs": {},
                "framework_events": [],
                "image_tokens": 0,
                "audio_tokens": 0,
                "video_tokens": 0
            }
        
        # Aggregate basic usage data
        models[key]["message_count"] += 1
        models[key]["total_requests"] += usage.get('total_requests', 0)
        models[key]["request_tokens"] += usage.get('request_tokens', 0)
        models[key]["response_tokens"] += usage.get('response_tokens', 0)
        models[key]["total_tokens"] += usage.get('total_tokens', 0)
        models[key]["cache_creation_tokens"] += usage.get('cache_creation_tokens', 0)
        models[key]["cache_read_tokens"] += usage.get('cache_read_tokens', 0)
        
        # Aggregate enhanced usage fields
        if 'content_types' in usage and usage['content_types']:
            content_types = usage['content_types']
            if isinstance(content_types, list):
                models[key]["content_types"].update(content_types)
                global_content_types.update(content_types)
        
        if 'processing_time_ms' in usage:
            models[key]["processing_time_ms"] += usage.get('processing_time_ms', 0.0)
            total_processing_time += usage.get('processing_time_ms', 0.0)
        
        if 'estimated_cost_usd' in usage:
            models[key]["estimated_cost_usd"] += usage.get('estimated_cost_usd', 0.0)
            total_estimated_cost += usage.get('estimated_cost_usd', 0.0)
        
        if 'cost_breakdown' in usage and usage['cost_breakdown']:
            breakdown = usage['cost_breakdown']
            for cost_type, cost_value in breakdown.items():
                if cost_type not in models[key]["cost_breakdown"]:
                    models[key]["cost_breakdown"][cost_type] = 0.0
                models[key]["cost_breakdown"][cost_type] += cost_value
        
        if 'media_costs' in usage and usage['media_costs']:
            media_costs = usage['media_costs']
            for media_type, cost_data in media_costs.items():
                if media_type not in models[key]["media_costs"]:
                    models[key]["media_costs"][media_type] = {"cost": 0.0, "tokens": 0}
                if isinstance(cost_data, dict):
                    models[key]["media_costs"][media_type]["cost"] += cost_data.get("cost", 0.0)
                    models[key]["media_costs"][media_type]["tokens"] += cost_data.get("tokens", 0)
        
        if 'framework_events' in usage and usage['framework_events']:
            events = usage['framework_events']
            if isinstance(events, list):
                models[key]["framework_events"].extend(events)
        
        # Aggregate media token usage
        models[key]["image_tokens"] += usage.get('image_tokens', 0)
        models[key]["audio_tokens"] += usage.get('audio_tokens', 0) 
        models[key]["video_tokens"] += usage.get('video_tokens', 0)
        
        total_tokens += usage.get('total_tokens', 0)
        total_requests += usage.get('total_requests', 0)
    
    # Convert sets to lists for JSON serialization
    for model in models.values():
        model["content_types"] = list(model["content_types"])
    
    return {
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "message_count": message_count,
        "models": list(models.values()),
        "unique_models": len(models),
        # Enhanced aggregated data
        "total_estimated_cost_usd": total_estimated_cost,
        "global_content_types": list(global_content_types),
        "total_processing_time_ms": total_processing_time,
        "has_multimodal_content": bool(global_content_types - {'text'}),
        "total_image_tokens": sum(m.get("image_tokens", 0) for m in models.values()),
        "total_audio_tokens": sum(m.get("audio_tokens", 0) for m in models.values()),
        "total_video_tokens": sum(m.get("video_tokens", 0) for m in models.values())
    }


@router.get("/sessions/{session_id}/usage")
async def get_session_usage(session_id: str):
    """Get detailed token usage analytics for a specific session.
    
    Args:
        session_id: The session UUID to analyze
        
    Returns:
        Detailed usage summary grouped by model
    """
    try:
        # Validate session ID
        session_uuid = safe_uuid(session_id)
        if not session_uuid:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Get all messages for the session
        messages, total_count = list_session_messages(session_uuid)
        
        if not messages:
            return {
                "session_id": session_id,
                "total_tokens": 0,
                "total_requests": 0,
                "models": [],
                "summary": {
                    "message_count": 0,
                    "unique_models": 0,
                    "total_request_tokens": 0,
                    "total_response_tokens": 0,
                    "total_cache_tokens": 0,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                },
                "enhanced_analytics": {
                    "total_estimated_cost_usd": 0.0,
                    "global_content_types": [],
                    "total_processing_time_ms": 0.0,
                    "has_multimodal_content": False,
                    "total_image_tokens": 0,
                    "total_audio_tokens": 0,
                    "total_video_tokens": 0
                }
            }
        
        # Extract usage data
        usage_data = _extract_usage_from_messages(messages)
        
        # Calculate summary
        total_request_tokens = sum(m["request_tokens"] for m in usage_data["models"])
        total_response_tokens = sum(m["response_tokens"] for m in usage_data["models"])
        total_cache_tokens = sum(m["cache_creation_tokens"] + m["cache_read_tokens"] for m in usage_data["models"])
        
        return {
            "session_id": session_id,
            "total_tokens": usage_data["total_tokens"],
            "total_requests": usage_data["total_requests"],
            "models": usage_data["models"],
            "summary": {
                "message_count": usage_data["message_count"],
                "unique_models": usage_data["unique_models"],
                "total_request_tokens": total_request_tokens,
                "total_response_tokens": total_response_tokens,
                "total_cache_tokens": total_cache_tokens,
                "analysis_timestamp": datetime.utcnow().isoformat()
            },
            # Enhanced usage analytics
            "enhanced_analytics": {
                "total_estimated_cost_usd": usage_data.get("total_estimated_cost_usd", 0.0),
                "global_content_types": usage_data.get("global_content_types", []),
                "total_processing_time_ms": usage_data.get("total_processing_time_ms", 0.0),
                "has_multimodal_content": usage_data.get("has_multimodal_content", False),
                "total_image_tokens": usage_data.get("total_image_tokens", 0),
                "total_audio_tokens": usage_data.get("total_audio_tokens", 0),
                "total_video_tokens": usage_data.get("total_video_tokens", 0)
            }
        }
        
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
        # Validate user ID
        user_uuid = safe_uuid(user_id)
        if not user_uuid:
            raise HTTPException(status_code=400, detail="Invalid user ID")
        
        # Get user sessions
        sessions, _ = list_sessions(user_id=user_uuid, page_size=1000)  # Limit to prevent huge queries
        
        if not sessions:
            return {
                "user_id": user_id,
                "days_analyzed": days,
                "total_tokens": 0,
                "models": [],
                "summary": {"session_count": 0, "message_count": 0, "unique_models": 0}
            }
        
        # Collect all messages from all sessions
        all_messages = []
        session_count = 0
        
        # Filter sessions by date if specified
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
        for session in sessions:
            # Skip sessions outside date range
            if days and session.get('created_at'):
                try:
                    session_date = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                    if session_date < cutoff_date:
                        continue
                except:
                    pass  # Continue if date parsing fails
            
            session_count += 1
            session_uuid = safe_uuid(session['id'])
            if session_uuid:
                messages, _ = list_session_messages(session_uuid)
                all_messages.extend(messages)
        
        # Extract usage data
        usage_data = _extract_usage_from_messages(all_messages)
        
        return {
            "user_id": user_id,
            "days_analyzed": days,
            "total_tokens": usage_data["total_tokens"],
            "models": usage_data["models"],
            "summary": {
                "session_count": session_count,
                "message_count": usage_data["message_count"],
                "unique_models": usage_data["unique_models"],
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        }
        
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
        Agent usage summary across sessions
    """
    try:
        # Get agent sessions
        sessions, _ = list_sessions(agent_id=agent_id, page_size=1000)
        
        if not sessions:
            return {
                "agent_id": agent_id,
                "days_analyzed": days,
                "total_tokens": 0,
                "models": [],
                "summary": {"session_count": 0, "user_count": 0, "message_count": 0, "unique_models": 0}
            }
        
        # Collect all messages from all sessions
        all_messages = []
        session_count = 0
        unique_users = set()
        
        # Filter sessions by date if specified
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
        for session in sessions:
            # Skip sessions outside date range
            if days and session.get('created_at'):
                try:
                    session_date = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                    if session_date < cutoff_date:
                        continue
                except:
                    pass
            
            session_count += 1
            if session.get('user_id'):
                unique_users.add(session['user_id'])
            
            session_uuid = safe_uuid(session['id'])
            if session_uuid:
                messages, _ = list_session_messages(session_uuid)
                all_messages.extend(messages)
        
        # Extract usage data
        usage_data = _extract_usage_from_messages(all_messages)
        
        return {
            "agent_id": agent_id,
            "days_analyzed": days,
            "total_tokens": usage_data["total_tokens"],
            "models": usage_data["models"],
            "summary": {
                "session_count": session_count,
                "user_count": len(unique_users),
                "message_count": usage_data["message_count"],
                "unique_models": usage_data["unique_models"],
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/top-usage")
async def get_top_usage_sessions(
    limit: Optional[int] = Query(10, description="Number of top sessions to return", ge=1, le=100),
    days: Optional[int] = Query(7, description="Number of days to look back", ge=1, le=365)
):
    """Get sessions with highest token usage.
    
    Args:
        limit: Number of top sessions to return (default: 10)
        days: Number of days to look back (default: 7)
        
    Returns:
        List of sessions ordered by token usage
    """
    try:
        # Get all sessions within date range
        sessions, _ = list_sessions(page_size=1000)  # Get up to 1000 sessions
        
        if not sessions:
            return {
                "count": 0,
                "limit": limit,
                "days_analyzed": days,
                "sessions": []
            }
        
        session_usage = []
        
        # Filter sessions by date if specified
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for session in sessions:
            # Skip sessions outside date range
            if days and session.get('created_at'):
                try:
                    session_date = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                    if session_date < cutoff_date:
                        continue
                except:
                    pass
            
            session_uuid = safe_uuid(session['id'])
            if not session_uuid:
                continue
                
            messages, _ = list_session_messages(session_uuid)
            usage_data = _extract_usage_from_messages(messages)
            
            if usage_data["total_tokens"] > 0:
                session_usage.append({
                    "session_id": str(session['id']),
                    "message_count": usage_data["message_count"],
                    "total_tokens": usage_data["total_tokens"],
                    "request_tokens": sum(m["request_tokens"] for m in usage_data["models"]),
                    "response_tokens": sum(m["response_tokens"] for m in usage_data["models"]),
                    "unique_models": usage_data["unique_models"],
                    "models_used": [m["model"] for m in usage_data["models"]],
                    "session_start": session.get('created_at'),
                    "session_end": session.get('updated_at')
                })
        
        # Sort by total tokens and limit
        session_usage.sort(key=lambda x: x["total_tokens"], reverse=True)
        session_usage = session_usage[:limit]
        
        return {
            "count": len(session_usage),
            "limit": limit,
            "days_analyzed": days,
            "sessions": session_usage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top usage sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))