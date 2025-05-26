#!/usr/bin/env python3
"""Script to check current MCP server status with proper async context management."""

import asyncio
import sys
import os
import signal
import logging
from contextlib import asynccontextmanager

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.mcp.client import MCPClientManager

# Setup logging to suppress MCP noise unless needed
logging.getLogger('mcp').setLevel(logging.WARNING)

class MCPStatusChecker:
    """Async context-managed MCP status checker."""
    
    def __init__(self):
        self.manager = None
        self.shutdown_event = asyncio.Event()
    
    async def __aenter__(self):
        """Async context manager entry."""
        try:
            self.manager = MCPClientManager()
            await self.manager.initialize()
            return self
        except Exception as e:
            print(f'Error initializing MCP manager: {e}')
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        if self.manager:
            try:
                await self.manager.shutdown()
            except Exception as e:
                print(f'Error during MCP manager shutdown: {e}')
    
    async def check_status(self):
        """Check and display MCP server status."""
        try:
            print('=== MCP SERVERS STATUS ===')
            servers = self.manager.list_servers()  # This is synchronous
            
            for server_state in servers:
                # Get the server manager to access config info
                server_manager = self.manager.get_server(server_state.name)
                print(f'Server: {server_state.name}')
                print(f'  Status: {server_state.status.value}')
                
                if server_manager:
                    print(f'  Type: {server_manager.config.server_type.value}')
                    print(f'  Agents: {server_manager.config.agent_names}')
                    print(f'  Command: {server_manager.config.command}')
                    print(f'  Tools: {len(server_state.tools_discovered)}')
                    print(f'  Resources: {len(server_state.resources_discovered)}')
                    
                    if server_state.last_error:
                        print(f'  Last Error: {server_state.last_error}')
                    
                    if server_state.started_at:
                        print(f'  Started: {server_state.started_at}')
                        
                print('---')
            
            print(f'Total servers: {len(servers)}')
            
            print('\n=== AGENT-SERVER ASSIGNMENTS ===')
            agent_servers = self.manager._agent_servers
            for agent_name, server_names in agent_servers.items():
                print(f'Agent {agent_name}: {list(server_names)}')
                
        except Exception as e:
            print(f'Error checking MCP status: {e}')
            import traceback
            traceback.print_exc()

async def main():
    """Main async function with proper signal handling."""
    
    def signal_handler():
        """Handle shutdown signals gracefully."""
        print('\nReceived shutdown signal, cleaning up...')
    
    # Setup signal handlers for graceful shutdown
    if hasattr(signal, 'SIGTERM'):
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        async with MCPStatusChecker() as checker:
            await checker.check_status()
    except KeyboardInterrupt:
        print('\nShutdown requested by user')
    except Exception as e:
        print(f'Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print('\nInterrupted')
        sys.exit(130) 