from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, model_validator
from datetime import datetime


class DeviceListMetadata(BaseModel):
    senderKeyHash: str
    senderTimestamp: str
    recipientKeyHash: str
    recipientTimestamp: str


class MessageContextInfo(BaseModel):
    deviceListMetadata: DeviceListMetadata
    deviceListMetadataVersion: int


class DisappearingMode(BaseModel):
    initiator: str


class ContextInfo(BaseModel):
    expiration: Optional[int] = None
    disappearingMode: DisappearingMode
    ephemeralSettingTimestamp: str


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
        """Extract the user phone number from the payload."""
        user_number = None
        
        if not user_number and hasattr(self.data, "key") and hasattr(self.data.key, "remoteJid"):
            remote_jid = self.data.key.remoteJid
            if remote_jid and "@" in remote_jid:
                user_number = remote_jid.split("@")[0]
                
        # Remove country code if present
        if user_number and user_number.startswith("55"):
            user_number = user_number[2:]
            
        return user_number
    
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
