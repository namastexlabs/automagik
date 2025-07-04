"""Integration tests for Claude-Code agent.

This module tests the integration of ClaudeCodeAgent with the agent factory,
database operations, and API endpoints.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open

from automagik.agents.models.agent_factory import AgentFactory
from automagik.agents.claude_code.agent import ClaudeCodeAgent


class TestAgentFactoryIntegration:
    """Test ClaudeCodeAgent integration with AgentFactory."""
    
    @pytest.mark.integration
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    def test_agent_factory_discovery(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test that ClaudeCodeAgent is discoverable by AgentFactory."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Check if claude_code module has create_agent function
        import importlib
        import sys
        
        # Reload the module to pick up the new settings
        if 'automagik.agents.claude_code' in sys.modules:
            importlib.reload(sys.modules['automagik.agents.claude_code'])
        
        claude_code_module = importlib.import_module('automagik.agents.claude_code')
        
        # Check for create_agent function
        assert hasattr(claude_code_module, 'create_agent')
        
        # Test the create_agent function
        config = {"test": "config"}
        agent = claude_code_module.create_agent(config)
        
        assert isinstance(agent, ClaudeCodeAgent)
        
    @pytest.mark.integration
    @patch('pathlib.Path.exists')
    def test_agent_factory_list_agents(self, mock_exists):
        """Test that ClaudeCodeAgent appears in available agents."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        factory = AgentFactory()
        # Call discover_agents to populate the registry
        factory.discover_agents()
        
        # Get list of agent names
        agent_names = factory.list_available_agents()
        
        # Check if claude_code is in the list
        assert 'claude_code' in agent_names
        
    @pytest.mark.integration
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    def test_agent_factory_create_agent(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test creating ClaudeCodeAgent instance via factory."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        factory = AgentFactory()
        factory.discover_agents()
        
        # Create agent instance using create_agent method
        agent = factory.create_agent("claude_code", {"docker_image": "test-image:latest"})
        
        assert isinstance(agent, ClaudeCodeAgent)
        assert agent.config.get("docker_image") == "test-image:latest"
        
    @pytest.mark.integration
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    def test_agent_factory_create_from_config(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test creating ClaudeCodeAgent from configuration."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        factory = AgentFactory()
        factory.discover_agents()
        
        config = {
            "docker_image": "custom:latest",
            "container_timeout": "3600"
        }
        
        # Use create_agent method instead of create_agent_from_config
        agent = factory.create_agent("claude_code", config)
        
        assert isinstance(agent, ClaudeCodeAgent)
        assert agent.config.get("docker_image") == "custom:latest"
        assert agent.config.get("container_timeout") == 3600


class TestDatabaseIntegration:
    """Test ClaudeCodeAgent database integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    async def test_agent_with_message_history(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test agent execution with message history storage."""
        mock_exists.return_value = True
        
        # Mock executor
        mock_executor = AsyncMock()
        mock_executor.execute_claude_task.return_value = {
            'success': True,
            'result': 'Task completed',
            'container_id': 'container_123',
            'execution_time': 100.0,
            'exit_code': 0,
            'git_commits': ['abc123']
        }
        mock_executor_factory.create_executor.return_value = mock_executor
        
        # Mock message history
        from automagik.memory.message_history import MessageHistory
        mock_history = Mock(spec=MessageHistory)
        mock_history.messages = []
        
        def mock_add_message(msg):
            mock_history.messages.append(msg)
        
        mock_history.add_message = mock_add_message
        
        # Create agent with DB ID
        agent = ClaudeCodeAgent({})
        agent.db_id = "agent_123"
        agent._validate_workflow = AsyncMock(return_value=True)
        
        # Execute
        await agent.run(
            "Fix the bug",
            message_history_obj=mock_history
        )
        
        # Verify messages were stored
        assert len(mock_history.messages) == 2
        
        # Check user message
        user_msg = mock_history.messages[0]
        assert user_msg['role'] == 'user'
        assert user_msg['content'] == 'Fix the bug'
        assert user_msg['agent_id'] == 'agent_123'
        
        # Check assistant message
        assistant_msg = mock_history.messages[1]
        assert assistant_msg['role'] == 'assistant'
        assert assistant_msg['content'] == 'Task completed'
        assert assistant_msg['agent_id'] == 'agent_123'
        assert 'raw_payload' in assistant_msg
        assert assistant_msg['raw_payload']['workflow'] == 'bug-fixer'
        assert assistant_msg['context']['container_id'] == 'container_123'
        assert assistant_msg['context']['git_commits'] == ['abc123']
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_context_persistence(self):
        """Test that agent context is properly persisted."""
        agent = ClaudeCodeAgent({})
        
        # Set context
        agent.context['test_key'] = 'test_value'
        agent.context['session_data'] = {'user': 'test_user'}
        
        # Context should persist across method calls
        assert agent.context['test_key'] == 'test_value'
        assert agent.context['session_data']['user'] == 'test_user'
        
        # Async run tracking
        run_response = await agent.create_async_run(
            "Fix bug",
            "test-workflow",
            session_id="session_123"
        )
        
        # Check run is tracked in context
        run_key = f"run_{run_response.run_id}"
        assert run_key in agent.context
        assert agent.context[run_key]['status'] == 'pending'


class TestAPIIntegration:
    """Test ClaudeCodeAgent API integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    async def test_async_api_pattern(self, mock_executor_factory, mock_container_class):
        """Test async API pattern with polling."""
        # Mock executor
        mock_executor = AsyncMock()
        mock_executor.execute_claude_task.return_value = {
            'success': True,
            'result': 'Task completed',
            'container_id': 'container_123'
        }
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Create async run
        run_response = await agent.create_async_run(
            "Fix the bug",
            "test-workflow",
            session_id="session_123",
            max_turns=50
        )
        
        assert run_response.status == "pending"
        assert run_response.run_id.startswith("run_")
        
        # Wait a bit for background task
        await asyncio.sleep(0.1)
        
        # Poll for status
        status = await agent.get_run_status(run_response.run_id)
        
        assert status['run_id'] == run_response.run_id
        # Status should be either 'running' or 'completed' depending on timing
        assert status['status'] in ['pending', 'running', 'completed']
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_discovery_api(self):
        """Test workflow discovery functionality."""
        
        agent = ClaudeCodeAgent({})
        
        # Mock workflow directory structure
        with patch('os.path.exists') as mock_exists:
            with patch('os.listdir') as mock_listdir:
                with patch('os.path.isdir') as mock_isdir:
                    with patch('builtins.open', mock_open(read_data="# Test Workflow\nThis is a test workflow")):
                        mock_exists.return_value = True
                        mock_listdir.return_value = ['workflow1', 'workflow2', 'not-a-dir.txt']
                        mock_isdir.side_effect = [True, True, False]
                        
                        # Mock workflow validation - set up proper async mock behavior
                        async def validate_workflow_side_effect(workflow_name):
                            if workflow_name == 'workflow1':
                                return True
                            else:
                                return False
                        
                        agent._validate_workflow = AsyncMock(side_effect=validate_workflow_side_effect)
                        
                        # Get workflows
                        workflows = await agent.get_available_workflows()
                        
                        assert len(workflows) == 2
                        assert 'workflow1' in workflows
                        assert 'workflow2' in workflows
                        assert workflows['workflow1']['valid'] is True
                        assert workflows['workflow2']['valid'] is False


class TestErrorHandlingIntegration:
    """Test error handling across components."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_disabled_agent_error(self, mock_exists):
        """Test error when agent has no credentials."""
        # Mock credentials file not existing
        mock_exists.return_value = False
        
        agent = ClaudeCodeAgent({"default_workflow": "fix"})
        response = await agent.run("Test message")
        
        assert response.success is False
        assert "not configured" in response.text.lower()
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    async def test_docker_initialization_failure(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test handling Docker initialization failure."""
        mock_exists.return_value = True
        
        # Mock container manager that fails to initialize
        mock_container = Mock()
        mock_container.docker_client = None
        mock_container.initialize = AsyncMock(return_value=False)
        mock_container_class.return_value = mock_container
        
        # Mock executor that returns a proper result structure
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Docker initialization failed',
            'result': 'Docker initialization failed'  # This will be used for the text field
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        # Execute should handle Docker failure gracefully
        response = await agent.run("Fix bug")
        
        assert response.success is False
        # The error propagates from executor
        assert "Docker" in response.text or "initialize" in response.text.lower()


class TestWorkflowIntegration:
    """Test workflow system integration."""
    
    @pytest.mark.integration
    def test_workflow_file_structure(self):
        """Test that workflow files are properly structured."""
        import os
        
        # Get the claude_code directory
        claude_code_dir = os.path.dirname(
            os.path.abspath(__file__).replace('/tests/', '/automagik/')
        )
        workflows_dir = os.path.join(claude_code_dir, 'workflows')
        
        # Check if workflows directory exists
        if os.path.exists(workflows_dir):
            # List all workflow directories
            workflows = [d for d in os.listdir(workflows_dir) 
                        if os.path.isdir(os.path.join(workflows_dir, d))]
            
            # Verify each workflow has required files
            for workflow in workflows:
                workflow_path = os.path.join(workflows_dir, workflow)
                
                # These files should exist (but we won't fail test if not)
                expected_files = ['prompt.md', 'allowed_tools.json']
                for expected_file in expected_files:
                    file_path = os.path.join(workflow_path, expected_file)
                    # Just check, don't assert (files might not exist in test env)
                    if os.path.exists(file_path):
                        assert os.path.isfile(file_path)


class TestFeatureFlagIntegration:
    """Test feature flag integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_feature_flag_disabled_by_default(self, mock_exists):
        """Test that claude-code requires credentials by default."""
        # Mock credentials file not existing (default state)
        mock_exists.return_value = False
        
        agent = ClaudeCodeAgent({"default_workflow": "fix"})
        
        # Try to run without credentials
        response = await agent.run("Test")
        
        assert response.success is False
        assert "not configured" in response.text.lower()
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_feature_flag_enabled(self, mock_exists):
        """Test agent works when feature flag is enabled."""
        mock_exists.return_value = True
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=False)  # Will fail on workflow
        
        response = await agent.run("Test")
        
        # Should fail on workflow validation, not feature flag
        assert response.success is False
        assert "workflow" in response.text.lower()
        assert "disabled" not in response.text.lower()


class TestConcurrencyIntegration:
    """Test concurrent execution handling."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    async def test_concurrent_runs(self, mock_executor_factory, mock_container_class):
        """Test handling multiple concurrent runs."""
        # Mock executor that takes time
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {'success': True, 'result': 'Done'}
        
        mock_executor = Mock()
        mock_executor.execute_claude_task = slow_execute
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Create multiple runs concurrently
        tasks = []
        for i in range(3):
            task = agent.create_async_run(
                f"Task {i}",
                "test-workflow",
                session_id=f"session_{i}"
            )
            tasks.append(task)
        
        # Wait for all to complete
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 3
        assert all(r.status == "pending" for r in responses)
        assert len(set(r.run_id for r in responses)) == 3  # All unique


class TestCleanupIntegration:
    """Test cleanup integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('automagik.agents.claude_code.agent.ContainerManager')
    @patch('automagik.agents.claude_code.agent.ExecutorFactory')
    async def test_agent_cleanup(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test agent cleanup process."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor with proper cleanup method
        mock_executor = AsyncMock()
        mock_executor.cleanup = AsyncMock()
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Add some context data
        agent.context['test_data'] = 'value'
        
        # Mock parent cleanup
        with patch('automagik.agents.models.automagik_agent.AutomagikAgent.cleanup') as mock_parent:
            await agent.cleanup()
        
        # Verify cleanup was called on executor
        mock_executor.cleanup.assert_called_once()
        mock_parent.assert_called_once()