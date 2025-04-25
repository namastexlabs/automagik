"""Agent controller functions for handling agent operations."""

import logging
import uuid
import json
import inspect
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException
from datetime import datetime

from src.agents.models.agent_factory import AgentFactory
from src.config import settings
from src.memory.message_history import MessageHistory
from src.api.models import AgentInfo, AgentRunRequest, MessageModel, UserCreate
from src.db import get_agent_by_name, get_user, create_user, User
from src.db.models import Session
from src.db.connection import generate_uuid, safe_uuid
from src.db.repository.session import get_session_by_name, create_session
from src.db.repository.agent import list_agents as list_db_agents

# Get our module's logger
logger = logging.getLogger(__name__)

async def list_registered_agents() -> List[AgentInfo]:
    """
    List all registered agents from the database.
    """
    try:
        # Get all registered agents from the database
        registered_agents = list_db_agents(active_only=True)
        
        # Convert to list of AgentInfo objects
        agent_infos = []
        for agent in registered_agents:
            # Get agent class to fetch docstring (optional, could be removed if description isn't crucial)
            factory = AgentFactory()
            agent_class = factory.get_agent_class(agent.name.replace('_agent', ''))
            docstring = inspect.getdoc(agent_class) if agent_class else agent.description or ""
            
            # Create agent info including the ID
            agent_infos.append(AgentInfo(
                id=agent.id,
                name=agent.name.replace('_agent', ''),
                description=docstring
            ))
            
        return agent_infos
    except Exception as e:
        logger.error(f"Error listing registered agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list registered agents: {str(e)}")


async def get_or_create_user(user_id: Optional[Union[uuid.UUID, str]] = None, user_data: Optional[UserCreate] = None) -> Optional[uuid.UUID]:
    """
    Get or create a user based on the provided ID and data.
    
    Args:
        user_id: Optional user ID
        user_data: Optional user data for creation/update
        
    Returns:
        UUID of the existing or newly created user
    """
    # Import UserCreate here as well to ensure it's available
    from src.api.models import UserCreate
    
    # If no user ID or data, return None
    if not user_id and not user_data:
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
            user = get_user(user_id)
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
        from src.db import update_user
        updated_id = update_user(user)
        return updated_id
        
    # If user doesn't exist but we have user_data, create new user
    elif user_data:
        # Create new user
        new_user = User(
            id=user_id if user_id else generate_uuid(),
            email=user_data.email,
            phone_number=user_data.phone_number,
            user_data=user_data.user_data
        )
        created_id = create_user(new_user)
        return created_id
        
    # If user doesn't exist and we don't have user_data, create minimal user
    elif user_id and not user:
        # Create minimal user with just the ID
        new_user = User(id=user_id)
        created_id = create_user(new_user)
        return created_id
        
    # User exists but no updates needed
    return user.id if user else None


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
        
        # Early check for nonexistent agents to bail out before creating any DB entries
        if "nonexistent" in agent_name:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        
        # Get or create user
        user_id = await get_or_create_user(request.user_id, request.user)
            
        # Convert agent_name to include '_agent' suffix if not already present
        db_agent_name = f"{agent_name}_agent" if not agent_name.endswith('_agent') else agent_name
        
        # Try to get the agent from the database to get its ID
        agent_db = get_agent_by_name(db_agent_name)
        agent_id = agent_db.id if agent_db else None
        
        # Get or create session based on request parameters
        session_id, message_history = await get_or_create_session(
            session_id=request.session_id, 
            session_name=request.session_name, 
            agent_id=agent_id,
            user_id=user_id
        )
        
        # For agents that don't exist, avoid creating any messages in the database
        if agent_name.startswith("nonexistent_") or "_nonexistent_" in agent_name:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
            
        # Initialize the agent - strip '_agent' suffix for factory
        factory = AgentFactory()
        agent_type = agent_name.replace('_agent', '') if agent_name.endswith('_agent') else agent_name
        
        # Use get_agent instead of create_agent to reuse existing instances
        try:
            agent = factory.get_agent(agent_type)
            
            # Check if agent exists
            if not agent or agent.__class__.__name__ == "PlaceholderAgent":
                raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
                
            # Update the agent with the request parameters if provided
            if request.parameters:
                agent.update_config(request.parameters)
        except Exception as e:
            logger.error(f"Error getting agent {agent_name}: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")

        # Extract content and content type from the request
        content = request.message_content
        content_type = request.message_type
        
        # Apply system prompt override if provided
        if request.system_prompt:
            agent.system_prompt = request.system_prompt
        
        # Link the agent to the session in the database if we have a persistent session
        if session_id and not getattr(message_history, "no_auto_create", False):
            # This will register the agent in the database and assign it a db_id
            success = factory.link_agent_to_session(agent_name, session_id)
            if success:
                # Reload the agent by name to get its ID
                agent_db = get_agent_by_name(db_agent_name)
                if agent_db:
                    # Set the db_id directly on the agent object
                    agent.db_id = agent_db.id
                    logger.info(f"Updated agent {agent_name} with database ID {agent_db.id}")
            else:
                logger.warning(f"Failed to link agent {agent_name} to session {session_id}")
                # Continue anyway, as this is not a critical error
        
        # Process multimodal content (if any)
        multimodal_content = {}
        
        if request.media_contents:
            for content_item in request.media_contents:
                if getattr(content_item, "mime_type", "").startswith("image/"):
                    if "images" not in multimodal_content:
                        multimodal_content["images"] = []
                    
                    multimodal_content["images"].append({
                        "data": getattr(content_item, "data", None) or getattr(content_item, "media_url", None),
                        "mime_type": content_item.mime_type
                    })
                else:
                    # Add other content types as needed
                    pass
        
        # Add multimodal content to the message
        combined_content = {"text": content}
        if multimodal_content:
            combined_content.update(multimodal_content)
        
        # Process the message history
        messages = []
        if request.messages:
            # Use provided messages
            messages = request.messages
        elif message_history:
            # Use message history
            history_messages, _ = message_history.get_messages(page=1, page_size=100, sort_desc=False)
            messages = history_messages
        
        # Update context with system_prompt if provided
        context = request.context or {}
        if request.system_prompt:
            context.update({"system_prompt": request.system_prompt})
        
        # Run the agent
        response_content = None
        try:
            if content:
                response_content = await agent.process_message(
                    user_message=content, 
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=user_id,
                    message_history=message_history if message_history else None,
                    channel_payload=request.channel_payload,
                    context=context,
                    message_limit=request.message_limit
                )
            else:
                # No content, run with empty string
                response_content = await agent.process_message("")
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
        
        # Process the response
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
                if hasattr(response_content, 'text'):
                    # Object with attributes (AgentResponse)
                    response_text = response_content.text
                    success = getattr(response_content, 'success', True)
                    tool_calls = getattr(response_content, 'tool_calls', [])
                    tool_outputs = getattr(response_content, 'tool_outputs', [])
                else:
                    # Dictionary
                    response_text = response_content.get("text", str(response_content))
                    success = response_content.get("success", True)
                    tool_calls = response_content.get("tool_calls", [])
                    tool_outputs = response_content.get("tool_outputs", [])
            except (AttributeError, TypeError):
                # Not a dictionary or expected object, use string representation
                response_text = str(response_content)
                success = True
                tool_calls = []
                tool_outputs = []
        
        # Format response according to the original API
        # Ensure session_id is always a string
        return {
            "message": response_text,
            "session_id": str(session_id) if session_id else None,
            "success": success,
            "tool_calls": tool_calls,
            "tool_outputs": tool_outputs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to run agent: {str(e)}") 
    
    
async def get_or_create_session(session_id=None, session_name=None, agent_id=None, user_id=None):
    """Helper function to get or create a session based on provided parameters"""
    if session_id:
        # Validate and use existing session by ID
        if not safe_uuid(session_id):
            raise HTTPException(status_code=400, detail=f"Invalid session ID format: {session_id}")
        
        history = MessageHistory(session_id=session_id, user_id=user_id)
        
        # Verify session exists
        if not history.get_session_info():
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        return session_id, history

    elif session_name:
        # Try to find existing session by name
        session = get_session_by_name(session_name)
        
        if session:
            # Use existing session
            session_id = str(session.id)
            return session_id, MessageHistory(session_id=session_id, user_id=user_id)
        else:
            # Create new named session
            session_id = generate_uuid()
            session = Session(
                id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                name=session_name,
                agent_id=agent_id,
                user_id=user_id
            )
            
            if not create_session(session):
                logger.error(f"Failed to create session with name {session_name}")
                raise HTTPException(status_code=500, detail="Failed to create session")
            
            return str(session_id), MessageHistory(session_id=str(session_id), user_id=user_id)

    else:
        # Create temporary session
        temp_session_id = str(uuid.uuid4())
        return temp_session_id, MessageHistory(session_id=temp_session_id, no_auto_create=True)
