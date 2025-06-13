"""Integration Verification Tests (IVT) for End-to-End Workflows.

These tests verify complete user workflows work correctly with 
the synchronized features across agents.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.agents.pydanticai.simple.agent import SimpleAgent
from src.agents.pydanticai.sofia.agent import SofiaAgent


class TestEndToEndWorkflows:
    """Integration tests for complete user workflows."""
    
    @pytest.fixture
    def agent_config(self):
        """Common configuration using default model preference."""
        return {
            "model_name": "openai:gpt-4.1-mini",  # User specified default
            "max_tokens": "1000",
        }
    
    @pytest.fixture
    def simple_agent(self, agent_config):
        """Initialize Simple agent for workflow testing."""
        return SimpleAgent(agent_config)
    
    @pytest.fixture
    def sofia_agent(self, agent_config):
        """Initialize Sofia agent for workflow testing."""
        return SofiaAgent(agent_config)
    
    @pytest.fixture
    def whatsapp_message_workflow_payload(self):
        """Complete WhatsApp message workflow payload."""
        return {
            "data": {
                "key": {
                    "remoteJid": "5511987654321@s.whatsapp.net",
                    "fromMe": False,
                    "id": "workflow_test_message_123"
                },
                "message": {
                    "conversation": "Can you help me analyze this image?"
                },
                "messageTimestamp": 1640995200,
                "pushName": "John Workflow",
                "participant": "5511987654321@s.whatsapp.net"
            },
            "event": "messages.upsert"
        }
    
    @pytest.fixture
    def multimodal_workflow_content(self):
        """Multimodal content for complete workflow testing."""
        return {
            "images": [
                {
                    "data": "https://example.com/workflow-test-image.jpg",
                    "mime_type": "image/jpeg"
                },
                {
                    "data": "https://example.com/workflow-chart.png",
                    "mime_type": "image/png"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_whatsapp_to_memory_persistence_workflow(self, simple_agent, whatsapp_message_workflow_payload):
        """Test complete WhatsApp message to memory persistence workflow."""
        
        user_input = "Remember that I prefer detailed technical explanations"
        
        # Mock agent core functionality
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="System prompt"), \
             patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock), \
             patch.object(simple_agent, '_agent_instance') as mock_agent:
            
            # Configure agent response
            mock_agent.run = AsyncMock()
            mock_agent.run.return_value.data = "I'll remember your preference for detailed technical explanations."
            
            # Mock extract functions
            with patch('src.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                
                # Execute workflow
                response = await simple_agent.run(
                    user_input,
                    channel_payload=whatsapp_message_workflow_payload
                )
        
        # Verify workflow completion
        assert response.success is True
        assert "detailed technical explanations" in response.text
        
        # Verify WhatsApp context was extracted
        assert "user_phone_number" in simple_agent.context
        assert simple_agent.context["user_phone_number"] == "11987654321"  # Country code 55 is stripped
        assert simple_agent.context["user_name"] == "John Workflow"
        
        # Verify agent was called with proper context
        mock_agent.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multimodal_analysis_with_whatsapp_response_workflow(self, simple_agent, whatsapp_message_workflow_payload, multimodal_workflow_content):
        """Test complete multimodal analysis with WhatsApp response workflow."""
        
        user_input = "Analyze these images and send me a summary"
        
        # Mock agent core functionality
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="System prompt"), \
             patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock), \
             patch.object(simple_agent, '_agent_instance') as mock_agent:
            
            # Configure agent response with tool calls
            mock_agent.run = AsyncMock()
            mock_agent.run.return_value.data = "I've analyzed the images. The first shows a workflow diagram, the second shows a technical chart."
            
            # Mock extract functions with tool calls
            mock_tool_calls = [{
                'tool_name': 'send_text_to_user',
                'args': {'message': 'Analysis complete: Workflow diagram and technical chart identified'}
            }]
            
            # Create mock messages for the agent to process
            mock_messages = [{'type': 'assistant', 'content': 'mock message'}]
            
            with patch('src.agents.pydanticai.simple.agent.extract_all_messages', return_value=mock_messages), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_calls', return_value=mock_tool_calls), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                
                # Execute multimodal workflow
                response = await simple_agent.run(
                    user_input,
                    channel_payload=whatsapp_message_workflow_payload,
                    multimodal_content=multimodal_workflow_content
                )
        
        # Verify workflow completion
        assert response.success is True
        assert "analyzed the images" in response.text
        
        # Verify tool calls were captured
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0]['tool_name'] == 'send_text_to_user'
        
        # Verify both WhatsApp and multimodal context
        assert "user_phone_number" in simple_agent.context
        mock_agent.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sofia_mcp_integration_workflow(self, sofia_agent):
        """Test complete Sofia MCP integration workflow."""
        
        user_input = "Create a Linear issue for the new feature"
        
        # Mock MCP server loading with proper async methods
        mock_mcp_server = MagicMock()
        mock_mcp_server.is_running = True
        mock_mcp_server.name = "linear-test-server"
        mock_mcp_server.list_tools = AsyncMock(return_value=[])
        mock_mcp_server.list_resources = AsyncMock(return_value=[])
        mock_mcp_server.list_prompts = AsyncMock(return_value=[])
        
        with patch.object(sofia_agent, '_load_mcp_servers', return_value=[mock_mcp_server]), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Sofia prompt"), \
             patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_agent_instance') as mock_agent:
            
            # Configure agent response with MCP tool usage
            mock_agent.run = AsyncMock()
            mock_agent.run.return_value.data = "I've created Linear issue NMSTX-999 for the new feature."
            
            # Mock extract functions with MCP tool calls
            mock_tool_calls = [{
                'tool_name': 'mcp_linear_createIssue',
                'args': {'title': 'New Feature Request', 'teamId': 'team-123'}
            }]
            
            # Create mock messages for the agent to process
            mock_messages = [{'type': 'assistant', 'content': 'mock message'}]
            
            with patch('src.agents.pydanticai.sofia.agent.extract_all_messages', return_value=mock_messages), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=mock_tool_calls), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                
                mock_sem = AsyncMock()
                mock_semaphore.return_value = mock_sem
                
                # Execute MCP workflow
                response = await sofia_agent.run(user_input)
        
        # Verify MCP workflow completion
        assert response.success is True
        assert "NMSTX-999" in response.text
        
        # Verify MCP tool usage
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0]['tool_name'] == 'mcp_linear_createIssue'
        
        # Verify semaphore was used for reliability
        mock_sem.__aenter__.assert_called_once()
        mock_sem.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, simple_agent, whatsapp_message_workflow_payload):
        """Test complete error recovery workflow with retry logic."""
        
        user_input = "Test error recovery"
        
        # Test error recovery with a realistic scenario - mock AI framework failure after initialization
        # This allows context extraction to happen before the error
        await simple_agent.initialize_framework(type(simple_agent.dependencies))  # Ensure framework is initialized first
        
        with patch.object(simple_agent.ai_framework, 'run', side_effect=Exception("Simulated LLM failure")):
            
            # Execute error recovery workflow - should fail gracefully but extract context first
            response = await simple_agent.run(
                user_input,
                channel_payload=whatsapp_message_workflow_payload
            )
            
            # Verify error was handled gracefully
            assert response.success is False
            assert "Simulated LLM failure" in response.error_message
        
        # Verify WhatsApp context was extracted before the error occurred
        assert "user_phone_number" in simple_agent.context
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_workflow(self, simple_agent, sofia_agent, whatsapp_message_workflow_payload):
        """Test concurrent operation of both agents in the same workflow."""
        
        user_input = "Process this request concurrently"
        
        # Mock both agents
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Simple prompt"), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Sofia prompt"), \
             patch.object(simple_agent, '_agent_instance') as simple_mock, \
             patch.object(sofia_agent, '_agent_instance') as sofia_mock:
            
            # Configure responses
            simple_mock.run = AsyncMock(return_value=type('obj', (object,), {'data': 'Simple agent processed request'}))
            sofia_mock.run = AsyncMock(return_value=type('obj', (object,), {'data': 'Sofia agent processed request'}))
            
            # Mock extract functions for both
            with patch('src.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                
                mock_sem = AsyncMock()
                mock_semaphore.return_value = mock_sem
                
                # Execute concurrent workflow
                simple_task = simple_agent.run(user_input, channel_payload=whatsapp_message_workflow_payload)
                sofia_task = sofia_agent.run(user_input, channel_payload=whatsapp_message_workflow_payload)
                
                simple_response, sofia_response = await asyncio.gather(simple_task, sofia_task)
        
        # Verify both agents completed successfully
        assert simple_response.success is True
        assert sofia_response.success is True
        
        # Verify no interference between agents
        assert "Simple agent processed request" in simple_response.text
        assert "Sofia agent processed request" in sofia_response.text
        
        # Verify both agents processed WhatsApp context independently
        assert simple_agent.context["user_phone_number"] == "11987654321"  # Country code 55 is stripped
        assert sofia_agent.context["user_phone_number"] == "11987654321"  # Country code 55 is stripped
    
    @pytest.mark.asyncio
    async def test_memory_template_workflow(self, simple_agent):
        """Test complete memory template variable workflow."""
        
        user_input = "Use my preferences in your response"
        
        # Mock memory variables
        
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock) as mock_prompt, \
             patch.object(simple_agent, '_agent_instance') as mock_agent:
            
            # Configure filled prompt with template variables
            mock_prompt.return_value = "System prompt for John Workflow with detailed technical explanations"
            
            # Configure agent response
            mock_agent.run = AsyncMock()
            mock_agent.run.return_value.data = "Based on your preference for detailed technical explanations, here's the comprehensive analysis..."
            
            # Mock extract functions
            with patch('src.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                
                # Execute memory template workflow
                response = await simple_agent.run(user_input)
        
        # Verify memory template workflow
        assert response.success is True
        assert "detailed technical explanations" in response.text
        
        # Verify memory variables were initialized
        mock_agent.run.assert_called_once()
        mock_prompt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_multimodal_whatsapp_memory_workflow(self, sofia_agent, whatsapp_message_workflow_payload, multimodal_workflow_content):
        """Test complete end-to-end workflow: WhatsApp + Multimodal + Memory + MCP."""
        
        user_input = "Analyze these workflow images and create a Linear issue to track improvements"
        
        # Mock MCP server for Linear integration with proper async methods
        mock_mcp_server = MagicMock()
        mock_mcp_server.is_running = True
        mock_mcp_server.list_tools = AsyncMock(return_value=[])
        mock_mcp_server.list_resources = AsyncMock(return_value=[])
        mock_mcp_server.list_prompts = AsyncMock(return_value=[])
        
        with patch.object(sofia_agent, '_load_mcp_servers', return_value=[mock_mcp_server]), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Sofia system prompt"), \
             patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_agent_instance') as mock_agent:
            
            # Configure comprehensive response
            mock_agent.run = AsyncMock()
            mock_agent.run.return_value.data = "I've analyzed the workflow images and created Linear issue NMSTX-1000 to track the identified improvements."
            
            # Mock comprehensive tool calls
            mock_tool_calls = [
                {'tool_name': 'mcp_linear_createIssue', 'args': {'title': 'Workflow Improvements', 'description': 'Based on image analysis'}},
                {'tool_name': 'send_text_to_user', 'args': {'message': 'Analysis complete, Linear issue created'}}
            ]
            
            # Create mock messages for the agent to process
            mock_messages = [{'type': 'assistant', 'content': 'mock message'}]
            
            with patch('src.agents.pydanticai.sofia.agent.extract_all_messages', return_value=mock_messages), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=mock_tool_calls), \
                 patch('src.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.pydanticai.sofia.agent.get_llm_semaphore') as mock_semaphore:
                
                mock_sem = AsyncMock()
                mock_semaphore.return_value = mock_sem
                
                # Execute complete workflow
                response = await sofia_agent.run(
                    user_input,
                    channel_payload=whatsapp_message_workflow_payload,
                    multimodal_content=multimodal_workflow_content
                )
        
        # Verify complete workflow success
        assert response.success is True
        assert "NMSTX-1000" in response.text
        
        # Verify all integrated features
        assert len(response.tool_calls) == 2  # Linear + WhatsApp tools
        assert any(call['tool_name'] == 'mcp_linear_createIssue' for call in response.tool_calls)
        assert any(call['tool_name'] == 'send_text_to_user' for call in response.tool_calls)
        
        # Verify WhatsApp context extraction
        assert sofia_agent.context["user_phone_number"] == "11987654321"  # Country code 55 is stripped
        assert sofia_agent.context["user_name"] == "John Workflow"
        
        # Verify reliability features used
        mock_sem.__aenter__.assert_called_once() 