"""Channel handler registry for automatic channel detection and handler selection.

This module provides a registry system for channel handlers, allowing automatic
detection of the appropriate handler based on message payloads.
"""

import logging
from typing import Dict, Optional, Type, Any

from automagik.channels.base import ChannelHandler
from automagik.channels.evolution import EvolutionHandler

logger = logging.getLogger(__name__)


class ChannelRegistry:
    """Registry for channel handlers.
    
    Manages registration and retrieval of channel handlers based on
    channel type or automatic detection from payloads.
    """
    
    def __init__(self):
        """Initialize the channel registry."""
        self._handlers: Dict[str, Type[ChannelHandler]] = {}
        self._register_default_handlers()
        
    def _register_default_handlers(self):
        """Register built-in channel handlers."""
        self.register("whatsapp", EvolutionHandler)
        self.register("evolution", EvolutionHandler)  # Alias
        
    def register(self, channel_name: str, handler_class: Type[ChannelHandler]):
        """Register a channel handler.
        
        Args:
            channel_name: Name of the channel (e.g., "whatsapp", "discord")
            handler_class: The handler class to register
        """
        if not issubclass(handler_class, ChannelHandler):
            raise ValueError(f"{handler_class} must be a subclass of ChannelHandler")
            
        self._handlers[channel_name.lower()] = handler_class
        logger.info(f"Registered channel handler for '{channel_name}'")
        
    def get_handler(self, channel_name: str, context: Optional[Dict[str, Any]] = None) -> Optional[ChannelHandler]:
        """Get a channel handler by name.
        
        Args:
            channel_name: Name of the channel
            context: Optional context for handler initialization
            
        Returns:
            Initialized channel handler or None if not found
        """
        handler_class = self._handlers.get(channel_name.lower())
        if handler_class:
            return handler_class(context)
        return None
        
    async def detect_channel(self, channel_payload: Dict[str, Any]) -> Optional[str]:
        """Detect the channel type from a payload.
        
        Args:
            channel_payload: The payload to analyze
            
        Returns:
            Detected channel name or None
        """
        if not channel_payload:
            return None
            
        # Try each registered handler's validation
        for channel_name, handler_class in self._handlers.items():
            try:
                handler = handler_class()
                if await handler.validate_payload(channel_payload):
                    logger.info(f"Detected channel type: {channel_name}")
                    return channel_name
            except Exception as e:
                logger.debug(f"Channel detection failed for {channel_name}: {str(e)}")
                continue
                
        # Fallback detection based on payload structure
        # Evolution/WhatsApp specific
        if "data" in channel_payload and "event" in channel_payload:
            data = channel_payload.get("data", {})
            if isinstance(data, dict) and "key" in data:
                key = data.get("key", {})
                if isinstance(key, dict) and "remoteJid" in key:
                    remote_jid = key.get("remoteJid", "")
                    if remote_jid.endswith("@s.whatsapp.net") or remote_jid.endswith("@g.us"):
                        logger.info("Detected WhatsApp channel from payload structure")
                        return "whatsapp"
                        
        return None
        
    async def get_handler_for_payload(self, 
                                    channel_payload: Dict[str, Any], 
                                    context: Optional[Dict[str, Any]] = None) -> Optional[ChannelHandler]:
        """Get the appropriate handler for a payload.
        
        Args:
            channel_payload: The payload to process
            context: Optional context for handler initialization
            
        Returns:
            Initialized channel handler or None
        """
        channel_name = await self.detect_channel(channel_payload)
        if channel_name:
            return self.get_handler(channel_name, context)
        return None


# Global registry instance
_registry = ChannelRegistry()


def get_channel_registry() -> ChannelRegistry:
    """Get the global channel registry instance.
    
    Returns:
        The global ChannelRegistry instance
    """
    return _registry


async def get_channel_handler(channel_payload: Optional[Dict[str, Any]] = None, 
                            channel_name: Optional[str] = None,
                            context: Optional[Dict[str, Any]] = None) -> Optional[ChannelHandler]:
    """Get a channel handler by name or auto-detect from payload.
    
    Args:
        channel_payload: Optional payload for auto-detection
        channel_name: Optional explicit channel name
        context: Optional context for handler initialization
        
    Returns:
        Initialized channel handler or None
    """
    registry = get_channel_registry()
    
    # If channel name is provided, use it
    if channel_name:
        return registry.get_handler(channel_name, context)
        
    # Otherwise try to detect from payload
    if channel_payload:
        return await registry.get_handler_for_payload(channel_payload, context)
        
    return None 