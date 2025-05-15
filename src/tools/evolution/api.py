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

# -----------------------------------------------------------------------------
# Additional helper functions
# -----------------------------------------------------------------------------


async def send_text_message(instance_name: str, number: str, text: str) -> Tuple[bool, str]:
    """Send plain text via Evolution API."""
    if not EVOLUTION_API_KEY or not EVOLUTION_API_URL:
        return False, "Evolution API URL or Key not configured."

    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{instance_name}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    payload = {"number": number, "text": text}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            msg_id = resp.json().get("key", {}).get("id", "N/A")
            return True, msg_id
    except Exception as e:
        logger.error(f"Evolution API text error: {e}")
        return False, str(e)


async def send_reaction(
    instance_name: str,
    remote_jid: str,
    message_id: str,
    reaction: str,
) -> Tuple[bool, str]:
    """Send a reaction (emoji) to a specific message."""
    if not EVOLUTION_API_KEY or not EVOLUTION_API_URL:
        return False, "Evolution API credentials missing"

    endpoint = f"{EVOLUTION_API_URL}/message/sendReaction/{instance_name}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    payload = {
        "reactionMessage": {
            "key": {
                "remoteJid": remote_jid,
                "fromMe": True,
                "id": message_id,
            },
            "reaction": reaction,
        }
    }

    logger.debug(f"Evolution send_reaction payload: {payload}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code == 201 or resp.status_code == 200:
                return True, "Reaction sent"
            else:
                return False, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        logger.error(f"Evolution reaction error: {e}")
        return False, str(e)


async def send_whatsapp_audio(
    instance_name: str,
    number: str,
    audio_url: str,
    delay: int = 0,
    encoding: bool = True,
) -> Tuple[bool, str]:
    """Send an audio (PTT) message to a number."""
    if not EVOLUTION_API_KEY or not EVOLUTION_API_URL:
        return False, "Evolution API credentials missing"

    endpoint = f"{EVOLUTION_API_URL}/message/sendWhatsAppAudio/{instance_name}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    payload = {
        "number": number,
        "audio": audio_url,
        "delay": delay,
        "encoding": encoding,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            return True, resp.json().get("key", {}).get("id", "N/A")
    except Exception as e:
        logger.error(f"Evolution audio error: {e}")
        return False, str(e)


async def get_group_info(instance_name: str, group_jid: str) -> Tuple[bool, dict]:
    """Fetch group metadata for a given group JID."""
    if not EVOLUTION_API_KEY or not EVOLUTION_API_URL:
        return False, {}

    endpoint = f"{EVOLUTION_API_URL}/group/findGroupInfos/{instance_name}"
    headers = {"apikey": EVOLUTION_API_KEY}

    params = {"groupJid": group_jid}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            return True, resp.json()
    except Exception as e:
        logger.error(f"Evolution group info error: {e}")
        return False, {}
