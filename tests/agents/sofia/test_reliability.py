"""Test Sofia agent reliability features."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from automagik.agents.pydanticai.sofia.agent import SofiaAgent


class TestSofiaAgentReliability:
    """Test reliability features in Sofia agent."""
    
    @pytest.fixture
    def sofia_agent(self):
        """Create SofiaAgent instance for testing."""
        config = {
            "model_name": "openai:gpt-4.1-mini",
            "max_tokens": "1000",
        }
        return SofiaAgent(config)
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_on_first_attempt(self, sofia_agent):
        """Test successful execution on first attempt."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Success on first try"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                result = await sofia_agent.run("Test input")
                                                
                                                assert result.success is True
                                                assert result.text == "Success on first try"
                                                
                                                # Verify agent.run was called only once (no retries)
                                                mock_agent.run.assert_called_once()
                                                
                                                # Verify semaphore was used
                                                mock_sem.__aenter__.assert_called_once()
                                                mock_sem.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_after_failures(self, sofia_agent):
        """Test successful execution after some failures."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                # Mock failures followed by success
                                mock_result = Mock()
                                mock_result.data = "Success after retries"
                                
                                mock_agent.run = AsyncMock(side_effect=[
                                    Exception("Temporary failure 1"),
                                    Exception("Temporary failure 2"),
                                    mock_result  # Success on third attempt
                                ])
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                # Mock asyncio.sleep to speed up test
                                                with patch('asyncio.sleep', new_callable=AsyncMock):
                                                    result = await sofia_agent.run("Test input")
                                                    
                                                    assert result.success is True
                                                    assert result.text == "Success after retries"
                                                    
                                                    # Verify agent.run was called 3 times (2 failures + 1 success)
                                                    assert mock_agent.run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_logic_max_retries_exceeded(self, sofia_agent):
        """Test behavior when max retries are exceeded."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                # Mock persistent failures
                                mock_agent.run = AsyncMock(side_effect=Exception("Persistent failure"))
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                # Mock settings for retry attempts
                                                with patch('automagik.agents.pydanticai.sofia.agent.settings') as mock_settings:
                                                    mock_settings.LLM_RETRY_ATTEMPTS = 3
                                                    
                                                    # Mock asyncio.sleep to speed up test
                                                    with patch('asyncio.sleep', new_callable=AsyncMock):
                                                        result = await sofia_agent.run("Test input")
                                                        
                                                        assert result.success is False
                                                        assert "Persistent failure" in result.error_message
                                                        
                                                        # Verify agent.run was called 3 times (all failures)
                                                        assert mock_agent.run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, sofia_agent):
        """Test that exponential backoff is applied correctly."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                # Mock failures followed by success
                                mock_result = Mock()
                                mock_result.data = "Success"
                                
                                mock_agent.run = AsyncMock(side_effect=[
                                    Exception("Failure 1"),
                                    Exception("Failure 2"),
                                    mock_result
                                ])
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                # Mock _retry_sleep to track delay timing specifically
                                                with patch.object(sofia_agent, '_retry_sleep', new_callable=AsyncMock) as mock_sleep:
                                                    await sofia_agent.run("Test input")
                                                    
                                                    # Verify exponential backoff: 2^0=1, 2^1=2
                                                    expected_delays = [1, 2]  # 2^(attempt-1)
                                                    actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
                                                    assert actual_delays == expected_delays
    
    @pytest.mark.asyncio
    async def test_semaphore_concurrency_control(self, sofia_agent):
        """Test that semaphore controls concurrency."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Semaphore controlled"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                await sofia_agent.run("Test input")
                                                
                                                # Verify semaphore was acquired and released
                                                mock_sem.__aenter__.assert_called_once()
                                                mock_sem.__aexit__.assert_called_once()
                                                
                                                # Verify get_llm_semaphore was called
                                                mock_semaphore.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_logging_during_retries(self, sofia_agent):
        """Test that errors are properly logged during retries."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                # Mock failure followed by success
                                mock_result = Mock()
                                mock_result.data = "Success after logging"
                                
                                mock_agent.run = AsyncMock(side_effect=[
                                    Exception("Logged failure"),
                                    mock_result
                                ])
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                # Mock logger to verify error logging
                                                with patch('automagik.agents.pydanticai.sofia.agent.logger') as mock_logger:
                                                    with patch('asyncio.sleep', new_callable=AsyncMock):
                                                        result = await sofia_agent.run("Test input")
                                                        
                                                        assert result.success is True
                                                        
                                                        # Verify warning was logged for the failure
                                                        mock_logger.warning.assert_called()
                                                        warning_call = mock_logger.warning.call_args[0][0]
                                                        assert "attempt 1/" in warning_call.lower()
                                                        assert "failed" in warning_call.lower()
    
    def test_reliability_imports_exist(self, sofia_agent):
        """Test that required imports for reliability features exist."""
        # Verify that the agent file has the necessary imports
        import automagik.agents.pydanticai.sofia.agent as sofia_module
        
        # Check for asyncio import (needed for sleep and retry logic)
        assert hasattr(sofia_module, 'asyncio')
        
        # Check for settings import (needed for retry configuration)
        assert hasattr(sofia_module, 'settings')
    
    @pytest.mark.asyncio
    async def test_reliability_configuration_from_settings(self, sofia_agent):
        """Test that retry configuration comes from settings."""
        with patch('automagik.agents.pydanticai.sofia.agent.settings') as mock_settings:
            mock_settings.LLM_RETRY_ATTEMPTS = 5  # Custom retry count
            
            with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                    with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                        with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                            with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                                with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                    # Mock persistent failures
                                    mock_agent.run = AsyncMock(side_effect=Exception("Always fails"))
                                    
                                    # Mock extract functions
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                            with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                                with patch('automagik.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                    mock_sem = AsyncMock()
                                                    mock_semaphore.return_value = mock_sem
                                                    
                                                    with patch('asyncio.sleep', new_callable=AsyncMock):
                                                        result = await sofia_agent.run("Test input")
                                                        
                                                        assert result.success is False
                                                        
                                                        # Verify custom retry count was used
                                                        assert mock_agent.run.call_count == 5 