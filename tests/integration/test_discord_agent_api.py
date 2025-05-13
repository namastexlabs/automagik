import requests
import pytest
import os
import json
import asyncio
import httpx
from dotenv import load_dotenv
import logging
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging for the test
logger = logging.getLogger(__name__)

# --- Configuration ---
# Ensure the API host and key are set as environment variables
API_HOST = os.getenv("AM_AGENTS_API_HOST", "192.168.112.129:8881")  # Use the same default as stan_agent test
API_KEY = os.getenv("AM_API_KEY")
AGENT_ENDPOINT = f"http://{API_HOST}/api/v1/agent/discord/run"  # Using 'discord' as the agent name
TEST_USER_IDENTIFIER = "discord-test-user@example.com"  # Use email for get/create
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- Test Cases ---
@pytest.mark.integration  # Mark as an integration test
@pytest.mark.asyncio  # Add asyncio marker
async def test_discord_agent_run_success():
    """Tests Discord agent API to list guilds and then send a message."""
    if not API_KEY:
        pytest.skip("API Key (AM_API_KEY) not found in environment variables.")
    
    if not DISCORD_BOT_TOKEN:
        pytest.skip("Discord Bot Token (DISCORD_BOT_TOKEN) not found in environment variables.")
    else:
        # Log partial token for debugging (first 5 chars only for security)
        token_preview = DISCORD_BOT_TOKEN[:5] + "..." if len(DISCORD_BOT_TOKEN) > 5 else "invalid_token"
        logger.info(f"Using Discord bot token starting with: {token_preview}")

    # --- Setup Phase: Ensure user exists ---
    logger.info(f"--- Starting Setup Phase: Ensuring user '{TEST_USER_IDENTIFIER}' exists ---")
    api_headers = {  # Headers for general API calls
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }
    user_endpoint_get = f"http://{API_HOST}/api/v1/users/{TEST_USER_IDENTIFIER}"
    user_endpoint_post = f"http://{API_HOST}/api/v1/users"

    try:
        async with httpx.AsyncClient(headers=api_headers, timeout=15) as client:
            # Try to fetch the user first
            logger.info(f"Attempting to GET user: {user_endpoint_get}")
            get_response = await client.get(user_endpoint_get)

            if get_response.status_code == 200:
                user_data = get_response.json()
                user_id_for_test = user_data.get("id")
                logger.info(f"User '{TEST_USER_IDENTIFIER}' found with ID: {user_id_for_test}")
            elif get_response.status_code == 404:
                logger.info(f"User '{TEST_USER_IDENTIFIER}' not found. Attempting to create.")
                create_payload = {
                    "email": TEST_USER_IDENTIFIER,
                    "user_data": {"source": "integration_test"}  # Optional data
                }
                post_response = await client.post(user_endpoint_post, json=create_payload)
                post_response.raise_for_status()  # Fail test if creation fails
                user_data = post_response.json()
                user_id_for_test = user_data.get("id")
                logger.info(f"User '{TEST_USER_IDENTIFIER}' created with ID: {user_id_for_test}")
            else:
                # Unexpected status code during GET
                get_response.raise_for_status()
        
        if not user_id_for_test:
            pytest.fail("Failed to obtain a user ID during setup phase.")

    except httpx.RequestError as e:
        pytest.fail(f"Setup phase API request failed: {e}")
    except httpx.HTTPStatusError as e:
        pytest.fail(f"Setup phase HTTP error: {e.response.status_code} - {e.response.text}")
    logger.info("--- Setup Phase Finished ---")

    # --- Agent Run Phase 1: List guilds and channels ---
    logger.info(f"--- Starting Agent Run Phase 1: List guilds for user ID: {user_id_for_test} ---")
    agent_headers = {
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }

    # Payload for the agent run - asking to list guilds
    list_payload = {
        "message_content": "List all my Discord servers and channels",
        "message_limit": 10,
        "user_id": user_id_for_test,
        "message_type": "text",
        "session_name": "discord-test-session",
        "session_origin": "cli",  # Must be one of the allowed values
        "preserve_system_prompt": False,
        "channel_payload": {
            "config": {
                "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN
            }
        }
    }

    channel_id = None  # Will store a channel ID if found
    
    try:
        # Use a single client for multiple requests
        async with httpx.AsyncClient(headers=agent_headers, timeout=60) as client:
            logger.info(f"Running Discord agent to list guilds via POST {AGENT_ENDPOINT}")
            response = await client.post(AGENT_ENDPOINT, json=list_payload)

            # Basic check: Successful HTTP status code
            assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}. Response: {response.text}"

            response_data = response.json()
            assert response_data.get("success") is True, "Agent run 'success' field was not True"
            print(f"\nDiscord List Guilds Response: {json.dumps(response_data, indent=2)}")
            
            # Try to extract a channel ID from the response text
            response_text = response_data.get("text", "")
            
            # Look for channel IDs in the format: channel_name (ID: 123456789)
            channel_id_matches = re.findall(r'ID: (\d+)', response_text)
            if channel_id_matches:
                channel_id = channel_id_matches[0]
                logger.info(f"Found channel ID in response: {channel_id}")
            else:
                # Try another pattern: #channel_name (123456789)
                channel_id_matches = re.findall(r'\((\d+)\)', response_text)
                if channel_id_matches:
                    channel_id = channel_id_matches[0]
                    logger.info(f"Found channel ID in response: {channel_id}")
    
    except httpx.RequestError as e:
        pytest.fail(f"Agent API request failed: {e}")
    except httpx.HTTPStatusError as e:
        pytest.fail(f"HTTP error: {e}")
    except Exception as e:
        pytest.fail(f"Error in list guilds phase: {str(e)}")

    # --- Agent Run Phase 2: Send a message if we found a channel ---
    if channel_id:
        logger.info(f"--- Starting Agent Run Phase 2: Send message to channel {channel_id} ---")
        
        # Payload for sending a message
        message_payload = {
            "message_content": f"Send the message 'This is a test from the Discord agent API' to channel {channel_id}",
            "message_limit": 10,
            "user_id": user_id_for_test,
            "message_type": "text",
            "session_name": "discord-test-session",
            "session_origin": "cli",
            "preserve_system_prompt": False,
            "channel_payload": {
                "config": {
                    "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(headers=agent_headers, timeout=60) as client:
                logger.info(f"Running Discord agent to send message via POST {AGENT_ENDPOINT}")
                send_response = await client.post(AGENT_ENDPOINT, json=message_payload)
                
                assert send_response.status_code == 200, f"Expected status code 200, but got {send_response.status_code}. Response: {send_response.text}"
                
                send_data = send_response.json()
                assert send_data.get("success") is True, "Send message 'success' field was not True"
                print(f"\nDiscord Send Message Response: {json.dumps(send_data, indent=2)}")
                
        except Exception as e:
            logger.error(f"Error in send message phase (non-critical): {str(e)}")
    else:
        logger.warning("No channel ID found in the response, skipping message send test")

    # --- Cleanup Phase ---
    logger.info("--- Starting Cleanup Phase ---")

    # Delete the test user
    user_endpoint_delete = f"http://{API_HOST}/api/v1/users/{user_id_for_test}"
    try:
        async with httpx.AsyncClient(headers=api_headers, timeout=15) as client:
            logger.info(f"Attempting to DELETE user: {user_endpoint_delete}")
            delete_response = await client.delete(user_endpoint_delete)
            # We might expect 200 or 204 depending on API design
            if delete_response.status_code not in [200, 204]:
                logger.warning(f"User deletion returned unexpected status {delete_response.status_code}: {delete_response.text}")
            else:
                logger.info(f"User {user_id_for_test} deleted successfully (Status: {delete_response.status_code}).")

    except httpx.RequestError as e:
        logger.warning(f"Failed to delete user during cleanup: {e}")
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error deleting user: {e.response.status_code} - {e.response.text}")

    logger.info("--- Cleanup Phase Finished ---")


if __name__ == "__main__":
    # For manual running (not via pytest)
    asyncio.run(test_discord_agent_run_success()) 