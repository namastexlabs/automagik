import pytest
import os
import json
import uuid
import httpx
from dotenv import load_dotenv
from src.tools.blackpearl.provider import BlackpearlProvider
import logging
from unittest.mock import patch

# Load environment variables from .env file
load_dotenv()

# Configure logging for the test
logger = logging.getLogger(__name__)

# --- Configuration ---
# Ensure the API host and key are set as environment variables
from src.config import load_settings
settings = load_settings()
# Use AM_HOST setting, but if it's 0.0.0.0 (bind all interfaces), use localhost for client connection
host = "localhost" if settings.AM_HOST == "0.0.0.0" else settings.AM_HOST
API_HOST = f"{host}:{settings.AM_PORT}"  # Use proper settings with host and port
API_KEY = os.getenv("AM_API_KEY")
AGENT_ENDPOINT = f"http://{API_HOST}/api/v1/agent/stan/run"
TEST_USER_IDENTIFIER = "integration-test-user@example.com" # Use email for get/create

# --- Fixtures (Optional) ---
# You could define fixtures here for reusable test data if needed

# --- Test Cases ---
@pytest.mark.integration # Mark as an integration test
@pytest.mark.asyncio # Add asyncio marker
@patch.dict(os.environ, {
    "DISABLE_MEMORY_OPERATIONS": "true",
    "MOCK_EXTERNAL_APIS": "false",  # Keep real BlackPearl for full integration test
    "TEST_MODE": "true"
})
async def test_stan_agent_run_success(): 
    """Tests user fetch/create, agent run, and cleanup (user, blackpearl)."""
    if not API_KEY:
        pytest.skip("API Key (AM_API_KEY) not found in environment variables.")

    user_id_for_test = None
    # --- Setup Phase: Ensure user exists ---
    logger.info(f"--- Starting Setup Phase: Ensuring user '{TEST_USER_IDENTIFIER}' exists ---")
    api_headers = { # Headers for general API calls
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }
    user_endpoint_get = f"http://{API_HOST}/api/v1/users/{TEST_USER_IDENTIFIER}" # Added prefix
    user_endpoint_post = f"http://{API_HOST}/api/v1/users" # Added prefix

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
                    "user_data": {"source": "integration_test"} # Optional data
                }
                post_response = await client.post(user_endpoint_post, json=create_payload)
                post_response.raise_for_status() # Fail test if creation fails
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

    # --- Agent Run Phase ---
    logger.info(f"--- Starting Agent Run Phase for user ID: {user_id_for_test} ---")
    agent_headers = {
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }

    # Payload for the agent run
    payload = {
        "channel_payload": {
            "event": "test.event",
            "data": {"key": {"remoteJid": "test@s.whatsapp.net", "fromMe": False, "id": "TESTID"}},
            "message": {"conversation": "test message from integration test"},
            "sender": "testsender@s.whatsapp.net"
        },
        "message_content": "test message from integration test",
        "message_limit": 10,
        "user_id": user_id_for_test, # Use ID obtained in setup
        "message_type": "text",
        "session_name": f"test-session-{uuid.uuid4()}",
        "session_origin": "whatsapp", # Emulate whatsapp origin
        "preserve_system_prompt": False,
    }

    response_data = None
    agent_run_successful = False
    try:
        # Use a single client for multiple requests
        async with httpx.AsyncClient(headers=agent_headers, timeout=30) as client:
            logger.info(f"Running agent via POST {AGENT_ENDPOINT}")
            response = await client.post(AGENT_ENDPOINT, json=payload)

            # Basic check: Successful HTTP status code
            assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}. Response: {response.text}"

            # Optional: More specific checks on the response content
            try:
                response_data = response.json()
                # Example: Assert a specific field exists or has a certain value
                assert response_data.get("success") is True, "Agent run 'success' field was not True"
                # assert response_data.get("status") == "completed"
                print(f"\nAgent API Response: {json.dumps(response_data, indent=2)}") # Print response for inspection
                agent_run_successful = True # Mark agent run as successful

            except httpx.JSONDecodeError:
                pytest.fail(f"Response was not valid JSON. Status Code: {response.status_code}. Response Text: {response.text}")

    except httpx.RequestError as e:
        pytest.fail(f"Agent API request failed: {e}")

    # --- Cleanup Phase ---
    if agent_run_successful:
        logger.info("--- Starting Cleanup Phase ---")
        cliente_id_to_delete = None
        contato_id_to_delete = None

        # 1. Fetch User Data to get Black Pearl IDs
        user_endpoint = f"http://{API_HOST}/api/v1/users/{user_id_for_test}" # Added prefix
        try:
            async with httpx.AsyncClient(headers=api_headers, timeout=15) as client:
                logger.info(f"Fetching user data via GET {user_endpoint}")
                user_response = await client.get(user_endpoint)
                user_response.raise_for_status() # Raise exception for 4xx/5xx errors
                user_data = user_response.json()
                print(f"\nUser Data Response: {json.dumps(user_data, indent=2)}")

                # Extract IDs directly from user_data using the correct keys
                user_data_dict = user_data.get("user_data", {}) 
                cliente_id_to_delete = user_data_dict.get("blackpearl_cliente_id")
                contato_id_to_delete = user_data_dict.get("blackpearl_contact_id")

                logger.info(f"Extracted Black Pearl IDs: cliente_id={cliente_id_to_delete}, contato_id={contato_id_to_delete}")

        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch user data for cleanup: {e}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching user data: {e.response.status_code} - {e.response.text}")
        except httpx.JSONDecodeError:
            logger.warning("Failed to decode user data JSON response.")
        except Exception as e:
             logger.warning(f"Unexpected error fetching user data: {e}")

        # 2. Delete Black Pearl Entities if IDs were found
        if cliente_id_to_delete is not None or contato_id_to_delete is not None:
            try:
                async with BlackpearlProvider() as bp_client:
                    if cliente_id_to_delete is not None:
                        logger.info(f"Attempting to delete Black Pearl cliente ID: {cliente_id_to_delete}")
                        delete_response = await bp_client.delete_cliente(int(cliente_id_to_delete)) # Ensure ID is int
                        logger.info(f"Black Pearl delete_cliente response: {delete_response}")
                    
                    if contato_id_to_delete is not None:
                        logger.info(f"Attempting to delete Black Pearl contato ID: {contato_id_to_delete}")
                        delete_response = await bp_client.delete_contato(int(contato_id_to_delete)) # Ensure ID is int
                        logger.info(f"Black Pearl delete_contato response: {delete_response}")

            except ImportError:
                 logger.error("BlackpearlProvider could not be imported. Is the 'src' directory in PYTHONPATH?")
            except ValueError as e:
                 logger.error(f"Error during Black Pearl cleanup (likely missing env var or invalid ID): {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during Black Pearl cleanup: {e}")
        else:
            logger.warning("No Black Pearl IDs found in user data, skipping deletion.")

        # Delete the test user
        user_endpoint_delete = f"http://{API_HOST}/api/v1/users/{user_id_for_test}" # Added prefix
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
    else:
        logger.warning("Agent run was not successful, skipping cleanup phase.")

# --- Add more test cases below as needed --- 
# e.g., test_stan_agent_run_invalid_key(), test_stan_agent_run_bad_payload(), etc.
