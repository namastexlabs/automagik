"""
Agent subcommands for the Automagik Agents CLI.

This package contains commands related to agent management, creation, and usage.
"""

import typer
import os
from automagik.cli.agent.create import create_app
from automagik.cli.agent.run import run_app
from automagik.cli.agent.chat import chat_app

# Create a subgroup for all agent commands
agent_app = typer.Typer(
    help="Agent management and interaction commands",
    no_args_is_help=True
)

# Add the subcommands
agent_app.add_typer(create_app, name="create", help="Create a new agent from a template")
agent_app.add_typer(run_app, name="run", help="Run a single message through an agent")
agent_app.add_typer(chat_app, name="chat", help="Start an interactive chat session with an agent")

@agent_app.callback()
def agent_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Manage and interact with Automagik Agents.
    
    This command group provides tools to create, run, and chat with agents.
    
    Common commands:
      - To create a new agent:
        automagik-agents agent create agent --name my_agent --template simple
        
      - To list available templates:
        automagik-agents agent create list
        
      - To run a single message:
        automagik-agents agent run message --agent my_agent --message "Hello"
        
      - To start a chat session:
        automagik-agents agent chat start --agent my_agent
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG" 