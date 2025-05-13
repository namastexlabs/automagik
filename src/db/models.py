"""Pydantic models representing database tables."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, ClassVar

from pydantic import BaseModel, Field, ConfigDict


class BaseDBModel(BaseModel):
    """Base model for all database models."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )


class User(BaseDBModel):
    """User model corresponding to the users table."""
    id: Optional[uuid.UUID] = Field(None, description="User ID")
    email: Optional[str] = Field(None, description="User email")
    phone_number: Optional[str] = Field(None, description="User phone number")
    user_data: Optional[Dict[str, Any]] = Field(None, description="Additional user data")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "User":
        """Create a User instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Agent(BaseDBModel):
    """Agent model corresponding to the agents table."""
    id: Optional[int] = Field(None, description="Agent ID")
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type")
    model: str = Field(..., description="Model used by the agent")
    description: Optional[str] = Field(None, description="Agent description")
    version: Optional[str] = Field(None, description="Agent version")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    active: bool = Field(True, description="Whether the agent is active")
    run_id: int = Field(0, description="Current run ID")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    active_default_prompt_id: Optional[int] = Field(None, description="ID of the active default prompt")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Agent":
        """Create an Agent instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Session(BaseDBModel):
    """Session model corresponding to the sessions table."""
    id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    agent_name: Optional[str] = Field(None, description="Name of the agent associated with the session")
    name: Optional[str] = Field(None, description="Session name")
    platform: Optional[str] = Field(None, description="Platform")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")
    run_finished_at: Optional[datetime] = Field(None, description="Run finished at timestamp")
    message_count: Optional[int] = Field(None, description="Number of messages in the session")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Session":
        """Create a Session instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Message(BaseDBModel):
    """Message model corresponding to the messages table."""
    id: Optional[uuid.UUID] = Field(None, description="Message ID")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    text_content: Optional[str] = Field(None, description="Message text content")
    media_url: Optional[str] = Field(None, description="Media URL")
    mime_type: Optional[str] = Field(None, description="MIME type")
    message_type: Optional[str] = Field(None, description="Message type")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Raw message payload")
    channel_payload: Optional[Dict[str, Any]] = Field(None, description="Channel-specific payload data")
    tool_calls: Optional[Dict[str, Any]] = Field(None, description="Tool calls")
    tool_outputs: Optional[Dict[str, Any]] = Field(None, description="Tool outputs")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    user_feedback: Optional[str] = Field(None, description="User feedback")
    flagged: Optional[str] = Field(None, description="Flagged status")
    context: Optional[Dict[str, Any]] = Field(None, description="Message context")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Message":
        """Create a Message instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Memory(BaseDBModel):
    """Memory model corresponding to the memories table."""
    id: Optional[uuid.UUID] = Field(None, description="Memory ID")
    name: str = Field(..., description="Memory name")
    description: Optional[str] = Field(None, description="Memory description")
    content: Optional[str] = Field(None, description="Memory content")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    read_mode: Optional[str] = Field(None, description="Read mode")
    access: Optional[str] = Field(None, description="Access permissions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Memory":
        """Create a Memory instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


# Prompt Models
class PromptBase(BaseDBModel):
    """Base class for Prompt models."""
    
    agent_id: int = Field(..., description="ID of the agent this prompt belongs to")
    prompt_text: str = Field(..., description="The actual prompt text content")
    version: int = Field(default=1, description="Version number for this prompt")
    is_active: bool = Field(default=False, description="Whether this prompt is currently active")
    is_default_from_code: bool = Field(default=False, description="Whether this prompt was defined in code")
    status_key: str = Field(default="default", description="Status key this prompt applies to (e.g., 'default', 'APPROVED', etc.)")
    name: Optional[str] = Field(default=None, description="Optional descriptive name for this prompt")


class PromptCreate(PromptBase):
    """Data needed to create a new Prompt."""
    pass


class PromptUpdate(BaseModel):
    """Data for updating an existing Prompt."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    prompt_text: Optional[str] = Field(default=None, description="Updated prompt text")
    is_active: Optional[bool] = Field(default=None, description="Whether to set this prompt as active")
    name: Optional[str] = Field(default=None, description="Updated prompt name")


class Prompt(PromptBase):
    """Complete Prompt model, including database fields."""
    
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Timestamp when this prompt was created")
    updated_at: datetime = Field(..., description="Timestamp when this prompt was last updated")
    
    DB_TABLE: ClassVar[str] = "prompts"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Prompt":
        """Create a Prompt instance from a database row.
        
        Args:
            row: Database row as dictionary
            
        Returns:
            Prompt instance
        """
        if not row:
            return None
            
        # Convert database row to model
        return cls(
            id=row["id"],
            agent_id=row["agent_id"],
            prompt_text=row["prompt_text"],
            version=row["version"],
            is_active=row["is_active"],
            is_default_from_code=row["is_default_from_code"],
            status_key=row["status_key"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )