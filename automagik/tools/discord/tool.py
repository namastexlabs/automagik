"""Discord tool implementation.

This module provides the core functionality for Discord tools.
"""
import logging
from typing import Dict, Any
from pydantic_ai import RunContext

from automagik.tools.discord.provider import DiscordProvider

logger = logging.getLogger(__name__)

# Tool descriptions
def get_list_guilds_description() -> str:
    """Get description for the list_guilds_and_channels function."""
    return "Lists all guilds and channels the bot has access to."

def get_guild_info_description() -> str:
    """Get description for the get_guild_info function."""
    return "Retrieves information about a specific guild."

def get_fetch_messages_description() -> str:
    """Get description for the fetch_messages function."""
    return "Fetches messages from a specific channel."

def get_send_message_description() -> str:
    """Get description for the send_message function."""
    return "Sends a message to a specific channel."

async def list_guilds_and_channels(
    ctx: RunContext[Dict],
    bot_token: str = None
) -> Dict[str, Any]:
    """
    Lists all guilds and channels the bot has access to.

    Args:
        ctx: The run context
        bot_token: Discord bot token (optional, will use environment variable if not provided)
    
    Returns:
        Dict with the guild and channel information
    """
    try:
        logger.info("Listing Discord guilds and channels")
        logger.debug(f"Run context: {ctx}")
        logger.debug(f"Using bot token: {'Provided' if bot_token else 'From environment'}")
        
        async with DiscordProvider(bot_token) as discord_client:
            logger.debug("Discord client initialized successfully")
            result = await discord_client.list_guilds_and_channels()
            logger.debug(f"Retrieved {len(result.get('guilds', []))} guilds")
            return result
    except Exception as e:
        logger.error(f"Error listing Discord guilds: {str(e)}")
        logger.debug(f"Full exception details: {e}", exc_info=True)
        return {"success": False, "error": f"Error: {str(e)}", "guilds": []}

async def get_guild_info(
    ctx: RunContext[Dict],
    bot_token: str,
    guild_id: str
) -> Dict[str, Any]:
    """
    Retrieves information about a specific guild.
    
    Args:
        ctx: The run context
        bot_token: Discord bot token
        guild_id: ID of the guild to retrieve information for
        
    Returns:
        Dict with the guild information
    """
    try:
        logger.info(f"Getting information for Discord guild ID: {guild_id}")
        
        async with DiscordProvider(bot_token) as discord_client:
            return await discord_client.get_guild_info(guild_id)
    except Exception as e:
        logger.error(f"Error getting Discord guild info: {str(e)}")
        return {"success": False, "error": f"Error: {str(e)}"}

async def fetch_messages(
    ctx: RunContext[Dict],
    bot_token: str,
    channel_id: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Fetches messages from a specific channel.
    
    Args:
        ctx: The run context
        bot_token: Discord bot token
        channel_id: ID of the channel to fetch messages from
        limit: Maximum number of messages to retrieve
        
    Returns:
        Dict with the fetched messages
    """
    try:
        logger.info(f"Fetching messages from Discord channel ID: {channel_id}, limit: {limit}")
        
        async with DiscordProvider(bot_token) as discord_client:
            return await discord_client.fetch_messages(channel_id, limit)
    except Exception as e:
        logger.error(f"Error fetching Discord messages: {str(e)}")
        return {"success": False, "error": f"Error: {str(e)}", "messages": []}

async def send_message(
    ctx: RunContext[Dict],
    bot_token: str,
    channel_id: str,
    content: str
) -> Dict[str, Any]:
    """
    Sends a message to a specific channel.
    
    Args:
        ctx: The run context
        bot_token: Discord bot token
        channel_id: ID of the channel to send the message to
        content: Content of the message to send
        
    Returns:
        Dict with information about the sent message
    """
    try:
        logger.info(f"Sending message to Discord channel ID: {channel_id}")
        
        async with DiscordProvider(bot_token) as discord_client:
            return await discord_client.send_message(channel_id, content)
    except Exception as e:
        logger.error(f"Error sending Discord message: {str(e)}")
        return {"success": False, "error": f"Error: {str(e)}"} 