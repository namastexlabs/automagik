"""Agent controller functions for handling agent operations."""

import logging
import uuid
import inspect
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from automagik.agents.models.agent_factory import AgentFactory
from automagik.memory.message_history import MessageHistory
from automagik.api.models import (
    AgentInfo,
    AgentRunRequest,
    AgentRunResponse,
    UserCreate,
)
from automagik.db import (
    get_agent_by_name,
    get_user,
    create_user,
    User,
    ensure_default_user_exists,
)
from automagik.db.models import Session
from automagik.db.connection import generate_uuid, safe_uuid
from automagik.db.repository.session import get_session_by_name, create_session
from automagik.db.repository.agent import list_agents as list_db_agents
from automagik.db.repository.user import list_users

# Get our module's logger
logger = logging.getLogger(__name__)


def is_langgraph_agent(agent_name: str) -> bool:
    """Check if an agent name follows legacy orchestration naming pattern."""
    return agent_name.startswith("langgraph-")


def should_use_orchestration(agent_name: str, request: AgentRunRequest) -> bool:
    """Determine if a request attempts to use orchestration features (deprecated)."""
    return (
        is_langgraph_agent(agent_name)
    )


async def handle_orchestrated_agent_run(
    agent_name: str, request: AgentRunRequest
) -> AgentRunResponse:
    """Handle orchestrated agent execution (DISABLED - orchestration implementation removed)."""
    logger.warning(
        f"Orchestration requested for {agent_name} but orchestration implementation has been removed"
    )

    execution_time = 0.0

    # Return error response indicating orchestration is unavailable
    return AgentRunResponse(
        status="error",
        message="Orchestration is currently unavailable. LangGraph implementation has been removed pending NMSTX-230 completion.",
        session_id=request.session_id,
        agent_name=agent_name,
        execution_time=execution_time,
        errors=[
            "Orchestration disabled - awaiting NMSTX-230 PydanticAI implementation"
        ],
    )


async def list_registered_agents() -> List[AgentInfo]:
    """
    List all registered agents from the database, excluding claude_code from standard listings.
    Removes duplicates by normalizing agent names and grouping them by base name.
    Only returns agents that are marked as active in the database.
    """
    try:
        # Get all registered agents from the database
        # Off-load blocking DB call to threadpool
        registered_agents = await run_in_threadpool(list_db_agents, active_only=True)

        # Group agents by their name to handle duplicates
        unique_agents = {}

        for agent in registered_agents:
            # Use agent name as-is, no normalization
            agent_name = agent.name

            # Skip claude_code in standard listings
            if agent_name == "claude_code":
                continue

            # Skip if we already have this agent with a newer ID (likely more up-to-date)
            if agent_name in unique_agents and unique_agents[agent_name].id > agent.id:
                logger.info(
                    f"Skipping duplicate agent {agent.name} (ID: {agent.id}) in favor of newer entry (ID: {unique_agents[agent_name].id})"
                )
                continue

            # Store this agent as the canonical version for this name
            unique_agents[agent_name] = agent

        logger.info(
            f"Found {len(registered_agents)} agents, {len(unique_agents)} unique agents (claude_code excluded)"
        )

        # Convert to list of AgentInfo objects
        agent_infos = []
        for agent_name, agent in unique_agents.items():
            # Get agent class to fetch docstring
            factory = AgentFactory()
            agent_class = factory.get_agent_class(agent_name)
            docstring = (
                inspect.getdoc(agent_class) if agent_class else agent.description or ""
            )

            # Create agent info including the ID
            agent_infos.append(
                AgentInfo(
                    id=agent.id,
                    name=agent_name,  # Return the actual agent name
                    description=docstring,
                )
            )

        # Sort by name for consistent ordering
        agent_infos.sort(key=lambda x: x.name)

        return agent_infos
    except Exception as e:
        logger.error(f"Error listing registered agents: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list registered agents: {str(e)}"
        )


async def get_or_create_user_for_whatsapp(
    channel_payload: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[uuid.UUID]:
    """
    Special user handling for WhatsApp/Evolution requests.
    
    For WhatsApp requests, we should NOT create random user IDs because:
    1. The agent needs to identify users via conversation codes or phone numbers
    2. Creating random IDs prevents proper user tracking across sessions
    
    Args:
        channel_payload: Channel payload from the request
        context: Context dictionary
        
    Returns:
        None for WhatsApp requests (let the agent handle user identification)
        or a default user ID for other channels
    """
    # Check if this is a WhatsApp/Evolution request
    is_whatsapp = False
    
    if channel_payload:
        # Check for Evolution/WhatsApp indicators
        if channel_payload.get("channel") == "evolution":
            is_whatsapp = True
        elif channel_payload.get("instance"):
            is_whatsapp = True
        elif channel_payload.get("remoteJid", "").endswith("@s.whatsapp.net"):
            is_whatsapp = True
            
    if context:
        # Check context for WhatsApp indicators
        if context.get("channel") == "whatsapp":
            is_whatsapp = True
        elif context.get("whatsapp_user_number"):
            is_whatsapp = True
            
    if is_whatsapp:
        logger.info("WhatsApp request detected - deferring user creation to agent")
        # Return None to let the agent handle user identification
        # The agent will create/identify users based on conversation codes
        return None
    else:
        # For non-WhatsApp requests, use default behavior
        # This maintains backward compatibility
        default_user_id = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        ensure_default_user_exists(default_user_id, "admin@automagik")
        return default_user_id


async def get_or_create_user(
    user_id: Optional[Union[uuid.UUID, str]] = None,
    user_data: Optional[UserCreate] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[uuid.UUID]:
    """
    Get or create a user based on the provided ID and data.

    Args:
        user_id: Optional user ID
        user_data: Optional user data for creation/update
        context: Optional context containing additional user info (e.g., external_user_id)

    Returns:
        UUID of the existing or newly created user
    """
    # Import UserCreate here as well to ensure it's available

    # Check for external_user_id in context first (for external agents)
    if context and not user_id:
        external_user_id = context.get("external_user_id") or context.get("flashed_user_id")
        if external_user_id:
            try:
                user_id = uuid.UUID(external_user_id)
                logger.debug(f"Using external_user_id from context: {user_id}")
            except ValueError:
                logger.warning(f"Invalid external_user_id format: {external_user_id}")

    # If no user ID or data, use the default user
    if not user_id and not user_data:
        # Try to find the first user in the database (the default user)
        users, _ = await run_in_threadpool(list_users, page=1, page_size=1)

        if users and len(users) > 0:
            logger.debug(f"Using default user with ID: {users[0].id}")
            return users[0].id

        # If no users exist, ensure the default user exists and return its ID
        try:
            # Use the UUID from the example in models.py
            default_user_id = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
            # This function will create the user if it doesn't exist
            if ensure_default_user_exists(default_user_id, "admin@automagik"):
                logger.debug(f"Using default user ID: {default_user_id}")
                return default_user_id
        except Exception as e:
            logger.error(f"Error ensuring default user exists: {str(e)}")

        # If we still don't have a user, log an error
        logger.error("Failed to get or create default user")
        return None

    # Try to get existing user first
    user = None
    if user_id:
        try:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                try:
                    user_id = uuid.UUID(user_id)
                except ValueError:
                    logger.warning(f"Invalid UUID format for user_id: {user_id}")

            # Try to get user by ID
            user = await run_in_threadpool(get_user, user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")

    # If user exists and we have user_data, update user
    if user and user_data:
        # Update user with provided data
        user.email = user_data.email or user.email
        user.phone_number = user_data.phone_number or user.phone_number

        # Merge user_data if provided
        if user_data.user_data:
            user.user_data = user.user_data or {}
            user.user_data.update(user_data.user_data)

        # Update user in database
        from automagik.db import update_user

        updated_id = await run_in_threadpool(update_user, user)
        return updated_id

    # If user doesn't exist but we have user_data, create new user
    elif user_data:
        # Create new user - check context for external_user_id before generating random UUID
        if not user_id and context:
            external_user_id = context.get("external_user_id") or context.get("flashed_user_id")
            if external_user_id:
                try:
                    user_id = uuid.UUID(external_user_id)
                    logger.debug(f"Using external_user_id for new user creation: {user_id}")
                except ValueError:
                    logger.warning(f"Invalid external_user_id format for new user: {external_user_id}")
        
        new_user = User(
            id=user_id if user_id else generate_uuid(),
            email=user_data.email,
            phone_number=user_data.phone_number,
            user_data=user_data.user_data,
        )
        created_id = await run_in_threadpool(create_user, new_user)
        return created_id

    # If user doesn't exist and we don't have user_data, create minimal user
    elif user_id and not user:
        # Create minimal user with just the ID
        new_user = User(id=user_id)
        created_id = await run_in_threadpool(create_user, new_user)
        return created_id

    # User exists but no updates needed
    return user.id if user else None


def _recursively_sanitize_base64(data: Any) -> Any:
    """Recursively sanitize base64 content in nested data structures."""
    
    try:
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key == "base64" and isinstance(value, str) and len(value) > 100:
                    # This looks like base64 data, truncate it
                    logger.debug(f"Truncating base64 data in key '{key}', length: {len(value)}")
                    sanitized[key] = value[:50] + "...[TRUNCATED " + str(len(value)-100) + " chars]..." + value[-50:]
                elif isinstance(value, str) and len(value) > 1000 and (
                    # Check for base64-like patterns
                    value.startswith("data:image/") or
                    (len(value) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in value[:100]))
                ):
                    # This looks like base64 data (data URL or pure base64), truncate it
                    logger.debug(f"Truncating potential base64 data in key '{key}', length: {len(value)}")
                    sanitized[key] = value[:50] + "...[TRUNCATED " + str(len(value)-100) + " chars]..." + value[-50:]
                else:
                    # Recursively sanitize nested structures
                    sanitized[key] = _recursively_sanitize_base64(value)
            return sanitized
        elif isinstance(data, list):
            return [_recursively_sanitize_base64(item) for item in data]
        else:
            return data
    except Exception as e:
        logger.warning(f"Failed to recursively sanitize base64 data: {e}")
        return data


def _sanitize_payload_for_logging(request: AgentRunRequest) -> Dict[str, Any]:
    """Sanitize request payload for logging by truncating base64 content."""
    import copy
    
    try:
        # Create a deep copy to avoid modifying the original request
        sanitized = copy.deepcopy(request.dict())
        
        # Truncate base64 content in media_contents
        if sanitized.get("media_contents"):
            for media in sanitized["media_contents"]:
                if hasattr(media, "data") and isinstance(media.get("data"), str):
                    data = media["data"]
                    # Check if it's base64 data (long string or data URL)
                    if len(data) > 100 and ("base64" in data or len(data) > 200):
                        media["data"] = data[:50] + "...[TRUNCATED " + str(len(data)-100) + " chars]..." + data[-50:]
                elif isinstance(media, dict) and "data" in media:
                    data = media["data"]
                    if isinstance(data, str) and len(data) > 100 and ("base64" in data or len(data) > 200):
                        media["data"] = data[:50] + "...[TRUNCATED " + str(len(data)-100) + " chars]..." + data[-50:]
        
        # Truncate base64 content in channel_payload
        if sanitized.get("channel_payload") and isinstance(sanitized["channel_payload"], dict):
            payload = sanitized["channel_payload"]
            logger.debug(f"Found channel_payload with keys: {list(payload.keys())}")
            
            # Use recursive sanitization to handle any nested base64 content
            sanitized["channel_payload"] = _recursively_sanitize_base64(payload)
        
        return sanitized
        
    except Exception as e:
        # If sanitization fails, just return a basic representation
        logger.warning(f"Failed to sanitize payload for logging: {e}")
        return {
            "message_content": getattr(request, "message_content", ""),
            "message_type": getattr(request, "message_type", ""),
            "agent_name": getattr(request, "agent_name", ""),
            "error": "Failed to sanitize payload"
        }


def _sanitize_multimodal_content_for_logging(content: Any) -> Any:
    """Sanitize multimodal content for logging by truncating base64 data."""
    import copy
    import re
    
    def _is_base64_like(value: str) -> bool:
        """Check if string looks like base64 data."""
        if len(value) < 50:
            return False
        
        # Check for data URL pattern
        if value.startswith('data:'):
            return True
        
        # Check for base64 keyword
        if 'base64' in value[:100].lower():
            return True
            
        # Check for long alphanumeric string (likely base64)
        if len(value) > 100:
            # Base64 pattern: mostly alphanumeric with +, /, = padding
            # Check first 100 chars for base64 pattern
            sample = value[:100]
            base64_chars = re.match(r'^[A-Za-z0-9+/]*={0,2}$', sample)
            if base64_chars:
                # Additional check: base64 strings are usually long and have limited character set
                non_base64_chars = len([c for c in sample if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='])
                if non_base64_chars == 0 and len(value) > 150:
                    return True
        
        return False
    
    def _truncate_base64(value: str) -> str:
        """Truncate base64 data for logging."""
        if value.startswith('data:'):
            # Handle data URLs
            if ';base64,' in value:
                prefix, base64_part = value.split(';base64,', 1)
                return f"{prefix};base64,[BASE64_DATA_TRUNCATED_{len(base64_part)}_chars]"
        
        # Handle raw base64
        return f"[BASE64_DATA_TRUNCATED_{len(value)}_chars]"
    
    try:
        if isinstance(content, str):
            if _is_base64_like(content):
                return _truncate_base64(content)
            return content
            
        elif isinstance(content, dict):
            sanitized = copy.deepcopy(content)
            for key, value in sanitized.items():
                if isinstance(value, str):
                    # Check known base64 keys and any suspicious string
                    if key.lower() in ["data", "base64", "image_data", "content", "payload"] or _is_base64_like(value):
                        sanitized[key] = _truncate_base64(value) if _is_base64_like(value) else value
                elif isinstance(value, (dict, list)):
                    sanitized[key] = _sanitize_multimodal_content_for_logging(value)
            return sanitized
            
        elif isinstance(content, list):
            return [_sanitize_multimodal_content_for_logging(item) for item in content]
            
        else:
            return content
            
    except Exception as e:
        logger.warning(f"Failed to sanitize multimodal content for logging: {e}")
        return "[SANITIZATION_ERROR]"


async def handle_agent_run(agent_name: str, request: AgentRunRequest) -> Dict[str, Any]:
    """
    Run an agent with the specified parameters
    """
    session_id = None
    message_history = None

    try:
        # Ensure agent_name is a string
        if not isinstance(agent_name, str):
            agent_name = str(agent_name)

        # Create sanitized payload for logging (truncate base64 data) - BEFORE orchestration check
        sanitized_request = _sanitize_payload_for_logging(request)
        logger.debug(f"Request payload: {sanitized_request}")

        # Check if this should use LangGraph orchestration
        if should_use_orchestration(agent_name, request):
            logger.info(f"Routing to orchestrated execution for agent: {agent_name}")
            response = await handle_orchestrated_agent_run(agent_name, request)
            # Convert to Dict format for backward compatibility
            response_data = {
                "status": response.status,
                "message": response.message,
                "session_id": response.session_id,
                "agent_name": response.agent_name,
                "execution_time": response.execution_time,
                "orchestration": response.orchestration.model_dump()
                if response.orchestration
                else None,
                "data": response.data,
                "errors": response.errors,
            }
            
            # Add usage information if available
            if hasattr(response, 'usage') and response.usage:
                response_data["usage"] = response.usage
                
            return response_data

        # Payload already logged above with sanitization

        # Continue with regular agent execution for non-orchestrated agents
        logger.info(f"Using regular execution for agent: {agent_name}")

        # Early check for nonexistent agents to bail out before creating any DB entries
        if "nonexistent" in agent_name:
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_name}"
            )

        # Validate agent name and normalize if it's a variation
        # Get all registered agents from the database
        registered_agents = await run_in_threadpool(list_db_agents, active_only=False)

        # Check if this agent name is a variation of an existing agent
        normalized_agent_name = agent_name
        for existing_agent in registered_agents:
            # Check for common variations
            if (
                agent_name.lower() == f"{existing_agent.name.lower()}agent"
                or agent_name.lower() == f"{existing_agent.name.lower()}-agent"
                or agent_name.lower() == f"{existing_agent.name.lower()}_agent"
            ):
                # Use the base agent name instead
                normalized_agent_name = existing_agent.name
                logger.info(
                    f"Normalized agent name '{agent_name}' to '{normalized_agent_name}'"
                )
                break

        # Use normalized name for all operations
        agent_name = normalized_agent_name

        # Get or create user - special handling for WhatsApp
        # Check if this is a WhatsApp request that should defer user creation
        if not request.user_id and request.channel_payload:
            # Try WhatsApp-specific user handling first
            user_id = await get_or_create_user_for_whatsapp(request.channel_payload, request.context)
            if user_id is None:
                # WhatsApp request - let agent handle user identification
                logger.info("Deferring user identification to agent for WhatsApp request")
                # Use a temporary placeholder that the agent will replace
                user_id = None
            else:
                # Non-WhatsApp or user_id was determined
                user_id = await get_or_create_user(request.user_id, request.user, request.context)
        else:
            # Normal user creation flow
            user_id = await get_or_create_user(request.user_id, request.user, request.context)

        # Use agent name as-is for database lookup
        db_agent_name = agent_name

        # Try to get the agent from the database to get its ID
        agent_db = await run_in_threadpool(get_agent_by_name, db_agent_name)
        agent_id = agent_db.id if agent_db else None

        # Get or create session based on request parameters
        # For WhatsApp conversations, create a consistent session name based on phone number
        session_name = request.session_name
        if not session_name and request.channel_payload:
            # Extract WhatsApp phone number for session naming
            whatsapp_number = None
            if request.channel_payload.get("user"):
                whatsapp_number = request.channel_payload["user"].get("phone_number")
            elif request.context and request.context.get("whatsapp_user_number"):
                whatsapp_number = request.context.get("whatsapp_user_number")
            
            if whatsapp_number:
                # Create consistent session name for WhatsApp conversations
                session_name = f"whatsapp-{agent_name}-{whatsapp_number}"
                logger.info(f"🔄 Created WhatsApp session name: {session_name}")
        
        session_id, message_history = await get_or_create_session(
            session_id=request.session_id,
            session_name=session_name,
            agent_id=agent_id,
            user_id=user_id,
        )

        # For agents that don't exist, avoid creating any messages in the database
        if agent_name.startswith("nonexistent_") or "_nonexistent_" in agent_name:
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_name}"
            )

        # Initialize the agent - use agent name as-is
        factory = AgentFactory()
        agent_type = agent_name

        # Determine effective user ID before creating agent
        effective_user_id = user_id
        if user_id is None and message_history and hasattr(message_history, 'user_id'):
            effective_user_id = message_history.user_id
            logger.debug(f"Using user_id {effective_user_id} from message_history for agent creation")

        # Use get_agent_with_session for conversational agents to maintain memory
        logger.info(f"🔍 Creating agent with session caching: agent={agent_type}, session_id={session_id}, user_id={effective_user_id}")
        try:
            # IMPORTANT: Pass session_name to agent so it respects API naming rules
            agent = factory.get_agent_with_session(
                agent_type, 
                session_id=session_id, 
                user_id=effective_user_id,
                session_name=session_name  # Pass API-determined session name to agent
            )
            
            # MEMORY FIX: For cached agents, update the agent's MessageHistory to use the current session
            if (agent and hasattr(agent, 'context') and 
                agent.context.get('_conversation_history_restored')):
                logger.debug(f"💾 Updating MessageHistory for cached agent session {session_id}")
                # Replace the cached agent's old MessageHistory with the current session's MessageHistory
                try:
                    # Set the agent's dependencies to use the new MessageHistory
                    if hasattr(agent, 'dependencies') and hasattr(agent.dependencies, 'message_history'):
                        logger.debug(f"💾 Replacing cached agent's MessageHistory with current session {session_id}")
                        agent.dependencies.message_history = message_history
                        logger.debug(f"💾 Updated agent MessageHistory for session continuity")
                except Exception as e:
                    logger.warning(f"Failed to update MessageHistory for cached agent: {str(e)}")
                    # Continue with standard behavior if update fails

            # Check if agent exists
            if not agent or agent.__class__.__name__ == "PlaceholderAgent":
                raise HTTPException(
                    status_code=404, detail=f"Agent not found: {agent_name}"
                )

            # Set the agent ID from database if available
            if agent_id and not agent.db_id:
                agent.db_id = agent_id
                logger.info(f"Set agent {agent_name} database ID to {agent_id}")

            # Update the agent with the request parameters if provided
            if request.parameters:
                agent.update_config(request.parameters)
        except Exception as e:
            logger.error(f"Error getting agent {agent_name}: {str(e)}")
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_name}"
            )

        # Extract content and content type from the request
        content = request.message_content

        # Apply system prompt override if provided
        if request.system_prompt:
            agent.system_prompt = request.system_prompt

        # Link the agent to the session in the database if we have a persistent session
        if session_id and not getattr(message_history, "no_auto_create", False):
            # This will register the agent in the database and assign it a db_id
            success = factory.link_agent_to_session(agent_name, session_id)
            if success:
                # Reload the agent by name to get its ID
                agent_db = await run_in_threadpool(get_agent_by_name, db_agent_name)
                if agent_db:
                    # Set the db_id directly on the agent object
                    agent.db_id = agent_db.id
                    logger.info(
                        f"Updated agent {agent_name} with database ID {agent_db.id}"
                    )
            else:
                logger.warning(
                    f"Failed to link agent {agent_name} to session {session_id}"
                )
                # Continue anyway, as this is not a critical error

        # Process multimodal content (if any)
        multimodal_content = {}

        if request.media_contents:
            logger.debug(
                f"Processing {len(request.media_contents)} media content items"
            )
            for content_item in request.media_contents:
                try:
                    mime_type = content_item.mime_type
                    logger.debug(f"Processing media item with MIME type: {mime_type}")

                    if mime_type.startswith("image/"):
                        if "images" not in multimodal_content:
                            multimodal_content["images"] = []

                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, "data") and content_item.data:
                            data_content = content_item.data
                        elif (
                            hasattr(content_item, "media_url")
                            and content_item.media_url
                        ):
                            data_content = content_item.media_url

                        if data_content:
                            multimodal_content["images"].append(
                                {"data": data_content, "media_type": mime_type}
                            )
                            logger.debug(
                                f"Added image to multimodal content: {mime_type}"
                            )
                        else:
                            logger.warning(
                                "Image content item has no data or media_url"
                            )

                    elif mime_type.startswith("audio/"):
                        if "audio" not in multimodal_content:
                            multimodal_content["audio"] = []

                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, "data") and content_item.data:
                            data_content = content_item.data
                        elif (
                            hasattr(content_item, "media_url")
                            and content_item.media_url
                        ):
                            data_content = content_item.media_url

                        if data_content:
                            multimodal_content["audio"].append(
                                {"data": data_content, "media_type": mime_type}
                            )
                            logger.debug(
                                f"Added audio to multimodal content: {mime_type}"
                            )
                        else:
                            logger.warning(
                                "Audio content item has no data or media_url"
                            )

                    elif mime_type.startswith(("application/", "text/")):
                        if "documents" not in multimodal_content:
                            multimodal_content["documents"] = []

                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, "data") and content_item.data:
                            data_content = content_item.data
                        elif (
                            hasattr(content_item, "media_url")
                            and content_item.media_url
                        ):
                            data_content = content_item.media_url

                        if data_content:
                            multimodal_content["documents"].append(
                                {"data": data_content, "media_type": mime_type}
                            )
                            logger.debug(
                                f"Added document to multimodal content: {mime_type}"
                            )
                        else:
                            logger.warning(
                                "Document content item has no data or media_url"
                            )
                    else:
                        logger.warning(f"Unsupported MIME type: {mime_type}")

                except Exception as e:
                    logger.error(f"Error processing media content item: {str(e)}")
                    continue

            logger.debug(f"Final multimodal_content: {_sanitize_multimodal_content_for_logging(multimodal_content)}")

        # Add multimodal content to the message
        combined_content = {"text": content}
        if multimodal_content:
            combined_content.update(multimodal_content)

        # Process the message history
        if request.messages:
            # Use provided messages
            pass
        elif message_history:
            # Use message history
            history_messages, _ = await run_in_threadpool(
                message_history.get_messages, 1, 100, False
            )

        # -----------------------------------------------
        # Prepare context (system prompt + multimodal + user data)
        # -----------------------------------------------
        context = request.context.copy() if request.context else {}

        # Add user data to context if provided
        if request.user:
            if request.user.phone_number:
                context["user_phone_number"] = request.user.phone_number
            if request.user.email:
                context["user_email"] = request.user.email
            if request.user.user_data:
                # Add user_data fields to context with user_data_ prefix to avoid conflicts
                for key, value in request.user.user_data.items():
                    context[f"user_data_{key}"] = value

        # Add WhatsApp user data from channel_payload if available  
        if request.channel_payload and request.channel_payload.get("user"):
            whatsapp_user = request.channel_payload["user"]
            if whatsapp_user.get("phone_number"):
                context["whatsapp_user_number"] = whatsapp_user["phone_number"]
                # Also set as user_phone_number if not already set
                if "user_phone_number" not in context:
                    context["user_phone_number"] = whatsapp_user["phone_number"]

        # Attach system prompt override (if any)
        if request.system_prompt:
            context["system_prompt"] = request.system_prompt

        # Attach multimodal content and message type so downstream agent can detect it
        if multimodal_content:
            context["multimodal_content"] = multimodal_content
        
        # Pass message_type for framework selection
        if request.message_type:
            context["message_type"] = request.message_type

        # Run the agent
        response_content = None
        try:
            # Update context with the effective user_id if available
            if effective_user_id:
                context["user_id"] = str(effective_user_id)
            
            if content:
                response_content = await agent.process_message(
                    user_message=content,
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=effective_user_id,
                    message_history=message_history if message_history else None,
                    channel_payload=request.channel_payload,
                    context=context,
                    message_limit=request.message_limit,
                )
            else:
                # No content, run with empty string but still pass context for multimodal content
                response_content = await agent.process_message(
                    user_message="",
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=effective_user_id,
                    message_history=message_history if message_history else None,
                    channel_payload=request.channel_payload,
                    context=context,
                    message_limit=request.message_limit,
                )
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Agent execution failed: {str(e)}"
            )

        # Process the response
        usage_info = None
        if isinstance(response_content, str):
            # Simple string response
            response_text = response_content
            success = True
            tool_calls = []
            tool_outputs = []
        else:
            # Complex response from agent
            try:
                # Check if response_content is an object with attributes or a dict
                if hasattr(response_content, "text"):
                    # Object with attributes (AgentResponse)
                    response_text = (
                        response_content.text or 
                        getattr(response_content, "response", None) or
                        str(response_content)
                    )
                    success = getattr(response_content, "success", True)
                    tool_calls = getattr(response_content, "tool_calls", [])
                    tool_outputs = getattr(response_content, "tool_outputs", [])
                    usage_info = getattr(response_content, "usage", None)
                else:
                    # Dictionary - handle different response field names
                    response_text = (
                        response_content.get("text") or 
                        response_content.get("response") or 
                        str(response_content)
                    )
                    success = response_content.get("success", True)
                    tool_calls = response_content.get("tool_calls", [])
                    tool_outputs = response_content.get("tool_outputs", [])
                    usage_info = response_content.get("usage", None)
            except (AttributeError, TypeError):
                # Not a dictionary or expected object, use string representation
                response_text = str(response_content)
                success = True
                tool_calls = []
                tool_outputs = []

        # Format response according to the original API
        # Ensure session_id is always a string
        response_data = {
            "message": response_text,
            "session_id": str(session_id) if session_id else None,
            "success": success,
            "tool_calls": tool_calls,
            "tool_outputs": tool_outputs,
        }
        
        # Add the current user_id to the response
        # First check if the agent updated the user_id during execution
        final_user_id = effective_user_id
        if hasattr(agent, 'user_id') and agent.user_id:
            final_user_id = agent.user_id
        elif message_history and hasattr(message_history, 'user_id') and message_history.user_id:
            final_user_id = message_history.user_id
        
        if final_user_id:
            response_data["user_id"] = str(final_user_id)
        
        # Add usage information if available
        if usage_info:
            response_data["usage"] = usage_info
            
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to run agent: {str(e)}")


async def get_or_create_session(
    session_id=None, session_name=None, agent_id=None, user_id=None
):
    """Helper function to get or create a session based on provided parameters"""
    if session_id:
        # Validate and use existing session by ID
        if not safe_uuid(session_id):
            raise HTTPException(
                status_code=400, detail=f"Invalid session ID format: {session_id}"
            )

        history = await run_in_threadpool(
            lambda: MessageHistory(session_id=session_id, user_id=user_id)
        )

        # Verify session exists
        if not await run_in_threadpool(history.get_session_info):
            raise HTTPException(
                status_code=404, detail=f"Session not found: {session_id}"
            )

        return session_id, history

    elif session_name:
        # Try to find existing session by name
        session = await run_in_threadpool(get_session_by_name, session_name)

        if session:
            # Use existing session
            session_id = str(session.id)
            
            # If user_id is None (WhatsApp deferred identification), use the session's existing user_id
            if user_id is None:
                # Use the user_id from the existing session if available
                existing_user_id = session.user_id if session.user_id else None
                logger.debug(f"Using existing session {session_id} with user_id {existing_user_id} from session")
                return session_id, await run_in_threadpool(
                    lambda: MessageHistory(session_id=session_id, user_id=existing_user_id, no_auto_create=True)
                )
            else:
                return session_id, await run_in_threadpool(
                    lambda: MessageHistory(session_id=session_id, user_id=user_id)
                )
        else:
            # Create new named session
            session_id = generate_uuid()
            
            # For WhatsApp requests with no user_id, don't create session in database
            # to avoid foreign key constraints
            if user_id is None:
                logger.debug(f"Creating in-memory session for WhatsApp deferred identification: {session_name}")
                return str(session_id), await run_in_threadpool(
                    lambda: MessageHistory(session_id=str(session_id), user_id=None, no_auto_create=True)
                )
            else:
                session = Session(
                    id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                    name=session_name,
                    agent_id=agent_id,
                    user_id=user_id,
                )

                if not await run_in_threadpool(create_session, session):
                    logger.error(f"Failed to create session with name {session_name}")
                    raise HTTPException(status_code=500, detail="Failed to create session")

                return str(session_id), await run_in_threadpool(
                    lambda: MessageHistory(session_id=str(session_id), user_id=user_id)
                )

    else:
        # Create temporary in-memory session (don't persist to database for performance)
        temp_session_id = str(uuid.uuid4())
        logger.debug(f"Creating temporary in-memory session: {temp_session_id}")
        
        # For WhatsApp requests with no user_id, create MessageHistory without user_id
        # to avoid foreign key constraints with non-existent users
        if user_id is None:
            logger.debug("Creating MessageHistory without user_id for WhatsApp deferred identification")
            return str(temp_session_id), await run_in_threadpool(
                lambda: MessageHistory(
                    session_id=str(temp_session_id), user_id=None, no_auto_create=True
                )
            )
        else:
            return str(temp_session_id), await run_in_threadpool(
                lambda: MessageHistory(
                    session_id=str(temp_session_id), user_id=user_id, no_auto_create=True
                )
            )
