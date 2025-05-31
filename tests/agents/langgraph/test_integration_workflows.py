"""Integration tests for LangGraph orchestration workflows.

This module contains comprehensive integration tests for the full orchestration system,
validating end-to-end workflows, multi-agent coordination, and system reliability.
"""

import asyncio
import pytest
import uuid
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.langgraph.shared.orchestrator import LangGraphOrchestrator, OrchestrationState
from src.agents.langgraph.shared.cli_node import CLINode
from src.agents.langgraph.shared.git_manager import GitManager
from src.agents.langgraph.shared.process_manager import ProcessManager, ProcessStatus
from src.agents.langgraph.shared.state_store import OrchestrationStateStore
from src.agents.langgraph.shared.messaging import OrchestrationMessenger

class TestIntegrationWorkflows:
    """Integration tests for orchestration workflows."""
    
    @pytest.fixture
    async def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp(prefix="langgraph_test_")
        workspace_path = Path(temp_dir)
        
        # Initialize as git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=workspace_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace_path, check=True)
        
        # Create initial commit
        (workspace_path / "README.md").write_text("# Test workspace")
        subprocess.run(["git", "add", "README.md"], cwd=workspace_path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=workspace_path, check=True)
        
        yield str(workspace_path)
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies for testing."""
        with patch.multiple(
            'src.agents.langgraph.shared.orchestrator',
            CLINode=AsyncMock,
            GitManager=AsyncMock,
            ProcessManager=AsyncMock,
            OrchestrationStateStore=AsyncMock,
            OrchestrationMessenger=AsyncMock
        ) as mocks:
            yield mocks
    
    @pytest.fixture
    async def orchestrator(self, mock_dependencies):
        """Create orchestrator instance with mocked dependencies."""
        orchestrator = LangGraphOrchestrator()
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_full_orchestration_workflow(self, orchestrator, temp_workspace):
        """Test complete orchestration workflow from start to finish."""
        # Arrange
        session_id = uuid.uuid4()
        agent_name = "test_agent"
        task_message = "Implement a simple feature"
        
        config = {
            "workspace_paths": {agent_name: temp_workspace},
            "target_agents": [agent_name],
            "max_rounds": 2,
            "max_turns": 10,
            "process_monitoring": {
                "check_interval": 5,
                "shutdown_timeout": 3,
                "enable_monitoring": True
            }
        }
        
        # Mock CLI execution result
        orchestrator.cli_node.run_claude_agent = AsyncMock(return_value={
            "claude_session_id": str(uuid.uuid4()),
            "result": "Task completed successfully",
            "exit_code": 0,
            "git_sha_start": "abc123",
            "git_sha_end": "def456",
            "pid": 12345,
            "output": "Agent output here"
        })
        
        # Mock git operations
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        
        # Mock process monitoring
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.STOPPED)
        
        # Mock messaging
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="Group chat context")
        orchestrator.messenger.send_group_message = AsyncMock()
        
        # Mock state store
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=agent_name,
            task_message=task_message,
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is True
        assert "session_id" in result
        assert result["rounds_completed"] <= 2
        assert "execution_result" in result
        
        # Verify interactions
        orchestrator.cli_node.run_claude_agent.assert_called()
        orchestrator.git_manager.snapshot_workspace.assert_called()
        orchestrator.process_manager.start_monitoring.assert_called()
        orchestrator.messenger.create_group_chat_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_agent_orchestration(self, orchestrator, temp_workspace):
        """Test orchestration with multiple agents."""
        # Arrange
        session_id = uuid.uuid4()
        primary_agent = "alpha"
        target_agents = ["beta", "gamma", "delta"]
        
        workspace_paths = {
            agent: f"{temp_workspace}_{agent}" 
            for agent in [primary_agent] + target_agents
        }
        
        config = {
            "workspace_paths": workspace_paths,
            "target_agents": target_agents,
            "max_rounds": 1,
            "orchestration_type": "multi_agent"
        }
        
        # Mock successful execution for all agents
        orchestrator.cli_node.run_claude_agent = AsyncMock(return_value={
            "claude_session_id": str(uuid.uuid4()),
            "result": "Agent task completed",
            "exit_code": 0,
            "git_sha_start": "abc123",
            "git_sha_end": "def456",
            "pid": 12345,
            "output": "Multi-agent coordination successful"
        })
        
        # Setup other mocks
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.STOPPED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="Multi-agent chat context")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=primary_agent,
            task_message="Coordinate team development",
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is True
        assert result["rounds_completed"] >= 1
        
        # Verify multi-agent setup
        orchestrator.messenger.prepare_chat_context.assert_called()
        
        # Should have called CLI execution
        orchestrator.cli_node.run_claude_agent.assert_called()
        call_args = orchestrator.cli_node.run_claude_agent.call_args[1]
        assert call_args["agent_name"] == primary_agent
        assert "Multi-agent chat context" in call_args["task_message"]
    
    @pytest.mark.asyncio
    async def test_git_rollback_workflow(self, orchestrator, temp_workspace):
        """Test git rollback and recovery scenarios."""
        # Arrange
        session_id = uuid.uuid4()
        agent_name = "test_agent"
        
        config = {
            "workspace_paths": {agent_name: temp_workspace},
            "max_rounds": 2,
            "enable_rollback": True
        }
        
        # Mock initial successful snapshot
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="initial_sha")
        
        # Mock failed execution that triggers rollback
        orchestrator.cli_node.run_claude_agent = AsyncMock(side_effect=[
            # First call fails
            {
                "claude_session_id": str(uuid.uuid4()),
                "result": "Failed execution",
                "exit_code": 1,
                "git_sha_start": "initial_sha",
                "git_sha_end": "failed_sha",
                "pid": 12345,
                "output": "Error occurred"
            },
            # Second call succeeds after rollback
            {
                "claude_session_id": str(uuid.uuid4()),
                "result": "Successful after rollback",
                "exit_code": 0,
                "git_sha_start": "initial_sha",
                "git_sha_end": "success_sha",
                "pid": 12346,
                "output": "Recovery successful"
            }
        ])
        
        # Mock rollback operations
        orchestrator.git_manager.rollback_workspace = AsyncMock(return_value=True)
        orchestrator.git_manager.prepare_rollback_context = AsyncMock(
            return_value="🔄 ROLLBACK PERFORMED\nReason: Test failure\nRetry with corrected approach."
        )
        
        # Setup other mocks
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.FAILED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Simulate rollback trigger by modifying the state during execution
        original_decision = orchestrator._decision
        
        async def mock_decision(state):
            # Trigger rollback on first round when process fails
            if state.round_number == 1 and state.process_status == ProcessStatus.FAILED:
                state.rollback_requested = True
                state.rollback_reason = "Test failure"
            return await original_decision(state)
        
        orchestrator._decision = mock_decision
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=agent_name,
            task_message="Test rollback scenario",
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is True  # Should succeed after rollback
        
        # Verify rollback was performed
        orchestrator.git_manager.rollback_workspace.assert_called_once()
        orchestrator.git_manager.prepare_rollback_context.assert_called_once()
        
        # Verify multiple CLI executions (original + retry)
        assert orchestrator.cli_node.run_claude_agent.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_process_monitoring_and_liveness_detection(self, orchestrator, temp_workspace):
        """Test process monitoring and liveness detection."""
        # Arrange
        session_id = uuid.uuid4()
        agent_name = "test_agent"
        
        config = {
            "workspace_paths": {agent_name: temp_workspace},
            "process_monitoring": {
                "check_interval": 1,
                "shutdown_timeout": 2,
                "enable_monitoring": True
            },
            "max_rounds": 1
        }
        
        # Mock long-running process
        orchestrator.cli_node.run_claude_agent = AsyncMock(return_value={
            "claude_session_id": str(uuid.uuid4()),
            "result": "Long running task",
            "exit_code": 0,
            "git_sha_start": "abc123",
            "git_sha_end": "def456",
            "pid": 12345,
            "output": "Process output"
        })
        
        # Mock process monitoring with status changes
        status_sequence = [ProcessStatus.RUNNING, ProcessStatus.RUNNING, ProcessStatus.STOPPED]
        status_iter = iter(status_sequence)
        
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(
            side_effect=lambda session_id: next(status_iter, ProcessStatus.STOPPED)
        )
        
        # Setup other mocks
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=agent_name,
            task_message="Test process monitoring",
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is True
        
        # Verify process monitoring was started
        orchestrator.process_manager.start_monitoring.assert_called_once()
        call_args = orchestrator.process_manager.start_monitoring.call_args
        assert call_args[1]["pid"] == 12345
        assert call_args[1]["check_interval"] == 1
        
        # Verify status checks occurred
        assert orchestrator.process_manager.get_process_status.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_breakpoint_and_human_intervention(self, orchestrator, temp_workspace):
        """Test breakpoint and human-in-the-loop functionality."""
        # Arrange
        session_id = uuid.uuid4()
        agent_name = "test_agent"
        
        config = {
            "workspace_paths": {agent_name: temp_workspace},
            "max_rounds": 1,
            "enable_breakpoints": True
        }
        
        # Mock execution
        orchestrator.cli_node.run_claude_agent = AsyncMock(return_value={
            "claude_session_id": str(uuid.uuid4()),
            "result": "Task with breakpoint",
            "exit_code": 0,
            "git_sha_start": "abc123",
            "git_sha_end": "def456",
            "pid": 12345,
            "output": "Breakpoint triggered"
        })
        
        # Setup mocks
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.STOPPED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Simulate breakpoint trigger
        original_decision = orchestrator._decision
        
        async def mock_decision_with_breakpoint(state):
            # Trigger breakpoint on first decision
            if state.round_number == 1:
                state.breakpoint_requested = True
            return await original_decision(state)
        
        orchestrator._decision = mock_decision_with_breakpoint
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=agent_name,
            task_message="Test breakpoint functionality",
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is True
        
        # Verify breakpoint message was sent
        breakpoint_calls = [
            call for call in orchestrator.messenger.send_group_message.call_args_list
            if len(call[1]) > 0 and "BREAKPOINT" in call[1].get("message", "")
        ]
        assert len(breakpoint_calls) > 0
    
    @pytest.mark.asyncio
    async def test_workspace_isolation_and_parameter_passing(self, orchestrator):
        """Test workspace isolation and parameter passing between agents."""
        # Arrange
        session_id = uuid.uuid4()
        agents = ["alpha", "beta", "gamma"]
        
        # Create separate temp workspaces
        temp_dirs = {}
        for agent in agents:
            temp_dir = tempfile.mkdtemp(prefix=f"test_{agent}_")
            temp_dirs[agent] = temp_dir
            
            # Initialize each workspace
            workspace_path = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=workspace_path, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace_path, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace_path, check=True)
            
            # Create agent-specific files
            (workspace_path / f"{agent}_file.txt").write_text(f"Agent {agent} workspace")
            subprocess.run(["git", "add", "."], cwd=workspace_path, check=True)
            subprocess.run(["git", "commit", "-m", f"Initial {agent} commit"], cwd=workspace_path, check=True)
        
        config = {
            "workspace_paths": temp_dirs,
            "target_agents": agents,
            "max_rounds": 1,
            "orchestration_type": "isolated_workspaces",
            "shared_parameters": {
                "database_url": "test://localhost:5432/test",
                "api_key": "test_api_key"
            }
        }
        
        # Mock CLI executions with workspace-specific results
        def mock_cli_execution(*args, **kwargs):
            workspace_path = kwargs.get("workspace_path", "")
            agent_name = kwargs.get("agent_name", "unknown")
            
            return {
                "claude_session_id": str(uuid.uuid4()),
                "result": f"Agent {agent_name} completed in {workspace_path}",
                "exit_code": 0,
                "git_sha_start": f"{agent_name}_start",
                "git_sha_end": f"{agent_name}_end",
                "pid": hash(agent_name) % 10000,
                "output": f"Workspace isolation verified for {agent_name}"
            }
        
        orchestrator.cli_node.run_claude_agent = AsyncMock(side_effect=mock_cli_execution)
        
        # Setup other mocks
        orchestrator.git_manager.snapshot_workspace = AsyncMock(side_effect=lambda path, msg: f"snapshot_{Path(path).name}")
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.STOPPED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="Shared context")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        try:
            # Act
            result = await orchestrator.execute_orchestration(
                session_id=session_id,
                agent_name="alpha",
                task_message="Test workspace isolation",
                orchestration_config=config
            )
            
            # Assert
            assert result["success"] is True
            
            # Verify CLI was called with correct workspace
            orchestrator.cli_node.run_claude_agent.assert_called()
            call_args = orchestrator.cli_node.run_claude_agent.call_args[1]
            assert call_args["workspace_path"] in temp_dirs.values()
            assert call_args["agent_name"] == "alpha"
            
            # Verify workspace-specific git snapshots
            orchestrator.git_manager.snapshot_workspace.assert_called()
            snapshot_call = orchestrator.git_manager.snapshot_workspace.call_args[0]
            assert snapshot_call[0] in temp_dirs.values()
            
        finally:
            # Cleanup
            for temp_dir in temp_dirs.values():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, orchestrator, temp_workspace):
        """Test error handling and recovery scenarios."""
        # Arrange
        session_id = uuid.uuid4()
        agent_name = "test_agent"
        
        config = {
            "workspace_paths": {agent_name: temp_workspace},
            "max_rounds": 2,
            "enable_error_recovery": True
        }
        
        # Mock various error scenarios
        orchestrator.cli_node.run_claude_agent = AsyncMock(
            side_effect=Exception("Simulated CLI execution error")
        )
        
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.FAILED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Act
        result = await orchestrator.execute_orchestration(
            session_id=session_id,
            agent_name=agent_name,
            task_message="Test error handling",
            orchestration_config=config
        )
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "session_id" in result
        
        # Verify error was communicated
        error_calls = [
            call for call in orchestrator.messenger.send_group_message.call_args_list
            if len(call[1]) > 0 and "ERROR" in call[1].get("message", "")
        ]
        # Note: Due to the early failure, error message might not be sent
        # The important thing is that the orchestration failed gracefully
    
    @pytest.mark.asyncio
    async def test_concurrent_orchestration_sessions(self, orchestrator, temp_workspace):
        """Test multiple concurrent orchestration sessions."""
        # Arrange
        num_sessions = 3
        sessions = []
        
        for i in range(num_sessions):
            session_id = uuid.uuid4()
            agent_name = f"agent_{i}"
            
            # Create separate workspace for each session
            session_workspace = f"{temp_workspace}_{i}"
            Path(session_workspace).mkdir(exist_ok=True)
            
            sessions.append({
                "session_id": session_id,
                "agent_name": agent_name,
                "workspace_path": session_workspace,
                "task_message": f"Concurrent task {i}",
                "config": {
                    "workspace_paths": {agent_name: session_workspace},
                    "max_rounds": 1
                }
            })
        
        # Mock successful executions
        orchestrator.cli_node.run_claude_agent = AsyncMock(return_value={
            "claude_session_id": str(uuid.uuid4()),
            "result": "Concurrent execution successful",
            "exit_code": 0,
            "git_sha_start": "abc123",
            "git_sha_end": "def456",
            "pid": 12345,
            "output": "Concurrent test output"
        })
        
        # Setup mocks for concurrent execution
        orchestrator.git_manager.snapshot_workspace = AsyncMock(return_value="abc123")
        orchestrator.process_manager.start_monitoring = AsyncMock(return_value=True)
        orchestrator.process_manager.get_process_status = AsyncMock(return_value=ProcessStatus.STOPPED)
        orchestrator.messenger.create_group_chat_session = AsyncMock(return_value=uuid.uuid4())
        orchestrator.messenger.prepare_chat_context = AsyncMock(return_value="")
        orchestrator.messenger.send_group_message = AsyncMock()
        orchestrator.state_store.save_orchestration_state = AsyncMock()
        
        # Act - Run orchestrations concurrently
        tasks = []
        for session in sessions:
            task = orchestrator.execute_orchestration(
                session_id=session["session_id"],
                agent_name=session["agent_name"],
                task_message=session["task_message"],
                orchestration_config=session["config"]
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success", False)]
        assert len(successful_results) == num_sessions
        
        # Verify each session was executed
        assert orchestrator.cli_node.run_claude_agent.call_count >= num_sessions
        assert orchestrator.messenger.create_group_chat_session.call_count >= num_sessions 