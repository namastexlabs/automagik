"""Base interface for channel handlers.

This module defines the abstract base class for all channel handlers.
Channel handlers are responsible for:
1. Preprocessing incoming messages from specific channels (e.g., WhatsApp, Discord)
2. Postprocessing outgoing messages for channel-specific formatting
3. Providing channel-specific tools and capabilities
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class ChannelHandler(ABC):
    """Abstract base class for channel-specific message handlers.
    
    Each channel handler implements logic for preprocessing incoming messages,
    postprocessing outgoing responses, and providing channel-specific tools.
    """
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize the channel handler.
        
        Args:
            context: Optional context dictionary with channel configuration
        """
        self.context = context or {}
        self._tools = []
        
    @abstractmethod
    async def preprocess_in(self, 
                          input_text: str, 
                          channel_payload: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Preprocess incoming message from the channel.
        
        This method extracts channel-specific information from the payload,
        enriches the context, and prepares the message for agent processing.
        
        Args:
            input_text: The raw message text
            channel_payload: Channel-specific payload (e.g., Evolution webhook data)
            context: Optional existing context to update
            
        Returns:
            Dict containing:
                - input_text: Processed message text
                - context: Updated context with channel-specific data
                - metadata: Any additional metadata for processing
        """
        pass
        
    @abstractmethod
    async def postprocess_out(self, 
                            response: Union[str, Dict[str, Any]], 
                            context: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
        """Postprocess outgoing response for the channel.
        
        This method formats the agent's response according to channel requirements,
        such as message length limits, formatting rules, or special features.
        
        Args:
            response: The agent's response (text or structured data)
            context: Optional context with channel information
            
        Returns:
            Formatted response ready for the channel
        """
        pass
        
    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Get channel-specific tools.
        
        Returns a list of tools that are specific to this channel,
        such as Evolution API tools for WhatsApp, Discord API tools, etc.
        
        Returns:
            List of tool functions or tool instances
        """
        pass
        
    @property
    def channel_name(self) -> str:
        """Get the channel name.
        
        Returns:
            String identifier for the channel (e.g., "whatsapp", "discord")
        """
        return self.__class__.__name__.replace("Handler", "").lower()
        
    def supports_multimodal(self) -> bool:
        """Check if the channel supports multimodal content.
        
        Returns:
            True if the channel can handle images, audio, etc.
        """
        return False
        
    def get_message_limit(self) -> Optional[int]:
        """Get the channel's message length limit.
        
        Returns:
            Maximum message length, or None if no limit
        """
        return None
        
    async def validate_payload(self, channel_payload: Dict[str, Any]) -> bool:
        """Validate that the payload is from this channel.
        
        Args:
            channel_payload: The payload to validate
            
        Returns:
            True if the payload appears to be from this channel
        """
        return True 