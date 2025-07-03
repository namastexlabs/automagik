"""Tests for the SimpleAgent tool registration functionality.

This module verifies that tools are properly registered with the agent
according to the documentation.
"""
import unittest
import logging
from unittest.mock import patch

from automagik.agents.pydanticai.simple.agent import SimpleAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSimpleAgentTools(unittest.TestCase):
    """Test cases for SimpleAgent tool registration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "model": "openai:gpt-4.1-mini",  # Updated to match the current default
            "enable_duckduckgo_search": "true",
            "agent_id": "test-agent"
        }
    
    @patch("automagik.tools.datetime.get_current_date_tool")
    @patch("automagik.tools.datetime.get_current_time_tool")
    @patch("automagik.tools.datetime.format_date_tool")
    @patch("automagik.db.repository.memory.get_memory_by_name", return_value=None)
    @patch("automagik.db.repository.memory.create_memory", return_value=1)
    def test_tool_registration(self, mock_create_memory, mock_get_memory, mock_format_date, 
                              mock_get_time, mock_get_date):
        """Test that tools are properly registered."""
        # Mock the prompt module import
        with patch("automagik.agents.pydanticai.simple.prompts.prompt.AGENT_PROMPT", "test prompt"):
            # This test will only create the agent and check the tool registry directly
            # without trying to call _initialize_agent
            with patch.object(SimpleAgent, '_initialize_agent', return_value=None):
                # Initialize the agent
                agent = SimpleAgent(self.config)
                
                # Verify tools were registered
                tool_registry = agent.tool_registry
                tools = tool_registry.get_registered_tools()
                
                # Check for expected tool types
                self.assertGreaterEqual(len(tools), 5)  # At least date/time and memory tools
    
    @patch("automagik.db.repository.memory.get_memory_by_name", return_value=None)
    @patch("automagik.db.repository.memory.create_memory", return_value=1)
    def test_tool_types(self, mock_create_memory, mock_get_memory):
        """Test that all tools have the expected types."""
        # Mock the prompt module import
        with patch("automagik.agents.pydanticai.simple.prompts.prompt.AGENT_PROMPT", "test prompt"):
            # This test will only create the agent and check the tool registry directly
            # without trying to call _initialize_agent
            with patch.object(SimpleAgent, '_initialize_agent', return_value=None):
                # Initialize the agent
                agent = SimpleAgent(self.config)
                
                # Get tools from registry
                tool_registry = agent.tool_registry
                tools = tool_registry.get_registered_tools()
                
                # Check that all tools are registered properly
                self.assertGreaterEqual(len(tools), 5)
                
                # Check that each tool is either callable directly or has a callable function attribute
                for name, tool in tools.items():
                    is_callable = callable(tool) or (hasattr(tool, 'function') and callable(tool.function))
                    self.assertTrue(is_callable, f"Tool {name} is not callable and doesn't have a callable function")

if __name__ == "__main__":
    unittest.main() 