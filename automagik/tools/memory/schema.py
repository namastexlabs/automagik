"""Memory tool schemas.

This module defines the Pydantic models for memory tool input and output.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Union
from datetime import datetime

# Common models
class MemoryBase(BaseModel):
    """Base model for memory objects."""
    name: str = Field(..., description="The name of the memory")
    content: Any = Field(..., description="The content of the memory")
    
class MemoryMetadata(BaseModel):
    """Metadata associated with a memory."""
    created_at: Optional[datetime] = Field(None, description="When the memory was created")
    updated_at: Optional[datetime] = Field(None, description="When the memory was last updated")
    agent_id: Optional[int] = Field(None, description="ID of the agent that owns this memory")
    user_id: Optional[int] = Field(None, description="ID of the user that owns this memory")
    session_id: Optional[str] = Field(None, description="ID of the session that owns this memory")
    
class Memory(MemoryBase):
    """Complete memory object with all fields."""
    id: str = Field(..., description="Unique identifier for the memory")
    description: Optional[str] = Field(None, description="Optional description of the memory")
    read_mode: str = Field("tool_calling", description="How this memory should be used (system_prompt or tool_calling)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

# Input models
class ReadMemoryInput(BaseModel):
    """Input for reading a memory."""
    name: Optional[str] = Field(None, description="The name of the memory to read")
    memory_id: Optional[str] = Field(None, description="The ID of the memory to read")
    list_all: bool = Field(False, description="Whether to list all memories")
    
class CreateMemoryInput(BaseModel):
    """Input for creating a memory."""
    name: str = Field(..., description="The name of the memory to create")
    content: Union[str, Dict[str, Any]] = Field(..., description="The content to store in the memory")
    description: Optional[str] = Field(None, description="Optional description of the memory")
    read_mode: str = Field("tool_calling", description="How this memory should be used (system_prompt or tool_calling)")
    scope: Optional[str] = Field(None, description="Scope of the memory (global, user, or session)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
class UpdateMemoryInput(BaseModel):
    """Input for updating a memory."""
    memory_id: str = Field(..., description="The ID of the memory to update")
    content: Union[str, Dict[str, Any]] = Field(..., description="The new content for the memory")
    name: Optional[str] = Field(None, description="Optional new name for the memory")
    description: Optional[str] = Field(None, description="Optional new description for the memory")
    
# Output models
class MemoryReadResult(BaseModel):
    """Result of a memory read operation."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    content: Optional[Any] = Field(None, description="The content of the memory if found")
    memory: Optional[Memory] = Field(None, description="The complete memory object if found")
    memories: Optional[List[Memory]] = Field(None, description="List of memories if list_all was True")

class MemoryCreateResponse(BaseModel):
    """Response for a memory creation operation."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    id: Optional[str] = Field(None, description="The ID of the created memory if successful")
    name: Optional[str] = Field(None, description="The name of the created memory if successful")

class MemoryUpdateResponse(BaseModel):
    """Response for a memory update operation."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    id: Optional[str] = Field(None, description="The ID of the updated memory if successful")
    name: Optional[str] = Field(None, description="The name of the updated memory if successful") 