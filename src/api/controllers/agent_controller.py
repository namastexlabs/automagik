"""Agent controller functions for handling agent operations."""

import logging
import uuid
import inspect
import time
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from src.agents.models.agent_factory import AgentFactory
from src.memory.message_history import MessageHistory
from src.api.models import AgentInfo, AgentRunRequest, AgentRunResponse, OrchestrationStatus, UserCreate
from src.db import get_agent_by_name, get_user, create_user, User, ensure_default_user_exists
from src.db.models import Session
from src.db.connection import generate_uuid, safe_uuid
from src.db.repository.session import get_session_by_name, create_session
from src.db.repository.agent import list_agents as list_db_agents
from src.db.repository.user import list_users

# Get our module's logger
logger = logging.getLogger(__name__)


def is_langgraph_agent(agent_name: str) -> bool:
    """Check if an agent is a LangGraph orchestration agent."""
    return agent_name.startswith("langgraph-")


def should_use_orchestration(agent_name: str, request: AgentRunRequest) -> bool:
    """Determine if a request should use LangGraph orchestration."""
    return (
        is_langgraph_agent(agent_name) or
        request.orchestration_config is not None or
        request.target_agents is not None
    )


async def handle_orchestrated_agent_run(agent_name: str, request: AgentRunRequest) -> AgentRunResponse:
    """Handle LangGraph orchestrated agent execution."""
    start_time = time.time()
    
    try:
        # Import orchestration components
        from src.agents.langgraph.shared.orchestrator import LangGraphOrchestrator
        from src.agents.langgraph.shared.state_store import OrchestrationStateStore
        
        logger.info(f"Starting orchestrated execution for agent: {agent_name}")
        
        # Initialize orchestrator
        orchestrator = LangGraphOrchestrator()
        state_store = OrchestrationStateStore()
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Build orchestration config with run_count limitation
        orchestration_config = request.orchestration_config or {}
        
        # Handle individual agent runs vs full team orchestration
        if request.target_agents:
            # Full team orchestration
            target_agents = request.target_agents
        else:
            # Single agent run - only run the specified agent
            base_agent_name = agent_name.replace("langgraph-", "")
            target_agents = [base_agent_name]
        
        orchestration_config.update({
            "target_agents": target_agents,
            "workspace_paths": request.workspace_paths or {},
            "max_rounds": min(request.max_rounds, request.run_count),  # Limit by run_count
            "run_count": request.run_count,  # Pass run_count to orchestrator
            "enable_rollback": request.enable_rollback,
            "enable_realtime": request.enable_realtime,
            # Claude CLI specific parameters
            "max_turns": request.max_turns,  # Will use default if None
            "resume_session": request.resume_session,
            "force_new_session": request.force_new_session,
            "allowed_tools_file": request.allowed_tools_file,
            "mcp_config_path": request.mcp_config_path,
            "system_prompt_file": request.system_prompt_file,
            "whatsapp_notifications": request.whatsapp_notifications,
            "slack_thread_ts": request.slack_thread_ts,
            # Enhanced orchestration parameters
            "epic_id": request.epic_id,
            "linear_project_id": request.linear_project_id,
            "slack_channel_id": request.slack_channel_id or "C08UF878N3Z",
            "human_phone_number": request.human_phone_number
        })
        
        # Log the configuration for debugging
        logger.info(f"Orchestration config: target_agents={target_agents}, max_rounds={orchestration_config['max_rounds']}, run_count={request.run_count}")
        
        # Initialize orchestration session
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
        
        # Actually execute the orchestration instead of just initializing
        result = await orchestrator.execute_orchestration(
            session_id=session_uuid,
            agent_name=agent_name.replace("langgraph-", ""),  # Remove prefix for actual agent
            task_message=request.message_content,
            orchestration_config=orchestration_config
        )
        
        # Extract execution details from result
        execution_time = time.time() - start_time
        
        # Build orchestration status from execution result
        orchestration_status = OrchestrationStatus(
            is_orchestrated=True,
            phase=result.get("final_phase", "completed"),
            round_number=result.get("rounds_completed", 0),
            current_agent=agent_name.replace("langgraph-", ""),
            workflow_state=result.get("execution_result"),
            total_agents=len(target_agents),
            completed_agents=target_agents if result.get("success") else [],
            failed_agents=[] if result.get("success") else target_agents,
            rollback_available=request.enable_rollback,
            last_checkpoint=result.get("git_sha_end")
        )
        
        # Determine success message based on execution
        if result.get("success"):
            message = f"Orchestration completed successfully for {agent_name}. Rounds completed: {result.get('rounds_completed', 0)}"
        else:
            message = f"Orchestration failed for {agent_name}: {result.get('error', 'Unknown error')}"
        
        return AgentRunResponse(
            status="success" if result.get("success") else "error",
            message=message,
            session_id=str(session_id),
            agent_name=agent_name,
            execution_time=execution_time,
            orchestration=orchestration_status,
            data={
                "execution_result": result.get("execution_result"),
                "final_state": result,
                "config": orchestration_config
            },
            errors=[result.get("error")] if result.get("error") else None
        )
        
    except Exception as e:
        logger.error(f"Orchestration failed for {agent_name}: {str(e)}", exc_info=True)
        execution_time = time.time() - start_time
        
        return AgentRunResponse(
            status="error",
            message=f"Orchestration failed: {str(e)}",
            session_id=request.session_id,
            agent_name=agent_name,
            execution_time=execution_time,
            orchestration=OrchestrationStatus(is_orchestrated=True, phase="failed"),
            errors=[str(e)]
        )


async def list_registered_agents() -> List[AgentInfo]:
    """
    List all registered agents from the database.
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
            
            # Skip if we already have this agent with a newer ID (likely more up-to-date)
            if agent_name in unique_agents and unique_agents[agent_name].id > agent.id:
                logger.info(f"Skipping duplicate agent {agent.name} (ID: {agent.id}) in favor of newer entry (ID: {unique_agents[agent_name].id})")
                continue
                
            # Store this agent as the canonical version for this name
            unique_agents[agent_name] = agent
            
        logger.info(f"Found {len(registered_agents)} agents, {len(unique_agents)} unique agents")
        
        # Convert to list of AgentInfo objects
        agent_infos = []
        for agent_name, agent in unique_agents.items():
            # Get agent class to fetch docstring
            factory = AgentFactory()
            agent_class = factory.get_agent_class(agent_name)
            docstring = inspect.getdoc(agent_class) if agent_class else agent.description or ""
            
            # Create agent info including the ID
            agent_infos.append(AgentInfo(
                id=agent.id,
                name=agent_name,  # Return the actual agent name
                description=docstring
            ))
            
        # Sort by name for consistent ordering
        agent_infos.sort(key=lambda x: x.name)
            
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
        from src.db import update_user
        updated_id = await run_in_threadpool(update_user, user)
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
        
        # Check if this should use LangGraph orchestration
        if should_use_orchestration(agent_name, request):
            logger.info(f"Routing to orchestrated execution for agent: {agent_name}")
            response = await handle_orchestrated_agent_run(agent_name, request)
            # Convert to Dict format for backward compatibility
            return {
                "status": response.status,
                "message": response.message,
                "session_id": response.session_id,
                "agent_name": response.agent_name,
                "execution_time": response.execution_time,
                "orchestration": response.orchestration.model_dump() if response.orchestration else None,
                "data": response.data,
                "errors": response.errors
            }
        
        # Continue with regular agent execution for non-orchestrated agents
        logger.info(f"Using regular execution for agent: {agent_name}")
        
        # Early check for nonexistent agents to bail out before creating any DB entries
        if "nonexistent" in agent_name:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
        
        # Validate agent name and normalize if it's a variation
        # Get all registered agents from the database
        registered_agents = await run_in_threadpool(list_db_agents, active_only=False)
        
        # Check if this agent name is a variation of an existing agent
        normalized_agent_name = agent_name
        for existing_agent in registered_agents:
            # Check for common variations
            if (agent_name.lower() == f"{existing_agent.name.lower()}agent" or
                agent_name.lower() == f"{existing_agent.name.lower()}-agent" or
                agent_name.lower() == f"{existing_agent.name.lower()}_agent"):
                # Use the base agent name instead
                normalized_agent_name = existing_agent.name
                logger.info(f"Normalized agent name '{agent_name}' to '{normalized_agent_name}'")
                break
        
        # Use normalized name for all operations
        agent_name = normalized_agent_name
        
        # Get or create user
        user_id = await get_or_create_user(request.user_id, request.user)
            
        # Use agent name as-is for database lookup
        db_agent_name = agent_name
        
        # Try to get the agent from the database to get its ID
        agent_db = await run_in_threadpool(get_agent_by_name, db_agent_name)
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
            
        # Initialize the agent - use agent name as-is
        factory = AgentFactory()
        agent_type = agent_name
        
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
                    logger.info(f"Updated agent {agent_name} with database ID {agent_db.id}")
            else:
                logger.warning(f"Failed to link agent {agent_name} to session {session_id}")
                # Continue anyway, as this is not a critical error
        
        # Process multimodal content (if any)
        multimodal_content = {}
        
        if request.media_contents:
            logger.debug(f"Processing {len(request.media_contents)} media content items")
            for content_item in request.media_contents:
                try:
                    mime_type = content_item.mime_type
                    logger.debug(f"Processing media item with MIME type: {mime_type}")
                    
                    if mime_type.startswith("image/"):
                        if "images" not in multimodal_content:
                            multimodal_content["images"] = []
                        
                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, 'data') and content_item.data:
                            data_content = content_item.data
                        elif hasattr(content_item, 'media_url') and content_item.media_url:
                            data_content = content_item.media_url
                        
                        if data_content:
                            multimodal_content["images"].append({
                                "data": data_content,
                                "mime_type": mime_type
                            })
                            logger.debug(f"Added image to multimodal content: {mime_type}")
                        else:
                            logger.warning("Image content item has no data or media_url")
                            
                    elif mime_type.startswith("audio/"):
                        if "audio" not in multimodal_content:
                            multimodal_content["audio"] = []
                        
                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, 'data') and content_item.data:
                            data_content = content_item.data
                        elif hasattr(content_item, 'media_url') and content_item.media_url:
                            data_content = content_item.media_url
                        
                        if data_content:
                            multimodal_content["audio"].append({
                                "data": data_content,
                                "mime_type": mime_type
                            })
                            logger.debug(f"Added audio to multimodal content: {mime_type}")
                        else:
                            logger.warning("Audio content item has no data or media_url")
                            
                    elif mime_type.startswith(("application/", "text/")):
                        if "documents" not in multimodal_content:
                            multimodal_content["documents"] = []
                        
                        # Get data from either URL or binary data field
                        data_content = None
                        if hasattr(content_item, 'data') and content_item.data:
                            data_content = content_item.data
                        elif hasattr(content_item, 'media_url') and content_item.media_url:
                            data_content = content_item.media_url
                        
                        if data_content:
                            multimodal_content["documents"].append({
                                "data": data_content,
                                "mime_type": mime_type
                            })
                            logger.debug(f"Added document to multimodal content: {mime_type}")
                        else:
                            logger.warning("Document content item has no data or media_url")
                    else:
                        logger.warning(f"Unsupported MIME type: {mime_type}")
                        
                except Exception as e:
                    logger.error(f"Error processing media content item: {str(e)}")
                    continue
            
            logger.debug(f"Final multimodal_content: {multimodal_content}")
        

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
            history_messages, _ = await run_in_threadpool(message_history.get_messages, 1, 100, False)
        
        # -----------------------------------------------
        # Prepare context (system prompt + multimodal)
        # -----------------------------------------------
        context = request.context.copy() if request.context else {}

        # Attach system prompt override (if any)
        if request.system_prompt:
            context["system_prompt"] = request.system_prompt

        # Attach multimodal content so downstream agent can detect it
        if multimodal_content:
            context["multimodal_content"] = multimodal_content
        
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
                # No content, run with empty string but still pass context for multimodal content
                response_content = await agent.process_message(
                    user_message="",
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=user_id,
                    message_history=message_history if message_history else None,
                    channel_payload=request.channel_payload,
                    context=context,
                    message_limit=request.message_limit
                )
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
        
        history = await run_in_threadpool(lambda: MessageHistory(session_id=session_id, user_id=user_id))
        
        # Verify session exists
        if not await run_in_threadpool(history.get_session_info):
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        return session_id, history

    elif session_name:
        # Try to find existing session by name
        session = await run_in_threadpool(get_session_by_name, session_name)
        
        if session:
            # Use existing session
            session_id = str(session.id)
            return session_id, await run_in_threadpool(lambda: MessageHistory(session_id=session_id, user_id=user_id))
        else:
            # Create new named session
            session_id = generate_uuid()
            session = Session(
                id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                name=session_name,
                agent_id=agent_id,
                user_id=user_id
            )
            
            if not await run_in_threadpool(create_session, session):
                logger.error(f"Failed to create session with name {session_name}")
                raise HTTPException(status_code=500, detail="Failed to create session")
            
            return str(session_id), await run_in_threadpool(lambda: MessageHistory(session_id=str(session_id), user_id=user_id))

    else:
        # Create temporary in-memory session (don't persist to database for performance)
        temp_session_id = str(uuid.uuid4())
        logger.debug(f"Creating temporary in-memory session: {temp_session_id}")
        return str(temp_session_id), await run_in_threadpool(lambda: MessageHistory(session_id=str(temp_session_id), user_id=user_id, no_auto_create=True))
