"""SDK Message Processor for Claude Code execution.

This module handles processing different message types from Claude SDK.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class StreamingBuffer:
    """Buffer for handling large streaming responses."""
    
    def __init__(self, max_chunk_size: int = 16384, max_buffer_size: int = 512000):
        self.max_chunk_size = max_chunk_size
        self.max_buffer_size = max_buffer_size
        self.buffer = ""
        self.completed_messages = []
        self.total_chars_processed = 0
    
    def add_chunk(self, chunk: str) -> List[str]:
        """Add a chunk to the buffer and return completed messages."""
        self.buffer += chunk
        self.total_chars_processed += len(chunk)
        
        completed = []
        
        # Check if buffer exceeds chunk size
        while len(self.buffer) >= self.max_chunk_size:
            # Extract a chunk
            message = self.buffer[:self.max_chunk_size]
            self.buffer = self.buffer[self.max_chunk_size:]
            completed.append(message)
            self.completed_messages.append(message)
        
        # Check total buffer size limit
        if len(self.buffer) > self.max_buffer_size:
            logger.warning(f"Buffer size ({len(self.buffer)}) exceeds max ({self.max_buffer_size}), flushing")
            completed.append(self.buffer)
            self.completed_messages.append(self.buffer)
            self.buffer = ""
        
        return completed
    
    def flush(self) -> Optional[str]:
        """Flush any remaining content in the buffer."""
        if self.buffer:
            message = self.buffer
            self.buffer = ""
            self.completed_messages.append(message)
            return message
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            "buffer_size": len(self.buffer),
            "completed_messages": len(self.completed_messages),
            "total_chars_processed": self.total_chars_processed
        }


class SDKMessageProcessor:
    """Processes messages from Claude SDK execution."""
    
    def __init__(self, workflow_name: Optional[str] = None):
        self.workflow_name = workflow_name
        self.streaming_buffer = None
        
        # Initialize streaming buffer for brain workflow
        if workflow_name == 'brain':
            self.streaming_buffer = StreamingBuffer(max_chunk_size=16384, max_buffer_size=512000)
            logger.info("Initialized streaming buffer for brain workflow with 512KB max size")
    
    def process_message(self, message: Any, messages: List[str], collected_messages: List[Any]) -> Dict[str, Any]:
        """Process a message from Claude SDK.
        
        Args:
            message: The message to process
            messages: List to append processed content to
            collected_messages: List to append raw messages to
            
        Returns:
            Dict with processing results including message type and extracted data
        """
        result = {
            "message_type": "unknown",
            "content": None,
            "metadata": {}
        }
        
        # Get message class name
        message_class = message.__class__.__name__ if hasattr(message, '__class__') else 'unknown'
        result["message_type"] = message_class
        
        # Process different message types
        if message_class == 'SystemMessage':
            result = self._process_system_message(message, result)
            collected_messages.append(message)
            
        elif message_class == 'AssistantMessage':
            result = self._process_assistant_message(message, messages, result)
            collected_messages.append(message)
            
        elif message_class == 'ResultMessage':
            result = self._process_result_message(message, result)
            collected_messages.append(message)
            
        elif message_class == 'UserMessage':
            result = self._process_user_message(message, messages, result)
            collected_messages.append(message)
            
        else:
            # Unknown message type
            logger.warning(f"Unknown message type: {message_class}")
            messages.append(str(message))
            collected_messages.append(message)
            result["content"] = str(message)
        
        return result
    
    def _process_system_message(self, message: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process SystemMessage with initialization data."""
        logger.debug(f"SystemMessage with data: {getattr(message, 'data', {})}")
        
        if hasattr(message, 'data'):
            result["metadata"]["data"] = message.data
            
            # Extract session ID if present
            if 'session_id' in message.data:
                result["metadata"]["session_id"] = message.data['session_id']
                logger.info(f"Captured session ID: {message.data['session_id']}")
        
        return result
    
    def _process_assistant_message(self, message: Any, messages: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
        """Process AssistantMessage with response content."""
        if hasattr(message, 'content'):
            # Extract text from content blocks
            content_text = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    content_text += block.text
            
            logger.debug(f"AssistantMessage content: {content_text[:200]}...")
            result["content"] = content_text
            
            # Process with streaming buffer if available
            if self.streaming_buffer:
                completed_messages = self.streaming_buffer.add_chunk(content_text)
                
                # Add completed messages
                for completed_msg in completed_messages:
                    messages.append(completed_msg)
                
                # Log buffer stats periodically
                if len(messages) % 10 == 0:
                    buffer_stats = self.streaming_buffer.get_stats()
                    logger.debug(f"Buffer stats: {buffer_stats}")
                    
                result["metadata"]["buffer_stats"] = self.streaming_buffer.get_stats()
            else:
                # Standard processing
                messages.append(content_text)
        
        return result
    
    def _process_result_message(self, message: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process ResultMessage with final metadata."""
        logger.debug(f"ResultMessage - turns: {getattr(message, 'num_turns', 0)}, duration: {getattr(message, 'duration_ms', 0)}ms")
        
        result["metadata"]["num_turns"] = getattr(message, 'num_turns', 0)
        result["metadata"]["duration_ms"] = getattr(message, 'duration_ms', 0)
        
        # Extract usage information
        if hasattr(message, 'usage') and message.usage:
            usage_data = self._extract_usage_data(message.usage)
            result["metadata"]["usage"] = usage_data
            
        return result
    
    def _process_user_message(self, message: Any, messages: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
        """Process UserMessage (tool responses, etc)."""
        if hasattr(message, 'content'):
            content_text = str(message.content)
            logger.debug(f"UserMessage content: {content_text[:200]}...")
            messages.append(content_text)
            result["content"] = content_text
        
        return result
    
    def _extract_usage_data(self, usage: Any) -> Dict[str, int]:
        """Extract token usage data from usage object."""
        usage_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0
        }
        
        if isinstance(usage, dict):
            # Extract from dict
            usage_data["input_tokens"] = usage.get('input_tokens', 0)
            usage_data["output_tokens"] = usage.get('output_tokens', 0)
            usage_data["cache_creation_tokens"] = usage.get('cache_creation_input_tokens', 0)
            usage_data["cache_read_tokens"] = usage.get('cache_read_input_tokens', 0)
            
            # Calculate total
            usage_data["total_tokens"] = (
                usage_data["input_tokens"] + 
                usage_data["output_tokens"] + 
                usage_data["cache_creation_tokens"] + 
                usage_data["cache_read_tokens"]
            )
            
            logger.info(f"📊 Token usage - Input: {usage_data['input_tokens']}, "
                       f"Output: {usage_data['output_tokens']}, "
                       f"Cache: {usage_data['cache_creation_tokens'] + usage_data['cache_read_tokens']}, "
                       f"Total: {usage_data['total_tokens']}")
        elif hasattr(usage, 'total_tokens'):
            usage_data["total_tokens"] = usage.total_tokens
        
        return usage_data
    
    def flush_buffer(self) -> Optional[str]:
        """Flush streaming buffer if present."""
        if self.streaming_buffer:
            return self.streaming_buffer.flush()
        return None