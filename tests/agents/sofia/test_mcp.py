"""Test Sofia agent MCP server integration functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from automagik.agents.pydanticai.sofia.agent import SofiaAgent


class TestSofiaAgentMCP:
    """Test MCP server integration in Sofia agent."""
    
    @pytest.fixture
    def sofia_agent(self):
        """Create SofiaAgent instance for testing."""
        config = {
            "model_name": "gpt-4.1-mini",
            "max_tokens": "1000",
        }
        return SofiaAgent(config)
    
    @pytest.fixture
    def mock_mcp_servers(self):
        """Mock MCP servers for testing."""
        server1 = Mock()
        server1.is_running = True
        server1.name = "test-server-1"
        
        server2 = Mock()
        server2.is_running = True  
        server2.name = "test-server-2"
        
        return [server1, server2]
    
    @pytest.fixture
    def mock_server_manager(self):
        """Mock MCP server manager."""
        manager = Mock()
        manager.is_running = True
        manager.name = "test-server"
        manager._server = Mock()
        manager._server.is_running = True
        return manager
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_success(self, sofia_agent, mock_server_manager):
        """Test successful loading of MCP servers."""
        with patch('automagik.agents.pydanticai.sofia.agent.get_mcp_manager') as mock_get_manager:
            mock_client_manager = Mock()
            mock_client_manager.get_servers_for_agent.return_value = [mock_server_manager]
            mock_get_manager.return_value = mock_client_manager
            
            servers = await sofia_agent._load_mcp_servers()
            
            assert len(servers) == 1
            assert servers[0] is mock_server_manager._server
            mock_get_manager.assert_called_once()
            mock_client_manager.get_servers_for_agent.assert_called_once_with('sofia')
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_no_servers(self, sofia_agent):
        """Test loading when no MCP servers are assigned."""
        with patch('automagik.agents.pydanticai.sofia.agent.get_mcp_manager') as mock_get_manager:
            mock_client_manager = Mock()
            mock_client_manager.get_servers_for_agent.return_value = []
            mock_get_manager.return_value = mock_client_manager
            
            servers = await sofia_agent._load_mcp_servers()
            
            assert len(servers) == 0
            mock_get_manager.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_server_not_running(self, sofia_agent):
        """Test handling of non-running MCP servers."""
        mock_server_manager = Mock()
        mock_server_manager.is_running = False  # Server not running
        mock_server_manager.name = "stopped-server"
        
        with patch('automagik.agents.pydanticai.sofia.agent.get_mcp_manager') as mock_get_manager:
            mock_client_manager = Mock()
            mock_client_manager.get_servers_for_agent.return_value = [mock_server_manager]
            mock_get_manager.return_value = mock_client_manager
            
            servers = await sofia_agent._load_mcp_servers()
            
            assert len(servers) == 0  # Non-running servers should be skipped
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_start_server_context(self, sofia_agent):
        """Test starting server context for PydanticAI."""
        mock_server_manager = Mock()
        mock_server_manager.is_running = True
        mock_server_manager.name = "context-server"
        mock_server_manager._server = Mock()
        mock_server_manager._server.is_running = False  # Needs to be started
        mock_server_manager._server.__aenter__ = AsyncMock(return_value="server_context")
        
        with patch('automagik.agents.pydanticai.sofia.agent.get_mcp_manager') as mock_get_manager:
            mock_client_manager = Mock()
            mock_client_manager.get_servers_for_agent.return_value = [mock_server_manager]
            mock_get_manager.return_value = mock_client_manager
            
            # After starting context, mark as running
            async def side_effect():
                mock_server_manager._server.is_running = True
                return "server_context"
            
            mock_server_manager._server.__aenter__.side_effect = side_effect
            
            servers = await sofia_agent._load_mcp_servers()
            
            assert len(servers) == 1
            assert servers[0] is mock_server_manager._server
            mock_server_manager._server.__aenter__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_error_handling(self, sofia_agent):
        """Test error handling during MCP server loading."""
        with patch('automagik.agents.pydanticai.sofia.agent.get_mcp_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("MCP client manager error")
            
            servers = await sofia_agent._load_mcp_servers()
            
            assert len(servers) == 0  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_initialize_pydantic_agent_with_mcp_servers(self, sofia_agent, mock_mcp_servers):
        """Test initializing PydanticAI agent with MCP servers."""
        with patch.object(sofia_agent, '_load_mcp_servers', return_value=mock_mcp_servers):
            with patch('automagik.agents.pydanticai.sofia.agent.Agent') as mock_agent_class:
                mock_agent_instance = Mock()
                mock_agent_class.return_value = mock_agent_instance
                
                await sofia_agent._initialize_pydantic_agent()
                
                assert sofia_agent._agent_instance is mock_agent_instance
                mock_agent_class.assert_called_once()
                
                # Verify MCP servers were passed to Agent constructor
                call_kwargs = mock_agent_class.call_args[1]
                assert 'mcp_servers' in call_kwargs
                assert call_kwargs['mcp_servers'] == mock_mcp_servers
    
    @pytest.mark.asyncio
    async def test_initialize_pydantic_agent_recreate_on_server_change(self, sofia_agent):
        """Test that agent is recreated when MCP servers change."""
        # First initialization with 1 server
        with patch.object(sofia_agent, '_load_mcp_servers', return_value=[Mock()]):
            with patch('automagik.agents.pydanticai.sofia.agent.Agent') as mock_agent_class:
                mock_agent_instance = Mock()
                mock_agent_instance.mcp_servers = [Mock()]  # 1 server
                mock_agent_class.return_value = mock_agent_instance
                sofia_agent._agent_instance = mock_agent_instance
                
                # Second initialization with 2 servers
                with patch.object(sofia_agent, '_load_mcp_servers', return_value=[Mock(), Mock()]):
                    await sofia_agent._initialize_pydantic_agent()
                    
                    # Should have been called again due to server count change
                    assert mock_agent_class.call_count == 1  # Called for recreation
    
    @pytest.mark.asyncio
    async def test_mcp_integration_in_run_method(self, sofia_agent):
        """Test that MCP servers are loaded and used during run."""
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock) as mock_init:
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "MCP response"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.sofia.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await sofia_agent.run("Test with MCP")
                                            
                                            assert result.success is True
                                            assert result.text == "MCP response"
                                            
                                            # Verify agent initialization was called (which loads MCP servers)
                                            mock_init.assert_called_once()
    
    def test_sofia_agent_has_mcp_methods(self, sofia_agent):
        """Test that Sofia agent has required MCP methods."""
        assert hasattr(sofia_agent, '_load_mcp_servers')
        assert callable(sofia_agent._load_mcp_servers)
        
        # Verify method signature matches expected pattern
        import inspect
        sig = inspect.signature(sofia_agent._load_mcp_servers)
        assert len(sig.parameters) == 0  # No parameters expected
    
    @pytest.mark.asyncio
    async def test_mcp_server_tools_availability(self, sofia_agent):
        """Test that tools from MCP servers are available."""
        # This would be an integration test with actual MCP servers
        # For unit testing, we verify the pattern exists
        assert hasattr(sofia_agent, 'tool_registry')
        assert sofia_agent.tool_registry is not None
        
        # Verify that MCP integration doesn't break tool registration
        registered_tools = sofia_agent.tool_registry.get_registered_tools()
        assert isinstance(registered_tools, dict)
        
        # Should have default tools plus any MCP tools
        assert len(registered_tools) >= 1  # At least some tools should be registered 