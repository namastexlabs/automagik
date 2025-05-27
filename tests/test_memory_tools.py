"""Tests for the refactored memory tools.

This module tests the new implementation of memory tools to ensure:
1. No circular dependencies exist
2. All operations work correctly
3. Outputs are properly structured and returned
"""
import pytest
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
    MemoryReadResult, Memory, ReadMemoryInput, CreateMemoryInput
)
from src.tools.memory.tool import (
    read_memory, create_memory, update_memory,
    get_memory_tool, store_memory_tool, list_memories_tool
)
from src.tools.memory.provider import MemoryProvider, get_memory_provider_for_agent
from src.tools.memory.interface import validate_memory_name, format_memory_content

from pydantic_ai.tools import RunContext

class TestMemoryTools:
    """Test cases for the refactored memory tools."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
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
        # Add patch for provider's import
        self.provider_list_memories_patch = patch("src.db.list_memories")
        
        # Start patches
        self.mock_list_memories = self.list_memories_patch.start()
        self.mock_get_memory = self.get_memory_patch.start()
        self.mock_create_memory = self.create_memory_patch.start()
        self.mock_update_memory = self.update_memory_patch.start()
        self.mock_agent_by_name = self.agent_by_name_patch.start()
        self.mock_agent_factory = self.agent_factory_patch.start()
        self.mock_provider_list_memories = self.provider_list_memories_patch.start()
        
        # Setup mock agent
        mock_agent = MagicMock()
        mock_agent.id = self.test_agent_id
        self.mock_agent_by_name.return_value = mock_agent
        
        # Setup mock agent factory
        self.mock_agent_factory.list_available_agents.return_value = ["test-agent"]
        
        yield
        
        # Teardown - Stop all patches
        self.list_memories_patch.stop()
        self.get_memory_patch.stop()
        self.create_memory_patch.stop()
        self.update_memory_patch.stop()
        self.agent_by_name_patch.stop()
        self.agent_factory_patch.stop()
        self.provider_list_memories_patch.stop()
    
    def test_schema_models(self):
        """Test that schema models work correctly."""
        # Test MemoryBase and Memory models
        memory = Memory(
            id="test-id",
            name=self.test_memory_name,
            content=self.test_memory_content
        )
        
        assert memory.id == "test-id"
        assert memory.name == self.test_memory_name
        assert memory.content == self.test_memory_content
        
        # Test input models
        read_input = ReadMemoryInput(name=self.test_memory_name)
        assert read_input.name == self.test_memory_name
        
        create_input = CreateMemoryInput(
            name=self.test_memory_name,
            content=self.test_memory_content
        )
        assert create_input.name == self.test_memory_name
        assert create_input.content == self.test_memory_content
        
        # Test output models
        read_result = MemoryReadResult(
            success=True,
            message="Memory found",
            content=self.test_memory_content
        )
        assert read_result.success is True
        assert read_result.message == "Memory found"
        assert read_result.content == self.test_memory_content
    
    @pytest.mark.asyncio
    async def test_memory_provider(self):
        """Test the memory provider functionality."""
        # Create a memory provider
        provider = MemoryProvider(self.test_agent_id)
        
        # Test provider registration
        assert get_memory_provider_for_agent(self.test_agent_id) == provider
        
        # Test cache operations
        provider._memory_cache[self.test_memory_name] = self.test_memory_content
        # Set cache expiry to future to prevent refresh
        from datetime import datetime, timedelta
        provider._cache_expiry = datetime.now() + timedelta(seconds=60)
        assert provider.get_memory(self.test_memory_name) == self.test_memory_content
        
        # Test cache invalidation
        provider.invalidate_cache()
        assert self.test_memory_name not in provider._memory_cache
        
        # Setup mock for list_memories
        mock_memory = MagicMock()
        mock_memory.name = self.test_memory_name
        mock_memory.content = self.test_memory_content
        self.mock_list_memories.return_value = [mock_memory]
        
        # Test cache refresh
        memory_value = provider.get_memory(self.test_memory_name)
        assert memory_value == self.test_memory_content
        self.mock_list_memories.assert_called_once_with(agent_id=self.test_agent_id)
    
    @pytest.mark.asyncio
    async def test_read_memory(self):
        """Test reading memories."""
        # Setup mock memory using a simple class instead of MagicMock
        class MockMemory:
            def __init__(self, name, content):
                self.id = "test-id"
                self.name = name
                self.content = content
                self.read_mode = "tool_calling"
                self.__dict__ = {
                    "id": "test-id",
                    "name": name,
                    "content": content,
                    "read_mode": "tool_calling"
                }
        
        mock_memory = MockMemory(self.test_memory_name, self.test_memory_content)
        
        # Test reading by name
        self.mock_list_memories.return_value = [mock_memory]
        result = await read_memory(self.mock_ctx, name=self.test_memory_name)
        
        assert result["success"] is True
        assert result["content"] == self.test_memory_content
        
        # Test reading by ID
        self.mock_get_memory.return_value = mock_memory
        result = await read_memory(self.mock_ctx, memory_id="test-id")
        
        assert result["success"] is True
        assert result["content"] == self.test_memory_content
        
        # Test list all
        self.mock_list_memories.return_value = [mock_memory]
        result = await read_memory(self.mock_ctx, list_all=True)
        
        assert result["success"] is True
        assert "memories" in result
        assert len(result["memories"]) == 1
        assert result["memories"][0]["name"] == self.test_memory_name
    
    @pytest.mark.asyncio
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
        
        assert result["success"] is True
        assert result["id"] == "test-id"
        assert result["name"] == self.test_memory_name
        
        # Verify create_memory_in_db was called with correct parameters
        self.mock_create_memory.assert_called_once()
        call_kwargs = self.mock_create_memory.call_args[1]
        assert call_kwargs["name"] == self.test_memory_name
        assert call_kwargs["content"] == self.test_memory_content
        assert call_kwargs["agent_id"] == self.test_agent_id
    
    @pytest.mark.asyncio
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
        
        assert result["success"] is True
        assert result["id"] == "test-id"
        assert result["name"] == self.test_memory_name
        
        # Verify update_memory_in_db was called with correct parameters
        self.mock_update_memory.assert_called_once()
        call_args = self.mock_update_memory.call_args
        assert call_args[1]["memory_id"] == "test-id"
        assert call_args[1]["content"] == new_content
    
    @pytest.mark.asyncio
    async def test_interface_functions(self):
        """Test interface utility functions."""
        # Test validate_memory_name
        assert validate_memory_name("valid_name") is True
        assert validate_memory_name("validName123") is True
        assert validate_memory_name("invalid name") is False
        assert validate_memory_name("invalid-name") is False
        
        # Test format_memory_content
        assert format_memory_content("test") == "test"
        assert format_memory_content({"key": "value"}) == '{"key": "value"}'
    
    @pytest.mark.asyncio
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
        
        # Mock the database functions that the tools actually use
        with patch("src.tools.memory.tool.db_get_memory_by_name") as mock_db_get, \
             patch("src.tools.memory.tool.db_create_memory") as mock_db_create:
            
            # Setup mock to return a memory object
            class MockMemory:
                def __init__(self, content):
                    self.content = content
            
            mock_db_get.return_value = MockMemory(self.test_memory_content)
            mock_db_create.return_value = "test-memory-id"
            
            # Test get_memory_tool
            result = await get_memory_tool({}, self.test_memory_name)
            assert result == self.test_memory_content
            
            # Test store_memory_tool
            result = await store_memory_tool({}, self.test_memory_name, self.test_memory_content)
            assert result == f"Memory stored with key '{self.test_memory_name}'"
            
            # Test list_memories_tool - mock the database function it uses
            with patch("src.tools.memory.tool.list_memories_in_db") as mock_list_db:
                class MockListMemory:
                    def __init__(self, name):
                        self.name = name
                
                mock_list_db.return_value = [MockListMemory(self.test_memory_name)]
                result = await list_memories_tool({})
                assert result == self.test_memory_name

if __name__ == "__main__":
    pytest.main([__file__]) 