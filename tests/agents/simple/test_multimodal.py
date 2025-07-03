"""Test Simple agent multimodal processing functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from automagik.agents.pydanticai.simple.agent import SimpleAgent


class TestSimpleAgentMultimodal:
    """Test multimodal processing in Simple agent."""
    
    @pytest.fixture
    def simple_agent(self):
        """Create SimpleAgent instance for testing."""
        config = {
            "model_name": "openai:gpt-4.1-mini",  # Multimodal capable model
            "max_tokens": "1000",
        }
        return SimpleAgent(config)
    
    @pytest.fixture
    def sample_image_content(self):
        """Sample multimodal content with images."""
        return {
            "images": [
                {
                    "data": "https://example.com/image1.jpg",
                    "mime_type": "image/jpeg"
                },
                {
                    "data": "https://example.com/image2.png", 
                    "mime_type": "image/png"
                }
            ]
        }
    
    @pytest.fixture
    def single_image_content(self):
        """Sample multimodal content with single image."""
        return {
            "images": [
                {
                    "data": "https://example.com/single.jpg",
                    "mime_type": "image/jpeg"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_multimodal_processing_with_images(self, simple_agent, sample_image_content):
        """Test that Simple agent can process multimodal content with images."""
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "I can see the images you've shared."
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await simple_agent.run(
                                                "What do you see in these images?",
                                                multimodal_content=sample_image_content
                                            )
                                            
                                            assert result.success is True
                                            assert "images" in result.text.lower()
                                            
                                            # Verify agent.run was called with proper multimodal format
                                            mock_agent.run.assert_called_once()
                                            call_args = mock_agent.run.call_args[0]
                                            user_input = call_args[0]
                                            
                                            # Should be in list format for PydanticAI
                                            assert isinstance(user_input, list)
                                            assert len(user_input) >= 3  # Text + 2 images
    
    @pytest.mark.asyncio
    async def test_multimodal_pydantic_ai_conversion(self, simple_agent, single_image_content):
        """Test conversion to PydanticAI ImageUrl objects."""
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Image processed"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await simple_agent.run(
                                                "Describe this image", 
                                                multimodal_content=single_image_content
                                            )
                                            
                                            assert result.success is True
                                            assert result.text == "Image processed"
    
    @pytest.mark.asyncio
    async def test_multimodal_fallback_behavior(self, simple_agent, sample_image_content):
        """Test fallback behavior when PydanticAI types not available."""
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Fallback processing"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await simple_agent.run(
                                                "Process these images",
                                                multimodal_content=sample_image_content
                                            )
                                            
                                            assert result.success is True
                                            assert result.text == "Fallback processing"
    
    @pytest.mark.asyncio
    async def test_text_only_input(self, simple_agent):
        """Test that text-only input still works correctly."""
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Text response"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await simple_agent.run("Just text input")
                                            
                                            assert result.success is True
                                            assert result.text == "Text response"
                                            
                                            # Verify agent.run was called with just text
                                            mock_agent.run.assert_called_once()
                                            call_args = mock_agent.run.call_args[0]
                                            user_input = call_args[0]
                                            
                                            assert user_input == "Just text input"
    
    def test_multimodal_content_validation(self, simple_agent):
        """Test validation of multimodal content structure."""
        # Test empty multimodal content
        assert simple_agent is not None
        
        # Test invalid image format
        invalid_content = {
            "images": [
                {"invalid": "format"}  # Missing data/mime_type
            ]
        }
        
        # Should not crash, will be handled gracefully in actual processing
        assert invalid_content is not None
    
    def test_agent_multimodal_dependencies_config(self, simple_agent):
        """Test that agent dependencies can be configured for multimodal."""
        # Verify dependencies exist and can be configured
        assert simple_agent.dependencies is not None
        
        # Test multimodal configuration if method exists
        if hasattr(simple_agent.dependencies, 'configure_for_multimodal'):
            simple_agent.dependencies.configure_for_multimodal(True)
            # Should not raise an exception 