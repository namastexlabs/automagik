"""
Command for running a single message through an agent.

This command provides a simplified interface to send a single message to an agent.
It's designed for quick tests and integrations.
"""

import sys
import asyncio
import json
import typer
from typing import Dict, List, Optional, Any
import requests
import os
import logging

# Import settings right at the beginning to ensure it's defined before use
from automagik.config import settings

# Import tracing decorators if available
try:
    from automagik.tracing.decorators import trace_cli_command, trace_async_cli_command
except ImportError:
    # Create no-op decorators if tracing is not available
    def trace_cli_command(command_name=None, track_args=True):
        def decorator(func):
            return func
        return decorator
    
    def trace_async_cli_command(command_name=None, track_args=True):
        def decorator(func):
            return func
        return decorator

# Create app for the run command
run_app = typer.Typer(no_args_is_help=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@run_app.callback()
def run_callback(
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode", is_flag=True, hidden=True
    ),
):
    """
    Run a single message through an agent and get the response.

    Use the 'message' command with required options:
      automagik-agents agent run message --agent <agent_name> --message "Your message here"

    Example:
      automagik-agents agent run message --agent simple --message "Hello, how are you?"

    For multimodal content:
      automagik-agents agent run message --agent simple --message "Describe this image" --image-url "https://example.com/image.jpg"
      automagik-agents agent run message --agent simple --message "What does this audio say?" --audio-url "https://example.com/audio.mp3"
      automagik-agents agent run message --agent simple --message "Summarize this document" --document-url "https://example.com/document.pdf"
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"


def get_api_endpoint(path: str) -> str:
    """Build a consistent API endpoint URL with the correct prefix."""
    # Ensure the path doesn't start with a slash
    if path.startswith("/"):
        path = path[1:]

    # Always use /api/v1/ prefix
    if not path.startswith("api/v1/"):
        path = f"api/v1/{path}"

    # Build the full URL with server from settings
    # The host and port values are stored in AUTOMAGIK_API_HOST and AUTOMAGIK_API_PORT
    server = f"http://{settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}"
    if not server.endswith('/'):
        server = f"{server}/"
    url = f"{server}{path}"

    return url


def get_available_agents() -> List[Dict[str, Any]]:
    """Get a list of available agents using the API."""
    # Check if debug mode is enabled either via settings or directly from environment variable
    debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (
        os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG"
    )

    try:
        # Define the API endpoint for listing agents
        endpoint = get_api_endpoint("agent/list")
        if debug_mode:
            typer.echo(f"Getting agents from: {endpoint}")

        # Prepare headers with API key if available
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY

        # Make the API request
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)

            # Check if the request was successful
            if response.status_code == 200:
                agents = response.json()
                if debug_mode:
                    typer.echo(f"Successfully retrieved {len(agents)} agents")

                # Convert the API response to a format compatible with the rest of the code
                for agent in agents:
                    # Ensure id field is present (use name as fallback)
                    if "id" not in agent:
                        agent["id"] = agent["name"]

                    # If description is missing, provide a default
                    if "description" not in agent or not agent["description"]:
                        agent["description"] = (
                            f"Agent of type {agent.get('type', 'unknown')}"
                        )

                    # If model is missing, provide a default
                    if "model" not in agent or not agent["model"]:
                        agent["model"] = "openai:gpt-4.1"  # Updated default model

                return agents
            else:
                typer.echo(
                    f"Error getting agents: HTTP {response.status_code}", err=True
                )
                if debug_mode:
                    typer.echo(f"Response: {response.text}", err=True)
                return []
        except requests.exceptions.ConnectionError:
            typer.echo(
                f"Connection error: Could not connect to API server at {endpoint}",
                err=True,
            )
            return []
    except Exception as e:
        typer.echo(f"Error getting agents from API: {str(e)}", err=True)
        return []


async def get_user_by_id(user_id: int) -> Dict[str, Any]:
    """Get user data from the API by ID."""
    # Check if debug mode is enabled either via settings or directly from environment variable
    debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (
        os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG"
    )

    try:
        # Define the API endpoint
        endpoint = get_api_endpoint(f"users/{user_id}")
        if debug_mode:
            typer.echo(f"Getting user data from: {endpoint}")

        # Prepare headers with API key if available
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY

        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=10)

        # Check if the request was successful
        if response.status_code == 200:
            user_data = response.json()
            if debug_mode:
                typer.echo(f"Successfully retrieved user {user_id} from API")
            return user_data
        else:
            if debug_mode:
                typer.echo(
                    f"Error getting user by ID {user_id}: HTTP {response.status_code}"
                )
                typer.echo("Using fallback user data")
            # Return fallback data
            return {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "name": f"User {user_id}",
            }
    except Exception as e:
        if debug_mode:
            typer.echo(f"Error getting user from API: {str(e)}")
            typer.echo("Using fallback user data")
        # Return fallback data
        return {
            "id": user_id,
            "email": f"user{user_id}@example.com",
            "name": f"User {user_id}",
        }


@trace_async_cli_command(command_name="run_agent")
async def run_agent(
    agent_name: str, input_message: str, session_name: str = None, user_id: int = 1,
    multimodal_content: Dict[str, str] = None
) -> dict:
    """Run the agent with the given message using the API."""
    try:
        # Check if debug mode is enabled either via settings or directly from environment variable
        debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (
            os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG"
        )

        # Define the API endpoint with the correct prefix
        endpoint = get_api_endpoint(f"agent/{agent_name}/run")

        # Only show endpoint in debug mode
        if debug_mode:
            typer.echo(f"Using endpoint: {endpoint}")

        # Prepare the payload according to the API's expected format
        payload = {
            "message_content": input_message,
            "user_id": user_id,
            "context": {"debug": debug_mode},
            "session_origin": "cli",
        }

        # Add multimodal content if provided
        if multimodal_content:
            payload["multimodal_content"] = multimodal_content

            if debug_mode:
                typer.echo(f"Adding multimodal content: {json.dumps(multimodal_content, indent=2)}")

        # Add session_name if provided
        if session_name:
            payload["session_name"] = session_name
            
            # Check if this is an existing session, so we can preserve its system_prompt
            try:
                # Make a call to get the session info first if it's an existing session
                session_endpoint = get_api_endpoint(f"sessions/{session_name}")
                requests.get(
                    session_endpoint, 
                    headers={"x-api-key": settings.AUTOMAGIK_API_KEY} if settings.AUTOMAGIK_API_KEY else {},
                    timeout=10
                )
               
            except Exception as e:
                if debug_mode:
                    typer.echo(f"Error checking session: {str(e)}")

        if debug_mode:
            typer.echo(f"Request payload: {json.dumps(payload, indent=2)}")

        # Prepare headers with API key
        headers = {"Content-Type": "application/json"}

        # Add API key to headers if available
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY

            if debug_mode:
                masked_key = (
                    f"{settings.AUTOMAGIK_API_KEY[:4]}...{settings.AUTOMAGIK_API_KEY[-4:]}"
                    if len(settings.AUTOMAGIK_API_KEY) > 8
                    else "****"
                )
                typer.echo(f"Using API key: {masked_key}")

        # Make the API request
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)

        # Check response status
        if response.status_code == 200:
            result = response.json()
            if debug_mode:
                typer.echo(f"API Response: {json.dumps(result, indent=2)}")
                if "session_id" in result:
                    typer.echo(f"Session ID from response: {result['session_id']}")
            return result
        else:
            error_msg = f"API Error: Status {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"API Error: {error_data['detail']}"

                    # Detect specific errors related to session name uniqueness
                    if (
                        "duplicate key value violates unique constraint"
                        in error_data.get("detail", "")
                        and "sessions_name_key" in error_data.get("detail", "")
                    ):
                        error_msg = f"Session name '{session_name}' is already in use. Please use a different session name."
            except Exception:
                error_msg = f"API Error: {response.text}"

            typer.echo(f"{error_msg}", err=True)
            return {"error": error_msg}

    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        typer.echo(f"{error_msg}", err=True)
        return {"error": error_msg}


def display_message(
    message: str, role: str, tool_calls: List = None, tool_outputs: List = None
) -> None:
    """Display a message in plain text format."""
    # Format tool usage in a simple way if present
    if role == "assistant" and tool_calls:
        tool_usage = []

        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.get("tool_name", "Unknown Tool")
            tool_args = tool_call.get("args", {})

            # Format tool arguments
            args_str = ""
            if tool_args:
                if isinstance(tool_args, dict) and len(tool_args) > 0:
                    args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
                else:
                    args_str = str(tool_args)

            # Simple tool call display
            tool_call_str = f"{tool_name}({args_str})"

            # Find and display matching output if available
            if tool_outputs:
                matching_output = next(
                    (
                        output
                        for output in tool_outputs
                        if output.get("tool_call_id") == tool_call.get("tool_call_id")
                    ),
                    None,
                )
                if matching_output:
                    output_content = matching_output.get("content", "")
                    # Combine tool call and result
                    tool_call_str = f"{tool_call_str} → {output_content}"

            tool_usage.append(tool_call_str)

        if tool_usage:
            typer.echo("\n".join([f"[Tool] {tool}" for tool in tool_usage]))

    # Print the message with role prefix
    if message.strip():
        typer.echo(f"{role}: {message}")


async def process_single_message(
    agent_name: str, message: str, session_name: str = None, user_id: int = 1,
    multimodal_content: Dict[str, str] = None
) -> None:
    """Run a single message through an agent and display the response.
    
    Args:
        agent_name: Name of the agent to use
        message: Message to send to the agent
        session_name: Optional session name for continuity
        user_id: User ID to associate with this run
        multimodal_content: Optional multimodal content dictionary
    """
    # Check if debug mode is enabled
    debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (
        os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG"
    )

    if debug_mode:
        typer.echo(f"Processing message: {message}")
        if multimodal_content:
            typer.echo(f"With multimodal content: {json.dumps(multimodal_content, indent=2)}")

    # Extract model override if provided
    model_override = None
    if multimodal_content and "model_override" in multimodal_content:
        model_override = multimodal_content["model_override"]
        # Remove the model_override from multimodal_content as it's not actual content
        del multimodal_content["model_override"]
        if debug_mode:
            typer.echo(f"Using model override: {model_override}")
    
    # Use API to run the agent
    try:
        if debug_mode:
            typer.echo(f"Using API at {settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}")
        
        response = await run_agent(
            agent_name, message, session_name, user_id,
            multimodal_content=multimodal_content
        )
        
        # Check if the response is valid
        if response and "message" in response:
            # Display the message with proper formatting
            display_message(
                message=response["message"],
                role="assistant",
                tool_calls=response.get("tool_calls", []),
                tool_outputs=response.get("tool_outputs", [])
            )
        else:
            typer.echo("Error: Invalid response from API", err=True)
            if debug_mode and response:
                typer.echo(f"API response: {json.dumps(response, indent=2)}", err=True)
            
    except Exception as e:
        typer.echo(f"Error running agent through API: {str(e)}", err=True)
        if debug_mode:
            import traceback
            typer.echo(traceback.format_exc(), err=True)


@run_app.command()
@trace_cli_command(command_name="agent_run_message")
def message(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to use"),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Session name to use/create"
    ),
    user: int = typer.Option(1, "--user", "-u", help="User ID to use"),
    message: Optional[str] = typer.Option(
        None,
        "--message",
        "-m",
        help="Message to send (if not provided, will read from stdin)",
    ),
    image_url: Optional[str] = typer.Option(None, "--image-url", help="URL to an image for multimodal processing"),
    audio_url: Optional[str] = typer.Option(None, "--audio-url", help="URL to an audio file for multimodal processing"),
    document_url: Optional[str] = typer.Option(None, "--document-url", help="URL to a document for multimodal processing"),
    model: Optional[str] = typer.Option(None, "--model", help="Model to use (overrides agent's default)"),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode", is_flag=True, hidden=True
    ),
):
    """
    Run a single message through an agent and get the response.

    This command sends a message to an agent and displays the response.
    It can include multimodal content like images, audio, and documents.

    Example:
      automagik-agents agent run message --agent simple --message "Hello, how are you?"
      automagik-agents agent run message --agent simple --message "Describe this image" --image-url "https://example.com/image.jpg"
      automagik-agents agent run message --agent simple --message "What does this audio say?" --audio-url "https://example.com/audio.mp3"
      automagik-agents agent run message --agent simple --message "Summarize this document" --document-url "https://example.com/document.pdf"
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
        typer.echo(f"Debug mode enabled. Using endpoint: {settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}")

    # If message is not provided, read from stdin
    if not message:
        typer.echo("Enter your message (Ctrl+D to submit):", err=True)
        message = ""
        for line in sys.stdin:
            message += line
        message = message.strip()
        if not message:
            typer.echo("Error: Message cannot be empty", err=True)
            sys.exit(1)

    # Ensure agent name is valid
    if not agent:
        typer.echo("Error: Agent name is required", err=True)
        sys.exit(1)

    # Prepare multimodal content
    multimodal_content = {}
    if image_url:
        multimodal_content["image_url"] = image_url
    if audio_url:
        multimodal_content["audio_url"] = audio_url
    if document_url:
        multimodal_content["document_url"] = document_url

    # If model is specified, update the agent's model
    if model:
        # Setting the model requires API access, we'll include it in the request payload
        typer.echo(f"Using custom model: {model}")
        multimodal_content["model_override"] = model

    # Run the agent and display the response
    asyncio.run(
        process_single_message(
            agent, message, session_name=session, user_id=user, 
            multimodal_content=multimodal_content if multimodal_content else None
        )
    )


def list_available_agents() -> None:
    """Print a list of available agents."""
    agents = get_available_agents()

    if not agents:
        typer.echo(
            "Error: No agents available or could not connect to the API.", err=True
        )
        typer.echo("\nPossible reasons:")
        typer.echo("1. The server might not be running. Start it with:")
        typer.echo("     automagik-agents api start")
        typer.echo("2. Your API server could be running on a different host/port.")
        typer.echo(f"   Current server setting: {settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}")
        typer.echo("3. You might not have added any agents yet.")

        typer.echo("\nTry creating an agent first:")
        typer.echo(
            "  automagik-agents agent create agent --name my_agent --template simple"
        )

        typer.echo("\nOr check if you can access the API directly:")
        typer.echo(
            f"  curl http://{settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}/api/v1/agent/list -H 'x-api-key: {settings.AUTOMAGIK_API_KEY}'"
        )
        return

    typer.echo("\nAvailable Agents:")
    for i, agent in enumerate(agents, 1):
        name = agent.get("name", "Unknown")
        description = agent.get("description", "No description")
        model = agent.get("model", "openai:gpt-4.1")  # Updated default model

        typer.echo(f"{i}. {name} - {description} (Model: {model})")

    typer.echo("\nUse the agent name with the run command:")
    typer.echo(
        '  automagik-agents agent run message --agent <agent_name> --message "Your message here"'
    )
    typer.echo("\nFor multimodal content:")
    typer.echo("  automagik-agents agent run message --agent <agent_name> --message \"Describe this image\" --image-url \"https://example.com/image.jpg\"")
    typer.echo("  automagik-agents agent run message --agent <agent_name> --message \"Transcribe this audio\" --audio-url \"https://example.com/audio.mp3\"")
    typer.echo("  automagik-agents agent run message --agent <agent_name> --message \"Summarize this document\" --document-url \"https://example.com/document.pdf\"")


@run_app.command()
def list():
    """
    List all available agents that can be used for running messages.
    """
    list_available_agents()
