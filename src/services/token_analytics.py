"""Token Analytics Service for usage tracking and reporting.

This service provides functionality to analyze token usage data stored in the messages table
and generate analytics reports for sessions, users, and agents.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid

from src.db.connection import execute_query, safe_uuid

logger = logging.getLogger(__name__)


class TokenAnalyticsService:
    """Service for analyzing token usage data and generating analytics reports."""
    
    @staticmethod
    def get_session_usage_summary(session_id: str) -> Dict[str, Any]:
        """Get token usage summary for a specific session grouped by model.
        
        Args:
            session_id: The session UUID to analyze
            
        Returns:
            Dictionary containing usage summary with model breakdown
        """
        try:
            session_uuid = safe_uuid(session_id)
            if not session_uuid:
                logger.error(f"Invalid session ID: {session_id}")
                return {"error": "Invalid session ID"}
            
            # Query to aggregate usage data by model for the session
            query = """
                SELECT 
                    usage->>'model' as model,
                    usage->>'framework' as framework,
                    COUNT(*) as message_count,
                    COALESCE(SUM(CAST(usage->>'total_requests' AS INTEGER)), 0) as total_requests,
                    COALESCE(SUM(CAST(usage->>'request_tokens' AS INTEGER)), 0) as total_request_tokens,
                    COALESCE(SUM(CAST(usage->>'response_tokens' AS INTEGER)), 0) as total_response_tokens,
                    COALESCE(SUM(CAST(usage->>'total_tokens' AS INTEGER)), 0) as total_tokens,
                    COALESCE(SUM(CAST(usage->>'cache_creation_tokens' AS INTEGER)), 0) as total_cache_creation_tokens,
                    COALESCE(SUM(CAST(usage->>'cache_read_tokens' AS INTEGER)), 0) as total_cache_read_tokens,
                    MIN(created_at) as first_usage,
                    MAX(created_at) as last_usage
                FROM messages 
                WHERE session_id = %s 
                    AND usage IS NOT NULL 
                    AND usage != 'null'
                    AND usage->>'model' IS NOT NULL
                GROUP BY usage->>'model', usage->>'framework'
                ORDER BY total_tokens DESC
            """
            
            result = execute_query(query, (session_uuid,))
            
            if not result:
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
                        "total_cache_tokens": 0
                    }
                }
            
            # Process results by model
            models = []
            total_session_tokens = 0
            total_session_requests = 0
            total_request_tokens = 0
            total_response_tokens = 0
            total_cache_tokens = 0
            total_messages = 0
            
            for row in result:
                model_data = {
                    "model": row.get("model"),
                    "framework": row.get("framework"),
                    "message_count": row.get("message_count", 0),
                    "total_requests": row.get("total_requests", 0),
                    "request_tokens": row.get("total_request_tokens", 0),
                    "response_tokens": row.get("total_response_tokens", 0),
                    "total_tokens": row.get("total_tokens", 0),
                    "cache_creation_tokens": row.get("total_cache_creation_tokens", 0),
                    "cache_read_tokens": row.get("total_cache_read_tokens", 0),
                    "first_usage": row.get("first_usage"),
                    "last_usage": row.get("last_usage")
                }
                
                models.append(model_data)
                
                # Aggregate totals
                total_session_tokens += model_data["total_tokens"]
                total_session_requests += model_data["total_requests"]
                total_request_tokens += model_data["request_tokens"]
                total_response_tokens += model_data["response_tokens"]
                total_cache_tokens += model_data["cache_creation_tokens"] + model_data["cache_read_tokens"]
                total_messages += model_data["message_count"]
            
            return {
                "session_id": session_id,
                "total_tokens": total_session_tokens,
                "total_requests": total_session_requests,
                "models": models,
                "summary": {
                    "message_count": total_messages,
                    "unique_models": len(models),
                    "total_request_tokens": total_request_tokens,
                    "total_response_tokens": total_response_tokens,
                    "total_cache_tokens": total_cache_tokens,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session usage summary for {session_id}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_user_usage_summary(user_id: str, days: Optional[int] = 30) -> Dict[str, Any]:
        """Get token usage summary for a specific user across sessions.
        
        Args:
            user_id: The user UUID to analyze
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary containing user usage summary
        """
        try:
            user_uuid = safe_uuid(user_id)
            if not user_uuid:
                logger.error(f"Invalid user ID: {user_id}")
                return {"error": "Invalid user ID"}
            
            # Calculate date filter
            start_date = datetime.utcnow() - timedelta(days=days) if days else None
            
            # Build query with optional date filter
            date_filter = "AND created_at >= %s" if start_date else ""
            params = [user_uuid]
            if start_date:
                params.append(start_date)
            
            query = f"""
                SELECT 
                    usage->>'model' as model,
                    usage->>'framework' as framework,
                    COUNT(DISTINCT session_id) as session_count,
                    COUNT(*) as message_count,
                    COALESCE(SUM(CAST(usage->>'total_requests' AS INTEGER)), 0) as total_requests,
                    COALESCE(SUM(CAST(usage->>'request_tokens' AS INTEGER)), 0) as total_request_tokens,
                    COALESCE(SUM(CAST(usage->>'response_tokens' AS INTEGER)), 0) as total_response_tokens,
                    COALESCE(SUM(CAST(usage->>'total_tokens' AS INTEGER)), 0) as total_tokens,
                    MIN(created_at) as first_usage,
                    MAX(created_at) as last_usage
                FROM messages 
                WHERE user_id = %s 
                    AND usage IS NOT NULL 
                    AND usage != 'null'
                    AND usage->>'model' IS NOT NULL
                    {date_filter}
                GROUP BY usage->>'model', usage->>'framework'
                ORDER BY total_tokens DESC
            """
            
            result = execute_query(query, params)
            
            if not result:
                return {
                    "user_id": user_id,
                    "days_analyzed": days,
                    "total_tokens": 0,
                    "models": [],
                    "summary": {"session_count": 0, "message_count": 0}
                }
            
            # Process results
            models = []
            total_tokens = 0
            total_sessions = 0
            total_messages = 0
            
            for row in result:
                model_data = {
                    "model": row.get("model"),
                    "framework": row.get("framework"),
                    "session_count": row.get("session_count", 0),
                    "message_count": row.get("message_count", 0),
                    "total_requests": row.get("total_requests", 0),
                    "request_tokens": row.get("total_request_tokens", 0),
                    "response_tokens": row.get("total_response_tokens", 0),
                    "total_tokens": row.get("total_tokens", 0),
                    "first_usage": row.get("first_usage"),
                    "last_usage": row.get("last_usage")
                }
                
                models.append(model_data)
                total_tokens += model_data["total_tokens"]
                total_sessions += model_data["session_count"]
                total_messages += model_data["message_count"]
            
            return {
                "user_id": user_id,
                "days_analyzed": days,
                "total_tokens": total_tokens,
                "models": models,
                "summary": {
                    "session_count": total_sessions,
                    "message_count": total_messages,
                    "unique_models": len(models),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user usage summary for {user_id}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_agent_usage_summary(agent_id: int, days: Optional[int] = 30) -> Dict[str, Any]:
        """Get token usage summary for a specific agent.
        
        Args:
            agent_id: The agent ID to analyze
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary containing agent usage summary
        """
        try:
            # Calculate date filter
            start_date = datetime.utcnow() - timedelta(days=days) if days else None
            
            # Build query with optional date filter
            date_filter = "AND created_at >= %s" if start_date else ""
            params = [agent_id]
            if start_date:
                params.append(start_date)
            
            query = f"""
                SELECT 
                    usage->>'model' as model,
                    usage->>'framework' as framework,
                    COUNT(DISTINCT session_id) as session_count,
                    COUNT(DISTINCT user_id) as user_count,
                    COUNT(*) as message_count,
                    COALESCE(SUM(CAST(usage->>'total_requests' AS INTEGER)), 0) as total_requests,
                    COALESCE(SUM(CAST(usage->>'request_tokens' AS INTEGER)), 0) as total_request_tokens,
                    COALESCE(SUM(CAST(usage->>'response_tokens' AS INTEGER)), 0) as total_response_tokens,
                    COALESCE(SUM(CAST(usage->>'total_tokens' AS INTEGER)), 0) as total_tokens,
                    MIN(created_at) as first_usage,
                    MAX(created_at) as last_usage
                FROM messages 
                WHERE agent_id = %s 
                    AND usage IS NOT NULL 
                    AND usage != 'null'
                    AND usage->>'model' IS NOT NULL
                    {date_filter}
                GROUP BY usage->>'model', usage->>'framework'
                ORDER BY total_tokens DESC
            """
            
            result = execute_query(query, params)
            
            if not result:
                return {
                    "agent_id": agent_id,
                    "days_analyzed": days,
                    "total_tokens": 0,
                    "models": [],
                    "summary": {"session_count": 0, "user_count": 0, "message_count": 0}
                }
            
            # Process results
            models = []
            total_tokens = 0
            total_sessions = 0
            total_users = 0
            total_messages = 0
            
            for row in result:
                model_data = {
                    "model": row.get("model"),
                    "framework": row.get("framework"),
                    "session_count": row.get("session_count", 0),
                    "user_count": row.get("user_count", 0),
                    "message_count": row.get("message_count", 0),
                    "total_requests": row.get("total_requests", 0),
                    "request_tokens": row.get("total_request_tokens", 0),
                    "response_tokens": row.get("total_response_tokens", 0),
                    "total_tokens": row.get("total_tokens", 0),
                    "first_usage": row.get("first_usage"),
                    "last_usage": row.get("last_usage")
                }
                
                models.append(model_data)
                total_tokens += model_data["total_tokens"]
                total_sessions += model_data["session_count"]
                total_users += model_data["user_count"]
                total_messages += model_data["message_count"]
            
            return {
                "agent_id": agent_id,
                "days_analyzed": days,
                "total_tokens": total_tokens,
                "models": models,
                "summary": {
                    "session_count": total_sessions,
                    "user_count": total_users,
                    "message_count": total_messages,
                    "unique_models": len(models),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting agent usage summary for {agent_id}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_top_usage_sessions(limit: int = 10, days: Optional[int] = 7) -> List[Dict[str, Any]]:
        """Get sessions with highest token usage.
        
        Args:
            limit: Number of top sessions to return
            days: Number of days to look back (default: 7)
            
        Returns:
            List of sessions ordered by token usage
        """
        try:
            # Calculate date filter
            start_date = datetime.utcnow() - timedelta(days=days) if days else None
            
            # Build query with optional date filter
            date_filter = "AND created_at >= %s" if start_date else ""
            params = []
            if start_date:
                params.append(start_date)
            params.append(limit)
            
            query = f"""
                SELECT 
                    session_id,
                    COUNT(*) as message_count,
                    COALESCE(SUM(CAST(usage->>'total_tokens' AS INTEGER)), 0) as total_tokens,
                    COALESCE(SUM(CAST(usage->>'request_tokens' AS INTEGER)), 0) as request_tokens,
                    COALESCE(SUM(CAST(usage->>'response_tokens' AS INTEGER)), 0) as response_tokens,
                    MIN(created_at) as session_start,
                    MAX(created_at) as session_end,
                    COUNT(DISTINCT usage->>'model') as unique_models,
                    array_agg(DISTINCT usage->>'model') as models_used
                FROM messages 
                WHERE usage IS NOT NULL 
                    AND usage != 'null'
                    AND usage->>'total_tokens' IS NOT NULL
                    {date_filter}
                GROUP BY session_id
                HAVING SUM(CAST(usage->>'total_tokens' AS INTEGER)) > 0
                ORDER BY total_tokens DESC
                LIMIT %s
            """
            
            result = execute_query(query, params)
            
            if not result:
                return []
            
            sessions = []
            for row in result:
                session_data = {
                    "session_id": str(row.get("session_id")),
                    "message_count": row.get("message_count", 0),
                    "total_tokens": row.get("total_tokens", 0),
                    "request_tokens": row.get("request_tokens", 0),
                    "response_tokens": row.get("response_tokens", 0),
                    "session_start": row.get("session_start"),
                    "session_end": row.get("session_end"),
                    "unique_models": row.get("unique_models", 0),
                    "models_used": row.get("models_used", [])
                }
                sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting top usage sessions: {e}")
            return []