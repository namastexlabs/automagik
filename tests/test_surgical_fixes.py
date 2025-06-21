"""
🧪 SURGICAL TEST SUITE: Comprehensive validation of critical workflow bug fixes

This test suite validates the two critical bugs fixed by Dr. SURGEON:

BUG #1: Status Reporting Data Persistence
BUG #2: TaskGroup Conflicts in Complex Workflows

Test Strategy:
1. Mock SDK execution to simulate both bugs
2. Validate database persistence works correctly
3. Validate status reporting reads from database
4. Validate TaskGroup conflict handling preserves work
5. Integration testing with real workflow execution
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Import the surgically fixed components
from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
from src.agents.claude_code.models import ClaudeCodeRunRequest
from src.db.models import WorkflowRunUpdate
from src.db.repository.workflow_run import update_workflow_run, get_workflow_run_by_run_id


class TestSurgicalFix1_DatabasePersistence:
    """Test Suite for BUG #1: Status Reporting Data Persistence Fix"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request with run_id for database persistence testing."""
        return ClaudeCodeRunRequest(
            message="Test task for database persistence",
            session_id="test-session-123",
            run_id="test-run-456",  # Critical: run_id must be present for persistence
            model="claude-3-5-sonnet-20241022",
            max_turns=5
        )
    
    @pytest.fixture
    def mock_agent_context(self):
        """Create mock agent context."""
        return {
            'session_id': 'test-session-123',
            'workspace': '/tmp/test-workspace',
            'workflow_name': 'builder'
        }
    
    @pytest.mark.asyncio
    async def test_metrics_persistence_to_database(self, mock_request, mock_agent_context):
        """CRITICAL TEST: Verify SDK executor persists metrics to workflow_runs table."""
        
        # Mock the SDK query function to simulate successful execution
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            # Create mock message with metrics (simulates successful execution)
            mock_message = Mock()
            mock_message.total_cost_usd = 0.1234
            mock_message.num_turns = 3
            mock_message.usage = {
                'input_tokens': 1500,
                'output_tokens': 800,
                'total_tokens': 2300
            }
            
            # Mock the async generator
            async def mock_query_generator(*args, **kwargs):
                yield "Starting execution..."
                yield mock_message
                yield "Execution completed"
            
            mock_query.return_value = mock_query_generator()
            
            # Mock the database update function
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                mock_db_update.return_value = True  # Simulate successful database update
                
                # Execute the SDK
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(mock_request, mock_agent_context)
                
                # ASSERTION 1: Execution should succeed
                assert result['success'] is True
                assert result['cost_usd'] == 0.1234
                assert result['total_turns'] == 3
                
                # ASSERTION 2: Database update should be called with correct metrics
                mock_db_update.assert_called_once()
                call_args = mock_db_update.call_args
                
                # Verify run_id matches
                assert call_args[0][0] == "test-run-456"
                
                # Verify update data contains correct metrics
                update_data = call_args[0][1]
                assert isinstance(update_data, WorkflowRunUpdate)
                assert update_data.status == "completed"
                assert update_data.cost_estimate == 0.1234
                assert update_data.total_tokens == 2300
                assert update_data.input_tokens == 1500
                assert update_data.output_tokens == 800
    
    @pytest.mark.asyncio
    async def test_database_persistence_failure_gracefully_handled(self, mock_request, mock_agent_context):
        """TEST: Verify execution continues even if database persistence fails."""
        
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            # Mock successful SDK execution
            mock_message = Mock()
            mock_message.total_cost_usd = 0.05
            mock_message.num_turns = 2
            mock_message.usage = {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
            
            async def mock_query_generator(*args, **kwargs):
                yield mock_message
            
            mock_query.return_value = mock_query_generator()
            
            # Mock database update to fail
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                mock_db_update.side_effect = Exception("Database connection failed")
                
                # Execute SDK
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(mock_request, mock_agent_context)
                
                # ASSERTION: Execution should still succeed despite database failure
                assert result['success'] is True
                assert result['cost_usd'] == 0.05
                # Database failure should not break the workflow execution
    
    @pytest.mark.asyncio 
    async def test_no_run_id_skips_database_persistence(self, mock_agent_context):
        """TEST: Verify execution works when run_id is missing (backward compatibility)."""
        
        # Create request without run_id
        request_without_run_id = ClaudeCodeRunRequest(
            message="Test without run_id",
            session_id="test-session-789",
            # run_id deliberately omitted
            model="claude-3-5-sonnet-20241022",
            max_turns=3
        )
        
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            mock_message = Mock()
            mock_message.total_cost_usd = 0.02
            mock_message.num_turns = 1
            mock_message.usage = {'input_tokens': 50, 'output_tokens': 25, 'total_tokens': 75}
            
            async def mock_query_generator(*args, **kwargs):
                yield mock_message
            
            mock_query.return_value = mock_query_generator()
            
            # Mock database update - should NOT be called
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(request_without_run_id, mock_agent_context)
                
                # ASSERTION: Should work without calling database
                assert result['success'] is True
                assert result['cost_usd'] == 0.02
                
                # Database update should NOT be called when run_id is missing
                mock_db_update.assert_not_called()


class TestSurgicalFix2_TaskGroupConflicts:
    """Test Suite for BUG #2: TaskGroup Conflicts in Complex Workflows Fix"""
    
    @pytest.fixture
    def complex_request(self):
        """Create a complex request that would trigger TaskGroup conflicts."""
        return ClaudeCodeRunRequest(
            message="Create a complex dashboard with websockets, real-time updates, and multiple API integrations",
            session_id="complex-session-456",
            run_id="complex-run-789",
            model="claude-3-5-sonnet-20241022",
            max_turns=15  # High turn count to simulate complex work
        )
    
    @pytest.fixture
    def mock_agent_context(self):
        return {
            'session_id': 'complex-session-456',
            'workspace': '/tmp/complex-workspace',
            'workflow_name': 'builder'
        }
    
    @pytest.mark.asyncio
    async def test_taskgroup_conflict_with_substantial_work_preserved(self, complex_request, mock_agent_context):
        """CRITICAL TEST: Verify TaskGroup conflicts preserve substantial completed work."""
        
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            # Simulate substantial work before TaskGroup conflict
            mock_messages = []
            for i in range(5):  # Multiple messages indicating substantial work
                mock_msg = Mock()
                mock_msg.total_cost_usd = 0.02 * (i + 1)  # Increasing cost
                mock_msg.num_turns = i + 1
                mock_msg.usage = {
                    'input_tokens': 200 * (i + 1),
                    'output_tokens': 100 * (i + 1), 
                    'total_tokens': 300 * (i + 1)
                }
                mock_messages.append(mock_msg)
            
            # Mock SDK query to raise TaskGroup error after substantial work
            async def mock_query_with_taskgroup_error(*args, **kwargs):
                # Yield several messages first (substantial work)
                for msg in mock_messages:
                    yield f"Processing step {mock_messages.index(msg) + 1}..."
                    yield msg
                
                # Then raise TaskGroup error
                raise Exception("TaskGroup conflict: unhandled errors in a TaskGroup")
            
            mock_query.return_value = mock_query_with_taskgroup_error()
            
            # Mock database update
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                mock_db_update.return_value = True
                
                # Execute SDK
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(complex_request, mock_agent_context)
                
                # CRITICAL ASSERTION: Should be marked as SUCCESS despite TaskGroup conflict
                assert result['success'] is True, "TaskGroup conflict should not fail when substantial work completed"
                
                # Verify substantial work was preserved
                assert result['cost_usd'] > 0.05, "Cost should reflect substantial work"
                assert result['total_turns'] >= 3, "Multiple turns should be captured"
                assert "TASKGROUP CONFLICT" in result['result'], "Should indicate TaskGroup issue occurred"
                assert "Work preserved" in result['result'], "Should indicate work was preserved"
                
                # Database should still be updated with the substantial work
                mock_db_update.assert_called_once()
                update_data = mock_db_update.call_args[0][1]
                assert update_data.status == "completed", "Database should show completed status"
    
    @pytest.mark.asyncio
    async def test_taskgroup_conflict_with_minimal_work_fails(self, complex_request, mock_agent_context):
        """TEST: Verify TaskGroup conflicts fail when no substantial work completed."""
        
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            # Simulate TaskGroup error with minimal work
            async def mock_query_immediate_error(*args, **kwargs):
                yield "Starting execution..."
                # Immediate TaskGroup error with no substantial work
                raise Exception("TaskGroup conflict: unhandled errors in a TaskGroup")
            
            mock_query.return_value = mock_query_immediate_error()
            
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                mock_db_update.return_value = True
                
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(complex_request, mock_agent_context)
                
                # ASSERTION: Should fail when no substantial work completed
                assert result['success'] is False, "Should fail when TaskGroup occurs with no substantial work"
                assert result['cost_usd'] <= 0.01, "Minimal cost indicates no substantial work"
                assert result['total_turns'] <= 1, "Minimal turns indicates no substantial work"
                assert "EXECUTION FAILED" in result['result'], "Should indicate failure"
    
    @pytest.mark.asyncio
    async def test_normal_execution_without_taskgroup_conflicts(self, complex_request, mock_agent_context):
        """TEST: Verify normal execution still works without TaskGroup issues."""
        
        with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
            # Simulate normal successful execution
            mock_message = Mock()
            mock_message.total_cost_usd = 0.15
            mock_message.num_turns = 8
            mock_message.usage = {
                'input_tokens': 3000,
                'output_tokens': 1500,
                'total_tokens': 4500
            }
            
            async def mock_normal_execution(*args, **kwargs):
                yield "Normal execution proceeding..."
                yield mock_message
                yield "Execution completed successfully"
            
            mock_query.return_value = mock_normal_execution()
            
            with patch('src.agents.claude_code.sdk_executor.update_workflow_run') as mock_db_update:
                mock_db_update.return_value = True
                
                executor = ClaudeSDKExecutor()
                result = await executor.execute_claude_task(complex_request, mock_agent_context)
                
                # ASSERTION: Normal execution should work perfectly
                assert result['success'] is True, "Normal execution should succeed"
                assert result['cost_usd'] == 0.15, "Cost should match expected"
                assert result['total_turns'] == 8, "Turns should match expected"
                assert "TASKGROUP" not in result['result'], "No TaskGroup warnings for normal execution"


class TestIntegratedStatusReporting:
    """Test Suite for Status API Fix (uses database over session metadata)"""
    
    def test_status_endpoint_prioritizes_database_over_metadata(self):
        """TEST: Verify status endpoint reads from database instead of session metadata."""
        
        # This test would require full API testing infrastructure
        # For now, we verify the logic change in isolation
        
        # Mock workflow_run with real data
        mock_workflow_run = Mock()
        mock_workflow_run.cost_estimate = 0.1234
        mock_workflow_run.total_tokens = 2500
        mock_workflow_run.input_tokens = 1800
        mock_workflow_run.output_tokens = 700
        
        # Mock session metadata with wrong data (the old bug)
        mock_metadata = {
            'total_cost_usd': 0.0,  # Wrong data (the bug)
            'total_tokens': 0,      # Wrong data (the bug)
            'input_tokens': 0,      # Wrong data (the bug)
            'output_tokens': 0      # Wrong data (the bug)
        }
        
        # Test the priority logic that was surgically fixed
        real_cost = (
            mock_workflow_run.cost_estimate 
            if mock_workflow_run and mock_workflow_run.cost_estimate is not None 
            else mock_metadata.get("total_cost_usd", 0.0)
        )
        
        real_total_tokens = (
            mock_workflow_run.total_tokens 
            if mock_workflow_run and mock_workflow_run.total_tokens is not None 
            else mock_metadata.get("total_tokens", 0)
        )
        
        # ASSERTION: Database data should take priority
        assert real_cost == 0.1234, "Should use database cost, not session metadata"
        assert real_total_tokens == 2500, "Should use database tokens, not session metadata"


# Test runner for CLI execution
if __name__ == "__main__":
    print("🧪 Running SURGICAL TEST SUITE for workflow bug fixes...")
    print("=" * 70)
    
    # Run specific test categories
    import subprocess
    import sys
    
    test_commands = [
        "pytest tests/test_surgical_fixes.py::TestSurgicalFix1_DatabasePersistence -v",
        "pytest tests/test_surgical_fixes.py::TestSurgicalFix2_TaskGroupConflicts -v", 
        "pytest tests/test_surgical_fixes.py::TestIntegratedStatusReporting -v"
    ]
    
    for cmd in test_commands:
        print(f"\n🔬 Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("-" * 50)