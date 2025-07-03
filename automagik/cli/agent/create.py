"""
Command for creating new agents from templates.
"""
import os
import shutil
from pathlib import Path
import typer
from typing import List
from automagik.config import settings

# Create the app for the create command
create_app = typer.Typer(no_args_is_help=True)

def get_available_categories() -> List[str]:
    """Get available agent categories from the agents directory."""
    try:
        agents_dir = Path("src/agents")
        if not agents_dir.exists() or not agents_dir.is_dir():
            if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                typer.echo(f"Agents directory not found: {agents_dir}")
            return []
        
        # Get all directories in the agents directory, excluding 'models' and '__pycache__'
        categories = [d.name for d in agents_dir.iterdir() 
                     if d.is_dir() and d.name not in ["models", "__pycache__"]]
        
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            typer.echo(f"Found agent categories: {categories}")
        
        return categories
    except Exception as e:
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            typer.echo(f"Error getting available categories: {str(e)}")
        return []

def get_available_templates(category: str) -> List[str]:
    """Get available templates for a specific agent category."""
    try:
        category_dir = Path(f"src/agents/{category}")
        if not category_dir.exists() or not category_dir.is_dir():
            if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
                typer.echo(f"Category directory not found: {category_dir}")
            return []
        
        # Get all directories in the category directory, excluding '__pycache__'
        templates = [d.name for d in category_dir.iterdir() 
                    if d.is_dir() and d.name != "__pycache__"]
        
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            typer.echo(f"Found templates for category '{category}': {templates}")
        
        return templates
    except Exception as e:
        if settings.AUTOMAGIK_LOG_LEVEL == "DEBUG":
            typer.echo(f"Error getting available templates for category '{category}': {str(e)}")
        return []

@create_app.callback()
def create_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Create new agents from templates.
    
    This command provides tools to create new agents from existing templates.
    Use 'list' to see available templates, or 'agent' to create a new agent.
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"

@create_app.command("agent")
def create_agent(
    name: str = typer.Option(..., "--name", "-n", help="Name of the new agent to create"),
    category: str = typer.Option("simple", "--category", "-c", help="Category folder to use (e.g., 'simple', 'graph')"),
    template: str = typer.Option("simple", "--template", "-t", help="Template folder to use as base (e.g., 'simple', 'notion')")
):
    """
    Create a new agent by cloning an existing agent template.
    
    The agent will be created in the specified category folder (e.g., simple, graph).
    The template should be the name of an existing agent within that category.
    By default, it uses the simple template in the simple category.
    """
    # Define the agents directory and category paths
    agents_dir = Path(__file__).resolve().parent.parent.parent.parent / 'src' / 'agents'
    category_dir = agents_dir / category
    
    # Ensure category exists
    available_categories = get_available_categories()
    if category not in available_categories:
        typer.echo(f"Error: Category '{category}' not found. Available categories: {', '.join(available_categories)}")
        raise typer.Exit(code=1)
    
    # Define the destination folder inside the category
    destination = category_dir / name
    
    # Check if destination already exists
    if destination.exists():
        typer.echo(f"Error: Folder {destination} already exists.")
        raise typer.Exit(code=1)

    # Get available templates in the category
    available_templates = get_available_templates(category)
    if not available_templates:
        typer.echo(f"Error: No templates found in category '{category}'.")
        raise typer.Exit(code=1)
    
    if template not in available_templates:
        typer.echo(f"Error: Template '{template}' not found in category '{category}'. Available templates: {', '.join(available_templates)}")
        raise typer.Exit(code=1)

    # Define the template folder
    template_path = category_dir / template
    if not template_path.exists() or not template_path.is_dir():
        typer.echo(f"Error: Template folder {template_path} does not exist.")
        raise typer.Exit(code=1)

    # Copy the template folder to the destination folder
    shutil.copytree(template_path, destination)

    # Get the base names for class naming (no _agent suffix needed)
    template_base = template
    
    # Compute the new agent class name and the template class name
    new_agent_class = ''.join(word.capitalize() for word in name.split('_')) + "Agent"
    template_class = ''.join(word.capitalize() for word in template_base.split('_')) + "Agent"
    create_func_name = f"create_{name}"
    template_func_name = f"create_{template_base}"

    # Recursively update file contents and filenames in the destination folder
    for root, dirs, files in os.walk(destination, topdown=False):
        for file in files:
            file_path = Path(root) / file
            # Skip binary files like __pycache__
            if '__pycache__' in str(file_path) or file.endswith('.pyc'):
                continue
                
            # Attempt to read file as text
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Replace class names and function names, but preserve config requirements
                new_content = content
                
                # Handle various import patterns
                # 1. Direct imports from the template's module
                for potential_import_path in [
                    f"from automagik.agents.{template}",
                    f"from automagik.agents.{template_base}_agent",
                    f"from automagik.agents.{category}.{template}",
                    f"from automagik.agents.{category}.{template_base}_agent",
                    f"import automagik.agents.{template}",
                    f"import automagik.agents.{template_base}_agent",
                    f"import automagik.agents.{category}.{template}",
                    f"import automagik.agents.{category}.{template_base}_agent",
                ]:
                    replacement = potential_import_path.replace(
                        template if template in potential_import_path else template_base, 
                        name
                    )
                    new_content = new_content.replace(potential_import_path, replacement)
                
                # 2. Handle any other template references in import statements
                new_content = new_content.replace(
                    f"automagik.agents.{template}.agent",
                    f"automagik.agents.{category}.{name}_agent.agent"
                )
                new_content = new_content.replace(
                    f"automagik.agents.{template_base}_agent.agent",
                    f"automagik.agents.{category}.{name}_agent.agent"
                )
                new_content = new_content.replace(
                    f"automagik.agents.{category}.{template}.agent",
                    f"automagik.agents.{category}.{name}_agent.agent"
                )
                new_content = new_content.replace(
                    f"automagik.agents.{category}.{template_base}_agent.agent",
                    f"automagik.agents.{category}.{name}_agent.agent"
                )
                
                # Handle references to simple specifically (common in many templates)
                if template != "simple" and template_base != "simple":
                    new_content = new_content.replace(
                        "automagik.agents.simple.simple",
                        f"automagik.agents.{category}.{name}_agent"
                    )
                    new_content = new_content.replace(
                        f"automagik.agents.{category}.simple",
                        f"automagik.agents.{category}.{name}_agent"
                    )
                
                # Handle direct simple imports in any category
                new_content = new_content.replace(
                    "from automagik.agents.test_agent.simple",
                    f"from automagik.agents.{category}.{name}_agent"
                )
                
                # Only replace exact class name matches (with word boundaries)
                new_content = new_content.replace(f" {template_class}", f" {new_agent_class}")
                new_content = new_content.replace(f"({template_class}", f"({new_agent_class}")
                new_content = new_content.replace(f"[{template_class}", f"[{new_agent_class}")
                new_content = new_content.replace(f":{template_class}", f":{new_agent_class}")
                new_content = new_content.replace(f"\"{template_class}", f"\"{new_agent_class}")
                new_content = new_content.replace(f"'{template_class}", f"'{new_agent_class}")
                
                # Replace function names
                new_content = new_content.replace(template_func_name, create_func_name)
                
                # Special handling for __init__.py to update docstrings
                if file == "__init__.py":
                    new_content = new_content.replace(
                        f"Create and initialize a {template_class} instance",
                        f"Create and initialize a {new_agent_class} instance"
                    )
                
                if new_content != content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
            except Exception as e:
                typer.echo(f"Warning: Could not process file {file_path}: {str(e)}")
                continue

            # Rename file if it contains the template name
            if template_base in file:
                new_file = file.replace(template_base, name)
                new_file_path = Path(root) / new_file
                file_path.rename(new_file_path)

        # Rename directories if needed
        for dir_name in dirs:
            if template_base in dir_name:
                old_dir = Path(root) / dir_name
                new_dir = Path(root) / dir_name.replace(template_base, name)
                os.rename(old_dir, new_dir)

    typer.echo(f"Agent '{name}' created successfully in {destination} (based on {template} template in {category} category).")
    typer.echo(f"The new agent class is named '{new_agent_class}'.")
    typer.echo(f"The initialization function is named '{create_func_name}'.")
    typer.echo("\nYou can now:")
    typer.echo(f"1. Edit {destination}/prompts/prompt.py to customize the agent's system prompt")
    typer.echo(f"2. Edit {destination}/agent.py to customize agent behavior")
    typer.echo(f"3. Edit {destination}/__init__.py to customize initialization config")

@create_app.command()
def list_templates():
    """
    List all available agent templates in all categories.
    
    This command shows all available templates that can be used 
    to create new agents using the 'agent create' command.
    """
    categories = get_available_categories()
    
    if not categories:
        typer.echo("No agent categories found. Your installation might be incomplete.")
        return
    
    typer.echo("\nAvailable Agent Templates by Category:")
    typer.echo("======================================")
    
    for category in sorted(categories):
        templates = get_available_templates(category)
        if templates:
            typer.echo(f"\n[Category: {category}]")
            for i, template in enumerate(sorted(templates), 1):
                typer.echo(f"  {i}. {template}")
    
    typer.echo("\nTo create a new agent using a template, run:")
    typer.echo("  automagik agents agent create agent --name my_agent --category simple --template simple")
    typer.echo("\nWhere 'simple' is the category and 'simple' is the template name.")

@create_app.command()
def list_categories():
    """
    List all available agent categories.
    
    Agent categories are top-level directories that organize
    related agent templates.
    """
    categories = get_available_categories()
    
    if not categories:
        typer.echo("No agent categories found. Your installation might be incomplete.")
        return
    
    typer.echo("\nAvailable Agent Categories:")
    typer.echo("==========================")
    
    for i, category in enumerate(sorted(categories), 1):
        typer.echo(f"{i}. {category}")
    
    typer.echo("\nTo see templates in a specific category, use:")
    typer.echo("  automagik-agents agent create list-templates")

@create_app.command()
def list():
    """
    List all available agent templates and categories.
    
    This is a shortcut for the list-templates command.
    """
    list_templates() 