"""Startup services for the automagik agents platform."""

import logging
import asyncio
from typing import Optional

from automagik.services.tool_discovery import get_tool_discovery_service

logger = logging.getLogger(__name__)


async def initialize_tools() -> None:
    """Initialize tools by discovering and syncing them to database."""
    try:
        logger.info("🔧 Starting tool discovery and initialization...")
        
        discovery_service = get_tool_discovery_service()
        
        # Discover all available tools with timeout
        try:
            discovered = await asyncio.wait_for(
                discovery_service.discover_all_tools(force_refresh=True), 
                timeout=60.0  # 60 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ Tool discovery timed out, continuing with cached tools")
            discovered = {"code_tools": [], "mcp_tools": []}
        except KeyboardInterrupt:
            logger.info("⚠️ Tool discovery interrupted, continuing with minimal setup")
            discovered = {"code_tools": [], "mcp_tools": []}
        
        # Sync tools to database using already discovered tools
        sync_stats = await discovery_service.sync_discovered_tools_to_database(discovered)
        
        code_count = len(discovered.get("code_tools", []))
        mcp_count = len(discovered.get("mcp_tools", []))
        
        logger.info(f"✅ Tool initialization complete:")
        logger.info(f"   📦 Code tools discovered: {code_count}")
        logger.info(f"   🔗 MCP tools discovered: {mcp_count}")
        logger.info(f"   ➕ Tools created: {sync_stats.get('created', 0)}")
        logger.info(f"   🔄 Tools updated: {sync_stats.get('updated', 0)}")
        logger.info(f"   ❌ Errors: {sync_stats.get('errors', 0)}")
        
        if sync_stats.get('errors', 0) > 0:
            logger.warning(f"⚠️  {sync_stats['errors']} tools had errors during sync")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize tools: {e}")
        logger.info("📝 Continuing startup without full tool discovery")
        # Don't raise exception - let the app start even if tool discovery fails
        

async def sync_mcp_json_to_database() -> None:
    """Sync .mcp.json file to database configurations."""
    try:
        logger.info("📄 Syncing .mcp.json to database...")
        
        import json
        import os
        from automagik.db.repository.mcp import create_mcp_config, get_mcp_config_by_name
        from automagik.db.models import MCPConfigCreate
        
        mcp_config_path = ".mcp.json"
        if not os.path.exists(mcp_config_path):
            logger.warning(f"⚠️  {mcp_config_path} file not found")
            return
        
        # Load .mcp.json
        with open(mcp_config_path, 'r') as f:
            mcp_data = json.load(f)
        
        mcp_servers = mcp_data.get("mcpServers", {})
        if not mcp_servers:
            logger.info("📋 No MCP servers found in .mcp.json")
            return
        
        logger.info(f"🔗 Found {len(mcp_servers)} MCP servers in .mcp.json")
        
        # Sync each server to database
        synced_count = 0
        updated_count = 0
        
        for server_name, server_config in mcp_servers.items():
            try:
                # Check if config already exists
                existing_config = get_mcp_config_by_name(server_name)
                
                # Determine server type
                if "command" in server_config:
                    server_type = "stdio"
                elif "url" in server_config:
                    server_type = "sse"
                else:
                    server_type = "unknown"
                
                # Prepare config data
                config_data = {
                    "server_type": server_type,
                    "enabled": True,
                    **server_config
                }
                
                if existing_config:
                    # Update existing config
                    from automagik.db.repository.mcp import update_mcp_config_by_name
                    from automagik.db.models import MCPConfigUpdate
                    
                    update_success = update_mcp_config_by_name(
                        server_name, 
                        MCPConfigUpdate(config=config_data)
                    )
                    if update_success:
                        updated_count += 1
                        logger.info(f"   🔄 Updated MCP config: {server_name}")
                else:
                    # Create new config
                    create_data = MCPConfigCreate(
                        name=server_name,
                        config=config_data
                    )
                    
                    config_id = create_mcp_config(create_data)
                    if config_id:
                        synced_count += 1
                        logger.info(f"   ✅ Created MCP config: {server_name}")
                
            except Exception as e:
                logger.warning(f"   ❌ Failed to sync MCP server {server_name}: {e}")
        
        logger.info(f"✅ MCP sync complete: {synced_count} created, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"❌ Failed to sync .mcp.json to database: {e}")


async def initialize_mcp_servers() -> None:
    """Initialize MCP servers from database configurations."""
    try:
        logger.info("🔌 Initializing MCP servers...")
        
        # Import here to avoid circular imports
        from automagik.mcp.client import get_mcp_manager
        from automagik.db.repository.mcp import list_mcp_configs
        
        mcp_manager = await get_mcp_manager()
        if not mcp_manager:
            logger.warning("⚠️  MCP client manager not available")
            return
            
        # Get MCP configurations from database
        mcp_configs = list_mcp_configs()
        
        if not mcp_configs:
            logger.info("📋 No MCP server configurations found in database")
            return
            
        logger.info(f"🔗 Found {len(mcp_configs)} MCP server configurations in database")
        
        # The MCP manager has already loaded and started enabled servers during initialization
        # Just report the status
        server_list = mcp_manager.list_servers()
        initialized_count = len(server_list)
        
        for server_info in server_list:
            logger.info(f"   ✅ MCP server running: {server_info['name']} ({server_info['type']})")
        
        logger.info(f"✅ MCP server initialization complete: {initialized_count} servers running")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP servers: {e}")


async def startup_initialization() -> None:
    """Run all startup initialization tasks."""
    logger.info("🚀 Starting platform initialization...")
    
    # First, sync .mcp.json to database to ensure all servers are available
    await sync_mcp_json_to_database()
    
    # Then initialize MCP servers from database
    await initialize_mcp_servers()
    
    # Finally discover and initialize tools (depends on MCP servers)
    await initialize_tools()
    
    logger.info("✅ Platform initialization complete!")


# REMOVED: run_startup_tasks() function that was causing asyncio.create_task() context boundary violations
# The startup_initialization() function is called directly from main.py with proper await