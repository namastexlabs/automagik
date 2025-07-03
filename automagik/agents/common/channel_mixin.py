"""Mixin for adding channel handler support to agents.

This mixin provides methods for integrating channel handlers into agent
processing, allowing agents to automatically handle channel-specific
preprocessing and postprocessing.
"""

import logging
from typing import Dict, Optional, Any, Union

from automagik.channels import get_channel_handler
from automagik.channels.base import ChannelHandler

logger = logging.getLogger(__name__)


class ChannelHandlerMixin:
    """Mixin that adds channel handler support to agents.
    
    This mixin should be used with AutomagikAgent subclasses to provide
    automatic channel detection and message processing.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        self._channel_handler: Optional[ChannelHandler] = None
        
    async def _get_channel_handler(self, channel_payload: Optional[Dict[str, Any]] = None) -> Optional[ChannelHandler]:
        """Get or create the channel handler.
        
        Args:
            channel_payload: Optional channel payload for detection
            
        Returns:
            Channel handler instance or None
        """
        if self._channel_handler:
            return self._channel_handler
            
        if channel_payload:
            # Pass agent context to channel handler
            handler_context = getattr(self, 'context', {})
            self._channel_handler = await get_channel_handler(
                channel_payload=channel_payload,
                context=handler_context
            )
            
        return self._channel_handler
        
    async def _preprocess_with_channel(self, 
                                     input_text: str,
                                     channel_payload: Optional[Dict[str, Any]] = None,
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Preprocess input using channel handler if available.
        
        Args:
            input_text: Raw input text
            channel_payload: Optional channel payload
            context: Optional existing context
            
        Returns:
            Preprocessed data with updated context
        """
        # Get channel handler
        handler = await self._get_channel_handler(channel_payload)
        
        if handler and channel_payload:
            try:
                # Use channel handler preprocessing
                result = await handler.preprocess_in(input_text, channel_payload, context)
                logger.debug(f"Preprocessed message with {handler.channel_name} handler")
                return result
            except Exception as e:
                logger.error(f"Error in channel preprocessing: {str(e)}")
                
        # Fallback: return original data
        return {
            "input_text": input_text,
            "context": context or {},
            "metadata": {}
        }
        
    async def _postprocess_with_channel(self,
                                      response: Union[str, Dict[str, Any]],
                                      context: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
        """Postprocess response using channel handler if available.
        
        Args:
            response: Agent response
            context: Optional context
            
        Returns:
            Postprocessed response
        """
        if self._channel_handler:
            try:
                # Use channel handler postprocessing
                result = await self._channel_handler.postprocess_out(response, context)
                logger.debug(f"Postprocessed response with {self._channel_handler.channel_name} handler")
                return result
            except Exception as e:
                logger.error(f"Error in channel postprocessing: {str(e)}")
                
        # Fallback: return original response
        return response
        
    def _get_channel_tools(self) -> list:
        """Get channel-specific tools if handler is available.
        
        Returns:
            List of channel-specific tools
        """
        if self._channel_handler:
            try:
                tools = self._channel_handler.get_tools()
                logger.debug(f"Retrieved {len(tools)} tools from {self._channel_handler.channel_name} handler")
                return tools
            except Exception as e:
                logger.error(f"Error getting channel tools: {str(e)}")
                
        return []
        
    def _update_context_with_channel_data(self, context: Dict[str, Any], channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update context with channel-specific data.
        
        Args:
            context: Existing context
            channel_data: Channel-specific data to merge
            
        Returns:
            Updated context
        """
        # Create a copy to avoid modifying the original
        updated_context = context.copy()
        updated_context.update(channel_data)
        
        # Store channel handler reference if available
        if self._channel_handler:
            updated_context["channel_handler"] = self._channel_handler.channel_name
            
        return updated_context 