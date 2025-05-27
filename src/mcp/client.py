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
        
        # Stop all servers
        stop_tasks = []
        for server in self._servers.values():
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
        return [server.state for server in self._servers.values()]
    
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
        """Load MCP server configurations from database."""
        from src.db.repository.mcp import list_mcp_servers, get_server_agents
        from src.db.repository.agent import get_agent
        
        try:
            # Get all MCP servers using repository method
            servers = list_mcp_servers(enabled_only=False)
            
            for server in servers:
                try:
                    # Get agent assignments for this server
                    agent_ids = get_server_agents(server.id)
                    agent_names = []
                    
                    # Convert agent IDs to names
                    for agent_id in agent_ids:
                        agent = get_agent(agent_id)
                        if agent:
                            agent_names.append(agent.name)
                    
                    # Create MCPServerConfig from MCPServerDB
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
                    
                    logger.debug(f"Loaded MCP server configuration: {config.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load MCP server configuration {server.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load server configurations: {str(e)}")
    
    async def _save_server_config(self, config: MCPServerConfig) -> None:
        """Save MCP server configuration to database."""
        from src.db.repository.mcp import (
            get_mcp_server_by_name, create_mcp_server, update_mcp_server,
            assign_agent_to_server, remove_agent_from_server, get_server_agents
        )
        from src.db.repository.agent import get_agent_by_name
        from src.db.models import MCPServerDB
        
        try:
            # Check if server already exists
            existing_server = get_mcp_server_by_name(config.name)
            
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
                # Update existing server
                success = update_mcp_server(server_data)
                if not success:
                    raise MCPError("Failed to update MCP server")
                server_id = existing_server.id
            else:
                # Create new server
                server_id = create_mcp_server(server_data)
                if not server_id:
                    raise MCPError("Failed to create MCP server")
            
            # Handle agent assignments
            # Get current agent assignments
            current_agent_ids = set(get_server_agents(server_id))
            
            # Get new agent IDs from names
            new_agent_ids = set()
            for agent_name in config.agent_names:
                agent = get_agent_by_name(agent_name)
                if agent:
                    new_agent_ids.add(agent.id)
                else:
                    logger.warning(f"Agent '{agent_name}' not found for server '{config.name}'")
            
            # Remove agents that are no longer assigned
            for agent_id in current_agent_ids - new_agent_ids:
                remove_agent_from_server(agent_id, server_id)
            
            # Add new agent assignments
            for agent_id in new_agent_ids - current_agent_ids:
                assign_agent_to_server(agent_id, server_id)
                
        except Exception as e:
            logger.error(f"Failed to save server config: {str(e)}")
            raise MCPError(f"Failed to save server configuration: {str(e)}")
    
    async def _delete_server_config(self, server_name: str) -> None:
        """Delete MCP server configuration from database."""
        from src.db.repository.mcp import get_mcp_server_by_name, delete_mcp_server
        
        try:
            # Get server by name to get its ID
            server = get_mcp_server_by_name(server_name)
            if not server:
                logger.warning(f"Server '{server_name}' not found for deletion")
                return
            
            # Delete server (this will also delete agent assignments due to CASCADE)
            success = delete_mcp_server(server.id)
            if not success:
                raise MCPError(f"Failed to delete server '{server_name}'")
                
        except Exception as e:
            logger.error(f"Failed to delete server config: {str(e)}")
            raise MCPError(f"Failed to delete server configuration: {str(e)}")
    
    async def _start_auto_start_servers(self) -> None:
        """Start servers configured for auto-start."""
        start_tasks = []
        
        for server in self._servers.values():
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
    
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Ping all running servers
                for server in self._servers.values():
                    if server.is_running:
                        is_healthy = await server.ping()
                        if not is_healthy:
                            logger.warning(f"Health check failed for MCP server: {server.name}")
                            
                            # Attempt restart if configured
                            if server.config.max_retries > 0:
                                try:
                                    await server.restart()
                                    logger.info(f"Successfully restarted unhealthy MCP server: {server.name}")
                                except Exception as e:
                                    logger.error(f"Failed to restart MCP server {server.name}: {str(e)}")
                
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