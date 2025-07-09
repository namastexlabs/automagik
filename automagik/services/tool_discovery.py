"""Dynamic tool discovery service for code and MCP tools."""

import inspect
import importlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from contextlib import AsyncExitStack

from automagik.db.repository.tool import create_tool, get_tool_by_name, list_tools
from automagik.db.repository.mcp import list_mcp_configs
from automagik.db.models import ToolCreate
from automagik.mcp.client import get_mcp_manager

# Import PydanticAI MCP for proper AsyncExitStack pattern
try:
    from pydantic_ai.mcp import MCPServerStdio
except ImportError:
    logger.warning("PydanticAI MCP not available - MCP tool discovery will be disabled")
    MCPServerStdio = None

logger = logging.getLogger(__name__)


class ToolDiscoveryService:
    """Service for discovering and managing tools."""
    
    def __init__(self):
        self.code_tools_cache: Dict[str, Dict[str, Any]] = {}
        self.mcp_tools_cache: Dict[str, Dict[str, Any]] = {}
        self._last_discovery: Optional[datetime] = None
    
    async def discover_all_tools(self, force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """Discover all available tools (code and MCP)."""
        if not force_refresh and self._last_discovery:
            # Return cached results if recent
            time_diff = datetime.utcnow() - self._last_discovery
            if time_diff.total_seconds() < 300:  # 5 minutes cache
                return {
                    "code_tools": list(self.code_tools_cache.values()),
                    "mcp_tools": list(self.mcp_tools_cache.values())
                }
        
        logger.info("Starting comprehensive tool discovery")
        
        # Discover code tools
        code_tools = await self._discover_code_tools()
        
        # Discover MCP tools
        mcp_tools = await self._discover_mcp_tools()
        
        # Update cache
        self.code_tools_cache = {tool["name"]: tool for tool in code_tools}
        self.mcp_tools_cache = {tool["name"]: tool for tool in mcp_tools}
        self._last_discovery = datetime.utcnow()
        
        logger.info(f"Discovered {len(code_tools)} code tools and {len(mcp_tools)} MCP tools")
        
        return {
            "code_tools": code_tools,
            "mcp_tools": mcp_tools
        }
    
    async def _discover_code_tools(self) -> List[Dict[str, Any]]:
        """Discover all code-based tools from automagik/tools/ directory."""
        tools = []
        tools_dir = Path("automagik/tools")
        
        if not tools_dir.exists():
            logger.warning(f"Tools directory {tools_dir} does not exist")
            return tools
        
        for tool_dir in tools_dir.iterdir():
            if not tool_dir.is_dir() or tool_dir.name.startswith("__"):
                continue
            
            tool_py = tool_dir / "tool.py"
            if not tool_py.exists():
                continue
            
            try:
                # Import the tool module
                module_path = f"automagik.tools.{tool_dir.name}.tool"
                module = importlib.import_module(module_path)
                
                # Find all callable functions that could be tools
                tool_functions = self._extract_tool_functions(module)
                
                for func_name, func in tool_functions.items():
                    tool_info = self._analyze_tool_function(
                        func, 
                        tool_dir.name,
                        module_path,
                        func_name
                    )
                    if tool_info:
                        tools.append(tool_info)
                        
            except Exception as e:
                logger.warning(f"Failed to import tool {tool_dir.name}: {e}")
        
        return tools
    
    def _extract_tool_functions(self, module) -> Dict[str, Callable]:
        """Extract tool functions from a module."""
        functions = {}
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isfunction(obj) and 
                not name.startswith("_") and 
                self._is_tool_function(obj)):
                functions[name] = obj
        
        return functions
    
    def _is_tool_function(self, func: Callable) -> bool:
        """Check if a function looks like a tool function."""
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            # Tool functions typically have 'ctx' as first parameter
            if params and params[0] in ['ctx', 'context']:
                return True
            
            # Or they might be async functions with tool-like names
            if inspect.iscoroutinefunction(func):
                return True
                
            return False
        except Exception:
            return False
    
    def _analyze_tool_function(
        self, 
        func: Callable, 
        tool_category: str,
        module_path: str,
        func_name: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a function to extract tool information."""
        try:
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or f"{tool_category} tool function"
            
            # Extract parameters schema
            params_schema = self._extract_parameters_schema(sig)
            
            # Generate tool name
            tool_name = f"{tool_category}_{func_name}"
            
            # Determine categories
            categories = [tool_category]
            if "send" in func_name or "message" in func_name:
                categories.append("messaging")
            if "get" in func_name or "list" in func_name or "retrieve" in func_name:
                categories.append("retrieval")
            if "create" in func_name or "upload" in func_name:
                categories.append("creation")
            if "update" in func_name or "modify" in func_name:
                categories.append("modification")
            if "delete" in func_name or "remove" in func_name:
                categories.append("deletion")
            
            return {
                "name": tool_name,
                "type": "code",
                "description": doc,
                "module_path": module_path,
                "function_name": func_name,
                "parameters_schema": params_schema,
                "categories": categories,
                "capabilities": self._infer_capabilities(func_name, doc),
                "context_signature": "RunContext[Dict]"
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze function {func_name}: {e}")
            return None
    
    def _extract_parameters_schema(self, sig: inspect.Signature) -> Dict[str, Any]:
        """Extract JSON schema from function signature."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            # Skip context parameter
            if param_name in ['ctx', 'context']:
                continue
            
            param_schema = {"type": "string"}  # Default type
            
            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                if annotation == str:
                    param_schema["type"] = "string"
                elif annotation == int:
                    param_schema["type"] = "integer"
                elif annotation == float:
                    param_schema["type"] = "number"
                elif annotation == bool:
                    param_schema["type"] = "boolean"
                elif annotation == list:
                    param_schema["type"] = "array"
                elif annotation == dict:
                    param_schema["type"] = "object"
            
            # Add description based on parameter name
            param_schema["description"] = self._generate_param_description(param_name)
            
            schema["properties"][param_name] = param_schema
            
            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                schema["required"].append(param_name)
        
        return schema
    
    def _generate_param_description(self, param_name: str) -> str:
        """Generate description for parameter based on name."""
        descriptions = {
            "message": "Message content to send",
            "text": "Text content",
            "content": "Content to process",
            "email": "Email address",
            "phone": "Phone number",
            "number": "Phone number",
            "to": "Recipient address",
            "from": "Sender address",
            "subject": "Email subject",
            "body": "Message body",
            "title": "Title or name",
            "name": "Name identifier",
            "id": "Unique identifier",
            "file": "File path or name",
            "path": "File or directory path",
            "url": "URL address",
            "data": "Data to process",
            "query": "Search query",
            "params": "Parameters object",
            "config": "Configuration object"
        }
        
        for key, desc in descriptions.items():
            if key in param_name.lower():
                return desc
        
        return f"{param_name.replace('_', ' ').title()} parameter"
    
    def _infer_capabilities(self, func_name: str, doc: str) -> List[str]:
        """Infer tool capabilities from function name and documentation."""
        capabilities = []
        
        text = f"{func_name} {doc}".lower()
        
        capability_keywords = {
            "send": ["messaging", "communication"],
            "get": ["retrieval", "read"],
            "list": ["retrieval", "enumeration"],
            "create": ["creation", "write"],
            "update": ["modification", "write"],
            "delete": ["deletion", "write"],
            "upload": ["file_transfer", "storage"],
            "download": ["file_transfer", "retrieval"],
            "search": ["search", "query"],
            "query": ["database", "search"],
            "schedule": ["scheduling", "calendar"],
            "notify": ["notification", "messaging"],
            "authenticate": ["authentication", "security"],
            "validate": ["validation", "security"]
        }
        
        for keyword, caps in capability_keywords.items():
            if keyword in text:
                capabilities.extend(caps)
        
        return list(set(capabilities))  # Remove duplicates
    
    async def _discover_mcp_tools(self) -> List[Dict[str, Any]]:
        """Discover all MCP tools using the singleton MCP manager."""
        tools = []
        
        # Check if PydanticAI MCP is available
        if MCPServerStdio is None:
            logger.warning("PydanticAI MCP not available - skipping MCP tool discovery")
            return tools
        
        try:
            # Use the singleton MCP manager instead of creating new servers
            from automagik.mcp.client import get_mcp_manager
            
            mcp_manager = await get_mcp_manager()
            if not mcp_manager:
                logger.warning("MCP manager not available - skipping MCP tool discovery")
                return tools
            
            # Get tools from all running MCP servers
            logger.debug("Discovering MCP tools from singleton manager")
            
            # List all available tools from the MCP manager
            available_tools = await mcp_manager.list_available_tools()
            
            logger.info(f"Successfully discovered {len(available_tools)} MCP tools from singleton manager")
            
            # Convert to our internal format
            for tool_name, tool_info in available_tools.items():
                try:
                    tool_data = {
                        'name': tool_name,
                        'description': tool_info.get('description', ''),
                        'server_name': tool_info.get('server_name', ''),
                        'type': 'mcp',
                        'tool_data': tool_info.get('tool_data', {}),
                        'mcp_server_name': tool_info.get('server_name', ''),
                        'mcp_tool_name': tool_info.get('original_name', tool_name),
                        'parameters_schema': tool_info.get('tool_data', {}).get('parameters_json_schema', {}),
                        'capabilities': self._infer_capabilities(tool_name, tool_info.get('description', '')),
                        'categories': self._infer_mcp_categories(tool_name, tool_info.get('description', ''))
                    }
                    
                    tools.append(tool_data)
                    logger.debug(f"Added MCP tool: {tool_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process MCP tool {tool_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error during MCP tool discovery: {e}")
        
        return tools
    
    def _process_mcp_tool(self, tool_data: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Process MCP tool data into standardized format."""
        try:
            name = tool_data.get("name", "unknown")
            description = tool_data.get("description", "")
            input_schema = tool_data.get("inputSchema", {})
            
            # Extract parameters from input schema
            parameters_schema = self._process_mcp_schema(input_schema)
            
            # Infer categories from tool name and description
            categories = self._infer_mcp_categories(name, description)
            
            # Infer capabilities
            capabilities = self._infer_capabilities(name, description)
            
            return {
                "name": name,
                "type": "mcp",
                "description": description,
                "server_name": server_name,
                "mcp_server_name": server_name,
                "mcp_tool_name": name,
                "parameters_schema": parameters_schema,
                "categories": categories,
                "capabilities": capabilities,
                "context_signature": "RunContext[Dict]"
            }
            
        except Exception as e:
            logger.warning(f"Failed to process MCP tool {tool_data}: {e}")
            return None
    
    def _process_mcp_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP input schema into our format."""
        if not input_schema:
            return {"type": "object", "properties": {}, "required": []}
        
        # MCP schemas are typically JSON Schema format
        return input_schema
    
    def _infer_mcp_categories(self, name: str, description: str) -> List[str]:
        """Infer categories for MCP tools."""
        text = f"{name} {description}".lower()
        categories = []
        
        category_keywords = {
            "git": ["version_control", "development"],
            "file": ["file_operations", "storage"],
            "memory": ["memory", "storage"],
            "linear": ["project_management", "productivity"],
            "sqlite": ["database", "storage"],
            "postgres": ["database", "storage"],
            "search": ["search", "retrieval"],
            "browser": ["web", "automation"],
            "wikipedia": ["knowledge", "retrieval"],
            "weather": ["data", "api"],
            "time": ["utility", "time"],
            "date": ["utility", "time"]
        }
        
        for keyword, cats in category_keywords.items():
            if keyword in text:
                categories.extend(cats)
        
        # Default category if none found
        if not categories:
            categories = ["mcp", "external"]
        
        return list(set(categories))
    
    async def sync_discovered_tools_to_database(self, discovered: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Synchronize already discovered tools with database."""
        created_count = 0
        updated_count = 0
        error_count = 0
        
        all_tools = discovered["code_tools"] + discovered["mcp_tools"]
        
        for tool_data in all_tools:
            try:
                existing_tool = get_tool_by_name(tool_data["name"])
                
                if existing_tool:
                    # Tool exists, could update if needed
                    updated_count += 1
                else:
                    # Create new tool
                    tool_create = ToolCreate(
                        name=tool_data["name"],
                        type=tool_data["type"],
                        description=tool_data["description"],
                        module_path=tool_data.get("module_path"),
                        function_name=tool_data.get("function_name"),
                        mcp_server_name=tool_data.get("mcp_server_name"),
                        mcp_tool_name=tool_data.get("mcp_tool_name"),
                        parameters_schema=tool_data.get("parameters_schema"),
                        capabilities=tool_data.get("capabilities", []),
                        categories=tool_data.get("categories", [])
                    )
                    
                    created_tool = create_tool(tool_create)
                    if created_tool:
                        created_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                logger.error(f"Error syncing tool {tool_data['name']}: {e}")
                error_count += 1
        
        logger.info(f"Tool sync complete: {created_count} created, {updated_count} updated, {error_count} errors")
        
        return {
            "created": created_count,
            "updated": updated_count,
            "errors": error_count,
            "total": len(all_tools)
        }
        
    async def sync_tools_to_database(self) -> Dict[str, int]:
        """Synchronize discovered tools with database."""
        discovered = await self.discover_all_tools(force_refresh=True)
        return await self.sync_discovered_tools_to_database(discovered)


# Global instance
_tool_discovery_service = None


def get_tool_discovery_service() -> ToolDiscoveryService:
    """Get the global tool discovery service instance."""
    global _tool_discovery_service
    if _tool_discovery_service is None:
        _tool_discovery_service = ToolDiscoveryService()
    return _tool_discovery_service