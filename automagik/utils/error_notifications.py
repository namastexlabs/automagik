"""Error notification system for team alerts."""
import logging
import os
import json
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class ErrorNotifier:
    """Handles error notifications to the team."""
    
    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_ERROR_WEBHOOK")
        self.whatsapp_enabled = os.getenv("WHATSAPP_ERROR_NOTIFICATIONS", "false").lower() == "true"
        self.whatsapp_numbers = os.getenv("WHATSAPP_ERROR_NUMBERS", "").split(",")
        self.environment = os.getenv("ENVIRONMENT", "development")
        
    async def notify_error(
        self,
        error: Exception,
        agent_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Send error notification to team."""
        try:
            error_details = {
                "timestamp": datetime.utcnow().isoformat(),
                "environment": self.environment,
                "agent": agent_name,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "user_id": user_id,
                "session_id": session_id,
                "request_data": request_data,
                "context": context
            }
            
            # Extract additional details for HTTP errors
            if hasattr(error, 'status'):
                error_details['http_status'] = error.status
            
            if hasattr(error, 'url'):
                error_details['url'] = str(error.url)
                
            if hasattr(error, 'response'):
                try:
                    # Try to get response body for API errors
                    if hasattr(error.response, 'text'):
                        error_details['response_body'] = error.response.text[:1000]  # Limit size
                except:
                    pass
                    
            # For aiohttp ClientResponseError
            if type(error).__name__ == 'ClientResponseError':
                error_details['error_message'] = f"HTTP {getattr(error, 'status', 'Unknown')}: {getattr(error, 'message', str(error))}"
                if hasattr(error, 'request_info'):
                    error_details['request_method'] = error.request_info.method
                    error_details['request_url'] = str(error.request_info.url)
            
            # Log the error
            logger.error(f"Agent error for {agent_name}: {error}", extra=error_details)
            
            # Send to monitoring service (if configured)
            await self._send_to_monitoring(error_details)
            
            # Send Slack notification
            if self.slack_webhook:
                await self._send_slack_notification(error_details)
                
            # Send WhatsApp notification for critical errors
            if self.whatsapp_enabled and self._is_critical_error(error):
                await self._send_whatsapp_notification(error_details)
                
        except Exception as e:
            # Don't let notification errors break the main flow
            logger.warning(f"Failed to send error notification: {e}")
    
    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if error is critical enough for WhatsApp notification."""
        critical_errors = [
            "DatabaseError",
            "APIKeyError", 
            "OutOfMemoryError",
            "RateLimitError"
        ]
        return type(error).__name__ in critical_errors or "500" in str(error)
    
    async def _send_slack_notification(self, error_details: Dict[str, Any]):
        """Send error notification to Slack."""
        try:
            async with httpx.AsyncClient() as client:
                message = {
                    "text": f"🚨 Agent Error in {error_details['environment']}",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"🚨 {error_details['agent']} Agent Error"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Environment:* {error_details['environment']}"
                                },
                                {
                                    "type": "mrkdwn", 
                                    "text": f"*Error Type:* {error_details['error_type']}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Session:* {error_details['session_id'] or 'N/A'}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*User:* {error_details['user_id'] or 'N/A'}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Error Message:*\n```{error_details['error_message'][:500]}```"
                            }
                        }
                    ]
                }
                
                if error_details['environment'] == 'production':
                    message["blocks"].append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ *This is a PRODUCTION error!*"
                        }
                    })
                
                await client.post(self.slack_webhook, json=message)
                
        except Exception as e:
            logger.debug(f"Failed to send Slack notification: {e}")
    
    async def _send_whatsapp_notification(self, error_details: Dict[str, Any]):
        """Send critical error notification via WhatsApp."""
        try:
            # This would integrate with Evolution API or WhatsApp Business API
            message = (
                f"🚨 CRITICAL ERROR - {error_details['environment']}\n"
                f"Agent: {error_details['agent']}\n"
                f"Error: {error_details['error_type']}\n"
                f"Message: {error_details['error_message'][:100]}...\n"
                f"Time: {error_details['timestamp']}"
            )
            
            # TODO: Implement actual WhatsApp sending
            logger.info(f"Would send WhatsApp notification: {message}")
            
        except Exception as e:
            logger.debug(f"Failed to send WhatsApp notification: {e}")
    
    async def _send_to_monitoring(self, error_details: Dict[str, Any]):
        """Send error to monitoring service (e.g., Sentry, DataDog)."""
        try:
            # TODO: Integrate with monitoring service
            pass
        except Exception as e:
            logger.debug(f"Failed to send to monitoring: {e}")


# Singleton instance
error_notifier = ErrorNotifier()


async def notify_agent_error(
    error: Exception,
    agent_name: str,
    error_webhook_url: Optional[str] = None,
    **kwargs
):
    """Convenience function to notify about agent errors."""
    # Send to agent-specific webhook if configured
    if error_webhook_url:
        await send_to_webhook(error_webhook_url, error, agent_name, **kwargs)
    
    # Also send to general notification system
    await error_notifier.notify_error(error, agent_name, **kwargs)


async def send_to_webhook(webhook_url: str, error: Exception, agent_name: str, **kwargs):
    """Send error notification to a custom webhook."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            error_info = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }
            
            # Add HTTP error details if available
            if hasattr(error, 'status'):
                error_info['http_status'] = error.status
            if hasattr(error, 'url'):
                error_info['url'] = str(error.url)
            if hasattr(error, 'response'):
                try:
                    if hasattr(error.response, 'text'):
                        error_info['response_body'] = error.response.text[:1000]
                except:
                    pass
            
            # For aiohttp ClientResponseError
            if type(error).__name__ == 'ClientResponseError':
                error_info['message'] = f"HTTP {getattr(error, 'status', 'Unknown')}: {getattr(error, 'message', str(error))}"
                if hasattr(error, 'request_info'):
                    error_info['request_method'] = error.request_info.method
                    error_info['request_url'] = str(error.request_info.url)
            
            payload = {
                "event": "agent_error",
                "agent": agent_name,
                "error": error_info,
                "context": {
                    "user_id": kwargs.get("user_id"),
                    "session_id": kwargs.get("session_id"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "request_content": kwargs.get("request_content"),
                    "request_data": kwargs.get("request_data")
                },
                "metadata": kwargs.get("context", {})
            }
            
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                logger.warning(f"Webhook returned error status: {response.status_code}")
                
    except Exception as e:
        logger.warning(f"Failed to send webhook notification: {e}")