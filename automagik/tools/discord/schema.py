"""Discord tool schemas.

This module defines the Pydantic models for Discord tool input and output.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

class DiscordAttachment(BaseModel):
    """Model for Discord message attachments."""
    filename: str = Field(..., description="Name of the attached file")
    url: str = Field(..., description="URL of the attachment")

class DiscordReference(BaseModel):
    """Model for Discord message references."""
    message_id: Optional[str] = Field(None, description="ID of the referenced message")
    channel_id: Optional[str] = Field(None, description="ID of the channel containing the referenced message")
    guild_id: Optional[str] = Field(None, description="ID of the guild containing the referenced message")

class DiscordMessage(BaseModel):
    """Model for Discord messages."""
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Message content")
    author: str = Field(..., description="Message author")
    timestamp: str = Field(..., description="Message timestamp")
    attachments: List[DiscordAttachment] = Field(default_factory=list, description="Message attachments")
    embeds: List[Dict[str, Any]] = Field(default_factory=list, description="Message embeds")
    type: str = Field(..., description="Message type")
    reference: Optional[DiscordReference] = Field(None, description="Message reference")

class DiscordChannel(BaseModel):
    """Model for Discord channels."""
    name: str = Field(..., description="Channel name")
    id: str = Field(..., description="Channel ID")
    type: str = Field(..., description="Channel type")

class DiscordGuild(BaseModel):
    """Model for Discord guilds."""
    name: str = Field(..., description="Guild name")
    id: str = Field(..., description="Guild ID")
    channels: List[DiscordChannel] = Field(default_factory=list, description="Guild channels")
    member_count: Optional[int] = Field(None, description="Number of members in the guild")

class DiscordResponse(BaseModel):
    """Base response model for Discord tools."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")

class ListGuildsResponse(DiscordResponse):
    """Response model for list_guilds_and_channels."""
    guilds: List[DiscordGuild] = Field(default_factory=list, description="List of guilds")

class GuildInfoResponse(DiscordResponse):
    """Response model for get_guild_info."""
    guild_info: Optional[DiscordGuild] = Field(None, description="Guild information")

class FetchMessagesResponse(DiscordResponse):
    """Response model for fetch_messages."""
    messages: List[DiscordMessage] = Field(default_factory=list, description="List of messages")

class SendMessageResponse(DiscordResponse):
    """Response model for send_message."""
    message: Optional[DiscordMessage] = Field(None, description="The sent message") 