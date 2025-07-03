"""Discord tools for Automagik Agents.

Provides tools for interacting with Discord via API.
"""

# Import from tool module
from automagik.tools.discord.tool import (
    list_guilds_and_channels,
    get_guild_info,
    fetch_messages,
    send_message,
    get_list_guilds_description,
    get_guild_info_description,
    get_fetch_messages_description,
    get_send_message_description
)

# Import schema models
from automagik.tools.discord.schema import (
    DiscordChannel,
    DiscordGuild,
    DiscordMessage,
    DiscordResponse,
    ListGuildsResponse,
    GuildInfoResponse,
    FetchMessagesResponse,
    SendMessageResponse
)

# Import interface
from automagik.tools.discord.interface import (
    DiscordTools,
    discord_tools
)

# Export public API
__all__ = [
    # Tool functions
    'list_guilds_and_channels',
    'get_guild_info',
    'fetch_messages',
    'send_message',
    
    # Description functions
    'get_list_guilds_description',
    'get_guild_info_description',
    'get_fetch_messages_description',
    'get_send_message_description',
    
    # Schema models
    'DiscordChannel',
    'DiscordGuild',
    'DiscordMessage',
    'DiscordResponse',
    'ListGuildsResponse',
    'GuildInfoResponse',
    'FetchMessagesResponse',
    'SendMessageResponse',
    
    # Interface
    'DiscordTools',
    'discord_tools'
] 