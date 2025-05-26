from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
import uuid

class BaseResponseModel(BaseModel):
    """Base model for all response models with common configuration."""
    model_config = ConfigDict(
        exclude_none=True,  # Exclude None values from response
        validate_assignment=True,  # Validate values on assignment
        extra='ignore'  # Ignore extra fields
    )

# Multimodal content models
class MediaContent(BaseResponseModel):
    """Base model for media content."""
    mime_type: str
    
class UrlMediaContent(MediaContent):
    """Media content accessible via URL."""
    media_url: str

class BinaryMediaContent(MediaContent):
    """Media content with binary data."""
    data: str  # Base64 encoded binary data
    
class ImageContent(MediaContent):
    """Image content with metadata."""
    mime_type: str = Field(pattern=r'^image/')
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    
class ImageUrlContent(ImageContent, UrlMediaContent):
    """Image content accessible via URL."""
    pass
    
class ImageBinaryContent(ImageContent, BinaryMediaContent):
    """Image content with binary data."""
    thumbnail_url: Optional[str] = None
    
class AudioContent(MediaContent):
    """Audio content with metadata."""
    mime_type: str = Field(pattern=r'^audio/')
    duration_seconds: Optional[float] = None
    transcript: Optional[str] = None
    
class AudioUrlContent(AudioContent, UrlMediaContent):
    """Audio content accessible via URL."""
    pass
    
class AudioBinaryContent(AudioContent, BinaryMediaContent):
    """Audio content with binary data."""
    pass
    
class DocumentContent(MediaContent):
    """Document content with metadata."""
    mime_type: str = Field(pattern=r'^(application|text)/')
    name: Optional[str] = None
    size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    
class DocumentUrlContent(DocumentContent, UrlMediaContent):
    """Document content accessible via URL."""
    pass
    
class DocumentBinaryContent(DocumentContent, BinaryMediaContent):
    """Document content with binary data."""
    pass

# Define UserCreate before it's referenced by AgentRunRequest
class UserCreate(BaseResponseModel):
    """Request model for creating a new user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

# Update AgentRunRequest to support multimodal content
class AgentRunRequest(BaseResponseModel):
    """Request model for running an agent."""
    message_content: str
    message_type: Optional[str] = None
    # Multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent,
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    context: dict = {}
    session_id: Optional[str] = None
    session_name: Optional[str] = None  # Optional friendly name for the session
    user_id: Optional[Union[uuid.UUID, str, int]] = None  # User ID as UUID, string, or int
    message_limit: Optional[int] = 10  # Default to last 10 messages
    session_origin: Optional[Literal["web", "whatsapp", "automagik-agent", "telegram", "discord", "slack", "cli", "app", "manychat"]] = "automagik-agent"  # Origin of the session
    agent_id: Optional[Any] = None  # Agent ID to store with messages, can be int or string
    parameters: Optional[Dict[str, Any]] = None  # Agent parameters
    messages: Optional[List[Any]] = None  # Optional message history
    system_prompt: Optional[str] = None  # Optional system prompt override
    user: Optional[UserCreate] = None  # Optional user data for creation/update
    
    model_config = ConfigDict(
        exclude_none=True,
        json_schema_extra={
            "example": {
                "message_content": "string",
                "message_type": "string",
                "media_contents": [
                    {
                        "mime_type": "image/",
                        "media_url": "string",
                        "width": 0,
                        "height": 0,
                        "alt_text": "string"
                    },
                    {
                        "mime_type": "image/",
                        "data": "string",
                        "width": 0,
                        "height": 0,
                        "alt_text": "string",
                        "thumbnail_url": "string"
                    },
                    {
                        "mime_type": "audio/",
                        "media_url": "string",
                        "duration_seconds": 0,
                        "transcript": "string"
                    },
                    {
                        "mime_type": "audio/",
                        "data": "string",
                        "duration_seconds": 0,
                        "transcript": "string"
                    },
                    {
                        "mime_type": "application/",
                        "media_url": "string",
                        "name": "string",
                        "size_bytes": 0,
                        "page_count": 0
                    },
                    {
                        "mime_type": "application/",
                        "data": "string",
                        "name": "string",
                        "size_bytes": 0,
                        "page_count": 0
                    }
                ],
                "channel_payload": {
                    "additionalProp1": {}
                },
                "context": {},
                "session_id": "string",
                "session_name": "string",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "message_limit": 10,
                "session_origin": "automagik-agent",
                "agent_id": "string",
                "parameters": {
                    "additionalProp1": {}
                },
                "messages": [
                    "string"
                ],
                "system_prompt": "string",
                "user": {
                    "email": "string",
                    "phone_number": "string",
                    "user_data": {
                        "additionalProp1": {}
                    }
                }
            }
        }
    )

class AgentInfo(BaseResponseModel):
    """Information about an available agent."""
    id: int
    name: str
    description: Optional[str] = None

class HealthResponse(BaseResponseModel):
    """Response model for health check endpoint."""
    status: str
    timestamp: datetime
    version: str
    environment: str = "development"  # Default to development if not specified

class DeleteSessionResponse(BaseResponseModel):
    """Response model for session deletion."""
    status: str
    session_id: str
    message: str

class ToolCallModel(BaseResponseModel):
    """Model for a tool call."""
    tool_name: str
    args: Dict
    tool_call_id: str

class ToolOutputModel(BaseResponseModel):
    """Model for a tool output."""
    tool_name: str
    tool_call_id: str
    content: Any

class MessageModel(BaseResponseModel):
    """Model for a single message in the conversation."""
    role: str
    content: str
    assistant_name: Optional[str] = None
    # Multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent, 
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    tool_calls: Optional[List[ToolCallModel]] = None
    tool_outputs: Optional[List[ToolOutputModel]] = None
    system_prompt: Optional[str] = None

    model_config = ConfigDict(
        exclude_none=True,
        json_schema_extra={"examples": [{"role": "assistant", "content": "Hello!"}]}
    )

class PaginationParams(BaseResponseModel):
    """Pagination parameters."""
    page: int = 1
    page_size: int = 50
    sort_desc: bool = True  # True for most recent first

class SessionResponse(BaseResponseModel):
    """Response model for session retrieval."""
    session_id: str
    messages: List[MessageModel]
    exists: bool
    total_messages: int
    current_page: int
    total_pages: int
    system_prompt: Optional[str] = None

class SessionInfo(BaseResponseModel):
    """Information about a session."""
    session_id: str
    user_id: Optional[uuid.UUID] = None
    agent_id: Optional[int] = None
    session_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    message_count: Optional[int] = None
    agent_name: Optional[str] = None
    session_origin: Optional[str] = None  # Origin of the session (e.g., "web", "api", "discord")
    system_prompt: Optional[str] = None

class SessionListResponse(BaseResponseModel):
    """Response model for listing all sessions."""
    sessions: List[SessionInfo]
    total: int
    total_count: int = None  # Added for backward compatibility
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    
    # Make sure both total and total_count have the same value for backward compatibility
    def __init__(self, **data):
        if 'total' in data and 'total_count' not in data:
            data['total_count'] = data['total']
        super().__init__(**data)

# UserCreate moved to before AgentRunRequest

class UserUpdate(BaseResponseModel):
    """Request model for updating an existing user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

class UserInfo(BaseResponseModel):
    """Response model for user information."""
    id: uuid.UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserListResponse(BaseResponseModel):
    """Response model for listing users."""
    users: List[UserInfo]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: Optional[bool] = None
    has_prev: Optional[bool] = None

class DeleteMessageResponse(BaseResponseModel):
    """Response model for message deletion."""
    status: str = "success"
    message_id: uuid.UUID
    detail: str = "Message deleted successfully"

# Prompt API models
class PromptResponse(BaseResponseModel):
    """Response model for a single prompt."""
    id: int
    agent_id: int
    prompt_text: str
    version: int
    is_active: bool
    is_default_from_code: bool
    status_key: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class PromptListResponse(BaseResponseModel):
    """Response model for listing prompts."""
    prompts: List[PromptResponse]
    total: int
    agent_id: int

class PromptCreateRequest(BaseResponseModel):
    """Request model for creating a new prompt."""
    prompt_text: str
    status_key: str = "default"
    name: Optional[str] = None
    is_active: bool = False
    version: int = 1

class PromptUpdateRequest(BaseResponseModel):
    """Request model for updating an existing prompt."""
    prompt_text: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None 