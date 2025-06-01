import logging
from typing import List, Dict, Any, Optional
import json  # Add json import
import re  # Move re import here
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body, BackgroundTasks, Depends
from starlette.responses import JSONResponse
from starlette import status
from pydantic import ValidationError, BaseModel, Field
from src.api.models import AgentInfo, AgentRunRequest
from src.api.controllers.agent_controller import list_registered_agents, handle_agent_run
from src.utils.session_queue import get_session_queue
from src.db.repository import session as session_repo
from src.db.repository import user as user_repo

# Create router for agent endpoints
agent_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)


class AsyncRunResponse(BaseModel):
    """Response for async run initiation."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status of the run")
    message: str = Field(..., description="Status message")
    agent_name: str = Field(..., description="Name of the agent")
    
    
class RunStatusResponse(BaseModel):
    """Response for run status check."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    agent_name: str = Field(..., description="Name of the agent")
    created_at: str = Field(..., description="When the run was created")
    started_at: Optional[str] = Field(None, description="When the run started")
    completed_at: Optional[str] = Field(None, description="When the run completed")
    result: Optional[Dict[str, Any]] = Field(None, description="Run result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")


async def execute_agent_async(
    run_id: str,
    agent_name: str,
    request: AgentRunRequest,
    session_id: str
):
    """Execute agent run in background."""
    try:
        # Update session metadata to mark as running
        metadata = {
            "run_id": run_id,
            "run_status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "agent_name": agent_name
        }
        # Store in session metadata
        session = session_repo.get_session(uuid.UUID(session_id))
        if session:
            updated_metadata = session.metadata or {}
            updated_metadata.update(metadata)
            session.metadata = updated_metadata
            session_repo.update_session(session)
        
        # Execute the agent
        result = await handle_agent_run(agent_name, request)
        
        # Update session with completion
        metadata = {
            "run_id": run_id,
            "run_status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "agent_name": agent_name
        }
        # Update through repository
        
    except Exception as e:
        # Update with error
        logger.error(f"Async run {run_id} failed: {e}")
        try:
            metadata = {
                "run_id": run_id,
                "run_status": "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e),
                "agent_name": agent_name
            }
            # Update through repository
        except Exception as update_error:
            logger.error(f"Failed to update session after error: {update_error}")


# Database-based cleanup happens automatically via session expiry

async def clean_and_parse_agent_run_payload(request: Request) -> AgentRunRequest:
    """
    Reads the raw request body, fixes common JSON issues, and parses it into a valid model.
    Handles problematic inputs like unescaped quotes and newlines in JSON strings.
    """
    raw_body = await request.body()
    try:
        # First try normal parsing
        try:
            # Try standard JSON parsing first
            body_str = raw_body.decode('utf-8')
            data_dict = json.loads(body_str)
            return AgentRunRequest.model_validate(data_dict)
        except json.JSONDecodeError as e:
            logger.info(f"Standard JSON parsing failed: {str(e)}")
            
            # Fallback to a simpler, more direct approach
            body_str = raw_body.decode('utf-8')
            
            # Fix common JSON issues
            try:
                # Simple approach: If we detect message_content with problematic characters,
                # extract and fix just that field
                
                # 1. Try to extract message_content field and clean it
                message_match = re.search(r'"message_content"\s*:\s*"((?:[^"\\]|\\.)*)(?:")', body_str, re.DOTALL)
                if message_match:
                    # Get the content
                    content = message_match.group(1)
                    
                    # Process content - escape newlines and internal quotes
                    processed_content = content.replace('\n', '\\n')
                    processed_content = processed_content.replace('"', '\\"')
                    # Clean any double escapes that might have been created
                    processed_content = processed_content.replace('\\\\', '\\')
                    processed_content = processed_content.replace('\\"', '\\\\"')
                    
                    # Replace in the original body with the fixed content
                    fixed_body = body_str.replace(message_match.group(0), f'"message_content":"{processed_content}"')
                    
                    try:
                        # Try to parse the fixed JSON
                        data_dict = json.loads(fixed_body)
                        return AgentRunRequest.model_validate(data_dict)
                    except Exception as e:
                        logger.warning(f"Failed to parse after message_content fix: {str(e)}")
                
                # 2. Try a more direct approach - manually construct a valid JSON object
                try:
                    # Extract fields using a safer pattern matching approach
                    message_content = None
                    message_type = None
                    session_name = None
                    user_id = None
                    message_limit = None
                    session_origin = None
                    user_data = {}
                    
                    # Extract message_content
                    message_match = re.search(r'"message_content"\s*:\s*"(.*?)(?<!\\)"', body_str, re.DOTALL)
                    if message_match:
                        message_content = message_match.group(1).replace('\n', '\\n').replace('"', '\\"')
                    
                    # Extract other fields
                    message_type_match = re.search(r'"message_type"\s*:\s*"([^"]*)"', body_str)
                    if message_type_match:
                        message_type = message_type_match.group(1)
                        
                    session_name_match = re.search(r'"session_name"\s*:\s*"([^"]*)"', body_str)
                    if session_name_match:
                        session_name = session_name_match.group(1)
                        
                    user_id_match = re.search(r'"user_id"\s*:\s*"([^"]*)"', body_str)
                    if user_id_match:
                        user_id = user_id_match.group(1)
                        
                    message_limit_match = re.search(r'"message_limit"\s*:\s*(\d+)', body_str)
                    if message_limit_match:
                        message_limit = int(message_limit_match.group(1))
                        
                    session_origin_match = re.search(r'"session_origin"\s*:\s*"([^"]*)"', body_str)
                    if session_origin_match:
                        session_origin = session_origin_match.group(1)
                    
                    # Extract user data
                    user_object_match = re.search(r'"user"\s*:\s*(\{[^}]*\})', body_str, re.DOTALL)
                    if user_object_match:
                        user_json_str = user_object_match.group(1)
                        
                        # Extract email
                        email_match = re.search(r'"email"\s*:\s*"([^"]*)"', user_json_str)
                        if email_match:
                            user_data['email'] = email_match.group(1)
                            
                        # Extract phone
                        phone_match = re.search(r'"phone_number"\s*:\s*"([^"]*)"', user_json_str)
                        if phone_match:
                            user_data['phone_number'] = phone_match.group(1)
                            
                        # Extract name if present
                        name_match = re.search(r'"name"\s*:\s*"([^"]*)"', user_json_str)
                        if name_match:
                            if 'user_data' not in user_data:
                                user_data['user_data'] = {}
                            user_data['user_data']['name'] = name_match.group(1)
                    
                    # Build a clean dictionary with extracted values
                    clean_data = {}
                    if message_content:
                        clean_data['message_content'] = message_content
                    if message_type:
                        clean_data['message_type'] = message_type
                    if session_name:
                        clean_data['session_name'] = session_name
                    if user_id:
                        clean_data['user_id'] = user_id
                    if message_limit:
                        clean_data['message_limit'] = message_limit
                    if session_origin:
                        clean_data['session_origin'] = session_origin
                    if user_data:
                        clean_data['user'] = user_data
                    
                    # Validate with our model
                    if clean_data:
                        return AgentRunRequest.model_validate(clean_data)
                
                except Exception as e:
                    logger.error(f"Manual JSON extraction failed: {str(e)}")
                
                # 3. Last resort - simply remove newlines and fix quotes
                try:
                    # Very basic approach - replace all literal newlines with escaped ones
                    simple_fixed = body_str.replace('\n', '\\n')
                    
                    # Try a very simple JSON load
                    data_dict = json.loads(simple_fixed)
                    return AgentRunRequest.model_validate(data_dict)
                except Exception as e:
                    logger.error(f"Simple newline replacement failed: {str(e)}")
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not parse malformed JSON after multiple attempts"
                )
                
            except Exception as e:
                logger.error(f"JSON cleaning failed: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process request: {str(e)}"
                )
                
    except UnicodeDecodeError:
        # Handle cases where the body is not valid UTF-8
        logger.warning(f"Failed to decode request body as UTF-8. Body starts with: {raw_body[:100]}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UTF-8 sequence in request body.",
        )
    except ValidationError as e:
        # If parsing fails even after cleaning (or due to other Pydantic rules),
        # raise the standard 422 error with Pydantic's detailed errors.
        logger.warning(f"Validation failed after cleaning attempt: {e.errors()}")
        # We need to re-format the errors slightly for FastAPI's detail structure
        error_details = []
        for error in e.errors():
            # Ensure 'loc' is a list of strings/ints as expected by FastAPI
            loc = [str(item) for item in error.get("loc", [])]
            error_details.append({
                "type": error.get("type"),
                "loc": ["body"] + loc, # Prepend 'body' to match FastAPI's convention
                "msg": error.get("msg"),
                "input": error.get("input"),
                "ctx": error.get("ctx"),
            })

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_details,
        )
    except Exception as e:
        # Catch any other unexpected errors during cleaning/parsing (e.g., JSONDecodeError not caught by Pydantic)
        logger.error(f"Unexpected error processing request body: {e}. Body starts with: {raw_body[:100]}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse JSON body: {str(e)}",
        )

@agent_router.get("/agent/list", response_model=List[AgentInfo], tags=["Agents"], 
           summary="List Registered Agents",
           description="Returns a list of all registered agents available in the database.")
async def list_agents():
    """
    Get a list of all registered agents
    """
    return await list_registered_agents()

@agent_router.post("/agent/{agent_name}/run", response_model=Dict[str, Any], tags=["Agents"],
            summary="Run Agent with Optional LangGraph Orchestration",
            description="Execute an agent with the specified name. Supports both simple agent execution and LangGraph orchestration for collaborative multi-agent workflows.")
async def run_agent(
    agent_name: str,
    agent_request: AgentRunRequest = Body(..., description="Agent request parameters with optional orchestration settings")
):
    """
    Run an agent with the specified parameters

    **Basic Agent Execution:**
    - **message_content**: Text message to send to the agent (required)
    - **session_id**: Optional ID to maintain conversation context
    - **session_name**: Optional name for the session (creates a persistent session)
    - **message_type**: Optional message type identifier
    - **user_id**: Optional user ID to associate with the request
    
    **LangGraph Orchestration (activated automatically for langgraph-* agents):**
    - **orchestration_config**: Orchestration settings and parameters
    - **target_agents**: List of agents to coordinate with (e.g., ["beta", "gamma", "delta"])
    - **workspace_paths**: Agent-specific workspace paths for isolated work
    - **max_rounds**: Maximum orchestration rounds (default: 3)
    - **run_count**: Number of agent iterations to run (default: 1 for cost control)
    - **enable_rollback**: Enable git rollback capabilities (default: true)
    - **enable_realtime**: Enable real-time progress streaming (default: false)
    
    **Examples:**
    ```
    # Simple agent
    POST /agent/simple/run
    {"message_content": "Hello world"}
    
    # LangGraph orchestrated workflow with full team
    POST /agent/langgraph-alpha/run  
    {
      "message_content": "Implement user authentication API",
      "target_agents": ["beta", "gamma", "delta"],
      "max_rounds": 5,
      "run_count": 2,
      "enable_rollback": true
    }
    
    # Single agent orchestration with limited runs
    POST /agent/langgraph-beta/run
    {
      "message_content": "Fix the authentication bug",
      "run_count": 1,
      "enable_rollback": false
    }
    ```
    """
    try:
        # Use session queue to ensure ordered processing per session
        session_queue = get_session_queue()

        # Determine a key to identify the session ordering scope
        queue_key = agent_request.session_id or agent_request.session_name or "_anonymous_"

        # Define processor function that will actually invoke the controller
        async def _processor(_sid, messages: list[str], *, agent_name: str, prototype_request: AgentRunRequest):
            # Merge message contents if multiple combined
            merged_content = "\n---\n".join(messages)
            # Create a new AgentRunRequest based on the prototype but with merged content
            try:
                new_request = prototype_request.model_copy(update={"message_content": merged_content})
            except AttributeError:
                # pydantic v1 fallback
                new_request = prototype_request.copy(update={"message_content": merged_content})
            return await handle_agent_run(agent_name, new_request)

        # Enqueue and await result
        result = await session_queue.process(
            queue_key,
            agent_request.message_content,
            _processor,
            agent_name=agent_name,
            prototype_request=agent_request,
        )

        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error running agent: {str(e)}"}
        )


@agent_router.post("/agent/{agent_name}/run/async", response_model=AsyncRunResponse, tags=["Agents"],
            summary="Run Agent Asynchronously",
            description="Start an agent run asynchronously and return immediately with a run ID.")
async def run_agent_async(
    agent_name: str,
    background_tasks: BackgroundTasks,
    agent_request: AgentRunRequest = Body(..., description="Agent request parameters")
):
    """
    Start an agent run asynchronously.
    
    Returns immediately with a run_id that can be used to check status.
    Useful for long-running operations that might timeout.
    
    **Example:**
    ```
    # Start async run
    POST /agent/alpha/run/async
    {"message_content": "Complex orchestration task"}
    
    # Returns:
    {
      "run_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "pending",
      "message": "Agent alpha run started",
      "agent_name": "alpha"
    }
    ```
    """
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    # Create session for async run using repositories
    try:
        # Ensure user exists
        user_id = agent_request.user_id
        if not user_id and agent_request.user:
            # Create user if needed
            from src.db.models import User
            email = agent_request.user.email
            phone_number = agent_request.user.phone_number
            user_data = agent_request.user.user_data or {}
            
            # Try to find existing user
            user = None
            if email:
                user = user_repo.get_user_by_email(email)
            
            # Create new user if not found
            if not user:
                new_user = User(
                    email=email,
                    phone_number=phone_number,
                    user_data=user_data
                )
                user_id = user_repo.create_user(new_user)
                user_id = str(user_id) if user_id else None
            else:
                user_id = str(user.id)
        
        # Create session with async run metadata
        from src.db.models import Session
        session = Session(
            agent_id=None,  # Will be set when agent is loaded
            name=agent_request.session_name or f"async-run-{run_id}",
            platform="api",
            user_id=uuid.UUID(user_id) if user_id else None,
            metadata={
                "run_id": run_id,
                "run_status": "pending",
                "agent_name": agent_name,
                "created_at": datetime.utcnow().isoformat(),
                "request": agent_request.dict()
            }
        )
        session_id = session_repo.create_session(session)
        
        # Update the request with the session ID
        agent_request.session_id = str(session_id)
        
        # Add to background tasks
        background_tasks.add_task(
            execute_agent_async,
            run_id,
            agent_name,
            agent_request,
            str(session_id)
        )
        
    except Exception as e:
        logger.error(f"Failed to create async run session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create async run: {str(e)}")
    
    return AsyncRunResponse(
        run_id=run_id,
        status="pending",
        message=f"Agent {agent_name} run started",
        agent_name=agent_name
    )


@agent_router.get("/run/{run_id}/status", response_model=RunStatusResponse, tags=["Agents"],
           summary="Get Async Run Status",
           description="Check the status of an asynchronous agent run.")
async def get_run_status(run_id: str):
    """
    Get the status of an async run.
    
    **Status values:**
    - `pending`: Run is queued but not started
    - `running`: Run is currently executing
    - `completed`: Run finished successfully
    - `failed`: Run failed with an error
    
    **Example:**
    ```
    GET /run/123e4567-e89b-12d3-a456-426614174000/status
    
    # Returns:
    {
      "run_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "agent_name": "alpha",
      "created_at": "2024-01-01T00:00:00",
      "started_at": "2024-01-01T00:00:01",
      "completed_at": "2024-01-01T00:00:30",
      "result": {...},
      "error": null
    }
    ```
    """
    try:
        # Find session by run_id using repository
        sessions = session_repo.list_sessions()  # Get all sessions
        
        # Find session with matching run_id in metadata
        target_session = None
        for session in sessions:
            if session.metadata and session.metadata.get('run_id') == run_id:
                target_session = session
                break
        
        if not target_session:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        metadata = target_session.metadata or {}
        
        # Get messages for the session
        from src.db.repository import message as message_repo
        messages = message_repo.list_messages(target_session.id)
        
        # Get the latest assistant message
        latest_message = None
        assistant_messages = [msg for msg in messages if msg.role == 'assistant']
        if assistant_messages:
            latest = assistant_messages[-1]
            latest_message = {
                "content": latest.text_content,
                "data": latest.raw_payload
            }
        
        return RunStatusResponse(
            run_id=run_id,
            status=metadata.get('run_status', 'unknown'),
            agent_name=metadata.get('agent_name', 'unknown'),
            created_at=target_session.created_at.isoformat() if target_session.created_at else None,
            started_at=metadata.get('started_at'),
            completed_at=metadata.get('completed_at') or (
                target_session.run_finished_at.isoformat() if target_session.run_finished_at else None
            ),
            result=latest_message,
            error=metadata.get('error'),
            progress={"message_count": len(messages)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get run status: {str(e)}") 