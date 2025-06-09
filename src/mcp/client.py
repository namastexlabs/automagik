"""MCP client manager for automagik-agents framework."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from contextlib import asynccontextmanager

from pydantic_ai.tools import Tool as PydanticTool


from .models import (
    MCPServerConfig, 
    MCPServerStatus, 
    MCPServerState,
    MCPServerType,
    MCPHealthResponse
)
from .server import MCPServerManager
from .exceptions import MCPError

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Central manager for all MCP servers in the automagik-agents framework."""
    
    def __init__(self):
        """Initialize MCP client manager."""
        self._servers: Dict[str, MCPServerManager] = {}
        self._agent_servers: Dict[str, Set[str]] = {}  # agent_name -> set of server names
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60  # seconds
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the MCP client manager and load configurations from database."""
        if self._initialized:
            logger.info("MCP client manager already initialized")
            return
            
        try:
            logger.info("Initializing MCP client manager")
            
            # Create database tables if they don't exist
            await self._ensure_database_tables()
            
            # Load server configurations from database
            await self._load_server_configurations()
            
            # Import configurations from .mcp.json if no servers loaded from database
            if not self._servers:
                logger.info("No MCP servers in database, attempting to import from .mcp.json")
                await self.import_from_mcp_json()
            
            # Start auto-start servers
            await self._start_auto_start_servers()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._initialized = True
            logger.info(f"MCP client manager initialized with {len(self._servers)} servers")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP client manager: {str(e)}")
            raise MCPError(f"Initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown the MCP client manager and all servers."""
        logger.info("Shutting down MCP client manager")
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop all servers (use snapshot for thread safety)
        servers_snapshot = dict(self._servers)
        stop_tasks = []
        for server in servers_snapshot.values():
            if server.is_running:
                stop_tasks.append(server.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self._servers.clear()
        self._agent_servers.clear()
        self._initialized = False
        
        logger.info("MCP client manager shutdown complete")
    
    async def add_server(self, config: MCPServerConfig) -> None:
        """Add a new MCP server configuration.
        
        Args:
            config: MCP server configuration
            
        Raises:
            MCPError: If server already exists or configuration is invalid
        """
        if config.name in self._servers:
            raise MCPError(f"Server {config.name} already exists")
        
        try:
            # Save configuration to database
            await self._save_server_config(config)
            
            # Create server manager
            server_manager = MCPServerManager(config)
            self._servers[config.name] = server_manager
            
            # Update agent assignments
            for agent_name in config.agent_names:
                if agent_name not in self._agent_servers:
                    self._agent_servers[agent_name] = set()
                self._agent_servers[agent_name].add(config.name)
            
            # Auto-start if configured
            if config.auto_start:
                await server_manager.start()
            
            logger.info(f"Added MCP server: {config.name}")
            
        except Exception as e:
            logger.error(f"Failed to add MCP server {config.name}: {str(e)}")
            raise MCPError(f"Failed to add server: {str(e)}")
    
    async def remove_server(self, server_name: str) -> None:
        """Remove an MCP server.
        
        Args:
            server_name: Name of the server to remove
            
        Raises:
            MCPError: If server not found
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        try:
            # Stop server if running
            server = self._servers[server_name]
            if server.is_running:
                await server.stop()
            
            # Remove from database
            await self._delete_server_config(server_name)
            
            # Remove from memory
            del self._servers[server_name]
            
            # Update agent assignments
            for agent_name, server_names in self._agent_servers.items():
                server_names.discard(server_name)
            
            logger.info(f"Removed MCP server: {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to remove MCP server {server_name}: {str(e)}")
            raise MCPError(f"Failed to remove server: {str(e)}")
    
    async def start_server(self, server_name: str) -> None:
        """Start an MCP server.
        
        Args:
            server_name: Name of the server to start
            
        Raises:
            MCPError: If server not found
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        await server.start()
        logger.info(f"Started MCP server: {server_name}")
    
    async def stop_server(self, server_name: str) -> None:
        """Stop an MCP server.
        
        Args:
            server_name: Name of the server to stop
            
        Raises:
            MCPError: If server not found
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        await server.stop()
        logger.info(f"Stopped MCP server: {server_name}")
    
    async def restart_server(self, server_name: str) -> None:
        """Restart an MCP server.
        
        Args:
            server_name: Name of the server to restart
            
        Raises:
            MCPError: If server not found
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        await server.restart()
        logger.info(f"Restarted MCP server: {server_name}")
    
    def get_server(self, server_name: str) -> Optional[MCPServerManager]:
        """Get an MCP server manager by name.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server manager or None if not found
        """
        return self._servers.get(server_name)
    
    def list_servers(self) -> List[MCPServerState]:
        """List all MCP servers and their states.
        
        Returns:
            List of server states
        """
        # Create snapshot to avoid race conditions during iteration
        servers_snapshot = dict(self._servers)
        return [server.state for server in servers_snapshot.values()]
    
    def get_servers_for_agent(self, agent_name: str) -> List[MCPServerManager]:
        """Get MCP servers assigned to a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of server managers assigned to the agent
        """
        server_names = self._agent_servers.get(agent_name, set())
        return [self._servers[name] for name in server_names if name in self._servers]
    
    def get_tools_for_agent(self, agent_name: str) -> List[PydanticTool]:
        """Get all MCP tools available to a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of PydanticAI tools from MCP servers
        """
        tools = []
        servers = self.get_servers_for_agent(agent_name)
        
        for server in servers:
            if server.is_running:
                tools.extend(server.get_pydantic_tools())
        
        return tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            MCPError: If server not found or not running
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        return await server.call_tool(tool_name, arguments)
    
    async def access_resource(self, server_name: str, uri: str) -> Any:
        """Access a resource on a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            uri: URI of the resource to access
            
        Returns:
            Resource content
            
        Raises:
            MCPError: If server not found or not running
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        return await server.access_resource(uri)
    
    async def get_health(self) -> MCPHealthResponse:
        """Get health status of all MCP servers.
        
        Returns:
            Health response with aggregate statistics
        """
        servers_total = len(self._servers)
        servers_running = sum(1 for server in self._servers.values() if server.is_running)
        servers_error = sum(1 for server in self._servers.values() if server.status == MCPServerStatus.ERROR)
        
        tools_available = sum(len(server.tools) for server in self._servers.values() if server.is_running)
        resources_available = sum(len(server.resources) for server in self._servers.values() if server.is_running)
        
        status = "healthy"
        if servers_error > 0:
            status = "degraded"
        if servers_running == 0 and servers_total > 0:
            status = "unhealthy"
        
        return MCPHealthResponse(
            status=status,
            servers_total=servers_total,
            servers_running=servers_running,
            servers_error=servers_error,
            tools_available=tools_available,
            resources_available=resources_available,
            timestamp=datetime.now()
        )
    
    async def _ensure_database_tables(self) -> None:
        """Ensure MCP-related database tables exist.
        
        Note: Tables are created by database migrations, not here.
        This method is kept for compatibility but doesn't create tables.
        """
        logger.debug("MCP database tables should be created by migrations")
    
    async def _load_server_configurations(self) -> None:
        """Load MCP server configurations from database using optimized JOIN query."""
        from fastapi.concurrency import run_in_threadpool
        from src.db.repository.mcp import get_servers_with_agents_optimized
        
        try:
            # Get all MCP servers with their agent names using optimized single query (async)
            servers_with_agents = await run_in_threadpool(get_servers_with_agents_optimized, enabled_only=False)
            
            for server, agent_names in servers_with_agents:
                try:
                    # Create MCPServerConfig from MCPServerDB and agent names
                    config = MCPServerConfig(
                        name=server.name,
                        server_type=MCPServerType(server.server_type),
                        description=server.description,
                        command=server.command or [],
                        env=server.env or {},
                        http_url=server.http_url,
                        agent_names=agent_names,
                        auto_start=server.auto_start,
                        max_retries=server.max_retries,
                        timeout_seconds=server.timeout_seconds,
                        tags=server.tags or [],
                        priority=server.priority
                    )
                    
                    # Create server manager
                    server_manager = MCPServerManager(config)
                    self._servers[config.name] = server_manager
                    
                    # Update agent assignments
                    for agent_name in config.agent_names:
                        if agent_name not in self._agent_servers:
                            self._agent_servers[agent_name] = set()
                        self._agent_servers[agent_name].add(config.name)
                    
                    logger.debug(f"Loaded MCP server configuration: {config.name} with {len(agent_names)} agents")
                    
                except Exception as e:
                    logger.error(f"Failed to load MCP server configuration {server.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load server configurations: {str(e)}")
    
    async def _save_server_config(self, config: MCPServerConfig) -> None:
        """Save MCP server configuration to database."""
        from fastapi.concurrency import run_in_threadpool
        from src.db.repository.mcp import (
            get_mcp_server_by_name, create_mcp_server, update_mcp_server,
            assign_agent_to_server, remove_agent_from_server, get_server_agents
        )
        from src.db.repository.agent import get_agent_by_name
        from src.db.models import MCPServerDB
        
        try:
            # Check if server already exists (async)
            existing_server = await run_in_threadpool(get_mcp_server_by_name, config.name)
            
            # Create MCPServerDB object from config
            server_data = MCPServerDB(
                id=existing_server.id if existing_server else None,
                name=config.name,
                server_type=config.server_type.value,
                description=config.description,
                command=config.command,
                env=config.env,
                http_url=config.http_url,
                auto_start=config.auto_start,
                max_retries=config.max_retries,
                timeout_seconds=config.timeout_seconds,
                tags=config.tags,
                priority=config.priority
            )
            
            if existing_server:
                # Update existing server (async)
                success = await run_in_threadpool(update_mcp_server, server_data)
                if not success:
                    raise MCPError("Failed to update MCP server")
                server_id = existing_server.id
            else:
                # Create new server (async)
                server_id = await run_in_threadpool(create_mcp_server, server_data)
                if not server_id:
                    raise MCPError("Failed to create MCP server")
            
            # Handle agent assignments
            # Get current agent assignments (async)
            current_agent_ids = set(await run_in_threadpool(get_server_agents, server_id))
            
            # Get new agent IDs from names (async)
            new_agent_ids = set()
            for agent_name in config.agent_names:
                agent = await run_in_threadpool(get_agent_by_name, agent_name)
                if agent:
                    new_agent_ids.add(agent.id)
                else:
                    logger.warning(f"Agent '{agent_name}' not found for server '{config.name}'")
            
            # Remove agents that are no longer assigned (async)
            for agent_id in current_agent_ids - new_agent_ids:
                await run_in_threadpool(remove_agent_from_server, agent_id, server_id)
            
            # Add new agent assignments (async)
            for agent_id in new_agent_ids - current_agent_ids:
                await run_in_threadpool(assign_agent_to_server, agent_id, server_id)
                
        except Exception as e:
            logger.error(f"Failed to save server config: {str(e)}")
            raise MCPError(f"Failed to save server configuration: {str(e)}")
    
    async def _delete_server_config(self, server_name: str) -> None:
        """Delete MCP server configuration from database."""
        from fastapi.concurrency import run_in_threadpool
        from src.db.repository.mcp import get_mcp_server_by_name, delete_mcp_server
        
        try:
            # Get server by name to get its ID (async)
            server = await run_in_threadpool(get_mcp_server_by_name, server_name)
            if not server:
                logger.warning(f"Server '{server_name}' not found for deletion")
                return
            
            # Delete server (this will also delete agent assignments due to CASCADE) (async)
            success = await run_in_threadpool(delete_mcp_server, server.id)
            if not success:
                raise MCPError(f"Failed to delete server '{server_name}'")
                
        except Exception as e:
            logger.error(f"Failed to delete server config: {str(e)}")
            raise MCPError(f"Failed to delete server configuration: {str(e)}")
    
    async def _cleanup_orphaned_processes(self) -> None:
        """Clean up any orphaned MCP processes before starting new ones."""
        try:
            import subprocess
            
            # Kill any existing mcp-linear processes
            try:
                result = subprocess.run(
                    ['pkill', '-f', 'mcp-linear'], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("🧹 Cleaned up orphaned mcp-linear processes")
                elif result.returncode == 1:
                    # No processes found, which is fine
                    logger.debug("No orphaned mcp-linear processes found")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout while cleaning up mcp-linear processes")
            except Exception as e:
                logger.warning(f"Could not clean up mcp-linear processes: {e}")
            
            # Kill any existing mcp-server-postgres processes
            try:
                result = subprocess.run(
                    ['pkill', '-f', 'mcp-server-postgres'], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("🧹 Cleaned up orphaned mcp-server-postgres processes")
            except Exception as e:
                logger.debug(f"No mcp-server-postgres processes to clean up: {e}")
            
            # Give processes time to fully terminate
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error during orphaned process cleanup: {e}")
    
    async def _start_auto_start_servers(self) -> None:
        """Start servers configured for auto-start."""
        # Clean up any orphaned MCP processes before starting
        await self._cleanup_orphaned_processes()
        
        start_tasks = []
        
        # Create snapshot to avoid race conditions during iteration
        servers_snapshot = dict(self._servers)
        
        for server in servers_snapshot.values():
            if server.config.auto_start:
                start_tasks.append(self._safe_start_server(server))
        
        if start_tasks:
            logger.info(f"Starting {len(start_tasks)} auto-start MCP servers")
            await asyncio.gather(*start_tasks, return_exceptions=True)
    
    async def _safe_start_server(self, server: MCPServerManager) -> None:
        """Safely start a server with error handling."""
        try:
            await server.start()
        except Exception as e:
            logger.error(f"Failed to auto-start MCP server {server.name}: {str(e)}")
    
    async def import_from_mcp_json(self, filepath: str = ".mcp.json") -> Dict[str, bool]:
        """Import MCP server configurations from a .mcp.json file.
        
        Args:
            filepath: Path to the .mcp.json file (default: ".mcp.json" in current directory)
            
        Returns:
            Dict mapping server names to import success status
        """
        import json
        from pathlib import Path
        
        results = {}
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"MCP configuration file not found: {filepath}")
            return results
            
        try:
            logger.info(f"Loading MCP configurations from {filepath}")
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Handle mcpServers section
            mcp_servers = data.get('mcpServers', {})
            
            for server_name, server_config in mcp_servers.items():
                try:
                    # Determine server type based on config
                    if 'type' in server_config and server_config['type'] == 'sse':
                        # SSE/HTTP server
                        config = MCPServerConfig(
                            name=server_name,
                            server_type=MCPServerType.HTTP,
                            description=f"Imported from {filepath}",
                            http_url=server_config.get('url'),
                            agent_names=[],  # Don't assign to agents by default
                            auto_start=True,  # Auto-start servers
                            timeout_seconds=90  # Much longer timeout for remote HTTP/SSE servers
                        )
                    else:
                        # STDIO server
                        command_parts = []
                        if 'command' in server_config:
                            command_parts.append(server_config['command'])
                        if 'args' in server_config:
                            command_parts.extend(server_config['args'])
                        
                        # Determine timeout based on command type
                        timeout = 30  # Default timeout
                        if command_parts and command_parts[0] == 'docker':
                            timeout = 90  # Much longer timeout for Docker commands
                        elif command_parts and command_parts[0] == 'npx':
                            timeout = 60  # Longer timeout for NPX commands
                            
                        config = MCPServerConfig(
                            name=server_name,
                            server_type=MCPServerType.STDIO,
                            description=f"Imported from {filepath}",
                            command=command_parts,
                            env=server_config.get('env', {}),
                            agent_names=[],  # Don't assign to agents by default
                            auto_start=True,  # Auto-start servers
                            timeout_seconds=timeout
                        )
                    
                    # Check if server already exists
                    if server_name in self._servers:
                        logger.info(f"Server '{server_name}' already loaded, skipping import")
                        results[server_name] = True
                    else:
                        logger.info(f"Adding new server: {server_name}")
                        await self.add_server(config)
                        results[server_name] = True
                    
                except Exception as e:
                    logger.error(f"Failed to import server '{server_name}': {str(e)}")
                    results[server_name] = False
            
            # Handle other standalone tools (like send_whatsapp_message in the example)
            for key, value in data.items():
                if key != 'mcpServers' and isinstance(value, dict) and 'command' in value:
                    try:
                        # This is likely a standalone MCP tool configuration
                        server_name = key
                        
                        command_parts = []
                        if 'command' in value:
                            command_parts.append(value['command'])
                        if 'args' in value:
                            command_parts.extend(value['args'])
                        
                        # Determine timeout based on command type
                        timeout = 30  # Default timeout
                        if command_parts and command_parts[0] == 'docker':
                            timeout = 90  # Much longer timeout for Docker commands
                        elif command_parts and command_parts[0] == 'npx':
                            timeout = 60  # Longer timeout for NPX commands
                            
                        config = MCPServerConfig(
                            name=server_name,
                            server_type=MCPServerType.STDIO,
                            description=f"Imported standalone tool from {filepath}",
                            command=command_parts,
                            env=value.get('env', {}),
                            agent_names=[],  # Don't assign to agents by default
                            auto_start=True,  # Auto-start servers
                            timeout_seconds=timeout
                        )
                        
                        if server_name in self._servers:
                            logger.info(f"Server '{server_name}' already loaded, skipping import")
                            results[server_name] = True
                        else:
                            logger.info(f"Adding new server: {server_name}")
                            await self.add_server(config)
                            results[server_name] = True
                        
                    except Exception as e:
                        logger.error(f"Failed to import standalone tool '{key}': {str(e)}")
                        results[key] = False
                        
            logger.info(f"MCP import completed. Success: {sum(results.values())}/{len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to load MCP configuration file: {str(e)}")
            return results
    
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Create snapshot to avoid race conditions during dictionary iteration
                # This prevents RuntimeError when servers are added/removed during health checks
                servers_snapshot = dict(self._servers)
                
                # Ping all running servers from snapshot
                for server in servers_snapshot.values():
                    # Check if server still exists (might have been removed after snapshot)
                    if server.name not in self._servers:
                        logger.debug(f"Skipping health check for removed server: {server.name}")
                        continue
                        
                    if server.is_running:
                        try:
                            is_healthy = await server.ping()
                            if not is_healthy:
                                logger.warning(f"Health check failed for MCP server: {server.name}")
                                
                                # Attempt restart if configured and server still exists
                                if server.config.max_retries > 0 and server.name in self._servers:
                                    try:
                                        await server.restart()
                                        logger.info(f"Successfully restarted unhealthy MCP server: {server.name}")
                                    except Exception as e:
                                        logger.error(f"Failed to restart MCP server {server.name}: {str(e)}")
                        except Exception as e:
                            logger.error(f"Health check ping failed for server {server.name}: {str(e)}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MCP health check loop: {str(e)}")
    
    @asynccontextmanager
    async def get_server_context(self, server_name: str):
        """Context manager to get a server and ensure it's running.
        
        Args:
            server_name: Name of the server
            
        Yields:
            MCPServerManager instance
            
        Raises:
            MCPError: If server not found
        """
        if server_name not in self._servers:
            raise MCPError(f"Server {server_name} not found")
        
        server = self._servers[server_name]
        
        async with server.ensure_running():
            yield server

    async def refresh_configurations(self) -> None:
        """Refresh server configurations from database.
        
        This method reloads all server configurations from the database
        and updates the in-memory state. Useful when configurations
        have been updated via API calls.
        """
        logger.info("Refreshing MCP server configurations from database")
        
        try:
            # Stop all currently running servers (use snapshot for thread safety)
            servers_snapshot = dict(self._servers)
            stop_tasks = []
            for server in servers_snapshot.values():
                if server.is_running:
                    stop_tasks.append(server.stop())
            
            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)
            
            # Clear current state
            self._servers.clear()
            self._agent_servers.clear()
            
            # Reload configurations from database
            await self._load_server_configurations()
            
            # Start auto-start servers
            await self._start_auto_start_servers()
            
            logger.info(f"Refreshed MCP configurations: {len(self._servers)} servers loaded")
            
        except Exception as e:
            logger.error(f"Failed to refresh MCP configurations: {str(e)}")
            raise MCPError(f"Configuration refresh failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers and cleanup resources."""
        try:
            logger.info("Shutting down MCP client manager...")
            
            # Stop health check task if running
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Stop all servers
            stop_tasks = []
            servers_snapshot = dict(self._servers)
            
            for server in servers_snapshot.values():
                if server.is_running:
                    stop_tasks.append(server.stop())
            
            if stop_tasks:
                logger.info(f"Stopping {len(stop_tasks)} MCP servers...")
                await asyncio.gather(*stop_tasks, return_exceptions=True)
            
            # Clear state
            self._servers.clear()
            self._agent_servers.clear()
            self._initialized = False
            
            logger.info("✅ MCP client manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during MCP client manager shutdown: {str(e)}")
            # Don't raise here to avoid interfering with application shutdown


# Global MCP client manager instance
mcp_client_manager: Optional[MCPClientManager] = None


async def get_mcp_client_manager() -> MCPClientManager:
    """Get the global MCP client manager instance.
    
    Returns:
        Initialized MCP client manager
    """
    global mcp_client_manager
    
    if mcp_client_manager is None:
        mcp_client_manager = MCPClientManager()
        await mcp_client_manager.initialize()
    
    return mcp_client_manager


async def refresh_mcp_client_manager() -> MCPClientManager:
    """Refresh the global MCP client manager instance.
    
    This forces a reload of all server configurations from the database.
    Useful when configurations have been updated via API calls.
    
    Returns:
        Refreshed MCP client manager
    """
    global mcp_client_manager
    
    if mcp_client_manager is not None:
        await mcp_client_manager.refresh_configurations()
    else:
        # Initialize if not already done
        mcp_client_manager = MCPClientManager()
        await mcp_client_manager.initialize()
    
    return mcp_client_manager


async def shutdown_mcp_client_manager() -> None:
    """Shutdown the global MCP client manager instance."""
    global mcp_client_manager
    
    if mcp_client_manager is not None:
        await mcp_client_manager.shutdown()
        mcp_client_manager = None