"""MCP server wrapper and manager for automagik-agents framework."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from pydantic_ai.tools import Tool as PydanticTool

try:
    from pydantic_ai.mcp import MCPServer, MCPServerStdio, MCPServerHTTP
except ImportError:
    # Fallback for older versions or if MCP is not available
    MCPServer = None
    MCPServerStdio = None  
    MCPServerHTTP = None

from .models import (
    MCPServerConfig, 
    MCPServerStatus, 
    MCPServerState, 
    MCPServerType,
    MCPToolInfo,
    MCPResourceInfo
)
from .exceptions import MCPError, MCPServerError, MCPToolError

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages a single MCP server instance and its lifecycle."""
    
    def __init__(self, config: MCPServerConfig):
        """Initialize MCP server manager.
        
        Args:
            config: MCP server configuration
        """
        if not MCPServer:
            raise MCPError("MCP support not available - pydantic_ai.mcp not found")
            
        self.config = config
        self.state = MCPServerState(
            name=config.name,
            status=MCPServerStatus.STOPPED
        )
        self._server: Optional[MCPServer] = None
        self._server_class = None
        self._server_args = None
        self._server_context = None
        self._tools: Dict[str, MCPToolInfo] = {}
        self._resources: Dict[str, MCPResourceInfo] = {}
        self._connection_lock = asyncio.Lock()
        
    @property
    def name(self) -> str:
        """Get server name."""
        return self.config.name
        
    @property
    def status(self) -> MCPServerStatus:
        """Get current server status."""
        return self.state.status
        
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.state.status == MCPServerStatus.RUNNING
        
    @property
    def tools(self) -> List[MCPToolInfo]:
        """Get list of available tools."""
        return list(self._tools.values())
        
    @property
    def resources(self) -> List[MCPResourceInfo]:
        """Get list of available resources."""
        return list(self._resources.values())
        
    async def start(self) -> None:
        """Start the MCP server."""
        async with self._connection_lock:
            if self.is_running:
                logger.info(f"MCP server {self.name} is already running")
                return
                
            try:
                self.state.status = MCPServerStatus.STARTING
                self.state.connection_attempts += 1
                logger.info(f"Starting MCP server: {self.name}")
                
                # Create server instance based on type
                if self.config.server_type == MCPServerType.STDIO:
                    if not self.config.command:
                        raise MCPServerError("Command required for stdio server", self.name)
                    
                    # Split command into command and args
                    if len(self.config.command) == 0:
                        raise MCPServerError("Command cannot be empty", self.name)
                    
                    command = self.config.command[0]
                    args = self.config.command[1:] if len(self.config.command) > 1 else []
                    
                    logger.info(f"Creating MCP server with command: {command}, args: {args}")
                    
                    # Create server instance
                    self._server_class = MCPServerStdio
                    self._server_args = {
                        'command': command,
                        'args': args,
                        'env': self.config.env or {}
                    }
                    
                    # Store server instance without entering context yet
                    # The context will be managed by the consumer (PydanticAI agent)
                    self._server = self._server_class(**self._server_args)
                    
                elif self.config.server_type == MCPServerType.HTTP:
                    if not self.config.http_url:
                        raise MCPServerError("HTTP URL required for HTTP server", self.name)
                    
                    # Create server instance
                    self._server_class = MCPServerHTTP
                    self._server_args = {'url': self.config.http_url}
                    
                    # Store server instance without entering context yet
                    # The context will be managed by the consumer (PydanticAI agent)
                    self._server = self._server_class(**self._server_args)
                    
                else:
                    raise MCPServerError(f"Unknown server type: {self.config.server_type}", self.name)
                
                # Test connection by temporarily entering context to discover capabilities
                # Add timeout to prevent hanging indefinitely
                try:
                    # Add startup delays for different server types
                    if self.config.server_type == MCPServerType.STDIO and self.config.command:
                        if self.config.command[0] == 'docker':
                            logger.info(f"Waiting for {self.name} Docker container to initialize...")
                            await asyncio.sleep(5)  # Give Docker more time to start
                        elif self.config.command[0] == 'npx':
                            logger.info(f"Waiting for {self.name} NPX server to initialize...")
                            await asyncio.sleep(3)  # Give NPX time to start
                    elif self.config.server_type == MCPServerType.HTTP:
                        logger.info(f"Connecting to remote {self.name} server...")
                        await asyncio.sleep(1)  # Brief delay for HTTP connection
                    
                    async def discover_with_timeout():
                        async with self._server as temp_server:
                            # Discover tools and resources
                            await self._discover_capabilities_with_server(temp_server)
                    
                    await asyncio.wait_for(discover_with_timeout(), timeout=self.config.timeout_seconds)
                except asyncio.TimeoutError:
                    logger.warning(f"MCP server {self.name} discovery timed out after {self.config.timeout_seconds}s")
                    logger.info(f"Proceeding without capability discovery for {self.name}")
                    # Continue without capabilities - server may still be functional
                    self._tools.clear()
                    self._resources.clear()
                    self.state.tools_discovered = []
                    self.state.resources_discovered = []
                except Exception as capability_error:
                    logger.warning(f"MCP server {self.name} capability discovery failed: {str(capability_error)}")
                    logger.info(f"Proceeding without capability discovery for {self.name}")
                    # Continue without capabilities if server starts but discovery fails
                    self._tools.clear()
                    self._resources.clear()
                    self.state.tools_discovered = []
                    self.state.resources_discovered = []
                    
                    # Add a small delay to ensure any async cleanup completes
                    await asyncio.sleep(0.05)
                
                self.state.status = MCPServerStatus.RUNNING
                self.state.started_at = datetime.now()
                self.state.last_error = None
                self.state.error_count = 0
                
                logger.info(f"MCP server {self.name} started successfully")
                logger.info(f"Discovered {len(self._tools)} tools and {len(self._resources)} resources")
                
            except Exception as e:
                self.state.status = MCPServerStatus.ERROR
                self.state.last_error = str(e)
                self.state.error_count += 1
                
                logger.error(f"Failed to start MCP server {self.name}: {str(e)}")
                
                # Cleanup on failure
                self._server = None
                self._server_context = None
                
                raise MCPServerError(f"Failed to start server: {str(e)}", self.name)
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        async with self._connection_lock:
            if not self.is_running and self._server is None:
                logger.info(f"MCP server {self.name} is already stopped")
                return
                
            try:
                self.state.status = MCPServerStatus.STOPPING
                logger.info(f"Stopping MCP server: {self.name}")
                
                # Properly cleanup server instance to avoid async context issues
                if self._server is not None:
                    try:
                        # Force cleanup of any remaining async contexts
                        # by creating a brief context and immediately closing it
                        await asyncio.sleep(0.1)  # Brief delay to let any pending operations complete
                    except Exception as cleanup_error:
                        logger.debug(f"Minor cleanup issue for {self.name}: {cleanup_error}")
                
                # Clear server instance - context management is handled by consumers
                self._server = None
                self._server_context = None
                
                self._tools.clear()
                self._resources.clear()
                
                self.state.status = MCPServerStatus.STOPPED
                self.state.started_at = None
                
                logger.info(f"MCP server {self.name} stopped successfully")
                
            except Exception as e:
                self.state.status = MCPServerStatus.ERROR
                self.state.last_error = str(e)
                self.state.error_count += 1
                
                logger.error(f"Error stopping MCP server {self.name}: {str(e)}")
                raise MCPServerError(f"Failed to stop server: {str(e)}", self.name)
    
    async def restart(self) -> None:
        """Restart the MCP server."""
        logger.info(f"Restarting MCP server: {self.name}")
        await self.stop()
        await self.start()
    
    async def ping(self) -> bool:
        """Ping the server to check if it's responsive."""
        if not self.is_running or not self._server:
            return False
        
        try:
            # For stdio servers, we can check if the process is still alive
            if hasattr(self._server, 'process') and self._server.process:
                if self._server.process.returncode is not None:
                    return False
            
            # Update last ping time
            self.state.last_ping = datetime.now()
            return True
            
        except Exception as e:
            logger.warning(f"Ping failed for MCP server {self.name}: {str(e)}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool call fails
        """
        if not self.is_running or not self._server:
            raise MCPToolError(f"Server {self.name} is not running", tool_name, self.name)
        
        if tool_name not in self._tools:
            raise MCPToolError(f"Tool {tool_name} not found", tool_name, self.name)
        
        try:
            start_time = time.time()
            
            # Call the tool through the MCP server using async context manager
            async with self._server as server_instance:
                result = await server_instance.call_tool(tool_name, arguments)
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            logger.debug(f"Tool {tool_name} executed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Tool call failed: {tool_name} on {self.name}: {str(e)}")
            raise MCPToolError(f"Tool execution failed: {str(e)}", tool_name, self.name)
    
    async def access_resource(self, uri: str) -> Any:
        """Access a resource on the MCP server.
        
        Args:
            uri: URI of the resource to access
            
        Returns:
            Resource content
            
        Raises:
            MCPToolError: If resource access fails
        """
        if not self.is_running or not self._server:
            raise MCPToolError(f"Server {self.name} is not running", server_name=self.name)
        
        if uri not in self._resources:
            raise MCPToolError(f"Resource {uri} not found", server_name=self.name)
        
        try:
            # Access the resource through the MCP server using async context manager
            async with self._server as server_instance:
                result = await server_instance.read_resource(uri)
            
            logger.debug(f"Resource {uri} accessed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Resource access failed: {uri} on {self.name}: {str(e)}")
            raise MCPToolError(f"Resource access failed: {str(e)}", server_name=self.name)
    
    async def _discover_capabilities_with_server(self, server_instance) -> None:
        """Discover tools and resources available on the server using provided server instance.
        
        Args:
            server_instance: Active MCP server instance within async context
        """
        try:
            logger.info(f"Starting capability discovery for server {self.name}")
            
            # Discover tools
            logger.debug(f"Calling list_tools() for server {self.name}")
            tools = await server_instance.list_tools()
            logger.info(f"Server {self.name} returned {len(tools)} tools")
            
            self._tools.clear()
            
            for tool in tools:
                logger.debug(f"Processing tool: {tool.name}")
                tool_info = MCPToolInfo(
                    name=tool.name,
                    description=getattr(tool, 'description', None),
                    server_name=self.name,
                    input_schema=getattr(tool, 'input_schema', None),
                    output_schema=getattr(tool, 'output_schema', None)
                )
                self._tools[tool.name] = tool_info
            
            self.state.tools_discovered = list(self._tools.keys())
            logger.info(f"Server {self.name} tools discovered: {self.state.tools_discovered}")
            
            # Discover resources
            try:
                # Check if server instance has list_resources method
                if hasattr(server_instance, 'list_resources'):
                    logger.debug(f"Calling list_resources() for server {self.name}")
                    resources = await server_instance.list_resources()
                    logger.info(f"Server {self.name} returned {len(resources)} resources")
                    self._resources.clear()
                    
                    for resource in resources:
                        resource_info = MCPResourceInfo(
                            uri=resource.uri,
                            name=getattr(resource, 'name', None),
                            description=getattr(resource, 'description', None),
                            mime_type=getattr(resource, 'mime_type', None),
                            server_name=self.name
                        )
                        self._resources[resource.uri] = resource_info
                    
                    self.state.resources_discovered = list(self._resources.keys())
                else:
                    # Server doesn't support resource discovery
                    logger.debug(f"Server {self.name} does not support resource discovery")
                    self.state.resources_discovered = []
                
            except Exception as e:
                # Resource discovery is optional
                logger.warning(f"Resource discovery failed for {self.name}: {str(e)}")
                self.state.resources_discovered = []
            
        except Exception as e:
            logger.error(f"Failed to discover capabilities for {self.name}: {str(e)}")
            import traceback
            logger.error(f"Capability discovery traceback: {traceback.format_exc()}")
            raise MCPServerError(f"Capability discovery failed: {str(e)}", self.name)

    async def _discover_capabilities(self) -> None:
        """Discover tools and resources available on the server."""
        if not self._server:
            return
        
        # Use the server within its own async context for capability discovery
        async with self._server as server_instance:
            await self._discover_capabilities_with_server(server_instance)
    
    def get_pydantic_tools(self) -> List[PydanticTool]:
        """Get tools as PydanticAI tools for integration with agents.
        
        Returns:
            List of PydanticAI tools
        """
        tools = []
        
        for tool_name, tool_info in self._tools.items():
            # Create a wrapper function for the MCP tool
            async def mcp_tool_wrapper(*args, **kwargs):
                """Wrapper for MCP tool call."""
                return await self.call_tool(tool_name, kwargs)
            
            # Create PydanticAI tool
            pydantic_tool = PydanticTool(
                name=f"{self.name}_{tool_name}",
                description=tool_info.description or f"Tool {tool_name} from MCP server {self.name}",
                function=mcp_tool_wrapper
            )
            
            tools.append(pydantic_tool)
        
        return tools
    
    @asynccontextmanager
    async def ensure_running(self):
        """Context manager to ensure server is running."""
        if not self.is_running:
            await self.start()
        
        try:
            yield self
        finally:
            # Optionally implement auto-stop logic here
            pass


class MCPManager:
    """
    Centralized manager for all MCP servers in the automagik-agents framework.
    
    This class provides a unified interface for managing multiple MCP servers,
    including initialization, lifecycle management, tool discovery, and execution.
    """
    
    def __init__(self):
        """Initialize the MCP manager."""
        self._servers: Dict[str, MCPServerManager] = {}
        self._initialized = False
        
    @property
    def initialized(self) -> bool:
        """Check if the manager has been initialized."""
        return self._initialized
        
    @property
    def server_count(self) -> int:
        """Get the number of registered servers."""
        return len(self._servers)
    
    async def initialize_servers(self, configs: List[MCPServerConfig]) -> None:
        """
        Initialize all MCP servers from configurations.
        
        Args:
            configs: List of MCP server configurations
        """
        logger.info(f"Initializing {len(configs)} MCP servers...")
        
        for config in configs:
            try:
                server_manager = MCPServerManager(config)
                self._servers[config.name] = server_manager
                logger.info(f"Registered MCP server: {config.name}")
            except Exception as e:
                logger.error(f"Failed to register MCP server {config.name}: {str(e)}")
        
        # Start all servers
        failed_servers = []
        for name, server in self._servers.items():
            try:
                await server.start()
                logger.info(f"Started MCP server: {name}")
            except Exception as e:
                logger.error(f"Failed to start MCP server {name}: {str(e)}")
                failed_servers.append(name)
        
        # Remove failed servers
        for name in failed_servers:
            del self._servers[name]
        
        self._initialized = True
        logger.info(f"MCP manager initialized with {len(self._servers)} active servers")
    
    async def shutdown_servers(self) -> None:
        """Shutdown all MCP servers."""
        logger.info("Shutting down all MCP servers...")
        
        for name, server in self._servers.items():
            try:
                await server.stop()
                logger.info(f"Stopped MCP server: {name}")
            except Exception as e:
                logger.error(f"Error stopping MCP server {name}: {str(e)}")
        
        self._servers.clear()
        self._initialized = False
        logger.info("All MCP servers shut down")
    
    def get_server_status(self, server_name: str) -> Optional[MCPServerState]:
        """
        Get the status of a specific server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server state or None if server not found
        """
        server = self._servers.get(server_name)
        return server.state if server else None
    
    def list_servers(self) -> List[str]:
        """
        Get list of all server names.
        
        Returns:
            List of server names
        """
        return list(self._servers.keys())
    
    def get_server(self, server_name: str) -> Optional[MCPServerManager]:
        """
        Get a specific server manager.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server manager or None if not found
        """
        return self._servers.get(server_name)
    
    async def create_server(self, config: MCPServerConfig) -> bool:
        """
        Create and start a new MCP server.
        
        Args:
            config: Server configuration
            
        Returns:
            True if server was created successfully
        """
        if config.name in self._servers:
            logger.warning(f"Server {config.name} already exists")
            return False
        
        try:
            server_manager = MCPServerManager(config)
            await server_manager.start()
            self._servers[config.name] = server_manager
            logger.info(f"Created and started MCP server: {config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create MCP server {config.name}: {str(e)}")
            return False
    
    async def update_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """
        Update an existing server configuration.
        
        Args:
            server_name: Name of the server to update
            config: New configuration
            
        Returns:
            True if server was updated successfully
        """
        if server_name not in self._servers:
            logger.warning(f"Server {server_name} not found")
            return False
        
        try:
            # Stop existing server
            await self._servers[server_name].stop()
            
            # Create new server with updated config
            server_manager = MCPServerManager(config)
            await server_manager.start()
            self._servers[server_name] = server_manager
            
            logger.info(f"Updated MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update MCP server {server_name}: {str(e)}")
            return False
    
    async def delete_server(self, server_name: str) -> bool:
        """
        Delete a server.
        
        Args:
            server_name: Name of the server to delete
            
        Returns:
            True if server was deleted successfully
        """
        if server_name not in self._servers:
            logger.warning(f"Server {server_name} not found")
            return False
        
        try:
            await self._servers[server_name].stop()
            del self._servers[server_name]
            logger.info(f"Deleted MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete MCP server {server_name}: {str(e)}")
            return False
    
    async def start_server(self, server_name: str) -> bool:
        """
        Start a specific server.
        
        Args:
            server_name: Name of the server to start
            
        Returns:
            True if server was started successfully
        """
        server = self._servers.get(server_name)
        if not server:
            logger.warning(f"Server {server_name} not found")
            return False
        
        try:
            await server.start()
            logger.info(f"Started MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server {server_name}: {str(e)}")
            return False
    
    async def stop_server(self, server_name: str) -> bool:
        """
        Stop a specific server.
        
        Args:
            server_name: Name of the server to stop
            
        Returns:
            True if server was stopped successfully
        """
        server = self._servers.get(server_name)
        if not server:
            logger.warning(f"Server {server_name} not found")
            return False
        
        try:
            await server.stop()
            logger.info(f"Stopped MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop MCP server {server_name}: {str(e)}")
            return False
    
    async def restart_server(self, server_name: str) -> bool:
        """
        Restart a specific server.
        
        Args:
            server_name: Name of the server to restart
            
        Returns:
            True if server was restarted successfully
        """
        server = self._servers.get(server_name)
        if not server:
            logger.warning(f"Server {server_name} not found")
            return False
        
        try:
            await server.restart()
            logger.info(f"Restarted MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart MCP server {server_name}: {str(e)}")
            return False
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on a specific server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool call fails
        """
        server = self._servers.get(server_name)
        if not server:
            raise MCPToolError(f"Server {server_name} not found", tool_name, server_name)
        
        return await server.call_tool(tool_name, arguments)
    
    def list_tools(self, server_name: Optional[str] = None) -> List[MCPToolInfo]:
        """
        List tools from all servers or a specific server.
        
        Args:
            server_name: Name of specific server, or None for all servers
            
        Returns:
            List of tool information
        """
        if server_name:
            server = self._servers.get(server_name)
            return server.tools if server else []
        
        # Return tools from all servers
        all_tools = []
        for server in self._servers.values():
            all_tools.extend(server.tools)
        return all_tools
    
    def list_resources(self, server_name: Optional[str] = None) -> List[MCPResourceInfo]:
        """
        List resources from all servers or a specific server.
        
        Args:
            server_name: Name of specific server, or None for all servers
            
        Returns:
            List of resource information
        """
        if server_name:
            server = self._servers.get(server_name)
            return server.resources if server else []
        
        # Return resources from all servers
        all_resources = []
        for server in self._servers.values():
            all_resources.extend(server.resources)
        return all_resources
    
    async def read_resource(self, server_name: str, uri: str) -> Any:
        """
        Read a resource from a specific server.
        
        Args:
            server_name: Name of the server
            uri: URI of the resource to read
            
        Returns:
            Resource content
            
        Raises:
            MCPToolError: If resource access fails
        """
        server = self._servers.get(server_name)
        if not server:
            raise MCPToolError(f"Server {server_name} not found", server_name=server_name)
        
        return await server.access_resource(uri)
    
    def get_all_pydantic_tools(self) -> List[PydanticTool]:
        """
        Get all tools from all servers as PydanticAI tools.
        
        Returns:
            List of PydanticAI tools from all servers
        """
        all_tools = []
        for server in self._servers.values():
            all_tools.extend(server.get_pydantic_tools())
        return all_tools


# Backward compatibility alias
MCPClientManager = MCPManager