"""Evolution tool implementation.

This module provides the core functionality for Evolution tools.
"""
import logging
import aiohttp
from typing import Dict, Any
from pydantic_ai import RunContext

from automagik.config import settings
from .schema import SendMessageResponse, GetChatHistoryResponse

logger = logging.getLogger(__name__)

def get_send_message_description() -> str:
    """Get description for the send_message function."""
    return "Send a message to a phone number via Evolution API."

def get_chat_history_description() -> str:
    """Get description for the get_chat_history function."""
    return "Get chat history for a phone number from Evolution API."

async def send_message(ctx: RunContext[Dict], phone: str, message: str, token: str = None, instance: str = None, api_url: str = None) -> Dict[str, Any]:
    """Send a message to a phone number.

    Args:
        ctx: The run context
        phone: The phone number to send the message to
        message: The message content
        token: Evolution API token
        instance: Evolution instance
        api_url: Evolution API URL

    Returns:
        Dict with the response data
    """
    try:
        logger.info(f"Sending message to {phone}: {message}")
        
        # Get Evolution API configuration from settings
        api_url = settings.EVOLUTION_API_URL if not api_url else api_url
        token = settings.EVOLUTION_API_KEY if not token else token
        instance = settings.EVOLUTION_INSTANCE if not instance else instance
        
        if not api_url:
            raise ValueError("EVOLUTION_API_URL not configured in settings")
            
        # Prepare the request
        url = f"{api_url}/message/sendText/{instance}"
        headers = {
            "apikey": token,
            "Content-Type": "application/json"
        }
        
        # Ensure phone is a string and properly formatted
        if not isinstance(phone, str):
            phone = str(phone)
        
        payload = {
            "number": phone,
            "text": message
        }
        
        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                result = await response.json()
                
                # Check if the request was successful
                if "key" in result:
                    response = SendMessageResponse(
                        success=True,
                        message_id=result["key"]["id"],
                        timestamp=str(result.get("messageTimestamp", ""))
                    )
                else:
                    response = SendMessageResponse(
                        success=False,
                        error=f"Error: {result.get('error', 'Unknown error')}"
                    )
                return response.dict()
                
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        response = SendMessageResponse(
            success=False,
            error=f"Error: {str(e)}"
        )
        return response.dict()

async def get_chat_history(ctx: RunContext[Dict], token: str, phone: str, limit: int = 50) -> Dict[str, Any]:
    """Get chat history for a phone number.

    Args:
        ctx: The run context
        token: Evolution API token
        phone: The phone number to get history for
        limit: Maximum number of messages to return

    Returns:
        Dict with the chat history
    """
    try:
        logger.info(f"Getting chat history for {phone}, limit: {limit}")
        
        # Mock implementation - in a real implementation, this would use the Evolution API
        # Return mock data
        mock_messages = [
            {
                "id": "msg1",
                "from": phone,
                "content": "Hello, I need information about your products",
                "timestamp": "2023-06-01T11:50:00.000Z",
                "type": "incoming",
            },
            {
                "id": "msg2",
                "from": "system",
                "content": "Hi there! I'd be happy to help with information about our products. What specific products are you interested in?",
                "timestamp": "2023-06-01T11:51:00.000Z",
                "type": "outgoing",
            },
        ][:limit]
        
        response = GetChatHistoryResponse(
            success=True,
            messages=mock_messages
        )
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        response = GetChatHistoryResponse(
            success=False,
            error=f"Error: {str(e)}"
        )
        return response.dict()

# -----------------------------------------------------------------------------
# New Evolution helper tools
# -----------------------------------------------------------------------------

# NOTE: All Evolution wrappers now try to pull credentials directly from the
# incoming EvolutionMessagePayload (when available). If not found we fall back
# to settings so local tests still work.

async def send_reaction(
    ctx: RunContext[Dict],
    remote_jid: str,
    message_id: str,
    reaction: str,
    instance: str = None,
    api_url: str = None,
    api_key: str = None,
) -> Dict[str, Any]:
    """Send an emoji reaction to a specific WhatsApp message.

    Args:
        ctx: tool run context (unused but provided by framework)
        remote_jid: JID of chat (user@s.whatsapp.net or group@g.us)
        message_id: ID of the message to react to
        reaction: Emoji string to send (e.g., "��")
        instance: Evolution instance name (defaults to settings)
    """
    from .api import send_reaction as _api_send_reaction

    instance_name = instance or settings.EVOLUTION_INSTANCE
    success, info = await _api_send_reaction(
        instance_name,
        remote_jid,
        message_id,
        reaction,
        api_url=api_url,
        api_key=api_key,
    )
    return {"success": success, "info": info}

async def send_audio(
    ctx: RunContext[Dict],
    phone: str,
    audio_url: str,
    instance: str = None,
    delay_ms: int = 0,
    ptt: bool = True,
    api_url: str = None,
    api_key: str = None,
) -> Dict[str, Any]:
    """Send a WhatsApp audio (PTT) message via Evolution API."""
    from .api import send_whatsapp_audio as _api_send_audio

    instance_name = instance or settings.EVOLUTION_INSTANCE
    success, info = await _api_send_audio(
        instance_name,
        phone,
        audio_url,
        delay_ms,
        ptt,
        api_url=api_url,
        api_key=api_key,
    )
    return {"success": success, "info": info}

async def get_group_info(
    ctx: RunContext[Dict],
    group_jid: str,
    instance: str = None,
    api_url: str = None,
    api_key: str = None,
) -> Dict[str, Any]:
    """Fetch metadata about a WhatsApp group (participants, subject, etc.)."""
    from .api import get_group_info as _api_group

    instance_name = instance or settings.EVOLUTION_INSTANCE
    success, data = await _api_group(
        instance_name,
        group_jid,
        api_url=api_url,
        api_key=api_key,
    )
    return {"success": success, "data": data} 