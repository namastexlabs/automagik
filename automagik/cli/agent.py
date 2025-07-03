"""
Agent management commands for Automagik Agents.
"""
import typer

# Import agent command modules
from automagik.cli.agent import create, run, chat

# Create the agent command group
agent_app = typer.Typer()

# Add the subcommands
agent_app.add_typer(create.create_app, name="create", help="Create a new agent from a template")
agent_app.add_typer(run.run_app, name="run", help="Run a single message through an agent")
agent_app.add_typer(chat.chat_app, name="chat", help="Start an interactive chat session with an agent") 