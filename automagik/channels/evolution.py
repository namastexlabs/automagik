"""Evolution/WhatsApp channel handler implementation.

This module handles WhatsApp-specific message processing via the Evolution API,
including user identification, contact management, and message formatting.
"""

import logging
from typing import Dict, List, Optional, Any, Union

from automagik.channels.base import ChannelHandler
from automagik.agents.common.evolution import EvolutionMessagePayload
from automagik.tools.evolution.tool import (
    send_message,
    send_audio,
    send_reaction,
    get_chat_history
)

logger = logging.getLogger(__name__)


class EvolutionHandler(ChannelHandler):
    """Handler for Evolution/WhatsApp messages.
    
    This handler processes WhatsApp messages received through the Evolution API,
    extracting user information, managing contacts, and formatting responses.
    """
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize the Evolution handler.
        
        Args:
            context: Optional context with Evolution configuration
        """
        super().__init__(context)
        self._evolution_instance = context.get("evolution_instance") if context else None
        
    async def preprocess_in(self, 
                          input_text: str, 
                          channel_payload: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Preprocess incoming WhatsApp message.
        
        Extracts user information from Evolution payload and enriches context.
        
        Args:
            input_text: The message text
            channel_payload: Evolution webhook payload
            context: Optional existing context
            
        Returns:
            Processed data with user information and updated context
        """
        context = context or {}
        metadata = {}
        
        try:
            # Convert to EvolutionMessagePayload
            evolution_payload = EvolutionMessagePayload(**channel_payload)
            
            # Extract user information
            user_number = evolution_payload.get_user_number()
            user_name = evolution_payload.get_user_name()
            user_jid = evolution_payload.get_user_jid()
            is_group = evolution_payload.is_group_chat()
            
            # Update context with WhatsApp-specific data
            context.update({
                "evolution_payload": evolution_payload,
                "whatsapp_user_number": user_number,
                "whatsapp_user_name": user_name,
                "whatsapp_user_jid": user_jid,
                "whatsapp_is_group": is_group,
                "channel_type": "whatsapp",
                # Backward compatibility mappings
                "user_phone_number": user_number,
                "user_name": user_name,
            })
            
            # Add group information if applicable
            if is_group:
                context["whatsapp_group_jid"] = evolution_payload.get_group_jid()
                
            # Store instance information
            if hasattr(evolution_payload.data, "instanceId"):
                context["evolution_instance"] = evolution_payload.data.instanceId
                self._evolution_instance = evolution_payload.data.instanceId
                
            # Add metadata
            metadata.update({
                "message_id": evolution_payload.data.key.id if hasattr(evolution_payload.data, "key") else None,
                "from_me": evolution_payload.data.key.fromMe if hasattr(evolution_payload.data, "key") else False,
                "timestamp": evolution_payload.data.messageTimestamp if hasattr(evolution_payload.data, "messageTimestamp") else None,
                "push_name": user_name,
                "event_type": evolution_payload.event
            })
            
            logger.info(f"Preprocessed WhatsApp message from {user_number} ({user_name})")
            
        except Exception as e:
            logger.error(f"Error preprocessing Evolution payload: {str(e)}")
            # Return original data if preprocessing fails
            return {
                "input_text": input_text,
                "context": context,
                "metadata": {"error": str(e)}
            }
            
        return {
            "input_text": input_text,
            "context": context,
            "metadata": metadata
        }
        
    async def postprocess_out(self, 
                            response: Union[str, Dict[str, Any]], 
                            context: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
        """Postprocess response for WhatsApp.
        
        Formats the response according to WhatsApp limitations and features.
        
        Args:
            response: The agent's response
            context: Optional context with channel information
            
        Returns:
            Formatted response for WhatsApp
        """
        # Handle string responses
        if isinstance(response, str):
            # WhatsApp message length limit is 4096 characters
            if len(response) > 4096:
                # Split into multiple messages if needed
                messages = []
                while response:
                    messages.append(response[:4096])
                    response = response[4096:]
                return {"messages": messages, "type": "multi_text"}
            return response
            
        # Handle structured responses
        if isinstance(response, dict):
            # Check for special response types (media, audio, etc.)
            if "type" in response:
                return response
                
            # Default: convert to text
            if "text" in response:
                return self.postprocess_out(response["text"], context)
                
        return str(response)
        
    def get_tools(self) -> List[Any]:
        """Get Evolution-specific tools.
        
        Returns:
            List of Evolution API tools for WhatsApp operations
        """
        tools = [
            send_message,
            send_audio,
            send_reaction,
            get_chat_history
        ]
        
        # Add instance-specific context to tools if available
        if self._evolution_instance:
            # Tools will use the instance from context
            pass
            
        return tools
        
    @property
    def channel_name(self) -> str:
        """Get the channel name."""
        return "whatsapp"
        
    def supports_multimodal(self) -> bool:
        """WhatsApp supports images, audio, and documents."""
        return True
        
    def get_message_limit(self) -> Optional[int]:
        """WhatsApp message length limit."""
        return 4096
        
    async def validate_payload(self, channel_payload: Dict[str, Any]) -> bool:
        """Validate Evolution webhook payload.
        
        Args:
            channel_payload: The payload to validate
            
        Returns:
            True if this appears to be an Evolution payload
        """
        # Check for Evolution-specific fields
        required_fields = ["data", "event"]
        if not all(field in channel_payload for field in required_fields):
            return False
            
        # Check for WhatsApp-specific data structure
        if "data" in channel_payload:
            data = channel_payload["data"]
            # Look for WhatsApp JID patterns
            if isinstance(data, dict) and "key" in data:
                key = data["key"]
                if isinstance(key, dict) and "remoteJid" in key:
                    remote_jid = key["remoteJid"]
                    # WhatsApp JIDs end with @s.whatsapp.net or @g.us
                    return isinstance(remote_jid, str) and (
                        remote_jid.endswith("@s.whatsapp.net") or 
                        remote_jid.endswith("@g.us")
                    )
                    
        return False 