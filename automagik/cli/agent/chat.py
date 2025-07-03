"""
Command for interactive chat with an agent.

This command provides an interactive chat interface to converse with an agent.
It maintains a conversation history and supports chat commands.
"""
import json
import typer
from typing import Dict, List, Optional, Any
import requests
from rich.console import Console
import uuid
import os

from automagik.config import settings

# Create app for the chat command
chat_app = typer.Typer(no_args_is_help=True)

# Create a rich console for output
console = Console()

@chat_app.callback()
def chat_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Start an interactive chat session with an agent.
    
    Use 'start' command with --agent option to begin chatting:
      automagik-agents agent chat start --agent <agent_name>
    
    Or list available agents first:
      automagik-agents agent chat list
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
    try:
        # Define the API endpoint for listing agents
        endpoint = get_api_endpoint("agent/list")
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            console.print(f"Getting agents from: {endpoint}")
        
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
                if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                    console.print(f"Successfully retrieved {len(agents)} agents")
                
                # Convert the API response to a format compatible with the rest of the code
                for agent in agents:
                    # Ensure id field is present (use name as fallback)
                    if "id" not in agent:
                        agent["id"] = agent["name"]
                    
                    # If description is missing, provide a default
                    if "description" not in agent or not agent["description"]:
                        agent["description"] = f"Agent of type {agent.get('type', 'unknown')}"
                    
                    # If model is missing, provide a default
                    if "model" not in agent or not agent["model"]:
                        agent["model"] = "unknown"
                
                return agents
            else:
                console.print(f"Error getting agents: HTTP {response.status_code}", style="bold red")
                if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                    console.print(f"Response: {response.text}", style="red")
                return []
        except requests.exceptions.ConnectionError:
            console.print(f"Connection error: Could not connect to API server at {endpoint}", style="bold red")
            return []
    except Exception as e:
        console.print(f"Error getting agents from API: {str(e)}", style="bold red")
        return []

def list_available_agents() -> None:
    """Print a list of available agents."""
    agents = get_available_agents()
    
    if not agents:
        console.print("No agents available or could not connect to the API.", style="bold red")
        console.print("\n[yellow]Possible reasons:[/]")
        console.print("1. The server might not be running. Start it with:")
        console.print("   [cyan]automagik-agents api start[/]")
        console.print("2. Your API server could be running on a different host/port.")
        console.print(f"   Current server setting: [cyan]{settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}[/]")
        console.print("3. You might not have added any agents yet.")
        
        console.print("\n[green]Try creating an agent first:[/]")
        console.print("  automagik-agents agent create agent --name my_agent --template simple")
        
        console.print("\n[green]Or check if you can access the API directly:[/]")
        console.print(f"  curl http://{settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}/api/v1/agent/list -H 'x-api-key: {settings.AUTOMAGIK_API_KEY}'")
        return
    
    console.print("\nAvailable Agents:", style="bold green")
    for i, agent in enumerate(agents, 1):
        name = agent.get("name", "Unknown")
        description = agent.get("description", "No description")
        model = agent.get("model", "Unknown model")
        
        console.print(f"{i}. [bold cyan]{name}[/] - {description} [dim](Model: {model})[/]")
    
    console.print("\nUse the agent name to start a chat session:", style="green")
    console.print("  automagik-agents agent chat start --agent <agent_name>", style="bright_black")

async def get_user_by_id(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get user data from the API by ID."""
    try:
        # Define the API endpoint
        endpoint = get_api_endpoint(f"users/{user_id}")
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            console.print(f"Getting user data from: {endpoint}")
        
        # Prepare headers with API key if available
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
        
        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            user_data = response.json()
            if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                console.print(f"Successfully retrieved user {user_id} from API")
            return user_data
        else:
            if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                console.print(f"Error getting user by ID {user_id}: HTTP {response.status_code}", style="red")
                console.print("Using fallback user data", style="yellow")
            # Return fallback data with UUID-like user_id if needed
            return {"id": user_id, "email": "user@example.com", "name": "User"}
    except Exception as e:
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            console.print(f"Error getting user from API: {str(e)}", style="red")
            console.print("Using fallback user data", style="yellow")
        # Return fallback data with UUID-like user_id if needed
        return {"id": user_id, "email": "user@example.com", "name": "User"}

async def run_agent(agent_name: str, input_message: str, session_name: str = None, user_id: Optional[str] = None) -> dict:
    """Run the agent with the given message using the API."""
    try:
        # Check if debug mode is enabled either via settings or directly from environment variable
        debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG")
        
        # Define the API endpoint with the correct prefix
        endpoint = get_api_endpoint(f"agent/{agent_name}/run")
        
        # Only show endpoint in debug mode
        if debug_mode:
            console.print(f"Using endpoint: {endpoint}")
        
        # Prepare the payload according to the API's expected format
        payload = {
            "message_content": input_message,
            "context": {"debug": debug_mode},
            "session_origin": "cli"  # Always include session_origin for consistency
        }
        
        # Add user_id to payload only if provided
        if user_id is not None:
            payload["user_id"] = user_id
        
        # Add session_name if provided
        if session_name:
            payload["session_name"] = session_name
            # Include debugging info
            if debug_mode:
                console.print(f"Using session name: {session_name}")
        
        if debug_mode:
            console.print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        # Prepare headers with API key
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key to headers if available
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
            
            if debug_mode:
                masked_key = f"{settings.AUTOMAGIK_API_KEY[:4]}...{settings.AUTOMAGIK_API_KEY[-4:]}" if len(settings.AUTOMAGIK_API_KEY) > 8 else "****"
                console.print(f"Using API key: {masked_key}")
        
        # Make the API request
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            if debug_mode:
                console.print(f"API Response: {json.dumps(result, indent=2)}")
                if "session_id" in result:
                    console.print(f"Session ID from response: {result['session_id']}")
            return result
        else:
            error_msg = f"API Error: Status {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"API Error: {error_data['detail']}"
                    
                    # Detect specific errors related to session name uniqueness
                    if "duplicate key value violates unique constraint" in error_data.get("detail", "") and "sessions_name_key" in error_data.get("detail", ""):
                        error_msg = f"Session name '{session_name}' is already in use but with a different agent. Please use a different session name."
                    
                    # Detect session agent mismatch errors
                    elif "already associated with a different agent" in error_data.get("detail", ""):
                        if debug_mode:
                            console.print("Session agent mismatch error. Will retry with agent ID from the existing session.", style="yellow")
                        # For CLI usage, we want to recover and use the session anyway
                        # Retry without specifying an agent_id to let the server use the existing one
                        retry_payload = payload.copy()
                        # Remove any agent_id if present in context
                        if "agent_id" in retry_payload:
                            del retry_payload["agent_id"]
                        if debug_mode:
                            console.print(f"Retrying with payload: {json.dumps(retry_payload, indent=2)}")
                        
                        # Make the retry request
                        retry_response = requests.post(endpoint, json=retry_payload, headers=headers, timeout=30)
                        if retry_response.status_code == 200:
                            retry_result = retry_response.json()
                            if debug_mode:
                                console.print("Retry successful!", style="green")
                            return retry_result
                        else:
                            error_msg = f"API Error on retry: {retry_response.status_code}"
                            if debug_mode:
                                console.print(f"Retry failed: {retry_response.text}", style="red")
            except Exception:
                error_msg = f"API Error: {response.text}"
            
            console.print(f"{error_msg}", style="bold red")
            return {"error": error_msg}
                
    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        console.print(f"{error_msg}", style="bold red")
        return {"error": error_msg}

def display_message(message: str, role: str, tool_calls: List = None, tool_outputs: List = None) -> None:
    """Display a message with proper formatting and panels similar to run_chat.py."""
    # Get terminal width to adjust message formatting
    term_width = console.width
    message_width = min(term_width - 20, 80)  # Keep messages reasonably sized
    
    if role == "user":
        # Skip displaying user messages - they're already shown in the chat loop
        pass
    
    elif role == "assistant":
        # Format tool usage in a compact, readable way
        if tool_calls:
            tool_panel_content = []
            
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get('tool_name', 'Unknown Tool')
                tool_args = tool_call.get('args', {})
                
                # Format tool arguments nicely
                args_str = ""
                if tool_args:
                    if isinstance(tool_args, dict) and len(tool_args) > 0:
                        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
                    else:
                        args_str = str(tool_args)
                
                # Simplified tool call display
                if args_str:
                    tool_call_str = f"🔍 {tool_name}({args_str})"
                else:
                    tool_call_str = f"🔍 {tool_name}()"
                
                # Find and display matching output if available
                if tool_outputs:
                    matching_output = next(
                        (output for output in tool_outputs if output.get("tool_call_id") == tool_call.get("tool_call_id")),
                        None
                    )
                    if matching_output:
                        output_content = matching_output.get('content', '')
                        # Combine tool call and result in a single entry
                        tool_call_str = f"{tool_call_str} → {output_content}"
                
                tool_panel_content.append(tool_call_str)
            
            # Make tool panel very compact and subtle
            if tool_panel_content:
                from rich.panel import Panel
                from rich import box
                console.print(Panel(
                    "\n".join(tool_panel_content),
                    border_style="dim blue",
                    padding=(0, 1),
                    expand=False,
                    width=message_width
                ), justify="right")
        
        # Render the message in a panel
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            message,
            box=box.ROUNDED,
            border_style="blue",
            padding=(0, 1),
            expand=False,
            width=message_width
        ), justify="right")
    
    elif role == "system":
        # Make system messages subtle and compact
        from rich.panel import Panel
        console.print(Panel(
            message,
            border_style="dim red",
            padding=(0, 1),
            expand=False
        ))
    else:
        # Fallback for any other role
        console.print(f"[{role}] {message}")

def print_help() -> None:
    """Print help information for chat commands."""
    console.print("\n[bold]Available commands:[/]")
    console.print("[cyan]/help[/] - Show this help message")
    console.print("[cyan]/exit[/] or [cyan]/quit[/] - Exit the chat")
    console.print("[cyan]/new[/] - Start a new session (clears history)")
    console.print("[cyan]/history[/] - Show message history for the current session")
    console.print("[cyan]/clear[/] - Clear the screen")
    console.print("[cyan]/debug[/] - Toggle debug mode")
    console.print("[cyan]/session [name][/] - Set or show the current session name")
    console.print("")

async def chat_loop(agent_name: str, session_name: str = None, user_id: Optional[str] = None) -> None:
    """Run an interactive chat loop with the specified agent."""
    # Check if debug mode is enabled either via settings or directly from environment variable
    debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG")
    
    current_session_name = session_name
    current_session_id = None
    
    # Get user info if user_id is provided
    if user_id is not None:
        await get_user_by_id(user_id)
    
    # First check if the agent exists
    agents = get_available_agents()
    agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
    
    if not agent:
        console.print(f"Error: Agent '{agent_name}' not found", style="bold red")
        console.print("Available agents:", style="yellow")
        list_available_agents()
        return
    
    # If session_name wasn't provided, generate a random one
    if not current_session_name:
        current_session_name = f"cli-{uuid.uuid4().hex[:8]}"
    
    # Display welcome message in a box
    from rich.panel import Panel
    from rich import box
    
    console.print(Panel(
        f"Welcome to the {agent_name} Agent Chat",
        box=box.HEAVY,
        border_style="green",
        expand=False
    ), justify="center")
    
    console.print(f"Starting chat with [bold cyan]{agent_name}[/]")
    console.print(f"Session: [dim]{current_session_name}[/]")
    console.print("[dim]Type your messages and press Enter to send. Type /help for available commands.[/]")
    console.print("")
    
    # Add an initial greeting from the agent
    try:
        # Process a greeting message
        response = await run_agent(agent_name, "Hello", current_session_name, user_id)
        
        # Get the message content
        message_content = ""
        if "message" in response:
            message_content = response.get("message", "")
        elif "history" in response and "messages" in response["history"]:
            # Find the last assistant message
            messages = response["history"]["messages"]
            assistant_msgs = [msg for msg in messages if msg.get("role") == "assistant"]
            if assistant_msgs:
                message_content = assistant_msgs[-1].get("content", "")
        
        # Only display if we got a message
        if message_content:
            # Display assistant greeting
            display_message(message_content, "assistant")
            console.print("")
    except Exception as e:
        if debug_mode:
            console.print(f"[dim]Error displaying initial greeting: {str(e)}[/dim]")
    
    # Chat loop
    while True:
        try:
            # Get user input with a prompt style matching run_chat.py
            console.print("> ", end="")
            user_message = input().strip()
            
            # Check for commands
            if user_message.startswith("/"):
                command = user_message.lower()
                
                # Exit commands
                if command in ["/exit", "/quit"]:
                    console.print("[italic]Exiting chat session.[/]")
                    break
                
                # Help command
                elif command == "/help":
                    print_help()
                    continue
                
                # New session command
                elif command == "/new":
                    # Generate a new session name
                    current_session_name = f"cli-{uuid.uuid4().hex[:8]}"
                    current_session_id = None
                    console.print(f"[italic]Starting new session: {current_session_name}[/]")
                    continue
                
                # History command - to be implemented
                elif command == "/history":
                    console.print("[italic yellow]History view not implemented yet.[/]")
                    continue
                
                # Clear screen command
                elif command == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                # Debug toggle command
                elif command == "/debug":
                    debug_mode = not debug_mode
                    console.print(f"[italic]Debug mode: {'enabled' if debug_mode else 'disabled'}[/]")
                    continue
                
                # Session command
                elif command.startswith("/session"):
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1 and parts[1].strip():
                        # Set new session name
                        current_session_name = parts[1].strip()
                        current_session_id = None
                        console.print(f"[italic]Using session: {current_session_name}[/]")
                    else:
                        # Show current session name
                        console.print(f"[italic]Current session: {current_session_name}[/]")
                    continue
                
                # Unknown command
                else:
                    console.print(f"[italic red]Unknown command: {command}[/]")
                    print_help()
                    continue
            
            # Don't duplicate displaying user message - our input prompt already shows it
            # Process message through the agent
            response = await run_agent(agent_name, user_message, current_session_name, user_id)
            
            # Check for errors
            if "error" in response and response["error"]:
                console.print(f"Error: {response['error']}", style="bold red")
                
                # Handle session-specific errors
                if current_session_name and "already in use" in response["error"]:
                    console.print("\n[yellow]This session name is already being used with a different agent.[/]")
                    console.print("[yellow]You can use /session <new_name> to set a different session name.[/]")
                
                # Continue with the next message
                continue
            
            # Store session ID if provided
            if "session_id" in response and response["session_id"]:
                current_session_id = response["session_id"]
                if debug_mode:
                    console.print(f"[dim]Session ID: {current_session_id}[/]")
            
            # Extract response parts
            message_content = ""
            tool_calls = []
            tool_outputs = []
            
            # Check for different response formats and adapt accordingly
            if "message" in response:
                # Direct message in response
                message_content = response.get("message", "")
                
                # Look for tool information in history
                if "history" in response and "messages" in response["history"]:
                    # Find the last assistant message in history
                    messages = response["history"]["messages"]
                    
                    for msg in reversed(messages):
                        if msg.get("role") == "assistant":
                            # If we find a more complete assistant message with tools, use that
                            tool_calls = msg.get("tool_calls", [])
                            tool_outputs = msg.get("tool_outputs", [])
                            break
            elif "history" in response and "messages" in response["history"]:
                # If no direct message, look in history
                messages = response["history"]["messages"]
                
                # Find only the assistant message we care about - skip user messages entirely
                assistant_msgs = [msg for msg in messages if msg.get("role") == "assistant"]
                if assistant_msgs:
                    # Get the last assistant message
                    last_assistant_msg = assistant_msgs[-1]
                    message_content = last_assistant_msg.get("content", "")
                    tool_calls = last_assistant_msg.get("tool_calls", [])
                    tool_outputs = last_assistant_msg.get("tool_outputs", [])
            
            # Display assistant response
            display_message(message_content, "assistant", tool_calls, tool_outputs)
            console.print("")  # Add a blank line after each response for better readability
            
        except KeyboardInterrupt:
            console.print("\n[italic]Chat session interrupted. Exiting...[/]")
            break
        except EOFError:
            console.print("\n[italic]End of input. Exiting...[/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {str(e)}")
            console.print("[italic]Try again or type /exit to quit.[/]")

@chat_app.command()
def start(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to chat with"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use/create"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (UUID) to use"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Start an interactive chat session with an agent.
    
    This opens a conversational interface where you can talk to the agent
    and receive responses. The conversation history is preserved within
    the session.
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
        
    try:
        import asyncio
        asyncio.run(chat_loop(
            agent_name=agent,
            session_name=session,
            user_id=user
        ))
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        raise typer.Exit(code=1)

@chat_app.command()
def list():
    """
    List all available agents that can be used for chat.
    """
    list_available_agents()

def get_chats(agent_name: str = None) -> list:
    """Get all chats from the API."""
    try:
        # Check if debug mode is enabled either via settings or directly from environment variable
        debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG")
        
        # Define the API endpoint with the correct prefix
        endpoint = get_api_endpoint("chats")
        if agent_name:
            endpoint = f"{endpoint}?agent_name={agent_name}"
        
        # Only show endpoint in debug mode
        if debug_mode:
            console.print(f"Using endpoint: {endpoint}")
        
        # Prepare headers with API key
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
            
            if debug_mode:
                masked_key = f"{settings.AUTOMAGIK_API_KEY[:4]}...{settings.AUTOMAGIK_API_KEY[-4:]}" if len(settings.AUTOMAGIK_API_KEY) > 8 else "****"
                console.print(f"Using API key: {masked_key}")
        
        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            
            if debug_mode:
                console.print(f"Successfully retrieved {len(result)} chats")
            
            return result
        else:
            error_msg = f"API Error: Status {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"API Error: {error_data['detail']}"
            except Exception:
                error_msg = f"API Error: {response.text}"
            
            console.print(f"{error_msg}", style="bold red")
            if debug_mode:
                console.print(f"Response content: {response.text}")
            
            return []
    except Exception as e:
        console.print(f"Error getting chats: {str(e)}", style="bold red")
        if debug_mode:
            import traceback
            console.print(traceback.format_exc())
        return []

def get_chat(session_id: str) -> dict:
    """Get a specific chat by ID from the API."""
    try:
        # Check if debug mode is enabled either via settings or directly from environment variable
        debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG")
        
        # Define the API endpoint with the correct prefix
        endpoint = get_api_endpoint(f"chats/{session_id}")
        
        # Only show endpoint in debug mode
        if debug_mode:
            console.print(f"Using endpoint: {endpoint}")
        
        # Prepare headers with API key
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
            
            if debug_mode:
                masked_key = f"{settings.AUTOMAGIK_API_KEY[:4]}...{settings.AUTOMAGIK_API_KEY[-4:]}" if len(settings.AUTOMAGIK_API_KEY) > 8 else "****"
                console.print(f"Using API key: {masked_key}")
        
        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            
            if debug_mode:
                console.print(f"Successfully retrieved chat with ID: {session_id}")
            
            return result
        else:
            error_msg = f"API Error: Status {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"API Error: {error_data['detail']}"
            except Exception:
                error_msg = f"API Error: {response.text}"
            
            console.print(f"{error_msg}", style="bold red")
            if debug_mode:
                console.print(f"Response content: {response.text}")
            
            return {}
    except Exception as e:
        console.print(f"Error getting chat: {str(e)}", style="bold red")
        if debug_mode:
            import traceback
            console.print(traceback.format_exc())
        return {}

def delete_chat(session_id: str) -> bool:
    """Delete a specific chat by ID using the API."""
    try:
        # Check if debug mode is enabled either via settings or directly from environment variable
        debug_mode = (settings.AUTOMAGIK_LOG_LEVEL == "DEBUG") or (os.environ.get("AUTOMAGIK_LOG_LEVEL") == "DEBUG")
        
        # Define the API endpoint with the correct prefix
        endpoint = get_api_endpoint(f"chats/{session_id}")
        
        # Only show endpoint in debug mode
        if debug_mode:
            console.print(f"Using endpoint for DELETE: {endpoint}")
        
        # Prepare headers with API key
        headers = {}
        if settings.AUTOMAGIK_API_KEY:
            headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
            
            if debug_mode:
                masked_key = f"{settings.AUTOMAGIK_API_KEY[:4]}...{settings.AUTOMAGIK_API_KEY[-4:]}" if len(settings.AUTOMAGIK_API_KEY) > 8 else "****"
                console.print(f"Using API key: {masked_key}")
        
        # Make the API request
        response = requests.delete(endpoint, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            if debug_mode:
                console.print(f"Successfully deleted chat with ID: {session_id}")
            
            return True
        else:
            error_msg = f"API Error: Status {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"API Error: {error_data['detail']}"
            except Exception:
                error_msg = f"API Error: {response.text}"
            
            console.print(f"{error_msg}", style="bold red")
            if debug_mode:
                console.print(f"Response content: {response.text}")
            
            return False
    except Exception as e:
        console.print(f"Error deleting chat: {str(e)}", style="bold red")
        if debug_mode:
            import traceback
            console.print(traceback.format_exc())
        return False 