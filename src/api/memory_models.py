from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

class MemoryCreate(BaseModel):
    name: str = Field(..., description="Name of the memory")
    description: Optional[str] = Field(None, description="Description of the memory")
    content: str = Field(..., description="Content of the memory")
    session_id: Optional[str] = Field(None, description="Associated session ID - can be a UUID string or None")
    user_id: Optional[UUID] = Field(None, description="Associated user ID (UUID)")
    agent_id: Optional[int] = Field(None, description="Associated agent ID")
    read_mode: Optional[str] = Field(None, description="Read mode of the memory (e.g., system_prompt, tool_call)")
    access: Optional[str] = Field(None, description="Access permissions of the memory (e.g., read, write)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the memory")

    @model_validator(mode='after')
    def validate_user_agent_relationship(self):
        """Validate that agent_id is required when user_id is not provided."""
        if self.user_id is None and self.agent_id is None:
            raise ValueError("agent_id is required when user_id is not provided")
        return self

class MemoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the memory")
    description: Optional[str] = Field(None, description="Description of the memory")
    content: Optional[str] = Field(None, description="Content of the memory")
    session_id: Optional[str] = Field(None, description="Associated session ID - can be a UUID string or None")
    user_id: Optional[UUID] = Field(None, description="Associated user ID (UUID)")
    agent_id: Optional[int] = Field(None, description="Associated agent ID")
    read_mode: Optional[str] = Field(None, description="Read mode of the memory (e.g., system_prompt, tool_call)")
    access: Optional[str] = Field(None, description="Access permissions of the memory (e.g., read, write)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the memory")

    @model_validator(mode='after')
    def validate_user_agent_relationship(self):
        """Validate that agent_id is required when user_id is explicitly set to None."""
        # Only validate when both fields are explicitly provided in the update
        update_dict = self.model_dump(exclude_unset=True)
        if 'user_id' in update_dict and 'agent_id' in update_dict:
            if self.user_id is None and self.agent_id is None:
                raise ValueError("agent_id is required when user_id is not provided")
        return self

class MemoryResponse(BaseModel):
    id: UUID = Field(..., description="Memory ID")
    name: str = Field(..., description="Name of the memory")
    description: Optional[str] = Field(None, description="Description of the memory")
    content: str = Field(..., description="Content of the memory")
    session_id: Optional[str] = Field(None, description="Associated session ID - can be a UUID string or None")
    user_id: Optional[UUID] = Field(None, description="Associated user ID (UUID)")
    agent_id: Optional[int] = Field(None, description="Associated agent ID")
    read_mode: Optional[str] = Field(None, description="Read mode of the memory")
    access: Optional[str] = Field(None, description="Access permissions of the memory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the memory")
    created_at: datetime = Field(..., description="Memory creation timestamp")
    updated_at: datetime = Field(..., description="Memory update timestamp")

class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse] = Field(..., description="List of memories")
    count: int = Field(..., description="Total count of memories")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of memories per page")
    pages: int = Field(..., description="Total number of pages")
