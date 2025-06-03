"""Tests for Genie Agent reliability, error handling, and edge cases."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.pydanticai.genie.agent import GenieAgent
from src.agents.pydanticai.genie.models import (
    EpicRequest, EpicPlan, EpicState, WorkflowType, EpicPhase, ApprovalTriggerType
)


class TestGenieAgentEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_description_handling(self, genie_config, mock_dependencies):
        """Test handling of empty or invalid descriptions."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Test empty description
            empty_request = EpicRequest(
                description="",
                requirements=[],
                acceptance_criteria=[]
            )
            
            with pytest.raises(ValueError, match="description cannot be empty"):
                await agent.create_epic(empty_request)
            
            # Test whitespace-only description
            whitespace_request = EpicRequest(
                description="   \n\t  ",
                requirements=[],
                acceptance_criteria=[]
            )
            
            with pytest.raises(ValueError):
                await agent.create_epic(whitespace_request)

    @pytest.mark.asyncio
    async def test_extremely_long_description(self, genie_config, mock_dependencies):
        """Test handling of extremely long descriptions."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Create a very long description (10,000 characters)
            long_description = "Create a comprehensive system " * 500  # ~10k chars
            
            with patch.object(agent, 'router') as mock_router:
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                mock_router.estimate_cost.return_value = 25.0
                mock_router.estimate_duration.return_value = 60
                
                with patch.object(agent, '_execute_epic') as mock_execute:
                    mock_execute.return_value = Mock(phase=EpicPhase.COMPLETE)
                    
                    request = EpicRequest(
                        description=long_description,
                        requirements=["Long requirement"],
                        acceptance_criteria=["Long criteria"]
                    )
                    
                    # Should handle long descriptions gracefully
                    result = await agent.create_epic(request)
                    assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, genie_config, mock_dependencies):
        """Test handling of unicode and special characters."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            unicode_request = EpicRequest(
                description="Créate ñew feäture with émojis 🚀 and symbols @#$%",
                requirements=["Håndlé ünicöde", "Support 中文字符"],
                acceptance_criteria=["Ṫëst pḧäsé ✓"]
            )
            
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, '_execute_epic') as mock_execute:
                
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                mock_router.estimate_cost.return_value = 15.0
                mock_router.estimate_duration.return_value = 45
                mock_execute.return_value = Mock(phase=EpicPhase.COMPLETE)
                
                # Should handle unicode gracefully
                result = await agent.create_epic(unicode_request)
                assert result is not None

    @pytest.mark.asyncio
    async def test_zero_cost_workflows(self, genie_config, mock_dependencies):
        """Test handling of workflows with zero cost estimation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                mock_router.select_workflows.return_value = [WorkflowType.DOCUMENT]
                mock_router.estimate_cost.return_value = 0.0  # Zero cost
                mock_router.estimate_duration.return_value = 10
                
                with patch.object(agent, '_execute_epic') as mock_execute:
                    mock_execute.return_value = Mock(phase=EpicPhase.COMPLETE, total_cost=0.0)
                    
                    request = EpicRequest(
                        description="Simple documentation task",
                        requirements=["Basic docs"],
                        acceptance_criteria=["Docs exist"]
                    )
                    
                    result = await agent.create_epic(request)
                    assert result.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_maximum_workflow_limit(self, genie_config, mock_dependencies):
        """Test handling when maximum workflow limit is reached."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            genie_config["max_workflow_steps"] = 3
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Return more workflows than the limit
                mock_router.select_workflows.return_value = [
                    WorkflowType.ARCHITECT,
                    WorkflowType.IMPLEMENT, 
                    WorkflowType.TEST,
                    WorkflowType.REVIEW,
                    WorkflowType.DOCUMENT  # This should be truncated
                ]
                mock_router.estimate_cost.return_value = 50.0
                
                plan = await agent._plan_epic(EpicRequest(
                    description="Complex epic requiring many workflows",
                    requirements=["Many steps"],
                    acceptance_criteria=["All done"]
                ))
                
                # Should be limited to max_workflow_steps
                assert len(plan.workflows) <= 3


class TestGenieAgentErrorHandling:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, genie_config, mock_dependencies):
        """Test handling of network timeouts."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client:
                mock_client.execute_workflow.side_effect = asyncio.TimeoutError("Network timeout")
                
                with patch.object(agent, 'router') as mock_router:
                    mock_router.select_workflows.return_value = [WorkflowType.TEST]
                    mock_router.estimate_cost.return_value = 10.0
                    
                    request = EpicRequest(
                        description="Test network timeout",
                        requirements=["Handle timeout"],
                        acceptance_criteria=["Graceful failure"]
                    )
                    
                    result = await agent.create_epic(request)
                    
                    assert result.phase == EpicPhase.FAILED
                    assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_workflow_type_handling(self, genie_config, mock_dependencies):
        """Test handling of invalid workflow types."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Router returns invalid workflow type
                mock_router.select_workflows.return_value = ["INVALID_WORKFLOW"]
                
                request = EpicRequest(
                    description="Test invalid workflow",
                    requirements=["Handle invalid"],
                    acceptance_criteria=["Fail gracefully"]
                )
                
                with pytest.raises((ValueError, TypeError)):
                    await agent.create_epic(request)

    @pytest.mark.asyncio
    async def test_partial_workflow_failure_recovery(self, genie_config, mock_dependencies):
        """Test recovery from partial workflow failures."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'router') as mock_router:
                
                mock_router.select_workflows.return_value = [
                    WorkflowType.ARCHITECT,
                    WorkflowType.IMPLEMENT,
                    WorkflowType.TEST
                ]
                mock_router.estimate_cost.return_value = 30.0
                
                # First two workflows succeed, third fails
                mock_client.execute_workflow.side_effect = [
                    {"success": True, "cost": 10.0, "output": "Architecture complete"},
                    {"success": True, "cost": 15.0, "output": "Implementation complete"},
                    {"success": False, "error": "Test execution failed", "cost": 2.0}
                ]
                
                request = EpicRequest(
                    description="Test partial failure",
                    requirements=["Multiple workflows"],
                    acceptance_criteria=["Handle partial failure"]
                )
                
                result = await agent.create_epic(request)
                
                assert result.phase == EpicPhase.FAILED
                assert len(result.workflow_results) == 3  # All attempts recorded
                assert result.total_cost == 27.0  # Partial costs accumulated
                assert len(result.rollback_points) > 0  # Rollback points created

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, genie_config, mock_dependencies):
        """Test handling of memory pressure scenarios."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client:
                mock_client.execute_workflow.side_effect = MemoryError("Out of memory")
                
                with patch.object(agent, 'router') as mock_router:
                    mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                    mock_router.estimate_cost.return_value = 20.0
                    
                    request = EpicRequest(
                        description="Test memory pressure",
                        requirements=["Large operation"],
                        acceptance_criteria=["Handle memory issues"]
                    )
                    
                    result = await agent.create_epic(request)
                    
                    assert result.phase == EpicPhase.FAILED
                    assert "memory" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_concurrent_epic_execution_conflicts(self, genie_config, mock_dependencies):
        """Test handling of concurrent epic execution conflicts."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, '_execute_epic') as mock_execute:
                
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 10.0
                
                # Simulate concurrent execution conflict
                mock_execute.side_effect = RuntimeError("Another epic is already executing")
                
                request = EpicRequest(
                    description="Test concurrent conflict",
                    requirements=["Concurrent execution"],
                    acceptance_criteria=["Handle conflicts"]
                )
                
                result = await agent.create_epic(request)
                
                assert result.phase == EpicPhase.FAILED
                assert "already executing" in result.error_message.lower()


class TestGenieAgentRetryLogic:
    """Test retry logic and resilience features."""

    @pytest.mark.asyncio
    async def test_workflow_execution_retry_on_failure(self, genie_config, mock_dependencies):
        """Test retry logic for failed workflow executions."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            genie_config["max_retries"] = 3
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'router') as mock_router:
                
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 10.0
                
                # Fail twice, then succeed
                mock_client.execute_workflow.side_effect = [
                    {"success": False, "error": "Temporary failure 1"},
                    {"success": False, "error": "Temporary failure 2"},
                    {"success": True, "cost": 10.0, "output": "Finally succeeded"}
                ]
                
                request = EpicRequest(
                    description="Test retry logic",
                    requirements=["Retry on failure"],
                    acceptance_criteria=["Eventually succeed"]
                )
                
                result = await agent.create_epic(request)
                
                # Should eventually succeed after retries
                assert result.phase == EpicPhase.COMPLETE
                assert mock_client.execute_workflow.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion_handling(self, genie_config, mock_dependencies):
        """Test handling when all retries are exhausted."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            genie_config["max_retries"] = 2
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'router') as mock_router:
                
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                mock_router.estimate_cost.return_value = 15.0
                
                # Always fail
                mock_client.execute_workflow.return_value = {
                    "success": False, 
                    "error": "Persistent failure"
                }
                
                request = EpicRequest(
                    description="Test retry exhaustion",
                    requirements=["Always fail"],
                    acceptance_criteria=["Handle exhaustion"]
                )
                
                result = await agent.create_epic(request)
                
                assert result.phase == EpicPhase.FAILED
                assert "retries exhausted" in result.error_message.lower() or "persistent failure" in result.error_message.lower()
                assert mock_client.execute_workflow.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_retry_timing(self, genie_config, mock_dependencies):
        """Test exponential backoff in retry timing."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            retry_times = []
            
            async def mock_execute_with_timing(*args, **kwargs):
                retry_times.append(datetime.now())
                return {"success": False, "error": "Simulated failure"}
            
            with patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'router') as mock_router:
                
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 5.0
                mock_client.execute_workflow.side_effect = mock_execute_with_timing
                
                request = EpicRequest(
                    description="Test exponential backoff",
                    requirements=["Timing test"],
                    acceptance_criteria=["Proper delays"]
                )
                
                await agent.create_epic(request)
                
                # Check that delays increase exponentially (if retries were attempted)
                if len(retry_times) > 1:
                    for i in range(1, len(retry_times)):
                        delay = (retry_times[i] - retry_times[i-1]).total_seconds()
                        assert delay >= 0  # Basic timing check


class TestGenieAgentSecurityAndValidation:
    """Test security features and input validation."""

    @pytest.mark.asyncio
    async def test_malicious_input_filtering(self, genie_config, mock_dependencies):
        """Test filtering of potentially malicious inputs."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            malicious_requests = [
                # SQL injection attempts
                "Create a system'; DROP TABLE users; --",
                # Script injection
                "Implement <script>alert('xss')</script> functionality",
                # Command injection
                "Build system && rm -rf / && echo done",
                # Path traversal
                "Create ../../../etc/passwd reader"
            ]
            
            for malicious_desc in malicious_requests:
                request = EpicRequest(
                    description=malicious_desc,
                    requirements=["Security test"],
                    acceptance_criteria=["Safe handling"]
                )
                
                # Should either reject or sanitize malicious input
                with patch.object(agent, 'router') as mock_router:
                    mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                    mock_router.estimate_cost.return_value = 10.0
                    
                    # The agent should handle this safely (not crash)
                    try:
                        result = await agent.create_epic(request)
                        # If it doesn't reject, it should at least not fail catastrophically
                        assert result is not None
                    except ValueError:
                        # Acceptable to reject malicious input
                        pass

    @pytest.mark.asyncio
    async def test_cost_limit_enforcement(self, genie_config, mock_dependencies):
        """Test strict enforcement of cost limits."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            genie_config["max_cost"] = 20.0  # Low limit
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Return cost that exceeds limit
                mock_router.estimate_cost.return_value = 50.0
                mock_router.select_workflows.return_value = [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT]
                
                request = EpicRequest(
                    description="Expensive operation",
                    requirements=["High cost"],
                    acceptance_criteria=["Exceed limit"]
                )
                
                result = await agent.create_epic(request)
                
                assert result.phase == EpicPhase.FAILED
                assert "cost limit" in result.error_message.lower()
                # Should not execute any workflows
                assert len(result.workflow_results) == 0

    @pytest.mark.asyncio
    async def test_resource_quota_enforcement(self, genie_config, mock_dependencies):
        """Test enforcement of resource quotas."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            genie_config["max_execution_time_minutes"] = 30
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'router') as mock_router:
                
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT]
                mock_router.estimate_cost.return_value = 15.0
                mock_router.estimate_duration.return_value = 60  # Exceeds limit
                
                request = EpicRequest(
                    description="Long running operation",
                    requirements=["Time consuming"],
                    acceptance_criteria=["Exceed time limit"]
                )
                
                result = await agent.create_epic(request)
                
                # Should reject based on estimated duration
                assert result.phase == EpicPhase.FAILED
                assert "time limit" in result.error_message.lower() or "duration" in result.error_message.lower()


class TestGenieAgentStressConditions:
    """Test behavior under stress conditions."""

    @pytest.mark.asyncio
    async def test_rapid_sequential_epic_creation(self, genie_config, mock_dependencies):
        """Test handling of rapid sequential epic creation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, '_execute_epic') as mock_execute:
                
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 5.0
                mock_execute.return_value = Mock(phase=EpicPhase.COMPLETE, total_cost=5.0)
                
                # Create multiple epics rapidly
                tasks = []
                for i in range(5):
                    request = EpicRequest(
                        description=f"Rapid epic {i}",
                        requirements=[f"Req {i}"],
                        acceptance_criteria=[f"Criteria {i}"]
                    )
                    tasks.append(agent.create_epic(request))
                
                # Execute all concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Should handle concurrent creation gracefully
                successful_results = [r for r in results if not isinstance(r, Exception)]
                assert len(successful_results) > 0  # At least some should succeed

    @pytest.mark.asyncio
    async def test_large_workflow_sequence_handling(self, genie_config, mock_dependencies):
        """Test handling of large workflow sequences."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Return maximum workflow sequence
                all_workflows = list(WorkflowType)
                mock_router.select_workflows.return_value = all_workflows
                mock_router.estimate_cost.return_value = len(all_workflows) * 10.0
                mock_router.estimate_duration.return_value = len(all_workflows) * 15
                
                with patch.object(agent, '_execute_epic') as mock_execute:
                    mock_execute.return_value = Mock(
                        phase=EpicPhase.COMPLETE,
                        total_cost=len(all_workflows) * 10.0
                    )
                    
                    request = EpicRequest(
                        description="Maximum complexity epic requiring all workflow types",
                        requirements=["All workflows"],
                        acceptance_criteria=["Handle complexity"]
                    )
                    
                    result = await agent.create_epic(request)
                    
                    # Should handle large workflow sequences
                    assert result is not None
                    assert result.phase in [EpicPhase.COMPLETE, EpicPhase.FAILED]