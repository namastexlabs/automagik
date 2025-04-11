"""Gmail API integration tests.

This module tests Gmail API tools against the real Gmail API.
The test uses the GOOGLE_CREDENTIAL_FILE environment variable for authentication.

Example:
    python -m pytest tests/tools/gmail/test_integration.py -v
"""
import os
import pytest
import logging

from src.tools.gmail import send_email
from src.tools.gmail.schema import SendEmailInput
from pydantic_ai import RunContext

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample context dictionary
ctx = {"agent_id": "test-agent"}

# Skip tests if GOOGLE_CREDENTIAL_FILE is not set
skip_gmail_tests = pytest.mark.skipif(
    not os.environ.get("GOOGLE_CREDENTIAL_FILE"),
    reason="GOOGLE_CREDENTIAL_FILE not set"
)

@skip_gmail_tests
@pytest.mark.asyncio
async def test_send_email():
    """Test sending an email via Gmail API."""
    logger.info("Testing send_email via Gmail API")
    
    # Get credentials path from environment variable
    credentials_path = os.environ.get("GOOGLE_CREDENTIAL_FILE")
    assert credentials_path, "GOOGLE_CREDENTIAL_FILE environment variable not set"
    
    # Create email input
    email_input = SendEmailInput(
        to="cezar@namastex.ai",
        subject="Gmail API Test",
        message="This is a test email sent via the Gmail API tools.",
        extra_content="This email was sent as part of an integration test."
    )
    
    # Send the email
    result = await send_email(ctx, email_input)
    
    # Verify the result
    assert isinstance(result, dict)
    assert "success" in result
    assert result["success"] is True, f"Failed to send email: {result.get('error', 'Unknown error')}"
    assert "message_id" in result
    
    logger.info(f"Successfully sent test email with message ID: {result['message_id']}")
    
@skip_gmail_tests
@pytest.mark.asyncio
async def test_send_email_with_cc():
    """Test sending an email with CC recipients via Gmail API."""
    logger.info("Testing send_email with CC via Gmail API")
    
    # Get credentials path from environment variable
    credentials_path = os.environ.get("GOOGLE_CREDENTIAL_FILE")
    assert credentials_path, "GOOGLE_CREDENTIAL_FILE environment variable not set"
    
    # Create email input with CC
    email_input = SendEmailInput(
        to="cezar@namastex.ai",
        cc=["test@example.com"],  # This is just for testing, doesn't need to be valid
        subject="Gmail API Test with CC",
        message="This is a test email sent via the Gmail API tools with CC recipients.",
        extra_content="This email was sent as part of an integration test."
    )
    
    # Send the email
    result = await send_email(ctx, email_input)
    
    # Verify the result
    assert isinstance(result, dict)
    assert "success" in result
    assert result["success"] is True, f"Failed to send email: {result.get('error', 'Unknown error')}"
    assert "message_id" in result
    
    logger.info(f"Successfully sent test email with CC and message ID: {result['message_id']}") 