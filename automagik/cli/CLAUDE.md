# CLAUDE.md

This file provides CLI development context for Claude Code working in this directory.

## CLI Development Context

This directory contains the Click-based command-line interface for Automagik Agents. When working here, you're developing commands, subcommands, and CLI interactions that provide a powerful terminal interface to the platform.

## 🖥️ CLI Architecture Overview

### Core Components
- **Main CLI** (`cli.py`) - Root command group and global options
- **Command Modules** (`agent/`, individual command files) - Organized command implementations
- **Agent Commands** (`agents.py`) - Agent-specific operations
- **Database Commands** (`db.py`) - Database management operations
- **MCP Commands** (`mcp.py`) - MCP server management
- **Alias System** (`alias.py`) - Command shortcuts and aliases

### CLI Structure
```
automagik
├── agents                    # Agent management commands
│   ├── chat                 # Interactive agent chat
│   ├── run                  # Execute agent with message
│   ├── create               # Create new agent
│   └── list                 # List available agents
├── db                       # Database operations
│   ├── init                 # Initialize database
│   ├── migrate              # Run migrations
│   └── clear                # Clear database
├── mcp                      # MCP server management
│   ├── list                 # List MCP servers
│   ├── add                  # Add MCP server
│   └── remove               # Remove MCP server
└── alias                    # Alias management
    ├── add                  # Add command alias
    └── list                 # List aliases
```

## 🛠️ CLI Development Patterns

### Click Command Pattern
```python
# agents.py - Agent management commands
import click
from typing import Optional, Dict, Any
import asyncio
import src.utils.logging as log
from src.agents.models.agent_factory import create_agent
from src.db import list_agents, get_agent_by_name

@click.group()
def agents():
    """Agent management commands."""
    pass

@agents.command()
@click.option(
    "--agent", "-a",
    required=True,
    help="Agent name to interact with"
)
@click.option(
    "--message", "-m",
    help="Message to send to agent (if not provided, starts interactive mode)"
)
@click.option(
    "--session", "-s",
    default="cli_session",
    help="Session name for conversation context"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def run(agent: str, message: Optional[str], session: str, verbose: bool):
    """Run agent with a message."""
    
    if verbose:
        log.set_level("DEBUG")
    
    async def _run_agent():
        try:
            # Get agent configuration
            agent_config = get_agent_by_name(agent)
            if not agent_config:
                click.echo(f"❌ Agent '{agent}' not found", err=True)
                return
            
            # Create agent instance
            agent_instance = create_agent(agent, agent_config.config)
            
            if message:
                # Single message execution
                click.echo(f"🤖 Running {agent} with message...")
                response = await agent_instance.process_message(message, {
                    "session_id": session,
                    "user_id": "cli_user"
                })
                click.echo(f"\n💬 Response:\n{response}")
            else:
                # Interactive mode
                click.echo(f"🤖 Starting interactive session with {agent}")
                click.echo("Type 'quit' to exit\n")
                
                while True:
                    user_input = click.prompt("You")
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    response = await agent_instance.process_message(user_input, {
                        "session_id": session,
                        "user_id": "cli_user"
                    })
                    click.echo(f"Agent: {response}\n")
        
        except Exception as e:
            click.echo(f"❌ Error: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
    
    asyncio.run(_run_agent())

@agents.command()
@click.option(
    "--limit", "-l",
    default=10,
    help="Maximum number of agents to display"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format"
)
def list(limit: int, format: str):
    """List available agents."""
    
    try:
        agents_list, total = list_agents(limit=limit)
        
        if format == "table":
            _display_agents_table(agents_list, total)
        elif format == "json":
            _display_agents_json(agents_list)
        elif format == "yaml":
            _display_agents_yaml(agents_list)
            
    except Exception as e:
        click.echo(f"❌ Error listing agents: {e}", err=True)

def _display_agents_table(agents_list, total):
    """Display agents in table format."""
    
    click.echo(f"\n📋 Available Agents ({len(agents_list)}/{total})")
    click.echo("=" * 60)
    
    for agent in agents_list:
        status = "🟢 Active" if agent.enabled else "🔴 Inactive"
        click.echo(f"🤖 {agent.name:<20} {status}")
        if agent.description:
            click.echo(f"   📝 {agent.description}")
        click.echo(f"   🏷️  Type: {agent.type}")
        click.echo()

@agents.command()
@click.option(
    "--name", "-n",
    required=True,
    help="Name for the new agent"
)
@click.option(
    "--type", "-t",
    type=click.Choice(["simple", "discord", "sofia", "stan"]),
    default="simple",
    help="Agent type to create"
)
@click.option(
    "--description", "-d",
    help="Description of the agent"
)
def create(name: str, type: str, description: Optional[str]):
    """Create a new agent from template."""
    
    try:
        click.echo(f"🛠️  Creating agent '{name}' of type '{type}'...")
        
        # Create agent directory structure
        from src.agents.common.agent_creator import create_agent_template
        
        agent_path = create_agent_template(
            name=name,
            agent_type=type,
            description=description
        )
        
        click.echo(f"✅ Agent created successfully at: {agent_path}")
        click.echo(f"📝 Edit the agent prompt in: {agent_path}/prompts/prompt.py")
        click.echo(f"🧪 Test with: automagik agents run -a {name}")
        
    except Exception as e:
        click.echo(f"❌ Error creating agent: {e}", err=True)
```

### Interactive Command Pattern
```python
# agent/chat.py - Interactive chat command
import click
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
import src.utils.logging as log

console = Console()

@click.command()
@click.option(
    "--agent", "-a",
    required=True,
    help="Agent name to chat with"
)
@click.option(
    "--session", "-s", 
    help="Session name (auto-generated if not provided)"
)
@click.option(
    "--history", "-h",
    is_flag=True,
    help="Load previous conversation history"
)
def chat(agent: str, session: Optional[str], history: bool):
    """Start interactive chat with an agent."""
    
    session_name = session or f"chat_{agent}_{int(time.time())}"
    
    async def _chat_session():
        try:
            # Initialize agent
            console.print(Panel(
                f"🤖 Initializing chat with [bold blue]{agent}[/bold blue]",
                title="Automagik Agents",
                border_style="blue"
            ))
            
            agent_instance = await _load_agent(agent)
            
            # Load conversation history if requested
            if history:
                await _load_chat_history(session_name)
            
            console.print(f"💬 Session: [italic]{session_name}[/italic]")
            console.print("Type [bold red]quit[/bold red] to exit, [bold yellow]help[/bold yellow] for commands\n")
            
            while True:
                # Get user input with rich prompt
                try:
                    user_input = Prompt.ask("[bold green]You[/bold green]")
                except KeyboardInterrupt:
                    console.print("\n👋 Goodbye!")
                    break
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    _show_chat_help()
                    continue
                elif user_input.lower() == 'clear':
                    console.clear()
                    continue
                elif user_input.lower().startswith('save'):
                    await _save_chat_session(session_name)
                    continue
                
                # Process message with agent
                with console.status("🤔 Agent thinking...", spinner="dots"):
                    response = await agent_instance.process_message(user_input, {
                        "session_id": session_name,
                        "user_id": "cli_user",
                        "cli_mode": True
                    })
                
                # Display response with rich formatting
                console.print(f"\n[bold blue]🤖 {agent}[/bold blue]:")
                if response.startswith('```') or '*' in response:
                    # Render as markdown for formatted responses
                    console.print(Markdown(response))
                else:
                    console.print(response)
                console.print()
        
        except Exception as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}", style="red")
            log.error(f"Chat session error: {e}")
    
    asyncio.run(_chat_session())

def _show_chat_help():
    """Display chat help information."""
    
    help_text = """
    [bold blue]Chat Commands:[/bold blue]
    
    • [bold]quit/exit/q[/bold] - Exit chat session
    • [bold]help[/bold] - Show this help message
    • [bold]clear[/bold] - Clear the screen
    • [bold]save[/bold] - Save current conversation
    • [bold]Ctrl+C[/bold] - Force exit
    
    [bold blue]Tips:[/bold blue]
    
    • Responses support markdown formatting
    • Session history is automatically saved
    • Use --history flag to load previous conversations
    """
    
    console.print(Panel(help_text, title="Help", border_style="yellow"))
```

### Database Command Pattern
```python
# db.py - Database management commands
import click
from src.db.connection import verify_database_health, get_database_provider
from src.db.migration_manager import apply_migrations

@click.group()
def db():
    """Database management commands."""
    pass

@db.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force initialization (drops existing tables)"
)
@click.confirmation_option(
    prompt="This will initialize the database. Continue?"
)
def init(force: bool):
    """Initialize database and apply migrations."""
    
    try:
        provider = get_database_provider()
        
        if force:
            click.echo("⚠️  Force mode: Dropping existing tables...")
            provider.drop_all_tables()
        
        click.echo("🗄️  Initializing database...")
        provider.create_tables()
        
        click.echo("🔄 Applying migrations...")
        migrations_applied = apply_migrations()
        
        click.echo(f"✅ Database initialized successfully")
        click.echo(f"📊 Applied {migrations_applied} migrations")
        
        # Verify health
        health_status = verify_database_health()
        if health_status:
            click.echo("🟢 Database health check passed")
        else:
            click.echo("🔴 Database health check failed", err=True)
            
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}", err=True)

@db.command()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed migration information"
)
def migrate(verbose: bool):
    """Apply pending database migrations."""
    
    try:
        click.echo("🔄 Checking for pending migrations...")
        
        migrations_applied = apply_migrations(verbose=verbose)
        
        if migrations_applied > 0:
            click.echo(f"✅ Applied {migrations_applied} migrations")
        else:
            click.echo("✅ No pending migrations")
            
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)

@db.command()
@click.confirmation_option(
    prompt="This will clear all data. Are you sure?"
)
def clear():
    """Clear all data from database (keeps schema)."""
    
    try:
        provider = get_database_provider()
        
        click.echo("🗑️  Clearing database data...")
        provider.clear_all_data()
        
        click.echo("✅ Database cleared successfully")
        
    except Exception as e:
        click.echo(f"❌ Database clear failed: {e}", err=True)
```

### Configuration and Options Pattern
```python
# cli.py - Main CLI with global options
import click
from pathlib import Path
import os
import src.utils.logging as log

@click.group(invoke_without_command=True)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Configuration file path"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode"
)
@click.option(
    "--env-file",
    type=click.Path(),
    default=".env",
    help="Environment file path"
)
@click.version_option(version="1.0.0", prog_name="automagik")
@click.pass_context
def cli(ctx, config, verbose, debug, env_file):
    """Automagik Agents CLI - AI agent platform management."""
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Configure logging
    if debug:
        log.set_level("DEBUG")
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
    elif verbose:
        log.set_level("INFO")
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "INFO"
    
    # Load environment file
    if Path(env_file).exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        if debug:
            click.echo(f"📄 Loaded environment from: {env_file}")
    
    # Store configuration in context
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    
    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Register command groups
from .agents import agents
from .db import db
from .mcp import mcp
from .alias import alias

cli.add_command(agents)
cli.add_command(db)
cli.add_command(mcp)
cli.add_command(alias)
```

## 🎨 CLI Output and Formatting Patterns

### Rich Console Integration
```python
# utils/cli_display.py - Rich formatting utilities
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from typing import List, Dict, Any

console = Console()

def display_agents_table(agents: List[Dict[str, Any]]):
    """Display agents in a formatted table."""
    
    table = Table(title="🤖 Available Agents")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Status", justify="center")
    table.add_column("Description", style="green")
    
    for agent in agents:
        status = "🟢 Active" if agent.get("enabled", True) else "🔴 Inactive"
        table.add_row(
            agent["name"],
            agent["type"],
            status,
            agent.get("description", "No description")
        )
    
    console.print(table)

def display_progress_bar(total: int, description: str = "Processing"):
    """Create a progress bar context manager."""
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    )

def display_code_block(code: str, language: str = "python"):
    """Display syntax-highlighted code."""
    
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)

def display_error_panel(error: str, title: str = "Error"):
    """Display error in a formatted panel."""
    
    console.print(Panel(
        error,
        title=f"❌ {title}",
        border_style="red",
        expand=False
    ))

def display_success_panel(message: str, title: str = "Success"):
    """Display success message in a formatted panel."""
    
    console.print(Panel(
        message,
        title=f"✅ {title}",
        border_style="green",
        expand=False
    ))
```

### Progress and Status Indicators
```python
# utils/cli_progress.py - Progress tracking utilities
import click
from rich.progress import track
from typing import Iterator, Any
import time

def with_progress_bar(items: Iterator[Any], description: str = "Processing"):
    """Wrapper for operations with progress tracking."""
    
    return track(items, description=description, console=console)

def show_spinner(func, message: str = "Working..."):
    """Decorator to show spinner during long operations."""
    
    def wrapper(*args, **kwargs):
        with console.status(message, spinner="dots"):
            return func(*args, **kwargs)
    
    return wrapper

class ProgressReporter:
    """Progress reporting for long-running operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.description = description
        self.current = 0
        self.progress = None
    
    def __enter__(self):
        self.progress = Progress(console=console)
        self.task = self.progress.add_task(self.description, total=self.total)
        self.progress.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
    
    def update(self, increment: int = 1):
        """Update progress by increment."""
        self.current += increment
        self.progress.update(self.task, advance=increment)
    
    def set_description(self, description: str):
        """Update the progress description."""
        self.progress.update(self.task, description=description)
```

## 🔧 CLI Utility Patterns

### Configuration Management
```python
# utils/cli_config.py - CLI configuration utilities
import click
from pathlib import Path
import json
import yaml
from typing import Dict, Any, Optional

class CLIConfig:
    """CLI configuration management."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "~/.automagik/config.yaml").expanduser()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f)
        except Exception as e:
            click.echo(f"Warning: Failed to load config: {e}", err=True)
            return {}
    
    def save_config(self):
        """Save configuration to file."""
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            if self.config_path.suffix.lower() in ['.yml', '.yaml']:
                yaml.safe_dump(self.config, f, default_flow_style=False)
            else:
                json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
```

### Command Validation and Helpers
```python
# utils/cli_validators.py - CLI validation utilities
import click
from typing import Any

def validate_agent_name(ctx, param, value):
    """Validate agent name format."""
    
    if not value:
        return value
    
    if not value.replace('_', '').replace('-', '').isalnum():
        raise click.BadParameter(
            "Agent name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    return value.lower()

def validate_session_name(ctx, param, value):
    """Validate session name format."""
    
    if not value:
        return value
    
    if len(value) > 100:
        raise click.BadParameter("Session name must be 100 characters or less")
    
    return value

class AgentChoice(click.Choice):
    """Dynamic choice validation for available agents."""
    
    def __init__(self):
        # Load available agents dynamically
        from src.db import list_agents
        agents_list, _ = list_agents()
        choices = [agent.name for agent in agents_list]
        super().__init__(choices, case_sensitive=False)
    
    def convert(self, value, param, ctx):
        """Convert and validate agent choice."""
        
        if value not in self.choices:
            # Refresh choices in case new agents were added
            self.__init__()
        
        return super().convert(value, param, ctx)
```

## 🧪 CLI Testing Patterns

### Click Testing
```python
# test_cli.py - CLI testing patterns
import pytest
from click.testing import CliRunner
from src.cli.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_cli_help(runner):
    """Test CLI help output."""
    
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "Automagik Agents CLI" in result.output

def test_agents_list(runner):
    """Test agents list command."""
    
    result = runner.invoke(cli, ['agents', 'list'])
    assert result.exit_code == 0
    assert "Available Agents" in result.output

def test_agent_create(runner):
    """Test agent creation command."""
    
    result = runner.invoke(cli, [
        'agents', 'create',
        '--name', 'test-agent',
        '--type', 'simple',
        '--description', 'Test agent'
    ])
    
    assert result.exit_code == 0
    assert "Agent created successfully" in result.output

def test_invalid_agent_name(runner):
    """Test invalid agent name handling."""
    
    result = runner.invoke(cli, [
        'agents', 'create',
        '--name', 'invalid@name',
        '--type', 'simple'
    ])
    
    assert result.exit_code != 0
    assert "must contain only alphanumeric" in result.output
```

## 🔍 CLI Debugging Techniques

```bash
# Enable CLI debug mode
automagik --debug agents list

# Test specific commands
automagik --verbose db init

# Check CLI configuration
automagik --help

# Test with mock data
ENVIRONMENT=test automagik agents list
```

## ⚠️ CLI Development Guidelines

### User Experience
- Provide clear, helpful error messages
- Use consistent command naming conventions
- Implement progress indicators for long operations
- Support both interactive and non-interactive modes
- Provide comprehensive help text

### Error Handling
- Use appropriate exit codes (0 for success, non-zero for errors)
- Handle keyboard interrupts gracefully
- Validate inputs before processing
- Provide suggestions for common mistakes

### Output Formatting
- Use colors and formatting judiciously
- Support multiple output formats (table, json, yaml)
- Implement --quiet and --verbose modes
- Use consistent emojis and symbols

### Configuration
- Support configuration files
- Use environment variables appropriately
- Provide sensible defaults
- Allow overrides via command line options

This context focuses specifically on CLI development patterns and should be used alongside the global development rules in the root CLAUDE.md.