"""Discord tools interface.

This module provides a compatibility layer for Discord tools.
"""
import logging
from typing import List, Dict, Any
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from .tool import (
    list_guilds_and_channels,
    get_guild_info,
    fetch_messages,
    send_message,
    get_list_guilds_description,
    get_guild_info_description,
    get_fetch_messages_description,
    get_send_message_description
)

logger = logging.getLogger(__name__)

class DiscordTools:
    """Discord tools interface for compatibility with old code."""
    
    def __init__(self, bot_token: str):
        """Initialize Discord tools with a bot token.
        
        Args:
            bot_token: Discord bot token
        """
        self.bot_token = bot_token
    
    async def list_guilds_and_channels(self, ctx: RunContext[Dict]) -> Dict[str, Any]:
        """Lists all guilds and channels the bot has access to.
        
        Args:
            ctx: The run context
            
        Returns:
            Dict with the guild and channel information
        """
        return await list_guilds_and_channels(ctx, self.bot_token)
    
    async def get_guild_info(self, ctx: RunContext[Dict], guild_id: str) -> Dict[str, Any]:
        """Retrieves information about a specific guild.
        
        Args:
            ctx: The run context
            guild_id: ID of the guild to retrieve information for
            
        Returns:
            Dict with the guild information
        """
        return await get_guild_info(ctx, self.bot_token, guild_id)
    
    async def fetch_messages(self, ctx: RunContext[Dict], channel_id: str, limit: int = 100) -> Dict[str, Any]:
        """Fetches messages from a specific channel.
        
        Args:
            ctx: The run context
            channel_id: ID of the channel to fetch messages from
            limit: Maximum number of messages to retrieve
            
        Returns:
            Dict with the fetched messages
        """
        return await fetch_messages(ctx, self.bot_token, channel_id, limit)
    
    async def send_message(self, ctx: RunContext[Dict], channel_id: str, content: str) -> Dict[str, Any]:
        """Sends a message to a specific channel.
        
        Args:
            ctx: The run context
            channel_id: ID of the channel to send the message to
            content: Content of the message to send
            
        Returns:
            Dict with information about the sent message
        """
        return await send_message(ctx, self.bot_token, channel_id, content)
    
    @property
    def tools(self) -> List:
        """Returns the list of available tool functions."""
        return [
            self.list_guilds_and_channels,
            self.get_guild_info,
            self.fetch_messages,
            self.send_message
        ]

# Create Discord tool instances
discord_list_guilds_tool = Tool(
    name="discord_list_guilds",
    description=get_list_guilds_description(),
    function=list_guilds_and_channels
)

discord_guild_info_tool = Tool(
    name="discord_guild_info",
    description=get_guild_info_description(),
    function=get_guild_info
)

discord_fetch_messages_tool = Tool(
    name="discord_fetch_messages",
    description=get_fetch_messages_description(),
    function=fetch_messages
)

discord_send_message_tool = Tool(
    name="discord_send_message",
    description=get_send_message_description(),
    function=send_message
)

# Group all Discord tools
discord_tools = [
    discord_list_guilds_tool,
    discord_guild_info_tool,
    discord_fetch_messages_tool,
    discord_send_message_tool
] 