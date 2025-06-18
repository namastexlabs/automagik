"""Startup services for the automagik agents platform."""

import logging
import asyncio
from typing import Optional

from src.services.tool_discovery import get_tool_discovery_service

logger = logging.getLogger(__name__)


async def initialize_tools() -> None:
    """Initialize tools by discovering and syncing them to database."""
    try:
        logger.info("🔧 Starting tool discovery and initialization...")
        
        discovery_service = get_tool_discovery_service()
        
        # Discover all available tools
        discovered = await discovery_service.discover_all_tools(force_refresh=True)
        
        # Sync tools to database
        sync_stats = await discovery_service.sync_tools_to_database()
        
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
        # Don't raise exception - let the app start even if tool discovery fails
        

async def initialize_mcp_servers() -> None:
    """Initialize MCP servers from configuration."""
    try:
        logger.info("🔌 Initializing MCP servers...")
        
        # Import here to avoid circular imports
        from src.mcp.client_manager import get_mcp_client_manager
        from src.db.repository.mcp import list_mcp_configs
        
        mcp_manager = get_mcp_client_manager()
        if not mcp_manager:
            logger.warning("⚠️  MCP client manager not available")
            return
            
        # Get MCP configurations from database
        mcp_configs = list_mcp_configs()
        
        if not mcp_configs:
            logger.info("📋 No MCP server configurations found")
            return
            
        logger.info(f"🔗 Found {len(mcp_configs)} MCP server configurations")
        
        # Initialize each server
        initialized_count = 0
        for config in mcp_configs:
            try:
                # Add server to manager (this should initialize the connection)
                await mcp_manager.add_server(config.name, config.config)
                initialized_count += 1
                logger.info(f"   ✅ Initialized MCP server: {config.name}")
                
            except Exception as e:
                logger.warning(f"   ❌ Failed to initialize MCP server {config.name}: {e}")
        
        logger.info(f"✅ MCP server initialization complete: {initialized_count}/{len(mcp_configs)} servers")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP servers: {e}")


async def startup_initialization() -> None:
    """Run all startup initialization tasks."""
    logger.info("🚀 Starting platform initialization...")
    
    # Initialize MCP servers first
    await initialize_mcp_servers()
    
    # Then discover and initialize tools (depends on MCP servers)
    await initialize_tools()
    
    logger.info("✅ Platform initialization complete!")


def run_startup_tasks() -> None:
    """Run startup tasks synchronously (for use in lifespan context)."""
    try:
        # Run async initialization
        asyncio.create_task(startup_initialization())
        logger.info("🔄 Startup tasks queued for execution")
        
    except Exception as e:
        logger.error(f"❌ Failed to queue startup tasks: {e}")