#!/usr/bin/env python3
"""Whisper transcription tool for audio processing."""

import logging
import tempfile
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
import base64

from automagik.config import settings

logger = logging.getLogger(__name__)

class WhisperTranscriptionTool:
    """Tool for transcribing audio using Whisper APIs."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.openai_client = None
        self.groq_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Whisper API clients."""
        # OpenAI Whisper
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI Whisper client initialized")
            except ImportError:
                logger.warning("OpenAI library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Groq Whisper (faster alternative)
        if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Groq Whisper client initialized")
            except ImportError:
                logger.warning("Groq library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
    
    async def transcribe_audio(
        self,
        audio_data: Union[str, bytes, Path],
        provider: str = "auto",
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper API.
        
        Args:
            audio_data: Audio file path, base64 data, or raw bytes
            provider: "openai", "groq", or "auto" (default)
            language: Optional language code (e.g., "pt", "en")
            prompt: Optional prompt to guide transcription
            
        Returns:
            Dict with transcription results
        """
        
        # Prepare audio file
        audio_file_path = await self._prepare_audio_file(audio_data)
        if not audio_file_path:
            return {
                "success": False,
                "error": "Failed to prepare audio file",
                "transcription": None
            }
        
        try:
            # Choose provider
            if provider == "auto":
                provider = "groq" if self.groq_client else "openai"
            
            # Transcribe based on provider
            if provider == "groq" and self.groq_client:
                result = await self._transcribe_with_groq(
                    audio_file_path, language, prompt
                )
            elif provider == "openai" and self.openai_client:
                result = await self._transcribe_with_openai(
                    audio_file_path, language, prompt
                )
            else:
                return {
                    "success": False,
                    "error": f"Provider '{provider}' not available or configured",
                    "transcription": None
                }
            
            return {
                "success": True,
                "transcription": result,
                "provider": provider,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcription": None
            }
        finally:
            # Cleanup temporary files
            if str(audio_file_path).startswith(tempfile.gettempdir()):
                try:
                    os.unlink(audio_file_path)
                except:
                    pass
    
    async def _prepare_audio_file(self, audio_data: Union[str, bytes, Path]) -> Optional[Path]:
        """Prepare audio file for transcription."""
        
        if isinstance(audio_data, (str, Path)) and Path(audio_data).exists():
            # File path provided
            return Path(audio_data)
        
        elif isinstance(audio_data, str) and audio_data.startswith("data:audio"):
            # Base64 data URL
            try:
                # Extract base64 data
                header, data = audio_data.split(",", 1)
                audio_bytes = base64.b64decode(data)
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", 
                    delete=False
                )
                temp_file.write(audio_bytes)
                temp_file.close()
                
                return Path(temp_file.name)
            except Exception as e:
                logger.error(f"Failed to decode base64 audio: {e}")
                return None
        
        elif isinstance(audio_data, bytes):
            # Raw bytes
            try:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", 
                    delete=False
                )
                temp_file.write(audio_data)
                temp_file.close()
                
                return Path(temp_file.name)
            except Exception as e:
                logger.error(f"Failed to save audio bytes: {e}")
                return None
        
        return None
    
    async def _transcribe_with_openai(
        self, 
        audio_file_path: Path, 
        language: Optional[str], 
        prompt: Optional[str]
    ) -> str:
        """Transcribe using OpenAI Whisper."""
        
        kwargs = {"model": "whisper-1", "response_format": "text"}
        
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt
        
        with open(audio_file_path, "rb") as audio_file:
            kwargs["file"] = audio_file
            transcription = self.openai_client.audio.transcriptions.create(**kwargs)
        
        return transcription
    
    async def _transcribe_with_groq(
        self, 
        audio_file_path: Path, 
        language: Optional[str], 
        prompt: Optional[str]
    ) -> str:
        """Transcribe using Groq Whisper (faster)."""
        
        kwargs = {
            "model": "whisper-large-v3-turbo",
            "response_format": "text"
        }
        
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt
        
        with open(audio_file_path, "rb") as audio_file:
            kwargs["file"] = audio_file
            transcription = self.groq_client.audio.transcriptions.create(**kwargs)
        
        return transcription.text
    
    def is_available(self) -> bool:
        """Check if any Whisper provider is available."""
        return bool(self.openai_client or self.groq_client)
    
    def get_available_providers(self) -> list:
        """Get list of available providers."""
        providers = []
        if self.openai_client:
            providers.append("openai")
        if self.groq_client:
            providers.append("groq")
        return providers

# Tool function for agent integration
async def transcribe_audio_content(
    audio_data: Union[str, bytes, Path],
    provider: str = "auto",
    language: Optional[str] = None,
    context: Optional[str] = None
) -> str:
    """
    Tool function to transcribe audio content.
    
    Args:
        audio_data: Audio file, base64 data, or bytes
        provider: Whisper provider ("openai", "groq", "auto")
        language: Language code for transcription
        context: Optional context to guide transcription
        
    Returns:
        Transcribed text or error message
    """
    
    tool = WhisperTranscriptionTool({})
    
    if not tool.is_available():
        return "Audio transcription not available - no Whisper API keys configured"
    
    result = await tool.transcribe_audio(
        audio_data=audio_data,
        provider=provider,
        language=language,
        prompt=context
    )
    
    if result["success"]:
        return result["transcription"]
    else:
        return f"Transcription failed: {result['error']}"

# Factory function for creating tool instance
def create_whisper_tool(config: Dict[str, str]) -> WhisperTranscriptionTool:
    """Factory function to create Whisper tool instance."""
    return WhisperTranscriptionTool(config)