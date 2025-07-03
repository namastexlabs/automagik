"""MCP (Model Context Protocol) CLI commands."""

import asyncio
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

console = Console()
mcp_app = typer.Typer(help="MCP server management commands")


@mcp_app.command("import")
def import_config(
    file: Optional[str] = typer.Option(
        ".mcp.json",
        "--file", "-f",
        help="Path to the .mcp.json configuration file"
    )
):
    """Import MCP server configurations from a .mcp.json file."""
    async def _import():
        try:
            from automagik.mcp.client import get_mcp_manager
            
            console.print(f"[yellow]Importing MCP configurations from {file}...[/yellow]")
            
            # Get the MCP manager
            mcp_manager = await get_mcp_manager()
            
            # Import configurations
            results = await mcp_manager.import_from_mcp_json(file)
            
            # Display results
            table = Table(title="MCP Import Results")
            table.add_column("Server Name", style="cyan")
            table.add_column("Status", style="green")
            
            success_count = 0
            for server_name, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                style = "green" if success else "red"
                table.add_row(server_name, f"[{style}]{status}[/{style}]")
                if success:
                    success_count += 1
            
            console.print(table)
            console.print(f"\n[bold]Import completed: {success_count}/{len(results)} servers imported successfully[/bold]")
            
        except FileNotFoundError:
            console.print(f"[red]Error: File '{file}' not found[/red]")
        except Exception as e:
            console.print(f"[red]Error importing MCP configurations: {str(e)}[/red]")
    
    asyncio.run(_import())


@mcp_app.command("list")
def list_servers():
    """List all MCP servers."""
    async def _list():
        try:
            from automagik.mcp.client import get_mcp_manager
            
            # Get the MCP manager
            mcp_manager = await get_mcp_manager()
            
            servers = mcp_manager.list_servers()
            
            if not servers:
                console.print("[yellow]No MCP servers configured[/yellow]")
                return
            
            table = Table(title="MCP Servers")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Agents", style="yellow")
            
            for server in servers:
                status_style = {
                    "running": "green",
                    "stopped": "red",
                    "error": "red bold",
                    "starting": "yellow",
                    "stopping": "yellow"
                }.get(server.status.value, "white")
                
                agents = ", ".join(server.config.agent_names) if server.config.agent_names else "None"
                
                table.add_row(
                    server.name,
                    server.config.server_type.value,
                    f"[{status_style}]{server.status.value}[/{status_style}]",
                    agents
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error listing MCP servers: {str(e)}[/red]")
    
    asyncio.run(_list())


@mcp_app.command("status")
def status(
    server_name: str = typer.Argument(..., help="Name of the MCP server")
):
    """Get detailed status of an MCP server."""
    async def _status():
        try:
            from automagik.mcp.client import get_mcp_manager
            
            # Get the MCP manager
            mcp_manager = await get_mcp_manager()
            
            status = await mcp_manager.get_server_status(server_name)
            
            console.print(f"\n[bold]MCP Server: {server_name}[/bold]")
            console.print(f"Status: {status.status.value}")
            console.print(f"Type: {status.config.server_type.value}")
            
            if status.started_at:
                console.print(f"Started: {status.started_at}")
            if status.last_ping:
                console.print(f"Last Ping: {status.last_ping}")
            if status.last_error:
                console.print(f"[red]Last Error: {status.last_error}[/red]")
            
            if status.tools_discovered:
                console.print(f"\n[bold]Tools ({len(status.tools_discovered)}):[/bold]")
                for tool in status.tools_discovered:
                    console.print(f"  • {tool}")
            
            if status.resources_discovered:
                console.print(f"\n[bold]Resources ({len(status.resources_discovered)}):[/bold]")
                for resource in status.resources_discovered:
                    console.print(f"  • {resource}")
                    
        except Exception as e:
            console.print(f"[red]Error getting MCP server status: {str(e)}[/red]")
    
    asyncio.run(_status())


@mcp_app.command("start")
def start(
    server_name: str = typer.Argument(..., help="Name of the MCP server to start")
):
    """Start an MCP server."""
    async def _start():
        try:
            from automagik.mcp.client import get_mcp_manager
            
            console.print(f"[yellow]Starting MCP server '{server_name}'...[/yellow]")
            
            # Get the MCP manager
            mcp_manager = await get_mcp_manager()
            
            await mcp_manager.start_server(server_name)
            
            console.print(f"[green]✅ MCP server '{server_name}' started successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]Error starting MCP server: {str(e)}[/red]")
    
    asyncio.run(_start())


@mcp_app.command("stop")
def stop(
    server_name: str = typer.Argument(..., help="Name of the MCP server to stop")
):
    """Stop an MCP server."""
    async def _stop():
        try:
            from automagik.mcp.client import get_mcp_manager
            
            console.print(f"[yellow]Stopping MCP server '{server_name}'...[/yellow]")
            
            # Get the MCP manager
            mcp_manager = await get_mcp_manager()
            
            await mcp_manager.stop_server(server_name)
            
            console.print(f"[green]✅ MCP server '{server_name}' stopped successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]Error stopping MCP server: {str(e)}[/red]")
    
    asyncio.run(_stop())


if __name__ == "__main__":
    mcp_app()