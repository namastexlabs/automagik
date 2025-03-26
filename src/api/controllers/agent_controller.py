import logging
import uuid
import json
import inspect
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from datetime import datetime

from src.agents.models.agent_factory import AgentFactory
from src.config import settings
from src.memory.message_history import MessageHistory
from src.api.models import AgentInfo, AgentRunRequest, MessageModel
from src.db import get_agent_by_name
from src.db.models import Session
from src.db.connection import generate_uuid, safe_uuid
from src.db.repository.session import get_session_by_name, create_session

# Get our module's logger
logger = logging.getLogger(__name__)

async def list_agent_templates() -> List[AgentInfo]:
    """
    List all available agent templates
    """
    try:
        # Get all available agent templates
        factory = AgentFactory()
        agent_templates = factory.list_available_agents()
        
        # Convert to list of AgentInfo objects
        agent_infos = []
        for template in agent_templates:
            # Get agent class
            agent_class = factory.get_agent_class(template)
            
            # Skip if agent class not found
            if not agent_class:
                continue
                
            # Get docstring (if any)
            docstring = inspect.getdoc(agent_class) or ""
            
            # Create agent info
            agent_infos.append(AgentInfo(
                name=template,
                description=docstring
            ))
            
        return agent_infos
    except Exception as e:
        logger.error(f"Error listing agent templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list agent templates: {str(e)}")


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
            
        # Convert agent_name to include '_agent' suffix if not already present
        db_agent_name = f"{agent_name}_agent" if not agent_name.endswith('_agent') else agent_name
        
        # Try to get the agent from the database to get its ID
        agent_db = get_agent_by_name(db_agent_name)
        agent_id = agent_db.id if agent_db else None
        # Process session information
        
        # Get or create session based on request parameters
        session_id, message_history = await get_or_create_session(
            session_id=request.session_id, 
            session_name=request.session_name, 
            agent_id=agent_id,
            user_id=request.user_id
        )
        
        # For agents that don't exist, avoid creating any messages in the database
        if agent_name.startswith("nonexistent_") or "_nonexistent_" in agent_name:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        # Initialize the agent - strip '_agent' suffix for factory
        factory = AgentFactory()
        agent_type = agent_name.replace('_agent', '') if agent_name.endswith('_agent') else agent_name
        agent = factory.create_agent(agent_type, request.parameters)
        
        # Check if agent is a PlaceholderAgent
        if agent.__class__.__name__ == "PlaceholderAgent":
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        
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
        content = request.message_content
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
        
        # Run the agent
        response_content = None
        try:
            if content:
                response_content = await agent.process_message(
                    user_message=content, 
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=request.user_id,
                    message_history=message_history if message_history else None,
                    channel_payload=request.channel_payload,
                    context=request.context,
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
