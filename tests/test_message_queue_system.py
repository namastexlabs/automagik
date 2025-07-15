#!/usr/bin/env python3
"""Unit tests for the message queue system."""

import pytest
import json
import time
from datetime import datetime
from automagik.agents.claude_code.message_queue import (
    MessageQueueManager,
    WorkflowMessageQueue,
    QueuedMessage
)


class TestQueuedMessage:
    """Test QueuedMessage class."""
    
    def test_message_creation(self):
        """Test creating a queued message."""
        message = QueuedMessage("user", "Test message")
        
        assert message.message_type == "user"
        assert message.content == "Test message"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata is None
    
    def test_message_with_metadata(self):
        """Test creating a message with metadata."""
        metadata = {"source": "api", "priority": "high"}
        message = QueuedMessage("system", "System message", metadata=metadata)
        
        assert message.message_type == "system"
        assert message.content == "System message"
        assert message.metadata == metadata
    
    def test_to_stream_json(self):
        """Test converting message to stream-json format."""
        message = QueuedMessage("user", "Hello world")
        json_str = message.to_stream_json()
        
        # Validate JSON format
        parsed = json.loads(json_str)
        assert parsed["type"] == "user"
        assert parsed["message"] == "Hello world"
    
    def test_system_message_stream_json(self):
        """Test system message in stream-json format."""
        message = QueuedMessage("system", "Focus on quality")
        json_str = message.to_stream_json()
        
        parsed = json.loads(json_str)
        assert parsed["type"] == "system"
        assert parsed["message"] == "Focus on quality"


class TestWorkflowMessageQueue:
    """Test WorkflowMessageQueue class."""
    
    def test_queue_creation(self):
        """Test creating a workflow message queue."""
        queue = WorkflowMessageQueue("test-run-123")
        
        assert queue.run_id == "test-run-123"
        assert queue.size() == 0
        assert queue.is_empty() is True
    
    def test_add_messages(self):
        """Test adding messages to queue."""
        queue = WorkflowMessageQueue("test-run-456")
        
        # Add first message
        size1 = queue.add_message("user", "First message")
        assert size1 == 1
        assert queue.size() == 1
        assert queue.is_empty() is False
        
        # Add second message
        size2 = queue.add_message("system", "Second message")
        assert size2 == 2
        assert queue.size() == 2
    
    def test_get_messages(self):
        """Test retrieving messages from queue."""
        queue = WorkflowMessageQueue("test-run-789")
        
        # Add test messages
        queue.add_message("user", "Message 1")
        queue.add_message("system", "Message 2")
        queue.add_message("user", "Message 3")
        
        # Get all messages (should clear queue by default)
        messages = queue.get_all_messages()
        
        assert len(messages) == 3
        assert messages[0].content == "Message 1"
        assert messages[0].message_type == "user"
        assert messages[1].content == "Message 2"
        assert messages[1].message_type == "system"
        assert messages[2].content == "Message 3"
        assert messages[2].message_type == "user"
        
        # Queue should be empty after retrieval
        assert queue.size() == 0
        assert queue.is_empty() is True
    
    def test_get_messages_preserve(self):
        """Test retrieving messages without clearing queue."""
        queue = WorkflowMessageQueue("test-run-preserve")
        
        queue.add_message("user", "Preserved message")
        
        # Get messages without clearing
        messages = queue.get_all_messages(clear=False)
        
        assert len(messages) == 1
        assert messages[0].content == "Preserved message"
        
        # Queue should still contain the message
        assert queue.size() == 1
        assert queue.is_empty() is False
    
    def test_peek(self):
        """Test peeking at messages without removing them."""
        queue = WorkflowMessageQueue("test-run-peek")
        
        queue.add_message("user", "Peek message")
        
        # Peek at messages
        peeked = queue.peek()
        
        assert len(peeked) == 1
        assert peeked[0].content == "Peek message"
        
        # Original queue should be unchanged
        assert queue.size() == 1
    
    def test_batch_as_stream_json(self):
        """Test getting batch as stream-json strings."""
        queue = WorkflowMessageQueue("test-run-json")
        
        queue.add_message("user", "First")
        queue.add_message("system", "Second")
        
        json_strings = queue.get_batch_as_stream_json()
        
        assert len(json_strings) == 2
        
        # Parse and validate JSON strings
        parsed1 = json.loads(json_strings[0])
        parsed2 = json.loads(json_strings[1])
        
        assert parsed1["type"] == "user"
        assert parsed1["message"] == "First"
        assert parsed2["type"] == "system"
        assert parsed2["message"] == "Second"
        
        # Queue should be empty after retrieval
        assert queue.size() == 0
    
    def test_queue_stats(self):
        """Test queue statistics."""
        queue = WorkflowMessageQueue("test-run-stats")
        
        # Initial stats
        stats = queue.get_stats()
        assert stats["run_id"] == "test-run-stats"
        assert stats["current_size"] == 0
        assert stats["total_added"] == 0
        assert stats["total_consumed"] == 0
        
        # Add messages
        queue.add_message("user", "Stat message 1")
        queue.add_message("user", "Stat message 2")
        
        stats = queue.get_stats()
        assert stats["current_size"] == 2
        assert stats["total_added"] == 2
        assert stats["total_consumed"] == 0
        
        # Consume messages
        queue.get_all_messages()
        
        stats = queue.get_stats()
        assert stats["current_size"] == 0
        assert stats["total_added"] == 2
        assert stats["total_consumed"] == 2


class TestMessageQueueManager:
    """Test MessageQueueManager class."""
    
    def test_manager_creation(self):
        """Test creating a message queue manager."""
        manager = MessageQueueManager()
        assert manager is not None
    
    def test_get_or_create_queue(self):
        """Test getting or creating queues."""
        manager = MessageQueueManager()
        run_id = "test-manager-run"
        
        # First call should create queue
        queue1 = manager.get_or_create_queue(run_id)
        assert isinstance(queue1, WorkflowMessageQueue)
        assert queue1.run_id == run_id
        
        # Second call should return same queue
        queue2 = manager.get_or_create_queue(run_id)
        assert queue1 is queue2
    
    def test_add_message_via_manager(self):
        """Test adding messages via manager."""
        manager = MessageQueueManager()
        run_id = "test-manager-add"
        
        # Add messages
        size1 = manager.add_message(run_id, "user", "Manager message 1")
        assert size1 == 1
        
        size2 = manager.add_message(run_id, "system", "Manager message 2")
        assert size2 == 2
    
    def test_get_messages_for_injection(self):
        """Test getting messages for injection."""
        manager = MessageQueueManager()
        run_id = "test-manager-injection"
        
        # Add messages
        manager.add_message(run_id, "user", "Inject message 1")
        manager.add_message(run_id, "user", "Inject message 2")
        
        # Get messages for injection
        messages = manager.get_messages_for_injection(run_id)
        
        assert len(messages) == 2
        
        # Should be stream-json formatted
        parsed1 = json.loads(messages[0])
        parsed2 = json.loads(messages[1])
        
        assert parsed1["type"] == "user"
        assert parsed1["message"] == "Inject message 1"
        assert parsed2["type"] == "user"
        assert parsed2["message"] == "Inject message 2"
    
    def test_queue_stats_via_manager(self):
        """Test getting queue statistics via manager."""
        manager = MessageQueueManager()
        run_id = "test-manager-stats"
        
        # Add messages
        manager.add_message(run_id, "user", "Stats test")
        
        # Get stats
        stats = manager.get_queue_stats(run_id)
        assert stats is not None
        assert stats["run_id"] == run_id
        assert stats["current_size"] == 1
        assert stats["total_added"] == 1
    
    def test_remove_queue(self):
        """Test removing a queue."""
        manager = MessageQueueManager()
        run_id = "test-manager-remove"
        
        # Create and populate queue
        manager.add_message(run_id, "user", "To be removed")
        
        # Verify queue exists
        stats = manager.get_queue_stats(run_id)
        assert stats is not None
        
        # Remove queue
        removed = manager.remove_queue(run_id)
        assert removed is True
        
        # Verify queue is gone
        stats = manager.get_queue_stats(run_id)
        assert stats is None
        
        # Removing non-existent queue should return False
        removed_again = manager.remove_queue(run_id)
        assert removed_again is False
    
    def test_get_all_stats(self):
        """Test getting all queue statistics."""
        manager = MessageQueueManager()
        
        # Create multiple queues
        manager.add_message("run-1", "user", "Message 1")
        manager.add_message("run-2", "user", "Message 2") 
        manager.add_message("run-2", "system", "Message 3")
        
        # Get all stats
        all_stats = manager.get_all_stats()
        
        assert all_stats["total_queues"] == 2
        assert "run-1" in all_stats["queues"]
        assert "run-2" in all_stats["queues"]
        assert all_stats["queues"]["run-1"]["current_size"] == 1
        assert all_stats["queues"]["run-2"]["current_size"] == 2
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        import threading
        import time
        
        manager = MessageQueueManager()
        run_id = "test-concurrent"
        results = []
        
        def add_messages(thread_id):
            for i in range(10):
                size = manager.add_message(run_id, "user", f"Thread {thread_id} message {i}")
                results.append(size)
                time.sleep(0.001)  # Small delay to encourage race conditions
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_messages, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify final state
        final_stats = manager.get_queue_stats(run_id)
        assert final_stats["total_added"] == 30  # 3 threads * 10 messages each
        assert final_stats["current_size"] == 30


class TestMessageQueueIntegration:
    """Integration tests for message queue system."""
    
    def test_full_workflow_simulation(self):
        """Test complete workflow message injection simulation."""
        manager = MessageQueueManager()
        run_id = "test-workflow-simulation"
        
        # Simulate API calls adding messages
        manager.add_message(run_id, "user", "Create a new feature")
        manager.add_message(run_id, "user", "Add error handling")
        manager.add_message(run_id, "system", "Focus on code quality")
        manager.add_message(run_id, "user", "Write unit tests")
        
        # Check queue state
        stats = manager.get_queue_stats(run_id)
        assert stats["current_size"] == 4
        assert stats["total_added"] == 4
        assert stats["total_consumed"] == 0
        
        # Simulate batch injection (what the workflow monitor does)
        messages = manager.get_messages_for_injection(run_id)
        
        # Verify all messages were retrieved in correct format
        assert len(messages) == 4
        
        # Parse messages and verify content
        parsed_messages = [json.loads(msg) for msg in messages]
        
        assert parsed_messages[0]["type"] == "user"
        assert parsed_messages[0]["message"] == "Create a new feature"
        assert parsed_messages[1]["type"] == "user"
        assert parsed_messages[1]["message"] == "Add error handling"
        assert parsed_messages[2]["type"] == "system"
        assert parsed_messages[2]["message"] == "Focus on code quality"
        assert parsed_messages[3]["type"] == "user"
        assert parsed_messages[3]["message"] == "Write unit tests"
        
        # Verify queue is empty after injection
        final_stats = manager.get_queue_stats(run_id)
        assert final_stats["current_size"] == 0
        assert final_stats["total_consumed"] == 4
        
        # Cleanup
        manager.remove_queue(run_id)
    
    def test_multiple_workflow_isolation(self):
        """Test that multiple workflows have isolated queues."""
        manager = MessageQueueManager()
        
        # Create messages for different workflows
        manager.add_message("workflow-a", "user", "Message for A")
        manager.add_message("workflow-b", "user", "Message for B")
        manager.add_message("workflow-a", "system", "Another for A")
        
        # Verify isolation
        stats_a = manager.get_queue_stats("workflow-a")
        stats_b = manager.get_queue_stats("workflow-b")
        
        assert stats_a["current_size"] == 2
        assert stats_b["current_size"] == 1
        
        # Get messages for workflow A
        messages_a = manager.get_messages_for_injection("workflow-a")
        assert len(messages_a) == 2
        
        # Workflow B should be unaffected
        stats_b_after = manager.get_queue_stats("workflow-b")
        assert stats_b_after["current_size"] == 1
        
        # Cleanup
        manager.remove_queue("workflow-a")
        manager.remove_queue("workflow-b")