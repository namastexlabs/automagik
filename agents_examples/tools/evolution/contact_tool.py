"""Evolution contact tool implementation.

This module provides the functionality for sending contact information via Evolution API.
"""
import logging
import json
import requests
from typing import Dict, Any
from pydantic_ai import RunContext

logger = logging.getLogger(__name__)

def get_send_contact_description() -> str:
    """Get description for the send_contact function."""
    return """Send contact information to a WhatsApp number via Evolution API.
    This tool sends business or personal contact information to a recipient.
    Use it when a user needs to be redirected from a personal number to a business number or vice versa.
    """

async def send_contact(
    ctx: RunContext[Dict], 
    instance_name: str,
    api_key: str,
    base_url: str,
    recipient_number: str,
    full_name: str,
    whatsapp_id: str,
    phone_number: str,
    organization: str = "",
    email: str = "",
    url: str = "",
    show_typing: bool = True,
    typing_delay: int = 3000
) -> Dict[str, Any]:
    """Send contact information to a WhatsApp number.

    Args:
        ctx: The run context
        instance_name: Evolution API instance identifier
        api_key: Evolution API key for authentication
        base_url: Evolution API base URL (e.g., http://localhost:8080)
        recipient_number: WhatsApp ID of the recipient (format: "5511999999999" or with @s.whatsapp.net)
        full_name: Full name of the contact
        whatsapp_id: WhatsApp ID of the contact (format: "5511999999999")
        phone_number: Phone number with country code (e.g., "+55 11 99999-9999")
        organization: Organization of the contact (optional)
        email: Email address of the contact (optional)
        url: URL of the contact (optional)
        show_typing: Whether to show typing indicator before sending
        typing_delay: How long to show typing indicator (in milliseconds)

    Returns:
        Dict with the response data
    """
    try:
        logger.info(f"Sending contact information to {recipient_number}")
        
        # Clean recipient number (ensure it has @s.whatsapp.net if needed)
        clean_recipient = recipient_number
        if "@" not in clean_recipient:
            clean_recipient = f"{clean_recipient}@s.whatsapp.net"

        # Format base URL
        base_url = base_url.rstrip('/')
        # Ensure URL has scheme
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"http://{base_url}"

        # Show typing indicator if requested
        if show_typing:
            try:
                typing_url = f"{base_url}/chat/sendPresence/{instance_name}"
                typing_headers = {
                    "apikey": api_key,
                    "Content-Type": "application/json"
                }
                typing_payload = {
                    "number": clean_recipient,
                    "delay": typing_delay,
                    "presence": "composing"
                }
                
                logger.info("Sending typing presence indicator...")
                typing_response = requests.post(
                    typing_url, 
                    headers=typing_headers, 
                    json=typing_payload
                )
                typing_response.raise_for_status()
                logger.info("Typing indicator sent successfully")
            except Exception as e:
                logger.warning(f"Failed to send typing indicator: {str(e)}")
                # Continue even if typing indicator fails
        
        # Create the contact payload
        contact = {
            "fullName": full_name,
            "wuid": whatsapp_id,
            "phoneNumber": phone_number,
            "organization": organization,
            "email": email,
            "url": url
        }
        
        # Create the full request payload
        payload = {
            "number": clean_recipient,
            "contact": [contact]
        }
        
        # Log sanitized payload
        safe_payload = {
            "number": "***hidden***",
            "contact": [{
                "fullName": contact["fullName"],
                "wuid": "***hidden***",
                "phoneNumber": "***hidden***",
                "organization": contact.get("organization", ""),
                "email": contact.get("email", ""),
                "url": contact.get("url", "")
            }]
        }
        logger.info(f"Prepared contact payload: {json.dumps(safe_payload, indent=2)}")
        
        # Send the contact
        url = f"{base_url}/message/sendContact/{instance_name}"
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Sending contact request to: {url}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        
        # Create a clean response (removing sensitive information)
        success = response.status_code == 200
        processed_response = {
            "success": success,
            "status": response_data.get("status", "unknown"),
            "messageId": response_data.get("key", {}).get("id", "unknown"),
            "timestamp": response_data.get("messageTimestamp", ""),
            "recipient": clean_recipient
        }
        
        logger.info(f"Contact sent successfully: {success}")
        return processed_response
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status": "ERROR"
        }
    except Exception as e:
        error_msg = f"Unexpected error sending contact: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status": "ERROR"
        }

def _extract_evolution_credentials_from_payload(ctx: RunContext[Dict]) -> Dict[str, str]:
    """Extract Evolution API credentials from context or channel payload.
    
    Args:
        ctx: The run context which may contain channel_payload
        
    Returns:
        Dict with extracted credentials
    """
    # Get the context data
    context_data = ctx.get_context() or {}
    
    # Try to get credentials from channel_payload if available
    channel_payload = context_data.get("channel_payload", {})
    
    # Extract evolution credentials that might be in the payload
    evolution_credentials = {}
    
    # Try to get from channel_payload.evolution object if it exists
    if isinstance(channel_payload, dict):
        # Direct evolution data
        evolution_data = channel_payload.get("evolution", {})
        if evolution_data:
            evolution_credentials["api_key"] = evolution_data.get("api_key")
            evolution_credentials["base_url"] = evolution_data.get("base_url")
            evolution_credentials["instance_name"] = evolution_data.get("instance_name")
            
        # Try alternative locations in the payload
        if "evolution_api_key" in channel_payload:
            evolution_credentials["api_key"] = channel_payload.get("evolution_api_key")
        if "evolution_base_url" in channel_payload:
            evolution_credentials["base_url"] = channel_payload.get("evolution_base_url")
        if "evolution_instance" in channel_payload:
            evolution_credentials["instance_name"] = channel_payload.get("evolution_instance")
            
        # Check if in whatsapp_payload
        whatsapp_payload = channel_payload.get("whatsapp_payload", {})
        if isinstance(whatsapp_payload, dict):
            # Extract from whatsapp_payload
            if "evolution" in whatsapp_payload:
                evolution_data = whatsapp_payload.get("evolution", {})
                if not evolution_credentials.get("api_key"):
                    evolution_credentials["api_key"] = evolution_data.get("api_key")
                if not evolution_credentials.get("base_url"):
                    evolution_credentials["base_url"] = evolution_data.get("base_url")
                if not evolution_credentials.get("instance_name"):
                    evolution_credentials["instance_name"] = evolution_data.get("instance_name")
    
    # Get env config as fallback
    env_config = ctx.get_env_config() or {}
    
    # Final credentials with fallbacks to environment variables
    credentials = {
        "api_key": evolution_credentials.get("api_key") or env_config.get("EVOLUTION_API_KEY", ""),
        "base_url": evolution_credentials.get("base_url") or env_config.get("EVOLUTION_API_URL", "http://localhost:8080"),
        "instance_name": evolution_credentials.get("instance_name") or env_config.get("EVOLUTION_INSTANCE", "instance1")
    }
    
    return credentials

# Simpler version for direct use by the agent
async def send_business_contact(
    ctx: RunContext[Dict],
    recipient_number: str
) -> Dict[str, Any]:
    """Send business contact information to a WhatsApp number.
    
    This is a simplified wrapper that uses context or environment configuration.

    Args:
        ctx: The run context
        recipient_number: The recipient's phone number (can include @s.whatsapp.net)

    Returns:
        Dict with the response data
    """
    try:
        # First try to get Evolution credentials from channel payload
        evolution_credentials = _extract_evolution_credentials_from_payload(ctx)
        
        # Get environment configuration as fallback
        ctx.get_env_config() or {}
        
        # Get business contact details
        business_name = "Victor Corrêa Gomes"
        business_phone = "5527997482360"
        business_display = "+55 27 99748-2360"
        business_org = ""
        business_email = ""
        business_url = ""
        
        # Check if we have required configuration
        if not evolution_credentials.get("api_key"):
            logger.error("Missing Evolution API credentials")
            return {
                "success": False,
                "error": "Missing Evolution API credentials. Contact the administrator."
            }
            
        # Clean recipient number
        clean_recipient = recipient_number.split("@")[0] if "@" in recipient_number else recipient_number
        # Add WhatsApp suffix if not present (required by Evolution API)
        if "@s.whatsapp.net" not in clean_recipient:
            clean_recipient = f"{clean_recipient}@s.whatsapp.net"
            
        logger.info(f"Sending business contact to {clean_recipient}")
        
        # Call the full implementation
        result = await send_contact(
            ctx=ctx,
            instance_name=evolution_credentials["instance_name"],
            api_key=evolution_credentials["api_key"],
            base_url=evolution_credentials["base_url"],
            recipient_number=clean_recipient,
            full_name=business_name,
            whatsapp_id=business_phone,
            phone_number=business_display,
            organization=business_org,
            email=business_email,
            url=business_url
        )
        
        return result
    except Exception as e:
        error_msg = f"Failed to send business contact: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# Simpler version for sending personal contact
async def send_personal_contact(
    ctx: RunContext[Dict],
    recipient_number: str
) -> Dict[str, Any]:
    """Send personal contact information to a WhatsApp number.
    
    This is a simplified wrapper that uses context or environment configuration.

    Args:
        ctx: The run context
        recipient_number: The recipient's phone number (can include @s.whatsapp.net)

    Returns:
        Dict with the response data
    """
    try:
        # First try to get Evolution credentials from channel payload
        evolution_credentials = _extract_evolution_credentials_from_payload(ctx)
        
        # Get environment configuration as fallback
        env_config = ctx.get_env_config() or {}
        
        # Get personal contact details
        personal_name = env_config.get("PERSONAL_CONTACT_NAME", "Personal Contact")
        personal_phone = env_config.get("PERSONAL_PHONE", "5511999999999")
        personal_display = env_config.get("PERSONAL_DISPLAY_PHONE", "+55 11 99999-9999")
        personal_org = env_config.get("PERSONAL_ORG", "")
        personal_email = env_config.get("PERSONAL_EMAIL", "")
        personal_url = env_config.get("PERSONAL_URL", "")
        
        # Check if we have required configuration
        if not evolution_credentials.get("api_key"):
            logger.error("Missing Evolution API credentials")
            return {
                "success": False,
                "error": "Missing Evolution API credentials. Contact the administrator."
            }
            
        # Clean recipient number
        clean_recipient = recipient_number.split("@")[0] if "@" in recipient_number else recipient_number
        # Add WhatsApp suffix if not present (required by Evolution API)
        if "@s.whatsapp.net" not in clean_recipient:
            clean_recipient = f"{clean_recipient}@s.whatsapp.net"
            
        logger.info(f"Sending personal contact to {clean_recipient}")
        
        # Call the full implementation
        result = await send_contact(
            ctx=ctx,
            instance_name=evolution_credentials["instance_name"],
            api_key=evolution_credentials["api_key"],
            base_url=evolution_credentials["base_url"],
            recipient_number=clean_recipient,
            full_name=personal_name,
            whatsapp_id=personal_phone,
            phone_number=personal_display,
            organization=personal_org,
            email=personal_email,
            url=personal_url
        )
        
        return result
    except Exception as e:
        error_msg = f"Failed to send personal contact: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# Direct test function that doesn't require environment variables
async def test_send_contact_direct(recipient_number: str) -> Dict[str, Any]:
    """Test function to send Victor's contact information directly without env variables.
    
    Args:
        recipient_number: The recipient's phone number
        
    Returns:
        Dict with the response data
    """
    try:
        # Hardcoded credentials and contact info
        api_key = "9B10B90426EA-45D6-9EB3-97723B34F302"  # Replace with actual API key
        base_url = "http://localhost:8080"  # Replace with actual URL
        instance_name = "victorEvo"  # Replace with actual instance
        
        # Victor's contact details
        contact_name = "Victor Corrêa Gomes"
        contact_phone = "5527997482360"
        contact_display = "+55 27 99748-2360"
        
        # Clean recipient number
        clean_recipient = recipient_number.split("@")[0] if "@" in recipient_number else recipient_number
        # Add WhatsApp suffix if not present (required by Evolution API)
        if "@s.whatsapp.net" not in clean_recipient:
            clean_recipient = f"{clean_recipient}@s.whatsapp.net"
        
        print(f"Sending Victor's contact to {clean_recipient}")
        
        # Create a mock context
        ctx = RunContext({}, 
            model={
                "name": "test-model",
                "id": "test-id",
                "max_tokens": 4000,
                "temperature": 0.7
            },
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            prompt="test prompt"
        )
        
        # Call the full implementation
        result = await send_contact(
            ctx=ctx,
            instance_name=instance_name,
            api_key=api_key,
            base_url=base_url,
            recipient_number=clean_recipient,
            full_name=contact_name,
            whatsapp_id=contact_phone,
            phone_number=contact_display,
            organization="",
            email="",
            url=""
        )
        
        return result
    except Exception as e:
        error_msg = f"Failed to send contact: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# Command line interface for testing
if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        # Get recipient number from command line
        if len(sys.argv) > 1:
            recipient = sys.argv[1]
            print(f"Testing contact send to {recipient}")
            result = await test_send_contact_direct(recipient)
            print(f"Result: {result}")
        else:
            print("Usage: python -m automagik.tools.evolution.contact_tool <recipient_number>")
    
    asyncio.run(main()) 