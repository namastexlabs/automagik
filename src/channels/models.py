"""Channel models for Evolution and other messaging platforms.

This module contains shared models for channel payload processing,
moved from agent-specific locations to centralized channel handling.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, model_validator
from datetime import datetime


class DeviceListMetadata(BaseModel):
    senderKeyHash: Optional[str] = None
    senderTimestamp: Optional[str] = None
    recipientKeyHash: Optional[str] = None
    recipientTimestamp: Optional[str] = None


class MessageContextInfo(BaseModel):
    deviceListMetadata: Optional[DeviceListMetadata] = None
    deviceListMetadataVersion: Optional[int] = None


class DisappearingMode(BaseModel):
    initiator: Optional[str] = None


class ContextInfo(BaseModel):
    expiration: Optional[int] = None
    disappearingMode: Optional[DisappearingMode] = None
    ephemeralSettingTimestamp: Optional[str] = None


class MessageKey(BaseModel):
    id: str
    fromMe: bool
    remoteJid: str


class Message(BaseModel):
    conversation: Optional[str] = None
    messageContextInfo: Optional[MessageContextInfo] = None


class WhatsAppData(BaseModel):
    key: MessageKey
    source: Optional[str] = None
    status: Optional[str] = None
    message: Optional[Message] = None
    pushName: Optional[str] = None
    instanceId: Optional[str] = None
    contextInfo: Optional[ContextInfo] = None
    messageType: Optional[str] = None
    messageTimestamp: Optional[int] = None


class EvolutionMessagePayload(BaseModel):
    """Evolution API message payload model.
    
    Centralized model for WhatsApp/Evolution message processing,
    moved from Stan agent to shared channel models.
    """
    data: WhatsAppData
    event: str
    apikey: Optional[str] = None
    sender: Optional[str] = None
    instance: Optional[str] = None
    date_time: Optional[datetime] = None
    server_url: Optional[str] = None
    destination: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def normalize_payload(cls, data: Any) -> Any:
        """Normalize different payload formats into a consistent structure."""
        if not isinstance(data, dict):
             # If it's not a dict (e.g., already a model instance), return it as is
             return data
            
        # Create a normalized copy of the input data dictionary
        normalized = dict(data)
        
        # Ensure data exists
        if "data" not in normalized:
            normalized["data"] = {}
            
        # Ensure data.key exists
        if "key" not in normalized["data"]:
            normalized["data"]["key"] = {}
            
        # Ensure event exists
        if "event" not in normalized:
            normalized["event"] = "unknown"
            
        return normalized
    
    def get_user_number(self) -> Optional[str]:
        """Extract the user phone number (stripping suffix and prefix) from the payload."""
        user_number: Optional[str] = None

        # In direct chats the remoteJid is the user's JID (number@s.whatsapp.net)
        # In group chats remoteJid ends with "@g.us" and the actual sender is in
        # data.key.participant (number@s.whatsapp.net)

        remote_jid: Optional[str] = None
        participant_jid: Optional[str] = None

        if hasattr(self.data, "key"):
            remote_jid = getattr(self.data.key, "remoteJid", None)
            participant_jid = getattr(self.data.key, "participant", None)

        # Decide which JID represents the user (sender)
        chosen_jid = participant_jid if (remote_jid and remote_jid.endswith("@g.us")) else remote_jid

        if chosen_jid and "@" in chosen_jid:
            user_number = chosen_jid.split("@")[0]

        # Keep the full phone number including country code for consistency
        # This ensures session IDs are consistent across different parts of the system
        return user_number

    def get_user_jid(self) -> Optional[str]:
        """Extract the full user JID (number@s.whatsapp.net) from the payload."""
        if not hasattr(self.data, "key"):
            return None

        remote_jid = getattr(self.data.key, "remoteJid", None)
        participant_jid = getattr(self.data.key, "participant", None)

        # If remote_jid is a group, return participant_jid; else remote_jid
        if remote_jid and remote_jid.endswith("@g.us") and participant_jid:
            return participant_jid

        return remote_jid

    def is_group_chat(self) -> bool:
        """Return True if the message originated from a WhatsApp group chat."""
        if hasattr(self.data, "key") and hasattr(self.data.key, "remoteJid"):
            remote_jid = self.data.key.remoteJid or ""
            return remote_jid.endswith("@g.us")
        return False

    def get_group_jid(self) -> Optional[str]:
        """Return the group JID (identifier@g.us) if this is a group chat."""
        if self.is_group_chat():
            return getattr(self.data.key, "remoteJid", None)
        return None

    def get_user_name(self) -> Optional[str]:
        """Extract the user name from the payload."""
        # Try to get from data.pushName
        if hasattr(self.data, "pushName") and self.data.pushName:
            return self.data.pushName
        return None
        
    @property
    def expiration(self) -> int:
        try:
            return self.data.contextInfo.expiration
        except AttributeError:
            return 0
    
    @property
    def disappearing_mode_initiator(self) -> Optional[str]:
        try:
            return self.data.contextInfo.disappearingMode.initiator
        except AttributeError:
            return None
    
    @property
    def ephemeral_setting_timestamp(self) -> str:
        try:
            return self.data.contextInfo.ephemeralSettingTimestamp
        except AttributeError:
            return "0"
    
    @property
    def device_list_metadata(self) -> Optional[Dict[str, str]]:
        try:
            return self.data.message.messageContextInfo.deviceListMetadata
        except AttributeError:
            return None
    
    @property
    def device_list_metadata_version(self) -> Optional[int]:
        try:
            return self.data.message.messageContextInfo.deviceListMetadataVersion
        except AttributeError:
            return None