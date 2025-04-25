import os
import httpx # Using httpx for async requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Environment variables for Evolution API
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")

async def send_evolution_media_logic(
    instance_name: str,
    number: str,
    media_url: str,
    media_type: str, # e.g., "image", "document", "audio", "video"
    caption: Optional[str] = None,
    file_name: Optional[str] = None # Sometimes needed, e.g., for documents
) -> Tuple[bool, str]:
    """Core async logic to send media using the Evolution API."""
    if not EVOLUTION_API_KEY or not EVOLUTION_API_URL:
        logger.error("Evolution API URL or Key not configured in environment variables.")
        return False, "Evolution API URL or Key not configured."

    api_endpoint = f"{EVOLUTION_API_URL}/message/sendMedia/{instance_name}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    
    # Construct payload according to the correct documentation structure
    payload = {
        "number": number,
        "mediatype": media_type,  # Changed key to lowercase 'mediatype'
        "media": media_url,
    }

    # Add optional fields directly to the payload
    if caption:
        payload["caption"] = caption
    if file_name:
        payload["fileName"] = file_name
    # We could also add mimetype if needed/available
    # if mimetype:
    #    payload["mimetype"] = mimetype

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_endpoint, headers=headers, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            response_json = response.json()
            message_id = response_json.get('key', {}).get('id', 'N/A')
            logger.info(f"Evolution API: Media sent successfully to {number}. Type: {media_type}, ID: {message_id}")
            return True, f"Media sent successfully. Message ID: {message_id}"
    except httpx.HTTPStatusError as e:
        error_details = str(e)
        try:
            error_details = e.response.json()
        except Exception:
            error_details = e.response.text
        logger.error(f"Error sending Evolution API media (HTTP Status {e.response.status_code}): {error_details}")
        return False, f"Evolution API HTTP Error {e.response.status_code}: {error_details}"
    except httpx.RequestError as e:
        logger.error(f"Error sending Evolution API media (Request Error): {e}")
        return False, f"Evolution API Request Error: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error sending Evolution media: {e}")
        return False, f"Unexpected error: {str(e)}"
