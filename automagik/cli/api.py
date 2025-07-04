"""
API management commands for Automagik.
Provides commands to start, stop, and manage the API server.
"""
import typer
import os
import sys
import subprocess
import signal
import time
import requests
from typing import Optional
from pathlib import Path
from rich.console import Console

console = Console()

# Create the API command group
api_app = typer.Typer(
    help="API server management commands",
    no_args_is_help=True
)


@api_app.command("start")
def start(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
    external_dir: Optional[str] = typer.Option(None, "--external-dir", "-e", help="External agents directory"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes (ignored with --reload)"),
):
    """Start the API server with automatic external agent discovery."""
    
    # Set up environment for external agents
    if external_dir:
        os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = str(Path(external_dir).resolve())
        console.print(f"📁 External agents directory: {external_dir}")
    elif "AUTOMAGIK_EXTERNAL_AGENTS_DIR" not in os.environ:
        # Try to auto-detect common locations
        possible_dirs = [
            Path.cwd() / "agents_examples",
            Path.cwd() / "external_agents",
            Path.home() / ".automagik" / "agents",
        ]
        
        for dir_path in possible_dirs:
            if dir_path.exists() and dir_path.is_dir():
                os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = str(dir_path)
                console.print(f"📁 Auto-detected external agents: {dir_path}")
                break
    
    # Set host and port in environment
    os.environ["AUTOMAGIK_API_HOST"] = host
    os.environ["AUTOMAGIK_API_PORT"] = str(port)
    
    console.print(f"🚀 Starting Automagik API server on {host}:{port}")
    
    if reload:
        console.print("🔄 Auto-reload enabled (development mode)")
    
    try:
        # Use uvicorn to run the server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "automagik.main:app",
            "--host", host,
            "--port", str(port),
        ]
        
        if reload:
            cmd.append("--reload")
        else:
            cmd.extend(["--workers", str(workers)])
        
        # Add color output if available
        # Note: Removed log-config as it's not required and was causing issues
        
        console.print("✅ API server starting...")
        console.print(f"📍 API endpoints: http://{host}:{port}/api/v1/")
        console.print(f"📚 Documentation: http://{host}:{port}/docs")
        console.print(f"🔑 Default API key: namastex888")
        console.print("\nPress CTRL+C to stop the server\n")
        
        # Run the server
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        console.print("\n👋 Shutting down API server...")
    except Exception as e:
        console.print(f"❌ Error starting API server: {e}", style="red")
        raise typer.Exit(1)


@api_app.command("stop")
def stop():
    """Stop the running API server."""
    
    console.print("🛑 Stopping API server...")
    
    try:
        # Find uvicorn processes
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*automagik.api.main"],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                os.kill(int(pid), signal.SIGTERM)
                console.print(f"✅ Stopped process {pid}")
        else:
            console.print("ℹ️  No running API server found")
            
    except Exception as e:
        console.print(f"❌ Error stopping server: {e}", style="red")
        raise typer.Exit(1)


@api_app.command("status")
def status(
    host: str = typer.Option("localhost", "--host", "-h", help="API host"),
    port: int = typer.Option(8000, "--port", "-p", help="API port"),
):
    """Check API server status."""
    
    url = f"http://{host}:{port}/health"
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            console.print("✅ API server is running", style="green")
            console.print(f"📍 URL: http://{host}:{port}")
            
            # Try to get agent list
            try:
                agent_response = requests.get(
                    f"http://{host}:{port}/api/v1/agent/list",
                    headers={"X-API-Key": "namastex888"},
                    timeout=5
                )
                
                if agent_response.status_code == 200:
                    agents = agent_response.json()
                    console.print(f"🤖 Available agents: {len(agents)}")
                    
                    # Check for external agents
                    external_agents = [a for a in agents if not a.get('internal', True)]
                    if external_agents:
                        console.print(f"📦 External agents: {len(external_agents)}")
                        
            except Exception:
                pass
                
        else:
            console.print("❌ API server returned error", style="red")
            
    except requests.ConnectionError:
        console.print("❌ API server is not running", style="red")
        console.print(f"   Unable to connect to http://{host}:{port}")
    except Exception as e:
        console.print(f"❌ Error checking status: {e}", style="red")


@api_app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
):
    """View API server logs."""
    
    log_file = Path("logs") / "automagik_api.log"
    
    if not log_file.exists():
        console.print("ℹ️  No log file found. Server may not have been started yet.")
        return
    
    try:
        if follow:
            # Use tail -f for following logs
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
        else:
            # Show last N lines
            with open(log_file, 'r') as f:
                lines_list = f.readlines()
                for line in lines_list[-lines:]:
                    console.print(line.rstrip())
                    
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"❌ Error reading logs: {e}", style="red")


@api_app.command("test")
def test(
    host: str = typer.Option("localhost", "--host", "-h", help="API host"),
    port: int = typer.Option(8000, "--port", "-p", help="API port"),
    agent: str = typer.Option("simple", "--agent", "-a", help="Agent to test"),
):
    """Test the API with a sample request."""
    
    url = f"http://{host}:{port}/api/v1/agent/{agent}/run"
    headers = {"X-API-Key": "namastex888", "Content-Type": "application/json"}
    payload = {
        "message_content": "Hello! Can you introduce yourself?",
        "session_name": "api_test",
        "message_type": "text"
    }
    
    console.print(f"🧪 Testing API with agent: {agent}")
    console.print(f"📍 URL: {url}")
    
    try:
        with console.status("Sending request..."):
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            console.print("✅ Test successful!", style="green")
            console.print(f"\n💬 Response: {result.get('message', 'No message')[:200]}...")
            
            if result.get('usage'):
                console.print(f"\n📊 Usage: {result['usage']}")
                
        else:
            console.print(f"❌ Test failed with status {response.status_code}", style="red")
            console.print(f"Response: {response.text}")
            
    except requests.ConnectionError:
        console.print("❌ Could not connect to API server", style="red")
        console.print("Make sure the server is running with: automagik api start")
    except Exception as e:
        console.print(f"❌ Test error: {e}", style="red")


# Helper function to make the API app available
def get_api_app():
    """Get the API typer app."""
    return api_app