"""Gmail tools interface.

This module provides a compatibility layer for Gmail API tools.
"""
import logging
import os
from typing import List, Dict, Any, Optional

from pydantic_ai.tools import Tool

from .tool import (
    send_email,
    get_send_email_description
)
from .provider import GmailProvider
from .schema import SendEmailInput

logger = logging.getLogger(__name__)

class GmailTools:
    """Tools for interacting with Gmail API."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """Initialize with OAuth credentials path and token path.
        
        Args:
            credentials_path: Path to OAuth credentials JSON file
            token_path: Path to OAuth token file
        """
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_CREDENTIAL_FILE')
        self.token_path = token_path or os.path.join('credentials', 'gmail_token.json')
        self.provider = GmailProvider(credentials_path=self.credentials_path, token_path=self.token_path)
        logger.info(f"Initialized GmailTools with credentials path: {self.credentials_path}")

    def get_tools(self) -> List[Any]:
        """Get tools for the agent."""
        return []

    async def send_email(self, to: str, subject: str, message: str, cc: Optional[List[str]] = None, 
                         extra_content: Optional[str] = None) -> Dict[str, Any]:
        """Send an email via Gmail API.

        Args:
            to: Email address of the recipient
            subject: Subject of the email
            message: Content of the email
            cc: List of email addresses to CC
            extra_content: Additional content to append to the email message

        Returns:
            Dictionary with the result of the operation
        """
        # Create input object
        input_data = {
            "to": to,
            "subject": subject,
            "message": message
        }
        
        if cc:
            input_data["cc"] = cc
            
        if extra_content:
            input_data["extra_content"] = extra_content
        
        email_input = SendEmailInput(**input_data)
        
        # Use the provider to send the email
        result = await self.provider.send_email(email_input)
        
        return result.dict()

# Create Gmail tool instances
gmail_send_email_tool = Tool(
    name="gmail_send_email",
    description=get_send_email_description(),
    function=send_email
)

# Group all Gmail tools
gmail_tools = [
    gmail_send_email_tool
] 