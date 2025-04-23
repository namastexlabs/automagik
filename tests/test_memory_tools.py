"""Tests for the refactored memory tools.

This module tests the new implementation of memory tools to ensure:
1. No circular dependencies exist
2. All operations work correctly
3. Outputs are properly structured and returned
"""
import asyncio
import unittest
import os
import sys
import logging
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the new memory tools package
from src.tools.memory.schema import (
    MemoryReadResult, MemoryCreateResponse, MemoryUpdateResponse,
    Memory, ReadMemoryInput, CreateMemoryInput, UpdateMemoryInput
)
from src.tools.memory.tool import (
    read_memory, create_memory, update_memory,
    map_agent_id, _convert_to_memory_object,
    get_memory_tool, store_memory_tool, list_memories_tool
)
from src.tools.memory.provider import MemoryProvider, get_memory_provider_for_agent
from src.tools.memory.interface import invalidate_memory_cache, validate_memory_name, format_memory_content

from pydantic_ai.tools import RunContext

class TestMemoryTools(unittest.TestCase):
    """Test cases for the refactored memory tools."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Generate a unique name for test memories
        self.test_memory_name = f"test_memory_{uuid.uuid4().hex[:8]}"
        self.test_memory_content = f"This is a test memory created at {datetime.now()}"
        
        # Create mock RunContext for testing
        model = None
        usage = None
        prompt = None
        self.mock_ctx = RunContext({}, model=model, usage=usage, prompt=prompt)
        
        # Generate a high agent ID unlikely to conflict with real agents
        self.test_agent_id = 9999
        
        # Set up patches
        self.list_memories_patch = patch("src.tools.memory.tool.list_memories_in_db")
        self.get_memory_patch = patch("src.tools.memory.tool.get_memory_in_db")
        self.create_memory_patch = patch("src.tools.memory.tool.create_memory_in_db")
        self.update_memory_patch = patch("src.tools.memory.tool.update_memory_in_db")
        self.agent_by_name_patch = patch("src.tools.memory.tool.get_agent_by_name")
        self.agent_factory_patch = patch("src.tools.memory.tool.AgentFactory")
        
        # Start patches
        self.mock_list_memories = self.list_memories_patch.start()
        self.mock_get_memory = self.get_memory_patch.start()
        self.mock_create_memory = self.create_memory_patch.start()
        self.mock_update_memory = self.update_memory_patch.start()
        self.mock_agent_by_name = self.agent_by_name_patch.start()
        self.mock_agent_factory = self.agent_factory_patch.start()
        
        # Setup mock agent
        mock_agent = MagicMock()
        mock_agent.id = self.test_agent_id
        self.mock_agent_by_name.return_value = mock_agent
        
        # Setup mock agent factory
        self.mock_agent_factory.list_available_agents.return_value = ["test-agent"]
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop all patches
        self.list_memories_patch.stop()
        self.get_memory_patch.stop()
        self.create_memory_patch.stop()
        self.update_memory_patch.stop()
        self.agent_by_name_patch.stop()
        self.agent_factory_patch.stop()
    
    def test_schema_models(self):
        """Test that schema models work correctly."""
        # Test MemoryBase and Memory models
        memory = Memory(
            id="test-id",
            name=self.test_memory_name,
            content=self.test_memory_content
        )
        
        self.assertEqual(memory.id, "test-id")
        self.assertEqual(memory.name, self.test_memory_name)
        self.assertEqual(memory.content, self.test_memory_content)
        
        # Test input models
        read_input = ReadMemoryInput(name=self.test_memory_name)
        self.assertEqual(read_input.name, self.test_memory_name)
        
        create_input = CreateMemoryInput(
            name=self.test_memory_name,
            content=self.test_memory_content
        )
        self.assertEqual(create_input.name, self.test_memory_name)
        self.assertEqual(create_input.content, self.test_memory_content)
        
        # Test output models
        read_result = MemoryReadResult(
            success=True,
            message="Memory found",
            content=self.test_memory_content
        )
        self.assertEqual(read_result.success, True)
        self.assertEqual(read_result.message, "Memory found")
        self.assertEqual(read_result.content, self.test_memory_content)
    
    async def test_memory_provider(self):
        """Test the memory provider functionality."""
        # Create a memory provider
        provider = MemoryProvider(self.test_agent_id)
        
        # Test provider registration
        self.assertEqual(get_memory_provider_for_agent(self.test_agent_id), provider)
        
        # Test cache operations
        provider._memory_cache[self.test_memory_name] = self.test_memory_content
        self.assertEqual(provider.get_memory(self.test_memory_name), self.test_memory_content)
        
        # Test cache invalidation
        provider.invalidate_cache()
        self.assertNotIn(self.test_memory_name, provider._memory_cache)
        
        # Setup mock for list_memories
        mock_memory = MagicMock()
        mock_memory.name = self.test_memory_name
        mock_memory.content = self.test_memory_content
        self.mock_list_memories.return_value = [mock_memory]
        
        # Test cache refresh
        memory_value = provider.get_memory(self.test_memory_name)
        self.assertEqual(memory_value, self.test_memory_content)
        self.mock_list_memories.assert_called_once_with(agent_id=self.test_agent_id)
    
    async def test_read_memory(self):
        """Test reading memories."""
        # Setup mock memory
        mock_memory = MagicMock()
        mock_memory.id = "test-id"
        mock_memory.name = self.test_memory_name
        mock_memory.content = self.test_memory_content
        mock_memory.read_mode = "tool_calling"
        mock_memory.__dict__ = {
            "id": "test-id",
            "name": self.test_memory_name,
            "content": self.test_memory_content,
            "read_mode": "tool_calling"
        }
        
        # Test reading by name
        self.mock_list_memories.return_value = [mock_memory]
        result = await read_memory(self.mock_ctx, name=self.test_memory_name)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], self.test_memory_content)
        
        # Test reading by ID
        self.mock_get_memory.return_value = mock_memory
        result = await read_memory(self.mock_ctx, memory_id="test-id")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], self.test_memory_content)
        
        # Test list all
        self.mock_list_memories.return_value = [mock_memory]
        result = await read_memory(self.mock_ctx, list_all=True)
        
        self.assertTrue(result["success"])
        self.assertIn("memories", result)
        self.assertEqual(len(result["memories"]), 1)
        self.assertEqual(result["memories"][0]["name"], self.test_memory_name)
    
    async def test_create_memory(self):
        """Test creating memories."""
        # Setup mock for create_memory_in_db
        mock_memory = MagicMock()
        mock_memory.id = "test-id"
        mock_memory.name = self.test_memory_name
        self.mock_create_memory.return_value = mock_memory
        
        # Test creating memory
        result = await create_memory(
            self.mock_ctx,
            name=self.test_memory_name,
            content=self.test_memory_content
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["id"], "test-id")
        self.assertEqual(result["name"], self.test_memory_name)
        
        # Verify create_memory_in_db was called with correct parameters
        self.mock_create_memory.assert_called_once()
        call_kwargs = self.mock_create_memory.call_args[1]
        self.assertEqual(call_kwargs["name"], self.test_memory_name)
        self.assertEqual(call_kwargs["content"], self.test_memory_content)
        self.assertEqual(call_kwargs["agent_id"], self.test_agent_id)
    
    async def test_update_memory(self):
        """Test updating memories."""
        # Setup mocks
        mock_memory = MagicMock()
        mock_memory.id = "test-id"
        mock_memory.name = self.test_memory_name
        self.mock_get_memory.return_value = mock_memory
        
        updated_mock = MagicMock()
        updated_mock.id = "test-id"
        updated_mock.name = self.test_memory_name
        self.mock_update_memory.return_value = updated_mock
        
        # Test updating by ID
        new_content = f"Updated content at {datetime.now()}"
        result = await update_memory(
            self.mock_ctx,
            memory_id="test-id",
            content=new_content
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["id"], "test-id")
        self.assertEqual(result["name"], self.test_memory_name)
        
        # Verify update_memory_in_db was called with correct parameters
        self.mock_update_memory.assert_called_once()
        call_args = self.mock_update_memory.call_args
        self.assertEqual(call_args[1]["memory_id"], "test-id")
        self.assertEqual(call_args[1]["content"], new_content)
    
    async def test_interface_functions(self):
        """Test interface utility functions."""
        # Test validate_memory_name
        self.assertTrue(validate_memory_name("valid_name"))
        self.assertTrue(validate_memory_name("validName123"))
        self.assertFalse(validate_memory_name("invalid name"))
        self.assertFalse(validate_memory_name("invalid-name"))
        
        # Test format_memory_content
        self.assertEqual(format_memory_content("test"), "test")
        self.assertEqual(format_memory_content({"key": "value"}), '{"key": "value"}')
    
    async def test_common_tools_connector(self):
        """Test that the common tools connector works correctly."""
        # Setup mocks
        mock_read = AsyncMock()
        mock_create = AsyncMock()
        mock_list = AsyncMock()
        
        read_result = {"success": True, "content": self.test_memory_content}
        create_result = {"success": True, "id": "test-id", "name": self.test_memory_name}
        list_result = {
            "success": True, 
            "memories": [{"name": self.test_memory_name}]
        }
        
        mock_read.return_value = read_result
        mock_create.return_value = create_result
        mock_list.return_value = list_result
        
        with patch("src.tools.memory.tool.raw_read_memory", mock_read), \
             patch("src.tools.memory.tool.raw_create_memory", mock_create), \
             patch("src.tools.memory.tool.raw_read_memory", mock_list):
            
            # Test get_memory_tool
            result = await get_memory_tool(self.test_memory_name)
            self.assertEqual(result, self.test_memory_content)
            
            # Test store_memory_tool
            result = await store_memory_tool(self.test_memory_name, self.test_memory_content)
            self.assertEqual(result, f"Memory stored with key '{self.test_memory_name}'")
            
            # Test list_memories_tool
            with patch("src.tools.memory.tool.raw_read_memory", mock_list):
                result = await list_memories_tool()
                self.assertEqual(result, self.test_memory_name)

if __name__ == "__main__":
    # Convert async tests to sync
    for attr in dir(TestMemoryTools):
        if attr.startswith("test_") and attr != "test_schema_models":
            async_test = getattr(TestMemoryTools, attr)
            setattr(TestMemoryTools, attr, lambda self, async_test=async_test: asyncio.run(async_test(self)))
    
    unittest.main() 