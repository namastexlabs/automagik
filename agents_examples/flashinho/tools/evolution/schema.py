"""Evolution tool schemas.

This module defines the Pydantic models for Evolution tool input and output.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class Message(BaseModel):
    """Model for Evolution message data."""
    id: str = Field(..., description="Message ID")
    from_field: str = Field(..., description="Sender of the message", alias="from")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Timestamp of the message")
    type: str = Field(..., description="Type of message (incoming/outgoing)")
    
    model_config = ConfigDict(
        populate_by_name=True
    )

class SendMessageResponse(BaseModel):
    """Response model for send_message."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    message_id: Optional[str] = Field(None, description="ID of the sent message")
    timestamp: Optional[str] = Field(None, description="Timestamp of the sent message")

class GetChatHistoryResponse(BaseModel):
    """Response model for get_chat_history."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    messages: List[Message] = Field(default_factory=list, description="List of messages in the chat history")
    
class Contact(BaseModel):
    """Model for contact information."""
    full_name: str = Field(..., description="Full name of the contact", alias="fullName")
    wuid: str = Field(..., description="WhatsApp ID of the contact")
    phone_number: str = Field(..., description="Phone number with country code", alias="phoneNumber")
    organization: Optional[str] = Field("", description="Organization of the contact")
    email: Optional[str] = Field("", description="Email address of the contact")
    url: Optional[str] = Field("", description="URL of the contact")
    
    model_config = ConfigDict(
        populate_by_name=True
    )

class SendContactRequest(BaseModel):
    """Request model for send_contact."""
    number: str = Field(..., description="Recipient's WhatsApp ID")
    contact: List[Contact] = Field(..., description="List of contacts to send")
    quoted_message_id: Optional[str] = Field(None, description="ID of the message to quote", alias="quotedMessageId")
    
    model_config = ConfigDict(
        populate_by_name=True
    )

class SendContactResponse(BaseModel):
    """Response model for send_contact."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    status: Optional[str] = Field(None, description="Status of the operation")
    message_id: Optional[str] = Field(None, description="ID of the sent message", alias="messageId")
    timestamp: Optional[str] = Field(None, description="Timestamp of the sent message")
    recipient: Optional[str] = Field(None, description="Recipient of the contact information")
    
    model_config = ConfigDict(
        populate_by_name=True
    ) 