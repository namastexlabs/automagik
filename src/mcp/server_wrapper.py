"""Custom MCP server wrapper to handle subprocess communication properly.

This module provides a wrapper around PydanticAI's MCP server classes to ensure
proper subprocess handling and JSON-RPC communication.
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MCPServerProcess:
    """Wrapper for MCP server subprocess that handles JSON-RPC communication."""
    
    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None, timeout: float = 30.0):
        self.command = command
        self.args = args
        self.env = env or {}
        self.timeout = timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._responses: Dict[int, asyncio.Future] = {}
        self._next_id = 0
        
    async def start(self):
        """Start the MCP server subprocess."""
        # Prepare environment
        process_env = os.environ.copy()
        process_env.update(self.env)
        
        # Build full command
        full_command = [self.command] + self.args
        
        logger.info(f"Starting MCP server process: {' '.join(full_command)}")
        
        try:
            # Create subprocess with proper pipe handling
            self.process = await asyncio.create_subprocess_exec(
                *full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )
            
            # Start reader task
            self._reader_task = asyncio.create_task(self._read_responses())
            
            # Initialize the connection
            await self._initialize()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def _read_responses(self):
        """Read responses from the server's stdout."""
        if not self.process or not self.process.stdout:
            return
            
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                    
                try:
                    response = json.loads(line.decode())
                    if 'id' in response and response['id'] in self._responses:
                        self._responses[response['id']].set_result(response)
                except json.JSONDecodeError:
                    logger.debug(f"Non-JSON output from server: {line.decode().strip()}")
                    
        except Exception as e:
            logger.error(f"Error reading from MCP server: {e}")
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send a JSON-RPC request to the server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server process not started")
            
        request_id = self._next_id
        self._next_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        # Create future for response
        response_future = asyncio.Future()
        self._responses[request_id] = response_future
        
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=self.timeout)
            
            # Check for error
            if 'error' in response:
                raise RuntimeError(f"MCP server error: {response['error']}")
                
            return response.get('result')
            
        finally:
            # Clean up
            self._responses.pop(request_id, None)
    
    async def _initialize(self):
        """Initialize the MCP connection."""
        await self._send_request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "sampling": {}
            },
            "clientInfo": {
                "name": "automagik-mcp-client",
                "version": "1.0.0"
            }
        })
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server."""
        result = await self._send_request("tools/list")
        return result.get('tools', [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server."""
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return result
    
    async def stop(self):
        """Stop the server process."""
        if self._reader_task:
            self._reader_task.cancel()
            
        if self.process:
            try:
                # Send shutdown request
                await self._send_request("shutdown")
            except:
                pass
                
            # Terminate process
            self.process.terminate()
            await self.process.wait()


class MCPServerStdioWrapper:
    """Wrapper around PydanticAI's MCPServerStdio that fixes subprocess issues."""
    
    def __init__(self, command: str, args: List[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 30.0):
        self.command = command
        self.args = args or []
        self.env = env
        self.timeout = timeout
        self._process: Optional[MCPServerProcess] = None
        self._original_server = None
        
        # Try to use PydanticAI's implementation first
        try:
            from pydantic_ai.models.mcp import MCPServerStdio
            self._original_server = MCPServerStdio(
                command=command,
                args=args,
                env=env,
                timeout=timeout
            )
        except Exception as e:
            logger.warning(f"Could not create PydanticAI MCPServerStdio: {e}")
    
    async def __aenter__(self):
        """Enter async context - start the server."""
        # Try PydanticAI's implementation first
        if self._original_server:
            try:
                result = await self._original_server.__aenter__()
                return result
            except Exception as e:
                logger.warning(f"PydanticAI MCP server failed, using custom wrapper: {e}")
        
        # Fallback to custom implementation
        self._process = MCPServerProcess(self.command, self.args, self.env, self.timeout)
        await self._process.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context - stop the server."""
        if self._original_server and hasattr(self._original_server, '__aexit__'):
            try:
                await self._original_server.__aexit__(exc_type, exc_val, exc_tb)
                return
            except:
                pass
                
        if self._process:
            await self._process.stop()
    
    async def list_tools(self) -> List[Any]:
        """List available tools."""
        if self._process:
            # Using custom implementation
            tools_data = await self._process.list_tools()
            # Convert to PydanticAI tool format
            from pydantic_ai.tools import Tool as PydanticTool
            tools = []
            for tool_data in tools_data:
                # Create a mock tool object
                tool = type('Tool', (), {
                    'name': tool_data.get('name', ''),
                    'description': tool_data.get('description', ''),
                    'input_schema': tool_data.get('inputSchema', {}),
                    'output_schema': tool_data.get('outputSchema', {})
                })()
                tools.append(tool)
            return tools
        else:
            # Using PydanticAI's implementation
            return await self._original_server.list_tools()
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool."""
        if self._process:
            return await self._process.call_tool(name, arguments)
        else:
            # This would be handled by PydanticAI internally
            raise NotImplementedError("Tool calling through original server")