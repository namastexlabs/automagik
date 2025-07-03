"""Server command for starting the API directly from pip installation."""
import os
import sys
import typer
from pathlib import Path
import uvicorn
from typing import Optional


def start_server_from_pip(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    agents_dir: Optional[str] = None
):
    """
    Start the Automagik API server from pip installation.
    
    This function is used as an entry point when installing via pip.
    It automatically detects environment variables and starts the server.
    """
    # Load environment variables if .env exists
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    # Set up default agents directory
    if agents_dir:
        os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = agents_dir
    elif "AUTOMAGIK_EXTERNAL_AGENTS_DIR" not in os.environ:
        # Default to ./automagik_agents relative to current directory
        default_agents_dir = Path.cwd() / "automagik_agents"
        default_agents_dir.mkdir(parents=True, exist_ok=True)
        os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = str(default_agents_dir)
    
    # Get host and port from environment if available
    host = os.getenv("AUTOMAGIK_API_HOST", host)
    port = int(os.getenv("AUTOMAGIK_API_PORT", str(port)))
    
    # Import and run the main app
    try:
        from automagik.main import app as fastapi_app
        
        typer.echo(f"🚀 Starting Automagik API server...")
        typer.echo(f"📍 Host: {host}")
        typer.echo(f"🔌 Port: {port}")
        typer.echo(f"📁 External agents: {os.environ.get('AUTOMAGIK_EXTERNAL_AGENTS_DIR')}")
        
        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError as e:
        typer.echo(f"❌ Failed to import FastAPI app: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"❌ Failed to start server: {e}", err=True)
        sys.exit(1)


# CLI command version
app = typer.Typer()

@app.command()
def start(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    agents_dir: Optional[str] = typer.Option(None, "--agents-dir", "-a", help="External agents directory")
):
    """Start the Automagik API server."""
    start_server_from_pip(host, port, reload, agents_dir)


if __name__ == "__main__":
    # Allow direct execution
    start_server_from_pip()