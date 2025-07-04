"""
CLI module for Automagik Bundle.
This module contains the CLI commands and utilities for the entire Automagik ecosystem.
"""
import typer
import os
import sys
from typing import Optional

# Handle --debug flag immediately before any other imports
debug_mode = "--debug" in sys.argv
if debug_mode:
    os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
    print("Debug mode enabled. Environment variable AUTOMAGIK_LOG_LEVEL set to DEBUG")

# Now import config after setting environment variables
from automagik.config import LogLevel, Settings, mask_connection_string
from pathlib import Path
from dotenv import load_dotenv

# Create the main CLI app for the Automagik Bundle
app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Automagik Bundle - AI agent framework and tools"
)

# Import component apps
from automagik.cli.agents import agents_app
from automagik.cli.api import api_app

# Add component subcommands
app.add_typer(agents_app, name="agents", help="Automagik Agents - AI agent framework")
app.add_typer(api_app, name="api", help="API server management")

# Placeholder for future components
@app.command("omni", hidden=True)
def omni_placeholder():
    """Omni component (coming soon)."""
    typer.echo("🌐 Omni component coming soon!")
    typer.echo("This will provide unified interface capabilities.")

@app.command("langflow", hidden=True) 
def langflow_placeholder():
    """Langflow component (coming soon)."""
    typer.echo("🔧 Langflow component coming soon!")
    typer.echo("This will provide visual workflow builder capabilities.")

# Alias management commands
@app.command("install-alias")
def install_alias():
    """Install shell alias for convenient access."""
    from automagik.cli.alias import install_shell_alias
    install_shell_alias()

@app.command("uninstall-alias")
def uninstall_alias():
    """Remove shell alias."""
    from automagik.cli.alias import uninstall_shell_alias
    uninstall_shell_alias()

# Define a callback that runs before any command
def global_callback(ctx: typer.Context, debug: bool = False):
    """Global callback for all commands to process common options."""
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
        # Print configuration info
        try:
            from automagik.config import settings
            print("🔧 Configuration loaded:")
            print(f"├── Environment: {settings.ENVIRONMENT}")
            print(f"├── Log Level: {settings.AUTOMAGIK_LOG_LEVEL}")
            print(f"├── Server: {settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}")
            print(f"├── OpenAI API Key: {settings.OPENAI_API_KEY[:5]}...{settings.OPENAI_API_KEY[-5:]}")
            print(f"├── API Key: {settings.AUTOMAGIK_API_KEY[:5]}...{settings.AUTOMAGIK_API_KEY[-5:]}")
            print(f"├── Discord Bot Token: {settings.DISCORD_BOT_TOKEN[:5]}...{settings.DISCORD_BOT_TOKEN[-5:]}")
            print(f"├── Database URL: {mask_connection_string(settings.AUTOMAGIK_DATABASE_URL)}")

            if settings.NOTION_TOKEN:
                print(f"└── Notion Token: {settings.NOTION_TOKEN[:5]}...{settings.NOTION_TOKEN[-5:]}")
            else:
                print("└── Notion Token: Not set")
        except Exception as e:
            print(f"Error displaying configuration: {str(e)}")

# Default callback for main app
@app.callback()
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode (shows detailed configuration)", is_flag=True)
):
    """
    Automagik Bundle - AI agent framework and tools.
    
    Available components:
    - agents: AI agent framework with memory, tools, and API
    - omni: Unified interface (coming soon)
    - langflow: Visual workflow builder (coming soon)
    
    Use 'automagik <component> --help' for component-specific commands.
    """
    # Call the global callback with the debug flag
    global_callback(ctx, debug) 