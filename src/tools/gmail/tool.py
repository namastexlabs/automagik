"""Gmail API tool implementation.

This module provides the core functionality for Gmail API tools.
"""
import logging
import os
from typing import Dict, Any, List
from pydantic_ai import RunContext

from .schema import SendEmailInput, SendEmailResult, FetchEmailsInput, FetchEmailsResult
from .provider import GmailProvider

logger = logging.getLogger(__name__)

# Gmail credentials file
GMAIL_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIAL_FILE")


def get_send_email_description() -> str:
    """Get description for the send_email function."""
    return "Send an email via Gmail API."

def get_fetch_emails_description() -> str:
    """Get description for the fetch_emails function."""
    return "Fetch unread emails from Gmail, optionally filtered by subject."

def get_mark_emails_read_description() -> str:
    """Get description for the mark_emails_read function."""
    return "Mark emails as read by removing the UNREAD label."

async def send_email(ctx: RunContext[Dict], input: SendEmailInput) -> Dict[str, Any]:
    """Send an email via Gmail API.
    
    Args:
        ctx: The run context
        input: Email parameters
        
    Returns:
        Dict with the result of the operation
    """
    logger.info(f"Sending email to: {input.to}")
    
    try:
        # Create provider instance
        provider = GmailProvider(credentials_path=GMAIL_CREDENTIALS_PATH)
        
        # Use provider to send email
        result = await provider.send_email(input)
        
        # Return the result as a dictionary
        return result.model_dump()
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg)
        
        response = SendEmailResult(
            success=False,
            error=error_msg
        )
        return response.model_dump()

async def fetch_emails(ctx: RunContext[Dict], input: FetchEmailsInput) -> Dict[str, Any]:
    """Fetch unread emails from Gmail, optionally filtered by subject.
    
    Args:
        ctx: The run context
        input: Email fetching parameters
        
    Returns:
        Dict with the result of the operation
    """
    logger.info(f"Fetching unread emails with subject filter: {input.subject_filter}")
    
    try:
        # Create provider instance
        provider = GmailProvider(credentials_path=GMAIL_CREDENTIALS_PATH)
        
        # Use provider to fetch emails
        result = await provider.fetch_unread_emails(
            subject_filter=input.subject_filter,
            max_results=input.max_results
        )
        
        # Return the result as a dictionary
        return result.model_dump()
    except Exception as e:
        error_msg = f"Error fetching emails: {str(e)}"
        logger.error(error_msg)
        
        response = FetchEmailsResult(
            success=False,
            error=error_msg,
            emails=[]
        )
        return response.model_dump()

async def fetch_all_emails_from_thread_by_email_id(ctx: RunContext[Dict], email_id: str) -> Dict[str, Any]:
    """Fetch all emails from a thread by email ID.
    
    Args:
        ctx: The run context
        email_id: The email ID of the thread
        
    Returns:
        Dict with the result of the operation including all emails in the thread
    """
    logger.info(f"Fetching all emails from thread with email ID: {email_id}")
    
    try:
        # Create provider instance
        provider = GmailProvider(credentials_path=GMAIL_CREDENTIALS_PATH)
        
        # Use provider to fetch all emails in the thread
        result = await provider.fetch_thread_by_email_id(email_id)
        
        # Return the result as a dictionary
        return result.model_dump()
    except Exception as e:
        error_msg = f"Error fetching thread emails: {str(e)}"
        logger.error(error_msg)
        
        response = {
            "success": False,
            "error": error_msg,
            "emails": []
        }
        return response

async def mark_emails_read(ctx: RunContext[Dict], message_ids: List[str]) -> Dict[str, Any]:
    """Mark emails as read by removing the UNREAD label.
    
    Args:
        ctx: The run context
        message_ids: List of message IDs to mark as read
        
    Returns:
        Dict with the result of the operation
    """
    logger.info(f"Marking {len(message_ids)} emails as read")
    
    try:
        # Create provider instance
        provider = GmailProvider(credentials_path=GMAIL_CREDENTIALS_PATH)
        
        # Use provider to mark emails as read
        result = await provider.mark_emails_as_read(message_ids)
        
        # Return the result
        return result
    except Exception as e:
        error_msg = f"Error marking emails as read: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'marked_count': 0
        } 