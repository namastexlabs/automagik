"""Message queue system for Claude Code workflows.

This module provides a thread-safe message queue for each running workflow,
allowing messages to be added via API and consumed by the stream-json monitor.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Represents a queued message for injection."""
    message_type: str  # "user" or "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_stream_json(self) -> str:
        """Convert to stream-json format."""
        return json.dumps({
            "type": self.message_type,
            "message": self.content
        })


class WorkflowMessageQueue:
    """Thread-safe message queue for a single workflow."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self._messages: List[QueuedMessage] = []
        self._lock = threading.Lock()
        self._consumed_count = 0
        self._total_added = 0
        
    def add_message(self, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a message to the queue.
        
        Args:
            message_type: Type of message ("user" or "system")
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Current queue size after adding
        """
        with self._lock:
            message = QueuedMessage(
                message_type=message_type,
                content=content,
                metadata=metadata
            )
            self._messages.append(message)
            self._total_added += 1
            queue_size = len(self._messages)
            
        logger.info(f"Added {message_type} message to queue for {self.run_id}. Queue size: {queue_size}")
        return queue_size
    
    def get_all_messages(self, clear: bool = True) -> List[QueuedMessage]:
        """Get all queued messages.
        
        Args:
            clear: If True, clear the queue after getting messages
            
        Returns:
            List of all queued messages
        """
        with self._lock:
            messages = self._messages.copy()
            if clear:
                self._consumed_count += len(messages)
                self._messages.clear()
                
        if messages:
            logger.info(f"Retrieved {len(messages)} messages from queue for {self.run_id}. Queue {'cleared' if clear else 'preserved'}")
        
        return messages
    
    def get_batch_as_stream_json(self, clear: bool = True) -> List[str]:
        """Get all messages as stream-json formatted strings.
        
        Args:
            clear: If True, clear the queue after getting messages
            
        Returns:
            List of stream-json formatted strings
        """
        messages = self.get_all_messages(clear=clear)
        return [msg.to_stream_json() for msg in messages]
    
    def peek(self) -> List[QueuedMessage]:
        """Peek at messages without removing them."""
        return self.get_all_messages(clear=False)
    
    def size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._messages)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.size() == 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                "run_id": self.run_id,
                "current_size": len(self._messages),
                "total_added": self._total_added,
                "total_consumed": self._consumed_count,
                "oldest_message_age": (
                    (datetime.utcnow() - self._messages[0].timestamp).total_seconds()
                    if self._messages else None
                )
            }


class MessageQueueManager:
    """Manages message queues for all active workflows."""
    
    def __init__(self):
        self._queues: Dict[str, WorkflowMessageQueue] = {}
        self._lock = threading.Lock()
        
    def get_or_create_queue(self, run_id: str) -> WorkflowMessageQueue:
        """Get or create a queue for a workflow run."""
        with self._lock:
            if run_id not in self._queues:
                self._queues[run_id] = WorkflowMessageQueue(run_id)
                logger.info(f"Created message queue for workflow {run_id}")
            return self._queues[run_id]
    
    def add_message(self, run_id: str, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a message to a workflow's queue.
        
        Args:
            run_id: Workflow run ID
            message_type: Type of message ("user" or "system")
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Current queue size after adding
        """
        queue = self.get_or_create_queue(run_id)
        return queue.add_message(message_type, content, metadata)
    
    def get_messages_for_injection(self, run_id: str) -> List[str]:
        """Get all messages for a workflow as stream-json strings, clearing the queue.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            List of stream-json formatted strings
        """
        queue = self.get_or_create_queue(run_id)
        return queue.get_batch_as_stream_json(clear=True)
    
    def remove_queue(self, run_id: str) -> bool:
        """Remove a workflow's queue (cleanup).
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            True if queue was removed, False if it didn't exist
        """
        with self._lock:
            if run_id in self._queues:
                stats = self._queues[run_id].get_stats()
                del self._queues[run_id]
                logger.info(f"Removed message queue for workflow {run_id}. Final stats: {stats}")
                return True
            return False
    
    def get_queue_stats(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a workflow's queue."""
        with self._lock:
            if run_id in self._queues:
                return self._queues[run_id].get_stats()
            return None
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues."""
        with self._lock:
            return {
                "total_queues": len(self._queues),
                "queues": {
                    run_id: queue.get_stats()
                    for run_id, queue in self._queues.items()
                }
            }


# Global message queue manager instance
message_queue_manager = MessageQueueManager()