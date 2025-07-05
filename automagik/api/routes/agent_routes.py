import logging
import os
from typing import List, Dict, Any, Optional
import json  # Add json import
import re  # Move re import here
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body, BackgroundTasks
from starlette.responses import JSONResponse
from starlette import status
from pydantic import ValidationError, BaseModel, Field
from automagik.api.models import (
    AgentInfo, AgentRunRequest, AgentCreateRequest, AgentUpdateRequest, 
    AgentCreateResponse, AgentUpdateResponse, AgentDeleteResponse,
    AgentCopyRequest, AgentCopyResponse,
    ToolInfo, ToolExecuteRequest, ToolExecuteResponse
)
from automagik.api.controllers.agent_controller import list_registered_agents, handle_agent_run
from automagik.utils.session_queue import get_session_queue
from automagik.db.repository import session as session_repo
from automagik.db.repository import user as user_repo
from automagik.db.repository import agent as agent_repo
from automagik.db.repository import prompt as prompt_repo
from automagik.db.models import Agent, Prompt, PromptCreate
from automagik.config import settings

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
    """Response for run status check with comprehensive progress tracking."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    agent_name: str = Field(..., description="Name of the agent")
    created_at: str = Field(..., description="When the run was created")
    started_at: Optional[str] = Field(None, description="When the run started")
    completed_at: Optional[str] = Field(None, description="When the run completed")
    result: Optional[str] = Field(None, description="Final Claude response content")
    error: Optional[str] = Field(None, description="Error message if failed")
    progress: Optional[Dict[str, Any]] = Field(None, description="Rich progress information with all available metrics")


def parse_log_file(log_file_path: str) -> Dict[str, Any]:
    """
    Parse Claude Code log file and extract ALL available rich data.
    
    Returns comprehensive data structure with:
    - Execution phases and timestamps
    - Performance metrics (duration, cost, token usage)
    - Session information and confirmation status
    - Claude response content and metadata
    - Tool usage and container information
    - Git and workflow context
    - Real-time progress indicators
    """
    if not os.path.exists(log_file_path):
        return {
            "error": "Log file not found",
            "phase": "unknown",
            "available": False
        }
    
    try:
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
        
        # Initialize comprehensive data structure
        data = {
            "phase": "unknown",
            "available": True,
            "execution_summary": {},
            "session_info": {},
            "performance_metrics": {},
            "claude_response": {},
            "container_info": {},
            "workflow_context": {},
            "tool_usage": {},
            "git_info": {},
            "progress_tracking": {},
            "timestamps": {},
            "raw_events": []
        }
        
        claude_responses = []
        events_by_type = {}
        
        for line in lines:
            try:
                event = json.loads(line.strip())
                data["raw_events"].append(event)
                
                # Categorize events by type
                event_type = event.get("event_type", "unknown")
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(event)
                
                # Extract data based on event type
                event_data = event.get("data", {})
                timestamp = event.get("timestamp")
                
                if event_type == "init":
                    data["timestamps"]["init"] = timestamp
                    data["phase"] = "initializing"
                
                elif event_type == "event":
                    message = event_data.get("message", "")
                    if "ClaudeCodeAgent.run() called" in message:
                        data["workflow_context"].update({
                            "workflow_name": event_data.get("workflow_name"),
                            "input_length": event_data.get("input_length"),
                            "has_multimodal": event_data.get("has_multimodal")
                        })
                    elif "Starting Claude CLI execution" in message:
                        data["workflow_context"].update({
                            "max_turns": event_data.get("request", {}).get("max_turns"),
                            "git_branch": event_data.get("request", {}).get("git_branch"),
                            "timeout": event_data.get("request", {}).get("timeout")
                        })
                    elif "completed" in message:
                        data["phase"] = "completed"
                        data["execution_summary"]["success"] = event_data.get("success")
                        data["execution_summary"]["exit_code"] = event_data.get("exit_code")
                        data["execution_summary"]["execution_time"] = event_data.get("execution_time")
                        data["git_info"]["commits"] = event_data.get("git_commits")
                        data["execution_summary"]["result_length"] = event_data.get("result_length")
                
                elif event_type == "raw_command":
                    data["container_info"].update({
                        "executable": event_data.get("executable"),
                        "working_directory": event_data.get("working_directory"),
                        "command_length": event_data.get("command_length"),
                        "user_message_length": event_data.get("user_message_length"),
                        "max_turns": event_data.get("max_turns"),
                        "workflow": event_data.get("workflow")
                    })
                    data["session_info"]["session_details"] = event_data.get("session_details", {})
                
                elif event_type == "session_confirmed":
                    data["session_info"].update({
                        "claude_session_id": event_data.get("session_id"),
                        "confirmed": event_data.get("confirmed"),
                        "confirmation_time": timestamp
                    })
                    data["phase"] = "session_active"
                
                elif event_type == "claude_output":
                    # Extract parsed data - check if parsing was successful first
                    if event_data.get("parsed") is True:
                        # Parse the message JSON string to get the actual data
                        try:
                            parsed_data = json.loads(event_data.get("message", "{}"))
                        except (json.JSONDecodeError, TypeError):
                            parsed_data = {}
                    else:
                        parsed_data = {}
                    
                    if parsed_data and parsed_data.get("type") == "result":
                        # This is the final result
                        data["claude_response"].update({
                            "final_result": parsed_data.get("result"),
                            "cost_usd": parsed_data.get("cost_usd"),
                            "total_cost": parsed_data.get("total_cost"),
                            "duration_ms": parsed_data.get("duration_ms"),
                            "duration_api_ms": parsed_data.get("duration_api_ms"),
                            "num_turns": parsed_data.get("num_turns"),
                            "session_id": parsed_data.get("session_id"),
                            "is_error": parsed_data.get("is_error")
                        })
                        data["performance_metrics"].update({
                            "cost_usd": parsed_data.get("cost_usd"),
                            "duration_ms": parsed_data.get("duration_ms"),
                            "duration_api_ms": parsed_data.get("duration_api_ms"),
                            "turns_used": parsed_data.get("num_turns")
                        })
                    elif parsed_data and parsed_data.get("type") == "assistant":
                        # Assistant message
                        message_data = parsed_data.get("message", {})
                        content = message_data.get("content", [])
                        if content and isinstance(content, list) and len(content) > 0:
                            text_content = content[0].get("text", "")
                            claude_responses.append({
                                "content": text_content,
                                "timestamp": timestamp,
                                "usage": message_data.get("usage", {}),
                                "stop_reason": message_data.get("stop_reason")
                            })
                    elif parsed_data and parsed_data.get("type") == "system":
                        # System initialization with tools
                        data["tool_usage"].update({
                            "available_tools": parsed_data.get("tools", []),
                            "mcp_servers": parsed_data.get("mcp_servers", []),
                            "model": parsed_data.get("model"),
                            "cwd": parsed_data.get("cwd")
                        })
                
                elif event_type == "workflow_init":
                    data["workflow_context"].update({
                        "workspace": event_data.get("workspace"),
                        "command_preview": event_data.get("command_preview"),
                        "full_command_length": event_data.get("full_command_length")
                    })
                    data["phase"] = "workflow_starting"
                
                elif event_type == "process":
                    data["container_info"]["pid"] = event_data.get("pid")
                    data["container_info"]["command_args"] = event_data.get("command_args")
                
                elif event_type == "workflow_completion":
                    data["phase"] = "completed"
                    data["execution_summary"].update({
                        "exit_code": event_data.get("exit_code"),
                        "success": event_data.get("success"),
                        "streaming_messages_count": event_data.get("streaming_messages_count"),
                        "stdout_lines": event_data.get("stdout_lines"),
                        "stderr_lines": event_data.get("stderr_lines"),
                        "result_preview": event_data.get("final_result_preview")
                    })
                    data["timestamps"]["completion"] = timestamp
                
            except (json.JSONDecodeError, KeyError):
                # Skip malformed lines
                continue
        
        # Process collected Claude responses
        if claude_responses:
            data["claude_response"]["messages"] = claude_responses
            data["claude_response"]["message_count"] = len(claude_responses)
            # Get the final response content
            if claude_responses:
                final_response = claude_responses[-1]
                data["claude_response"]["final_content"] = final_response.get("content")
        
        # Calculate progress metrics
        data["progress_tracking"] = {
            "total_events": len(data["raw_events"]),
            "events_by_type": {k: len(v) for k, v in events_by_type.items()},
            "response_count": len(claude_responses),
            "has_final_result": bool(data["claude_response"].get("final_result")),
            "session_confirmed": data["session_info"].get("confirmed", False)
        }
        
        # Final phase determination - check if we have completion events
        if "workflow_completion" in events_by_type or data["claude_response"].get("final_result"):
            data["phase"] = "completed"
        
        # Add tool analysis
        available_tools = data["tool_usage"].get("available_tools", [])
        if available_tools:
            tool_categories = {
                "file_operations": [t for t in available_tools if t in ["Read", "Write", "Edit", "MultiEdit"]],
                "system_operations": [t for t in available_tools if t in ["Task", "Bash", "LS"]],
                "search_operations": [t for t in available_tools if t in ["Grep", "Glob"]],
                "mcp_tools": [t for t in available_tools if t.startswith("mcp__")],
                "collaboration": [t for t in available_tools if "linear" in t.lower() or "slack" in t.lower()],
                "git_operations": [t for t in available_tools if "git" in t.lower()]
            }
            data["tool_usage"]["tool_categories"] = tool_categories
            data["tool_usage"]["total_tools"] = len(available_tools)
        
        return data
        
    except Exception as e:
        return {
            "error": f"Failed to parse log file: {str(e)}",
            "phase": "error",
            "available": False
        }


def find_claude_code_log(run_id: str) -> Optional[str]:
    """Find Claude Code log file by run_id."""
    log_dir = settings.AUTOMAGIK_LOG_DIRECTORY
    if not os.path.exists(log_dir):
        return None
    
    # Look for log files matching the run_id pattern
    for filename in os.listdir(log_dir):
        if run_id in filename and filename.endswith('.log'):
            return os.path.join(log_dir, filename)
    
    return None


def find_claude_stream_file(run_id: str) -> Optional[str]:
    """Find Claude Code stream JSONL file by run_id."""
    log_dir = settings.AUTOMAGIK_LOG_DIRECTORY
    if not os.path.exists(log_dir):
        return None
    
    # Look for stream files matching the run_id pattern
    stream_file = os.path.join(log_dir, f"run_{run_id}_stream.jsonl")
    if os.path.exists(stream_file):
        return stream_file
    
    return None


def parse_stream_file(stream_file_path: str) -> Dict[str, Any]:
    """Parse Claude Code stream JSONL file and extract real-time data."""
    if not os.path.exists(stream_file_path):
        return {
            "error": "Stream file not found",
            "status": "unknown",
            "available": False
        }
    
    try:
        data = {
            "status": "running",
            "available": True,
            "messages": [],
            "session_info": {},
            "final_result": None,
            "cost_usd": 0.0,
            "turns": 0,
            "completed": False
        }
        
        with open(stream_file_path, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    data["messages"].append(event)
                    
                    # Extract key information
                    if event.get("type") == "system" and event.get("subtype") == "init":
                        data["session_info"] = {
                            "session_id": event.get("session_id"),
                            "model": event.get("model"),
                            "tools_count": len(event.get("tools", [])),
                            "mcp_servers": event.get("mcp_servers", [])
                        }
                        data["status"] = "running"
                    
                    elif event.get("type") == "result":
                        data["completed"] = True
                        data["cost_usd"] = event.get("total_cost_usd", 0.0)
                        data["turns"] = event.get("num_turns", 0)
                        
                        if event.get("subtype") == "success":
                            data["status"] = "completed"
                            data["final_result"] = event.get("result")
                        else:
                            data["status"] = "failed"
                            data["final_result"] = f"Error: {event.get('subtype', 'unknown')}"
                    
                    elif event.get("type") == "assistant":
                        # Extract assistant responses for preview
                        message = event.get("message", {})
                        content = message.get("content", [])
                        if content and isinstance(content, list):
                            for item in content:
                                if item.get("type") == "text":
                                    # Store latest response as preview
                                    data["latest_response"] = item.get("text", "")
                        
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return data
        
    except Exception as e:
        return {
            "error": f"Failed to parse stream file: {str(e)}",
            "status": "error",
            "available": False
        }


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
        await handle_agent_run(agent_name, request)
        
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

@agent_router.get("/agents", response_model=List[AgentInfo], tags=["Agents"], 
           summary="List Registered Agents",
           description="Returns a list of all registered agents available in the database.")
async def list_agents():
    """
    Get a list of all registered agents
    """
    return await list_registered_agents()

@agent_router.post("/agent/{agent_name}/run", response_model=Dict[str, Any], tags=["Agents"],
            summary="Run Agent",
            description="Execute an agent with the specified name. Supports agent execution with configurable parameters and session management.")
async def run_agent(
    agent_name: str,
    agent_request: AgentRunRequest = Body(..., description="Agent request parameters including message content and session configuration")
):
    """
    Run an agent with the specified parameters

    **Agent Execution Parameters:**
    - **message_content**: Text message to send to the agent (required)
    - **session_id**: Optional ID to maintain conversation context
    - **session_name**: Optional name for the session (creates a persistent session)
    - **message_type**: Optional message type identifier
    - **user_id**: Optional user ID to associate with the request
    - **run_count**: Number of agent iterations to run (default: 1)
    - **enable_rollback**: Enable git rollback capabilities (default: true)
    
    **Examples:**
    ```
    # Simple agent execution
    POST /agent/simple/run
    {"message_content": "Hello world"}
    
    # Agent with session persistence
    POST /agent/claude_code/run  
    {
      "message_content": "Analyze this code snippet",
      "session_name": "code_review_session",
      "run_count": 1
    }
    
    # Agent with user context
    POST /agent/claude_code/run
    {
      "message_content": "Help me debug this issue",
      "user_id": "user123",
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
            from automagik.db.models import User
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
        from automagik.db.models import Session
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
    Get the comprehensive status of an async run with ALL available rich data.
    
    **Enhanced Status Response:**
    - **Basic status**: pending, running, completed, failed
    - **Execution metrics**: duration, cost, token usage, turn count
    - **Session information**: Claude session ID, confirmation status
    - **Real Claude response**: actual content (not just metadata)
    - **Progress tracking**: phase, events, tool usage, container info
    - **Performance data**: API response times, execution times
    - **Workflow context**: workspace, git info, tool categories
    
    **Example:**
    ```
    GET /run/run_3e78488309c5/status
    
    # Returns rich data including:
    {
      "run_id": "run_3e78488309c5",
      "status": "completed",
      "result": "Here are my top 3 most essential tools:\\n\\n1. **Read** - ...",
      "progress": {
        "phase": "completed",
        "execution_summary": {"success": true, "execution_time": 35.39},
        "performance_metrics": {"cost_usd": 0.0005248, "duration_ms": 30449},
        "session_info": {"claude_session_id": "aea79791-...", "confirmed": true},
        "tool_usage": {"total_tools": 81, "tool_categories": {...}},
        "workflow_context": {"workflow_name": "test", "max_turns": 30}
      }
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
        from automagik.db.repository import message as message_repo
        messages = message_repo.list_messages(target_session.id)
        
        # Try to find and parse Claude Code stream file for real-time data
        stream_file_path = find_claude_stream_file(run_id)
        stream_data = {}
        if stream_file_path:
            stream_data = parse_stream_file(stream_file_path)
            logger.info(f"Parsed stream file for run {run_id}: {stream_file_path}")
        else:
            logger.warning(f"No stream file found for run {run_id}")
        
        # Extract result - prefer stream data, fallback to database
        result_content = None
        if stream_data.get("final_result"):
            # Use Claude's actual final result from stream
            result_content = stream_data["final_result"]
        elif stream_data.get("latest_response"):
            # Use latest response from stream
            result_content = stream_data["latest_response"]
        else:
            # Fallback to database message
            assistant_messages = [msg for msg in messages if msg.role == 'assistant']
            if assistant_messages:
                latest = assistant_messages[-1]
                result_content = latest.text_content
        
        # Determine status - prefer stream data, fallback to metadata
        status = stream_data.get("status", "unknown")
        if status == "unknown":
            # Fallback to metadata
            status = metadata.get('run_status', 'pending')
        
        # Build comprehensive progress object with real-time stream data
        progress = {
            "message_count": len(messages),
            "stream_available": bool(stream_file_path),
            "stream_file_path": stream_file_path
        }
        
        # Add all stream data if available
        if stream_data.get("available"):
            progress.update({
                "status": stream_data.get("status", "unknown"),
                "completed": stream_data.get("completed", False),
                "session_info": stream_data.get("session_info", {}),
                "cost_usd": stream_data.get("cost_usd", 0.0),
                "turns": stream_data.get("turns", 0),
                "messages_count": len(stream_data.get("messages", [])),
                "latest_response": stream_data.get("latest_response", ""),
                "real_time": True  # Indicates this is from real-time stream
            })
        else:
            # Stream data not available, add error info
            if stream_data.get("error"):
                progress["stream_error"] = stream_data["error"]
        
        return RunStatusResponse(
            run_id=run_id,
            status=status,
            agent_name=metadata.get('agent_name', "unknown"),
            created_at=target_session.created_at.isoformat() if target_session.created_at else None,
            started_at=metadata.get('started_at'),
            completed_at=metadata.get('completed_at') or (
                target_session.run_finished_at.isoformat() if target_session.run_finished_at else None
            ),
            result=result_content,  # Real Claude response content from stream
            error=metadata.get('error') or stream_data.get("error"),
            progress=progress  # Rich progress data with ALL metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get run status: {str(e)}")


# AGENT CRUD ENDPOINTS

@agent_router.post("/agent/create", response_model=AgentCreateResponse, tags=["Agents"],
                  summary="Create a new virtual agent",
                  description="Create a new virtual agent with configuration. Supports both virtual and code-based agents.")
async def create_agent(request: AgentCreateRequest):
    """Create a new agent (virtual or code-based)."""
    try:
        logger.info(f"Creating agent: {request.name}")
        
        # Validate virtual agent configuration if applicable
        config = request.config or {}
        if config.get("agent_source") == "virtual":
            from automagik.agents.common.virtual_agent_validator import VirtualAgentConfigValidator
            
            validation_errors = VirtualAgentConfigValidator.validate_config(config)
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail=f"Virtual agent configuration invalid: {'; '.join(validation_errors)}"
                )
            
            # Validate tool names if tools are enabled
            tool_config = config.get("tool_config", {})
            enabled_tools = tool_config.get("enabled_tools", [])
            if enabled_tools:
                tool_errors = VirtualAgentConfigValidator.validate_tool_names(enabled_tools)
                if tool_errors:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Virtual agent tools invalid: {'; '.join(tool_errors)}"
                    )
        
        # Create Agent model first (without prompt reference)
        agent = Agent(
            name=request.name,
            type=request.type,
            model=request.model,
            description=request.description,
            config=config,
            active=True,
            active_default_prompt_id=None  # Will be set after prompt creation
        )
        
        # Create the agent in database first
        agent_id = agent_repo.create_agent(agent)
        
        # Handle system prompt - create in prompts table after agent exists
        prompt_id = None
        if config.get("system_prompt"):
            prompt_id = await _create_agent_prompt(agent_id=agent_id, prompt_text=config["system_prompt"], agent_name=request.name)
            # Update agent with prompt reference
            if prompt_id:
                from automagik.db.connection import execute_query
                from fastapi.concurrency import run_in_threadpool
                await run_in_threadpool(
                    lambda: execute_query(
                        "UPDATE agents SET active_default_prompt_id = %s, updated_at = NOW() WHERE id = %s",
                        (prompt_id, agent_id),
                        fetch=False
                    )
                )
            # Remove from config since it's now in prompts table
            del config["system_prompt"]
        
        if agent_id is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create agent {request.name}"
            )
        
        logger.info(f"Successfully created agent {request.name} with ID {agent_id}")
        
        return AgentCreateResponse(
            status="success",
            message=f"Agent '{request.name}' created successfully",
            agent_id=agent_id,
            agent_name=request.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent {request.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@agent_router.put("/agent/{agent_name}", response_model=AgentUpdateResponse, tags=["Agents"],
                 summary="Update an existing agent",
                 description="Update an existing agent's configuration.")
async def update_agent(agent_name: str, request: AgentUpdateRequest):
    """Update an existing agent."""
    try:
        logger.info(f"Updating agent: {agent_name}")
        
        # Get existing agent
        existing_agent = agent_repo.get_agent_by_name(agent_name)
        if not existing_agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found"
            )
        
        # Update fields that were provided
        if request.type is not None:
            existing_agent.type = request.type
        if request.model is not None:
            existing_agent.model = request.model
        if request.description is not None:
            existing_agent.description = request.description
        if request.config is not None:
            existing_agent.config = request.config
        if request.active is not None:
            existing_agent.active = request.active
        
        # Update the agent in database
        agent_id = agent_repo.update_agent(existing_agent)
        
        if agent_id is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update agent {agent_name}"
            )
        
        logger.info(f"Successfully updated agent {agent_name}")
        
        return AgentUpdateResponse(
            status="success",
            message=f"Agent '{agent_name}' updated successfully",
            agent_name=agent_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@agent_router.delete("/agent/{agent_name}", response_model=AgentDeleteResponse, tags=["Agents"],
                    summary="Delete an agent",
                    description="Delete an agent by name.")
async def delete_agent(agent_name: str):
    """Delete an agent by name."""
    try:
        logger.info(f"Deleting agent: {agent_name}")
        
        # Get existing agent
        existing_agent = agent_repo.get_agent_by_name(agent_name)
        if not existing_agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found"
            )
        
        # Delete the agent from database
        success = agent_repo.delete_agent(existing_agent.id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete agent {agent_name}"
            )
        
        logger.info(f"Successfully deleted agent {agent_name}")
        
        return AgentDeleteResponse(
            status="success",
            message=f"Agent '{agent_name}' deleted successfully",
            agent_name=agent_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")


@agent_router.post("/agent/{source_agent_name}/copy", response_model=AgentCopyResponse, tags=["Agents"],
                  summary="Copy an existing agent with modifications",
                  description="Create a copy of an existing agent with optional prompt and configuration changes.")
async def copy_agent(source_agent_name: str, request: AgentCopyRequest):
    """Copy an existing agent with modifications."""
    try:
        logger.info(f"Copying agent {source_agent_name} to {request.new_name}")
        
        # Get source agent
        source_agent = agent_repo.get_agent_by_name(source_agent_name)
        if not source_agent:
            raise HTTPException(
                status_code=404,
                detail=f"Source agent '{source_agent_name}' not found"
            )
        
        # Check if new agent name already exists
        existing_agent = agent_repo.get_agent_by_name(request.new_name)
        if existing_agent:
            raise HTTPException(
                status_code=409,
                detail=f"Agent '{request.new_name}' already exists"
            )
        
        # Copy source agent configuration
        new_config = {}
        if source_agent.config:
            new_config = source_agent.config.copy()
        
        # Ensure it's marked as virtual (copies are always virtual)
        new_config["agent_source"] = "virtual"
        
        if request.tool_config:
            new_config["tool_config"] = request.tool_config
        
        # Set default_model for virtual agents (required by validator)
        if request.model:
            new_config["default_model"] = request.model
        elif not new_config.get("default_model"):
            # Use source agent model as fallback
            new_config["default_model"] = source_agent.model
        
        # Create the copied agent first (without prompt reference)
        copied_agent = Agent(
            name=request.new_name,
            type=source_agent.type,
            model=request.model or source_agent.model,
            description=request.description or f"Copy of {source_agent_name}",
            config=new_config,
            active=True,
            active_default_prompt_id=None  # Will be set after prompt creation
        )
        
        # Validate virtual agent configuration
        if new_config.get("agent_source") == "virtual":
            from automagik.agents.common.virtual_agent_validator import VirtualAgentConfigValidator
            
            validation_errors = VirtualAgentConfigValidator.validate_config(new_config)
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail=f"Copied agent configuration invalid: {'; '.join(validation_errors)}"
                )
        
        # Create the agent in database first
        agent_id = agent_repo.create_agent(copied_agent)
        
        # Handle system prompt - create in prompts table after agent exists
        prompt_id = None
        if request.system_prompt:
            prompt_id = await _create_agent_prompt(agent_id=agent_id, prompt_text=request.system_prompt, agent_name=request.new_name)
            # Update agent with prompt reference
            if prompt_id:
                from automagik.db.connection import execute_query
                from fastapi.concurrency import run_in_threadpool
                await run_in_threadpool(
                    lambda: execute_query(
                        "UPDATE agents SET active_default_prompt_id = %s, updated_at = NOW() WHERE id = %s",
                        (prompt_id, agent_id),
                        fetch=False
                    )
                )
        
        if agent_id is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create copied agent {request.new_name}"
            )
        
        logger.info(f"Successfully copied agent {source_agent_name} to {request.new_name} with ID {agent_id}")
        
        return AgentCopyResponse(
            status="success",
            message=f"Agent '{source_agent_name}' copied to '{request.new_name}' successfully",
            source_agent=source_agent_name,
            new_agent=request.new_name,
            agent_id=agent_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying agent {source_agent_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to copy agent: {str(e)}")


# TOOL MANAGEMENT ENDPOINTS
# 
# NOTE: Tool management endpoints have been moved to src/api/routes/tool_routes.py
# for better organization and comprehensive functionality. The new endpoints provide:
# - GET /tools - List all tools with filtering and search
# - GET /tools/{tool_name} - Get tool details with execution stats
# - POST /tools/{tool_name}/execute - Execute tools with proper logging
# - POST /tools - Create new tools
# - PUT /tools/{tool_name} - Update existing tools  
# - DELETE /tools/{tool_name} - Delete tools
# - GET /tools/categories/list - List all categories
# - POST /tools/discover - Discover and sync all tools
# - POST /tools/mcp/servers - Create MCP server configurations
#
# The old hardcoded tool discovery has been replaced with dynamic discovery
# that scans automagik/tools/ directories and connects to MCP servers for comprehensive
# tool management with proper database persistence and execution metrics.


async def _create_agent_prompt(agent_id: Optional[int], prompt_text: str, agent_name: str) -> Optional[int]:
    """Create a prompt in the database for an agent.
    
    Args:
        agent_id: Agent ID (None if agent not created yet)
        prompt_text: The prompt text content
        agent_name: Name of the agent (for prompt naming)
        
    Returns:
        Prompt ID if successful, None otherwise
    """
    try:
        from fastapi.concurrency import run_in_threadpool
        
        if not agent_id:
            raise ValueError("Agent ID is required for prompt creation")
            
        prompt_create = PromptCreate(
            agent_id=agent_id,
            prompt_text=prompt_text,
            version=1,
            is_active=True,
            is_default_from_code=False,
            status_key="default",
            name=f"{agent_name} - Default Prompt"
        )
        
        prompt_id = await run_in_threadpool(prompt_repo.create_prompt, prompt_create)
        logger.info(f"Created prompt {prompt_id} for agent {agent_name}")
        return prompt_id
        
    except Exception as e:
        logger.error(f"Error creating prompt for agent {agent_name}: {e}")
        return None


async def _update_prompt_agent_id(prompt_id: int, agent_id: int) -> None:
    """Update prompt with correct agent_id after agent creation.
    
    Args:
        prompt_id: ID of the prompt to update
        agent_id: Correct agent ID to set
    """
    try:
        from fastapi.concurrency import run_in_threadpool
        from automagik.db.connection import execute_query
        
        # Update the prompt with direct SQL since PromptUpdate doesn't have agent_id field
        await run_in_threadpool(
            lambda: execute_query(
                "UPDATE prompts SET agent_id = %s, updated_at = NOW() WHERE id = %s",
                (agent_id, prompt_id),
                fetch=False
            )
        )
        logger.debug(f"Updated prompt {prompt_id} with agent_id {agent_id}")
        
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id} with agent_id {agent_id}: {e}") 