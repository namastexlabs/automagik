"""Discord API provider.

This module provides the API client implementation for interacting with Discord.
"""
import logging
import os
from typing import Optional, Dict, Any
import discord
import asyncio
from functools import wraps

from automagik.tools.discord.schema import (
    ListGuildsResponse, GuildInfoResponse, FetchMessagesResponse, SendMessageResponse
)

logger = logging.getLogger(__name__)

def validate_discord_response(func):
    """Decorator to validate Discord API response.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with validation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if result is None:
            logger.error(f"Discord API call {func.__name__} returned None")
            raise ValueError(f"Discord API call {func.__name__} returned None")
        return result
    return wrapper

def handle_discord_error(func):
    """Decorator to handle Discord API errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except discord.errors.DiscordException as e:
            logger.error(f"Discord API error in {func.__name__}: {str(e)}")
            # Return an error response that matches our schema
            error_type = type(e).__name__
            error_msg = str(e)
            return {"success": False, "error": f"{error_type}: {error_msg}"}
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return {"success": False, "error": f"Error: {str(e)}"}
    return wrapper

class DiscordProvider:
    """Client for interacting with Discord API.
    
    This class provides a high-level interface for Discord API operations.
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """Initialize the Discord API client.
        
        Args:
            bot_token: Discord bot token (optional, defaults to DISCORD_BOT_TOKEN env var)
        """
        self.bot_token = bot_token or os.environ.get("DISCORD_BOT_TOKEN")
        if not self.bot_token:
            logger.warning("Discord bot token not provided and not found in environment variables")
            
        self.client: Optional[discord.Client] = None
        self.ready_event = asyncio.Event()
        
    async def __aenter__(self):
        """Start Discord client when entering context."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close Discord client when exiting context."""
        if self.client:
            await self.client.close()
            
    async def initialize(self):
        """Initialize the Discord client."""
        if not self.bot_token:
            raise ValueError("Discord bot token is required")
            
        if self.client is not None:
            return
            
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self.ready_event = asyncio.Event()
        
        @self.client.event
        async def on_ready():
            self.ready_event.set()
            
        # Start the client
        await self.client.login(self.bot_token)
        self.client_task = asyncio.create_task(self.client.connect())
        
        # Wait for client to be ready
        await self.ready_event.wait()
        # Short delay to ensure connection stability and guild population
        await asyncio.sleep(1)
        
    @handle_discord_error
    @validate_discord_response
    async def list_guilds_and_channels(self) -> Dict[str, Any]:
        """Lists all guilds and channels the bot has access to.
        
        Returns:
            Dict with guild and channel information
        """
        if not self.client:
            await self.initialize()
            
        guilds_info = []
        for guild in self.client.guilds:
            channels_info = [
                {"name": channel.name, "id": str(channel.id), "type": str(channel.type)}
                for channel in guild.channels
            ]
            guilds_info.append({
                "name": guild.name,
                "id": str(guild.id),
                "channels": channels_info
            })
        
        response = ListGuildsResponse(
            success=True,
            guilds=guilds_info
        )
        return response.model_dump()
    
    @handle_discord_error
    @validate_discord_response
    async def get_guild_info(self, guild_id: str) -> Dict[str, Any]:
        """Retrieves information about a specific guild.
        
        Args:
            guild_id: ID of the guild to retrieve information for
            
        Returns:
            Dict with the guild information
        """
        if not self.client:
            await self.initialize()
            
        guild = self.client.get_guild(int(guild_id))
        if guild:
            guild_info = {
                "name": guild.name,
                "id": str(guild.id),
                "member_count": guild.member_count,
                "channels": [
                    {"name": channel.name, "id": str(channel.id), "type": str(channel.type)} 
                    for channel in guild.channels
                ]
            }
            response = GuildInfoResponse(success=True, guild_info=guild_info)
        else:
            response = GuildInfoResponse(success=False, error=f"Guild with ID {guild_id} not found.")
            
        return response.model_dump()
    
    @handle_discord_error
    @validate_discord_response
    async def fetch_messages(self, channel_id: str, limit: int = 100) -> Dict[str, Any]:
        """Fetches messages from a specific channel.
        
        Args:
            channel_id: ID of the channel to fetch messages from
            limit: Maximum number of messages to retrieve
            
        Returns:
            Dict with the fetched messages
        """
        if not self.client:
            await self.initialize()
            
        channel = self.client.get_channel(int(channel_id))
        if isinstance(channel, discord.TextChannel):
            messages = []
            async for msg in channel.history(limit=limit):
                messages.append(msg)
                
            message_data = [
                {
                    "id": str(msg.id),
                    "content": msg.content,
                    "author": str(msg.author),
                    "timestamp": str(msg.created_at),
                    "attachments": [{"filename": a.filename, "url": a.url} for a in msg.attachments],
                    "embeds": [e.to_dict() for e in msg.embeds],
                    "type": str(msg.type),
                    "reference": {
                        "message_id": str(msg.reference.message_id),
                        "channel_id": str(msg.reference.channel_id),
                        "guild_id": str(msg.reference.guild_id)
                    } if msg.reference else None
                }
                for msg in messages
            ]
            
            response = FetchMessagesResponse(success=True, messages=message_data)
        else:
            response = FetchMessagesResponse(
                success=False, 
                error=f"Channel with ID {channel_id} is not a text channel or not found."
            )
            
        return response.model_dump()
    
    @handle_discord_error
    @validate_discord_response
    async def send_message(self, channel_id: str, content: str) -> Dict[str, Any]:
        """Sends a message to a specific channel.
        
        Args:
            channel_id: ID of the channel to send the message to
            content: Content of the message to send
            
        Returns:
            Dict with information about the sent message
        """
        if not self.client:
            await self.initialize()
            
        channel = self.client.get_channel(int(channel_id))
        if isinstance(channel, discord.TextChannel):
            message = await channel.send(content)
            result = {
                "id": str(message.id),
                "content": message.content,
                "author": str(message.author),
                "timestamp": str(message.created_at)
            }
            
            response = SendMessageResponse(success=True, message=result)
        else:
            response = SendMessageResponse(
                success=False, 
                error=f"Channel with ID {channel_id} is not a text channel or not found."
            )
            
        return response.model_dump() 