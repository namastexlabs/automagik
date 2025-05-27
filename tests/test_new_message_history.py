"""Tests for the simplified MessageHistory implementation.

This module contains tests to verify that the new MessageHistory implementation works correctly,
is compatible with PydanticAI, and integrates directly with the repository pattern.
"""

import unittest
import uuid
import logging

from src.memory.message_history import MessageHistory
from pydantic_ai.messages import (
    ModelRequest, 
    ModelResponse,
    SystemPromptPart, 
    UserPromptPart, 
    TextPart,
    ToolCallPart,
    ToolReturnPart
)

# Configure logging - only show errors during tests
logging.basicConfig(level=logging.ERROR)

class TestNewMessageHistory(unittest.TestCase):
    """Test the new MessageHistory implementation."""
    
    def setUp(self):
        """Set up a fresh MessageHistory instance for each test."""
        self.session_id = str(uuid.uuid4())
        self.message_history = MessageHistory(session_id=self.session_id)
    
    def test_create_with_system_prompt(self):
        """Test creating a MessageHistory with a system prompt."""
        system_prompt = "This is a system prompt."
        history = MessageHistory(self.session_id, system_prompt)
        
        # Get all messages and check if the system prompt is there
        messages = history.all_messages()
        self.assertTrue(any(
            any(isinstance(part, SystemPromptPart) and part.content == system_prompt 
                for part in msg.parts)
            for msg in messages
        ))
    
    def test_add_user_message(self):
        """Test adding a user message to the history."""
        content = "This is a user message."
        user_message = self.message_history.add(content)
        
        # Verify the returned message
        self.assertTrue(isinstance(user_message, ModelRequest))
        self.assertTrue(any(isinstance(part, UserPromptPart) for part in user_message.parts))
        
        # Verify the message is in the history
        messages = self.message_history.all_messages()
        self.assertTrue(any(
            any(isinstance(part, UserPromptPart) and part.content == content 
                for part in msg.parts)
            for msg in messages
        ))
    
    def test_add_assistant_message(self):
        """Test adding an assistant message to the history."""
        content = "This is an assistant message."
        assistant_message = self.message_history.add_response(content)
        
        # Verify the returned message
        self.assertTrue(isinstance(assistant_message, ModelResponse))
        self.assertTrue(any(isinstance(part, TextPart) for part in assistant_message.parts))
        
        # Verify the message is in the history
        messages = self.message_history.all_messages()
        self.assertTrue(any(
            any(isinstance(part, TextPart) and part.content == content 
                for part in msg.parts)
            for msg in messages
        ))
    
    def test_add_assistant_message_with_tools(self):
        """Test adding an assistant message with tool calls and outputs."""
        content = "This is an assistant message with tools."
        tool_calls = [
            {
                "tool_name": "calculator",
                "args": {"expression": "2+2"},
                "tool_call_id": "call_123"
            }
        ]
        tool_outputs = [
            {
                "tool_name": "calculator",
                "content": "4",
                "tool_call_id": "call_123"
            }
        ]
        
        # Add message with tools
        assistant_message = self.message_history.add_response(
            content=content,
            tool_calls=tool_calls,
            tool_outputs=tool_outputs
        )
        
        # Verify the returned message
        self.assertTrue(isinstance(assistant_message, ModelResponse))
        self.assertTrue(any(isinstance(part, TextPart) for part in assistant_message.parts))
        self.assertTrue(any(isinstance(part, ToolCallPart) for part in assistant_message.parts))
        self.assertTrue(any(isinstance(part, ToolReturnPart) for part in assistant_message.parts))
        
        # Verify the message is in the history
        messages = self.message_history.all_messages()
        tool_call_parts = [
            part for msg in messages 
            for part in msg.parts 
            if isinstance(part, ToolCallPart)
        ]
        tool_return_parts = [
            part for msg in messages 
            for part in msg.parts 
            if isinstance(part, ToolReturnPart)
        ]
        
        self.assertTrue(len(tool_call_parts) > 0)
        self.assertTrue(len(tool_return_parts) > 0)
    
    def test_all_messages(self):
        """Test the all_messages method returns all messages."""
        # Add some messages
        self.message_history.add_system_prompt("System prompt")
        self.message_history.add("User message 1")
        self.message_history.add_response("Assistant message 1")
        self.message_history.add("User message 2")
        self.message_history.add_response("Assistant message 2")
        
        # Check all messages
        messages = self.message_history.all_messages()
        self.assertEqual(len(messages), 5)  # System + 2 user + 2 assistant
    
    def test_new_messages(self):
        """Test the new_messages method returns the correct messages."""
        # Add some messages
        self.message_history.add_system_prompt("System prompt")
        self.message_history.add("User message 1")
        self.message_history.add_response("Assistant message 1")
        
        # For now, new_messages should be the same as all_messages
        self.assertEqual(len(self.message_history.new_messages()), 
                         len(self.message_history.all_messages()))
    
    def test_json_serialization(self):
        """Test serializing messages to JSON and back."""
        # Add some messages
        self.message_history.add_system_prompt("System prompt")
        self.message_history.add("User message")
        self.message_history.add_response("Assistant message")
        
        # Serialize to JSON
        json_data = self.message_history.to_json()
        
        # Create a new history from the JSON
        new_session_id = str(uuid.uuid4())
        new_history = MessageHistory.from_json(json_data, new_session_id)
        
        # Verify the new history has the same messages
        self.assertEqual(len(new_history.all_messages()), len(self.message_history.all_messages()))
    
    def test_from_model_messages(self):
        """Test creating a MessageHistory from a list of ModelMessage objects."""
        # Create some model messages
        system_message = ModelRequest(parts=[SystemPromptPart(content="System prompt")])
        user_message = ModelRequest(parts=[UserPromptPart(content="User message")])
        assistant_message = ModelResponse(parts=[TextPart(content="Assistant message")])
        
        # Create a history from these messages
        model_messages = [system_message, user_message, assistant_message]
        new_session_id = str(uuid.uuid4())
        history = MessageHistory.from_model_messages(model_messages, new_session_id)
        
        # Verify the history has all the messages
        messages = history.all_messages()
        self.assertEqual(len(messages), 3)
    
    def test_clear(self):
        """Test clearing the message history."""
        # Add some messages
        self.message_history.add_system_prompt("System prompt")
        self.message_history.add("User message")
        self.message_history.add_response("Assistant message")
        
        # Verify messages were added
        self.assertTrue(len(self.message_history.all_messages()) > 0)
        
        # Clear the history
        self.message_history.clear()
        
        # Verify messages were cleared
        self.assertEqual(len(self.message_history.all_messages()), 0)


if __name__ == "__main__":
    unittest.main() 