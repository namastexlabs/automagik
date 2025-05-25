"""
Automagik Agents CLI commands.
This module contains all commands related to the Automagik Agents component.
"""
import typer
import os
import subprocess
import signal
import time
import requests
from typing import Optional

# Import existing command modules
from src.cli.db import db_app
from src.cli.agent import agent_app

# Create the agents command group
agents_app = typer.Typer(
    help="Automagik Agents - AI agent framework with memory, tools, and API",
    no_args_is_help=True
)

# Add existing subcommands
agents_app.add_typer(db_app, name="db", help="Database management commands")
agents_app.add_typer(agent_app, name="agent", help="Agent management and interaction commands")

# Add direct commands from agent subcommand for convenience
@agents_app.command("create")
def create_agent_command(
    name: str = typer.Option(..., "--name", "-n", help="Name of the new agent to create"),
    template: str = typer.Option("simple_agent", "--template", "-t", help="Template folder to use as base"),
    category: str = typer.Option("simple", "--category", "-c", help="Category folder to use")
):
    """Create a new agent by cloning an existing agent template."""
    from src.cli.agent.create import create_agent
    create_agent(name=name, category=category, template=template)

@agents_app.command("run")
def run_agent_command(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to use"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use/create"),
    user: int = typer.Option(1, "--user", "-u", help="User ID to use"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to send"),
    model: Optional[str] = typer.Option(None, "--model", help="Model to use (overrides agent's default)"),
):
    """Run a single message through an agent."""
    from src.cli.agent.run import message
    message(agent=agent, session=session, user=user, message=message, model=model)

@agents_app.command("chat")
def chat_agent_command(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to chat with"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use/create"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (UUID) to use"),
):
    """Start an interactive chat session with an agent."""
    from src.cli.agent.chat import start
    start(agent=agent, session=session, user=user)

# New server management commands
def kill_process_on_port(port: int) -> bool:
    """Kill any process running on the specified port."""
    try:
        # Find process using the port (works on Linux/macOS)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            killed_any = False
            
            for pid in pids:
                try:
                    pid_int = int(pid)
                    typer.echo(f"🔪 Terminating process {pid_int} on port {port}")
                    os.kill(pid_int, signal.SIGTERM)
                    killed_any = True
                    
                    # Wait a bit, then force kill if still running
                    time.sleep(2)
                    try:
                        os.kill(pid_int, 0)  # Check if still running
                        typer.echo(f"🔪 Force killing process {pid_int}")
                        os.kill(pid_int, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated
                        
                except (ValueError, ProcessLookupError):
                    continue
                    
            return killed_any
        else:
            typer.echo(f"ℹ️  No process found on port {port}")
            return False
            
    except FileNotFoundError:
        # lsof not available, try alternative methods
        typer.echo(f"⚠️  lsof not available, cannot clean port {port}")
        return False
    except Exception as e:
        typer.echo(f"⚠️  Could not clean port {port}: {e}")
        return False

@agents_app.command("start")
def start_server(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True)
):
    """Start the Automagik Agents server (python -m src)."""
    if debug:
        os.environ["AM_LOG_LEVEL"] = "DEBUG"
        
    typer.echo("🚀 Starting Automagik Agents server...")
    
    try:
        subprocess.run(["python", "-m", "src"], check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start server: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n🛑 Server stopped by user")
        raise typer.Exit(code=0)

@agents_app.command("dev")
def dev_server(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True)
):
    """Start server in development mode with auto-reload (python -m src --reload)."""
    if debug:
        os.environ["AM_LOG_LEVEL"] = "DEBUG"
        
    # Get port from settings
    try:
        from src.config import settings
        port = settings.AM_PORT
    except Exception:
        port = 8881  # Default port
    
    typer.echo(f"🔍 Checking for existing server on port {port}...")
    
    # Check if something is running on the port
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        if response.status_code == 200:
            typer.echo(f"🛑 Found existing server on port {port}, stopping it...")
            killed = kill_process_on_port(port)
            if killed:
                typer.echo("✅ Existing server stopped")
                time.sleep(1)  # Give it a moment to fully stop
            else:
                typer.echo("⚠️  Could not stop existing server, proceeding anyway...")
    except requests.exceptions.RequestException:
        typer.echo(f"✅ Port {port} is available")
    
    typer.echo("🚀 Starting development server with auto-reload...")
    
    try:
        subprocess.run(["python", "-m", "src", "--reload"], check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start development server: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n🛑 Development server stopped by user")
        raise typer.Exit(code=0)

@agents_app.callback()
def agents_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Automagik Agents - AI agent framework with memory, tools, and API.
    
    Available commands:
    - start: Start the server (python -m src)
    - dev: Start in development mode with auto-reload
    - create: Create a new agent from template
    - run: Run a single message through an agent
    - chat: Start interactive chat with an agent
    - db: Database management commands
    - agent: Advanced agent management commands
    
    Examples:
      automagik agents start                    # Start the server
      automagik agents dev                      # Start in development mode
      automagik agents create --name my_agent   # Create a new agent
      automagik agents run --agent simple --message "Hello"  # Run agent
      automagik agents chat --agent simple     # Start chat session
    """
    if debug:
        os.environ["AM_LOG_LEVEL"] = "DEBUG" 