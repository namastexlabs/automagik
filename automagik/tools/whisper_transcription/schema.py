"""Pydantic schemas for Whisper transcription tool."""

from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class TranscriptionRequest(BaseModel):
    """Request model for audio transcription."""
    
    audio_data: Union[str, bytes] = Field(..., description="Audio file path, base64 data, or raw bytes")
    provider: str = Field("auto", description="Whisper provider: 'openai', 'groq', or 'auto'")
    language: Optional[str] = Field(None, description="Language code (e.g., 'pt', 'en')")
    prompt: Optional[str] = Field(None, description="Optional prompt to guide transcription")

class TranscriptionResponse(BaseModel):
    """Response model for audio transcription."""
    
    success: bool = Field(..., description="Whether transcription succeeded")
    transcription: Optional[str] = Field(None, description="Transcribed text")
    provider: Optional[str] = Field(None, description="Provider used for transcription")
    language: Optional[str] = Field(None, description="Detected or specified language")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AudioProcessingConfig(BaseModel):
    """Configuration for audio processing."""
    
    max_file_size_mb: int = Field(25, description="Maximum audio file size in MB")
    supported_formats: list = Field(
        default=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"],
        description="Supported audio formats"
    )
    default_provider: str = Field("auto", description="Default Whisper provider")
    default_language: Optional[str] = Field(None, description="Default language for transcription")