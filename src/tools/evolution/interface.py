"""Evolution tools interface.

This module provides a compatibility layer for Evolution tools.
"""
import logging
from typing import List, Dict, Any
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from .tool import (
    send_message, 
    get_chat_history,
    get_send_message_description,
    get_chat_history_description
)

from .contact_tool import (
    send_business_contact,
    send_personal_contact
)

logger = logging.getLogger(__name__)

class EvolutionTools:
    """Tools for interacting with Evolution API."""

    def __init__(self, token: str):
        """Initialize with API token.
        
        Args:
            token: Evolution API token
        """
        self.token = token

    def get_tools(self) -> List[Any]:
        """Get tools for the agent."""
        return []

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """Send a message to a phone number.

        Args:
            phone: The phone number to send the message to
            message: The message content

        Returns:
            Response data from the API
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await send_message(ctx, self.token, phone, message)
        
        # Simplify the result structure for backward compatibility
        if result.get("success", False):
            return {
                "success": True,
                "message_id": result.get("message_id", "unknown"),
                "timestamp": result.get("timestamp", "")
            }
        return {
            "success": False,
            "error": result.get("error", "Unknown error")
        }

    async def get_chat_history(self, phone: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a phone number.

        Args:
            phone: The phone number to get history for
            limit: Maximum number of messages to return

        Returns:
            List of message objects
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await get_chat_history(ctx, self.token, phone, limit)
        
        # Extract the messages from the result
        if result.get("success", False) and "messages" in result:
            return result["messages"]
        return []
        
    async def send_business_contact(self, phone: str) -> Dict[str, Any]:
        """Send business contact information to a phone number.

        Args:
            phone: The phone number to send the contact to

        Returns:
            Response data from the API
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await send_business_contact(ctx, phone)
        
        return result
        
    async def send_personal_contact(self, phone: str) -> Dict[str, Any]:
        """Send personal contact information to a phone number.

        Args:
            phone: The phone number to send the contact to

        Returns:
            Response data from the API
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await send_personal_contact(ctx, phone)
        
        return result

# Create Evolution tool instances
evolution_send_message_tool = Tool(
    name="evolution_send_message",
    description=get_send_message_description(),
    function=send_message
)

evolution_get_chat_history_tool = Tool(
    name="evolution_get_chat_history",
    description=get_chat_history_description(),
    function=get_chat_history
)

evolution_send_business_contact_tool = Tool(
    name="evolution_send_business_contact",
    description="Send business contact information to a WhatsApp user.",
    function=send_business_contact
)

evolution_send_personal_contact_tool = Tool(
    name="evolution_send_personal_contact",
    description="Send personal contact information to a WhatsApp user.",
    function=send_personal_contact
)

# Group all Evolution tools
evolution_tools = [
    evolution_send_message_tool,
    evolution_get_chat_history_tool,
    evolution_send_business_contact_tool,
    evolution_send_personal_contact_tool
] 