"""Meeting bot tool implementation."""

import logging
import httpx
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from automagik.config import settings

logger = logging.getLogger(__name__)

class MeetingService(str, Enum):
    """Supported meeting services."""
    GMEET = "gmeet"
    ZOOM = "zoom"
    TEAMS = "teams"

class CreateBotRequest(BaseModel):
    """Request model for creating a meeting bot."""
    service: MeetingService = Field(..., description="Meeting service type")
    meeting_url: str = Field(..., description="URL of the meeting to join")
    transcription_model: str = Field(default="whisper", description="Transcription model to use")
    bot_name: str = Field(default="Testonho Sofia", description="Name of the meeting bot")
    webhook_url: str = Field(..., description="Webhook URL for receiving transcription data")
    lang: str = Field(default="pt", description="Language code for transcription")

class CreateBotResponse(BaseModel):
    """Response model for bot creation."""
    success: bool = Field(..., description="Whether the bot was created successfully")
    message: str = Field(..., description="Response message")
    bot_id: Optional[str] = Field(None, description="ID of the created bot if successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

async def join_meeting_with_url(meeting_url: str, service: MeetingService = MeetingService.GMEET) -> str:
    """Join a meeting automatically with an AI bot that provides live transcription.
    
    This tool deploys an AI-powered meeting assistant that will:
    - Automatically join the specified meeting (Google Meet, Zoom, or Microsoft Teams)
    - Provide real-time transcription of the conversation in Portuguese
    - Send transcribed content to a webhook for further processing
    - Act as a silent participant focused on transcription accuracy
    
    The bot uses Whisper AI for high-quality speech recognition and can handle
    multiple speakers, background noise, and various audio qualities commonly
    found in online meetings.
    
    Args:
        meeting_url: The complete meeting URL to join (e.g., https://meet.google.com/abc-def-ghi, 
                    https://zoom.us/j/123456789, or https://teams.microsoft.com/l/meetup-join/...)
        service: The meeting platform type - 'gmeet' for Google Meet, 'zoom' for Zoom, 
                or 'teams' for Microsoft Teams. Defaults to gmeet.
        
    Returns:
        Success confirmation with bot details and meeting info, or error message if joining failed.
    """
    try:
        # Check if meeting bot URL is configured
        if not settings.MEETING_BOT_URL:
            error_msg = "Meeting bot service is not configured. Please set MEETING_BOT_URL environment variable."
            logger.error(error_msg)
            return error_msg
        
        # Validate meeting URL
        if not meeting_url or not meeting_url.startswith(('https://', 'http://')):
            error_msg = f"Invalid meeting URL: {meeting_url}. URL must start with https:// or http://"
            logger.error(error_msg)
            return error_msg
        
        # Create the bot request
        bot_request = CreateBotRequest(
            service=service,
            meeting_url=meeting_url,
            transcription_model="whisper",
            bot_name="Sofia - Namastex", 
            webhook_url=f"{settings.MEETING_BOT_URL}/webhooks/skribby",
            lang="pt"
        )
        
        logger.info(f"Joining {service.value} meeting with AI bot: {meeting_url}")
        
        # Make the API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.MEETING_BOT_URL}/bots/create",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=bot_request.model_dump()
            )
            
            # Check response status
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    
                    # Create response object
                    bot_response = CreateBotResponse(
                        success=True,
                        message="Meeting bot created successfully",
                        bot_id=response_data.get("bot_id") or response_data.get("id"),
                        data=response_data
                    )
                    
                    success_msg = f"✅ AI meeting assistant '{bot_request.bot_name}' successfully joined {service.value} meeting!"
                    if bot_response.bot_id:
                        success_msg += f"\nBot ID: {bot_response.bot_id}"
                    success_msg += f"\nMeeting URL: {meeting_url}"
                    success_msg += f"\nTranscription: {bot_request.transcription_model} ({bot_request.lang})"
                    
                    logger.info(f"AI assistant successfully joined meeting: {bot_response.bot_id}")
                    return success_msg
                    
                except Exception as e:
                    error_msg = f"Bot joined meeting but failed to parse response: {str(e)}"
                    logger.error(error_msg)
                    return f"✅ AI assistant joined meeting (response parsing failed: {str(e)})"
                    
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", "Unknown error"))
                except Exception:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                
                full_error = f"❌ Failed to join meeting with AI assistant: {error_msg}"
                logger.error(f"AI assistant failed to join meeting: {response.status_code} - {error_msg}")
                return full_error
                
    except httpx.TimeoutException:
        error_msg = "❌ Meeting join attempt timed out. The service may be temporarily unavailable."
        logger.error("AI assistant meeting join timed out")
        return error_msg
        
    except httpx.RequestError as e:
        error_msg = f"❌ Failed to connect to meeting bot service: {str(e)}"
        logger.error(f"Meeting bot service connection error: {str(e)}")
        return error_msg
        
    except Exception as e:
        error_msg = f"❌ Unexpected error joining meeting with AI assistant: {str(e)}"
        logger.error(f"Unexpected error in join_meeting_with_url: {str(e)}")
        return error_msg

 