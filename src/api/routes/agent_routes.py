import logging
from typing import List, Any, Dict
import json  # Add json import
import re  # Move re import here
from fastapi import APIRouter, HTTPException, Request, Depends, Body
from starlette.responses import JSONResponse
from starlette import status
from pydantic import ValidationError
from src.api.models import AgentInfo, AgentRunRequest
from src.api.controllers.agent_controller import list_registered_agents, handle_agent_run

# Create router for agent endpoints
agent_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

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

@agent_router.post("/agent/{agent_name}/run", tags=["Agents"],
            summary="Run Agent",
            description="Execute an agent with the specified name. Optionally provide a session ID or name to maintain conversation context.")
async def run_agent(
    agent_name: str,
    agent_request: AgentRunRequest = Body(..., description="Agent request parameters")
):
    """
    Run an agent with the specified parameters

    - **message_content**: Text message to send to the agent (required)
    - **session_id**: Optional ID to maintain conversation context
    - **session_name**: Optional name for the session (creates a persistent session)
    - **message_type**: Optional message type identifier
    - **user_id**: Optional user ID to associate with the request
    """
    try:
        # Our middleware will have already fixed any JSON parsing issues
        # FastAPI will have already validated the request against the AgentRunRequest model
        return await handle_agent_run(agent_name, agent_request)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error running agent: {str(e)}"}
        ) 