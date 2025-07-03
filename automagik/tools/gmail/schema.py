"""Gmail tool schemas.

This module defines the Pydantic models for Gmail tool input and output.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SendEmailInput(BaseModel):
    """Input model for sending email."""
    to: str = Field(..., description="Email address of the recipient")
    cc: Optional[List[str]] = Field(None, description="List of email addresses to CC")
    subject: str = Field(..., description="Subject of the email")
    message: str = Field(..., description="Content of the email")
    content_type: Optional[str] = Field("text/plain", description="Content type of the email: text/plain or text/html")
    plain_text_alternative: Optional[str] = Field(None, description="Plain text alternative for HTML emails")
    extra_content: Optional[str] = Field(None, description="Additional content to append to the email message")

class SendEmailResult(BaseModel):
    """Result model for sending email."""
    success: bool = Field(..., description="Whether the email was sent successfully")
    message_id: Optional[str] = Field(None, description="ID of the sent message if successful")
    error: Optional[str] = Field(None, description="Error message if sending failed")

class FetchEmailsInput(BaseModel):
    """Input model for fetching emails."""
    subject_filter: Optional[str] = Field(None, description="Filter emails by subject (e.g. '[STAN] - Novo Lead')")
    max_results: int = Field(10, description="Maximum number of emails to retrieve")

class EmailMessage(BaseModel):
    """Model for an email message."""
    id: str = Field(..., description="ID of the email message")
    from_email: str = Field(..., description="Sender email address")
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Subject of the email")
    date: str = Field(..., description="Date the email was sent")
    body: str = Field(..., description="Body content of the email")
    raw_data: Dict[str, Any] = Field(..., description="Raw message data from Gmail API")

class FetchEmailsResult(BaseModel):
    """Result model for fetching emails."""
    success: bool = Field(..., description="Whether the emails were fetched successfully")
    emails: List[EmailMessage] = Field(default_factory=list, description="List of fetched email messages")
    error: Optional[str] = Field(None, description="Error message if fetching failed") 