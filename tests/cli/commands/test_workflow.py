import asyncio
import pytest
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock, MagicMock
import json

from automagik.cli.commands.workflow import workflow_group, sync_flow


def test_sync_flow_with_id(capsys, event_loop):
    """Test sync_flow command when flow_id is provided."""
    # Mock the necessary dependencies
    mock_session = AsyncMock()
    mock_manager = AsyncMock()
    mock_manager.get_flow_components.return_value = [
        {"node_id": "input", "type": "input"},
        {"node_id": "output", "type": "output"},
    ]
    mock_manager.sync_flow.return_value = "new-workflow-id"

    with patch("automagik.cli.commands.workflow.get_session") as mock_get_session, \
         patch("automagik.cli.commands.workflow.WorkflowManager") as MockWorkflowManager, \
         patch("automagik.cli.commands.workflow.run_async", side_effect=event_loop.run_until_complete):
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        MockWorkflowManager.return_value.__aenter__.return_value = mock_manager

        # Run command with simulated user input
        runner = CliRunner()
        result = runner.invoke(workflow_group, ["sync", "test-flow-id"], input="1\n2\n")

        # Verify result
        assert result.exit_code == 0
        mock_manager.get_flow_components.assert_called_once_with("test-flow-id")
        mock_manager.sync_flow.assert_called_once_with(
            flow_id="test-flow-id",
            input_component="input",
            output_component="output"
        )


def test_sync_flow_interactive(capsys, event_loop):
    """Test sync_flow command in interactive mode (no flow_id provided)."""
    # Mock the necessary dependencies
    mock_session = AsyncMock()
    mock_manager = AsyncMock()
    mock_manager.list_remote_flows.return_value = [
        {"id": "flow1", "name": "Flow 1", "description": "Test flow 1"},
        {"id": "flow2", "name": "Flow 2"},
    ]
    mock_manager.get_flow_components.return_value = [
        {"node_id": "input", "type": "input"},
        {"node_id": "process", "type": "process"},
        {"node_id": "output", "type": "output"},
    ]
    mock_manager.sync_flow.return_value = "new-workflow-id"

    with patch("automagik.cli.commands.workflow.get_session") as mock_get_session, \
         patch("automagik.cli.commands.workflow.WorkflowManager") as MockWorkflowManager, \
         patch("automagik.cli.commands.workflow.run_async", side_effect=event_loop.run_until_complete):
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        MockWorkflowManager.return_value.__aenter__.return_value = mock_manager

        # Run command with simulated user input
        runner = CliRunner()
        result = runner.invoke(workflow_group, ["sync"], input="1\n1\n3\n")

        # Verify result
        assert result.exit_code == 0
        mock_manager.list_remote_flows.assert_called_once()
        mock_manager.get_flow_components.assert_called_once_with("flow1")
        mock_manager.sync_flow.assert_called_once_with(
            flow_id="flow1",
            input_component="input",
            output_component="output"
        )


def test_sync_flow_no_flows(capsys, event_loop):
    """Test sync_flow command when no flows are available."""
    # Mock the necessary dependencies
    mock_session = AsyncMock()
    mock_manager = AsyncMock()
    mock_manager.list_remote_flows.return_value = []

    with patch("automagik.cli.commands.workflow.get_session") as mock_get_session, \
         patch("automagik.cli.commands.workflow.WorkflowManager") as MockWorkflowManager, \
         patch("automagik.cli.commands.workflow.run_async", side_effect=event_loop.run_until_complete):
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        MockWorkflowManager.return_value.__aenter__.return_value = mock_manager

        # Run command
        runner = CliRunner()
        result = runner.invoke(workflow_group, ["sync"])

        # Verify result
        assert result.exit_code == 0
        mock_manager.list_remote_flows.assert_called_once()
        mock_manager.get_flow_components.assert_not_called()
        mock_manager.sync_flow.assert_not_called()


def test_sync_flow_invalid_selection(capsys, event_loop):
    """Test sync_flow command with invalid flow selection."""
    # Mock the necessary dependencies
    mock_session = AsyncMock()
    mock_manager = AsyncMock()
    mock_manager.list_remote_flows.return_value = [
        {"id": "flow1", "name": "Flow 1"},
        {"id": "flow2", "name": "Flow 2"},
    ]

    with patch("automagik.cli.commands.workflow.get_session") as mock_get_session, \
         patch("automagik.cli.commands.workflow.WorkflowManager") as MockWorkflowManager, \
         patch("automagik.cli.commands.workflow.run_async", side_effect=event_loop.run_until_complete):
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        MockWorkflowManager.return_value.__aenter__.return_value = mock_manager

        # Run command with invalid selection
        runner = CliRunner()
        result = runner.invoke(workflow_group, ["sync"], input="999\n")

        # Verify result
        assert result.exit_code == 0
        mock_manager.list_remote_flows.assert_called_once()
        mock_manager.get_flow_components.assert_not_called()
        mock_manager.sync_flow.assert_not_called()


def test_sync_flow_invalid_component_response(capsys, event_loop):
    """Test sync_flow command when component API returns invalid response."""
    # Mock the necessary dependencies
    mock_session = AsyncMock()
    mock_manager = AsyncMock()
    mock_manager.list_remote_flows.return_value = [
        {"id": "flow1", "name": "Flow 1"},
    ]
    mock_manager.get_flow_components.return_value = [
        {"node_id": "node1", "type": "genericNode", "data": {}}
    ]
    mock_manager.sync_flow.return_value = "new-workflow-id"

    with patch("automagik.cli.commands.workflow.get_session") as mock_get_session, \
         patch("automagik.cli.commands.workflow.WorkflowManager") as MockWorkflowManager, \
         patch("automagik.cli.commands.workflow.run_async", side_effect=event_loop.run_until_complete):
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        MockWorkflowManager.return_value.__aenter__.return_value = mock_manager

        # Run command with simulated user input
        runner = CliRunner()
        result = runner.invoke(workflow_group, ["sync", "flow1"], input="1\n1\n")

        # Verify result
        assert result.exit_code == 0
        mock_manager.get_flow_components.assert_called_once_with("flow1")
        mock_manager.sync_flow.assert_called_once()
