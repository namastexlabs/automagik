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


class StreamingBuffer:
    """Buffer for handling large streaming responses with chunked processing."""
    
    def __init__(self, max_chunk_size: int = 32768, max_buffer_size: int = 1048576):
        """Initialize streaming buffer.
        
        Args:
            max_chunk_size: Maximum size of each chunk to process (32KB default)
            max_buffer_size: Maximum total buffer size (1MB default)
        """
        self.max_chunk_size = max_chunk_size
        self.max_buffer_size = max_buffer_size
        self.buffer = ""
        self.processed_chunks = []
        self.total_size = 0
        self.overflow_detected = False
    
    def add_chunk(self, chunk: str) -> List[str]:
        """Add chunk to buffer and return completed messages.
        
        Args:
            chunk: New chunk of data to add
            
        Returns:
            List of completed messages ready for processing
        """
        if not chunk:
            return []
            
        # Check for buffer overflow
        if self.total_size + len(chunk) > self.max_buffer_size:
            self.overflow_detected = True
            logger.warning(f"Buffer overflow detected. Buffer size: {self.total_size}, chunk size: {len(chunk)}")
            
            # Process what we have and reset
            completed_messages = self._extract_completed_messages()
            self._reset_buffer()
            
            # Add the new chunk to fresh buffer
            self.buffer = chunk
            self.total_size = len(chunk)
            
            return completed_messages
        
        # Add chunk to buffer
        self.buffer += chunk
        self.total_size += len(chunk)
        
        # Extract completed messages
        return self._extract_completed_messages()
    
    def _extract_completed_messages(self) -> List[str]:
        """Extract completed JSON messages from buffer."""
        if not self.buffer.strip():
            return []
        
        completed_messages = []
        remaining_buffer = self.buffer
        
        # Try to extract complete JSON objects
        start_idx = 0
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(remaining_buffer):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    # Found complete JSON object
                    if brace_count == 0:
                        json_str = remaining_buffer[start_idx:i+1].strip()
                        if json_str:
                            completed_messages.append(json_str)
                        start_idx = i + 1
        
        # Update buffer with remaining incomplete data
        if start_idx < len(remaining_buffer):
            self.buffer = remaining_buffer[start_idx:]
            self.total_size = len(self.buffer)
        else:
            self.buffer = ""
            self.total_size = 0
        
        return completed_messages
    
    def _reset_buffer(self):
        """Reset buffer state."""
        self.buffer = ""
        self.total_size = 0
        self.overflow_detected = False
    
    def get_final_content(self) -> Optional[str]:
        """Get any remaining content in buffer."""
        if self.buffer.strip():
            return self.buffer.strip()
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            "buffer_size": self.total_size,
            "max_buffer_size": self.max_buffer_size,
            "max_chunk_size": self.max_chunk_size,
            "overflow_detected": self.overflow_detected,
            "processed_chunks": len(self.processed_chunks)
        }


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


def handle_brain_workflow_json_error(error: Exception, buffer_content: str, workflow_name: str) -> Dict[str, Any]:
    """Handle JSON parsing errors specifically for brain workflow.
    
    Args:
        error: The JSON parsing error
        buffer_content: Content that failed to parse
        workflow_name: Name of the workflow (should be 'brain')
        
    Returns:
        Recovery information and fallback content
    """
    recovery_info = {
        "error_type": "json_parsing_error",
        "workflow_name": workflow_name,
        "error_message": str(error),
        "recovery_attempted": False,
        "fallback_content": None,
        "partial_content": None
    }
    
    if workflow_name != 'brain':
        logger.debug(f"JSON error handling optimized for brain workflow, got: {workflow_name}")
        return recovery_info
    
    try:
        # Attempt to extract partial content for brain workflow
        recovery_info["recovery_attempted"] = True
        
        # Try to extract completed thoughts or memory operations
        if "add_memory" in buffer_content:
            # Extract memory operation calls
            memory_calls = []
            lines = buffer_content.split('\n')
            current_call = []
            in_memory_call = False
            
            for line in lines:
                if "add_memory" in line:
                    in_memory_call = True
                    current_call = [line]
                elif in_memory_call:
                    current_call.append(line)
                    if line.strip().endswith(')') and not line.strip().endswith('"),'):
                        memory_calls.append('\n'.join(current_call))
                        current_call = []
                        in_memory_call = False
            
            if memory_calls:
                recovery_info["partial_content"] = {
                    "type": "memory_operations",
                    "content": memory_calls,
                    "count": len(memory_calls)
                }
                logger.info(f"Extracted {len(memory_calls)} memory operations from failed JSON")
        
        # Try to extract patterns or structured data
        if "patterns:" in buffer_content or "learnings:" in buffer_content:
            # Extract YAML-like structures
            yaml_sections = []
            lines = buffer_content.split('\n')
            current_section = []
            in_yaml_section = False
            
            for line in lines:
                if line.strip().endswith(':') and not line.strip().startswith(' '):
                    if current_section:
                        yaml_sections.append('\n'.join(current_section))
                    current_section = [line]
                    in_yaml_section = True
                elif in_yaml_section and (line.startswith('  ') or line.startswith('-')):
                    current_section.append(line)
                elif in_yaml_section and line.strip() == '':
                    current_section.append(line)
                else:
                    if current_section:
                        yaml_sections.append('\n'.join(current_section))
                        current_section = []
                    in_yaml_section = False
            
            if current_section:
                yaml_sections.append('\n'.join(current_section))
            
            if yaml_sections:
                recovery_info["partial_content"] = {
                    "type": "yaml_structures",
                    "content": yaml_sections,
                    "count": len(yaml_sections)
                }
                logger.info(f"Extracted {len(yaml_sections)} YAML sections from failed JSON")
        
        # Fallback: Extract any meaningful text content
        if not recovery_info["partial_content"]:
            # Remove obvious JSON artifacts and keep readable content
            clean_content = buffer_content.replace('{', '').replace('}', '').replace('"', '')
            clean_lines = [line.strip() for line in clean_content.split('\n') if line.strip()]
            
            if clean_lines:
                recovery_info["fallback_content"] = {
                    "type": "cleaned_text",
                    "content": '\n'.join(clean_lines[:50]),  # Limit to first 50 lines
                    "original_length": len(buffer_content)
                }
                logger.info(f"Extracted {len(clean_lines)} clean lines from failed JSON")
        
        logger.info(f"Brain workflow JSON error recovery completed: {recovery_info}")
        
    except Exception as recovery_error:
        logger.error(f"JSON error recovery failed: {recovery_error}")
        recovery_info["recovery_error"] = str(recovery_error)
    
    return recovery_info