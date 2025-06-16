"""Stream processing utilities for Claude Code agent.

This module consolidates stream processing and JSON parsing functions
to avoid duplication across the codebase.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class StreamProcessingError(Exception):
    """Base exception for stream processing errors."""
    pass


class JSONParsingError(StreamProcessingError):
    """Exception raised when JSON parsing fails."""
    
    def __init__(self, message: str, raw_data: str = "", original_error: Exception = None):
        self.raw_data = raw_data
        self.original_error = original_error
        super().__init__(message)


def parse_json_safely(text: str, raise_on_error: bool = False) -> Optional[Dict[str, Any]]:
    """Parse JSON text with safe error handling.
    
    Args:
        text: JSON text to parse
        raise_on_error: If True, raise JSONParsingError on failures
        
    Returns:
        Parsed dictionary or None if parsing fails
        
    Raises:
        JSONParsingError: If raise_on_error is True and parsing fails
    """
    if not isinstance(text, str):
        if raise_on_error:
            raise JSONParsingError(f"Expected string, got {type(text).__name__}", str(text))
        logger.debug(f"Invalid input type for JSON parsing: {type(text).__name__}")
        return None
    
    if not text.strip():
        return None
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse JSON: {e}")
        if raise_on_error:
            raise JSONParsingError(f"JSON decode error: {e}", text, e)
        return None
    except (TypeError, ValueError) as e:
        logger.debug(f"Invalid JSON format: {e}")
        if raise_on_error:
            raise JSONParsingError(f"Invalid JSON format: {e}", text, e)
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        if raise_on_error:
            raise JSONParsingError(f"Unexpected JSON parsing error: {e}", text, e)
        return None


def extract_claude_message_content(message_data: Dict[str, Any]) -> Optional[str]:
    """Extract content from a Claude message data structure.
    
    Args:
        message_data: Claude message dictionary
        
    Returns:
        Extracted content string or None if not found
    """
    try:
        # Handle different Claude message formats
        if isinstance(message_data, dict):
            # Try direct content field
            if "content" in message_data:
                content = message_data["content"]
                if isinstance(content, str):
                    return content
                elif isinstance(content, list) and len(content) > 0:
                    # Handle content blocks
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            return block["text"]
            
            # Try message field
            if "message" in message_data:
                return extract_claude_message_content(message_data["message"])
                
            # Try text field
            if "text" in message_data:
                return message_data["text"]
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to extract Claude message content: {e}")
        return None


def is_claude_stream_event(data: Dict[str, Any], event_type: str) -> bool:
    """Check if a data structure is a specific Claude stream event type.
    
    Args:
        data: Event data dictionary
        event_type: Expected event type (e.g., 'content_block_delta', 'message_start')
        
    Returns:
        True if the data matches the expected event type
    """
    try:
        return (
            isinstance(data, dict) and
            data.get("type") == event_type
        )
    except Exception:
        return False


def extract_streaming_content(data: Dict[str, Any]) -> Optional[str]:
    """Extract streaming content from Claude stream events.
    
    Args:
        data: Stream event data
        
    Returns:
        Extracted content text or None if not a content event
    """
    try:
        # Handle content_block_delta events
        if is_claude_stream_event(data, "content_block_delta"):
            delta = data.get("delta", {})
            if isinstance(delta, dict) and "text" in delta:
                return delta["text"]
        
        # Handle other content events
        if "content" in data:
            return extract_claude_message_content(data)
            
        return None
        
    except Exception as e:
        logger.debug(f"Failed to extract streaming content: {e}")
        return None


def parse_claude_stream_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single line from Claude CLI stream output.
    
    Args:
        line: Raw line from Claude stream
        
    Returns:
        Parsed event data or None if not valid
    """
    try:
        # Strip whitespace and check for empty lines
        line = line.strip()
        if not line:
            return None
            
        # Handle server-sent events format
        if line.startswith("data: "):
            data_part = line[6:]  # Remove "data: " prefix
            if data_part == "[DONE]":
                return {"type": "stream_end"}
            return parse_json_safely(data_part)
        
        # Try direct JSON parsing
        return parse_json_safely(line)
        
    except Exception as e:
        logger.debug(f"Failed to parse Claude stream line: {e}")
        return None


def extract_session_id_from_stream(data: Dict[str, Any]) -> Optional[str]:
    """Extract session ID from Claude stream events.
    
    Args:
        data: Stream event data
        
    Returns:
        Session ID string or None if not found
    """
    try:
        # Check direct session_id field
        if "session_id" in data:
            return data["session_id"]
            
        # Check in message metadata
        if "message" in data:
            message = data["message"]
            if isinstance(message, dict) and "id" in message:
                return message["id"]
        
        # Check in metadata
        if "metadata" in data:
            metadata = data["metadata"]
            if isinstance(metadata, dict) and "session_id" in metadata:
                return metadata["session_id"]
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to extract session ID: {e}")
        return None