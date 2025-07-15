#!/usr/bin/env python3
"""Test workflow execution flow without requiring Claude CLI.

This tests the execution pipeline, parameter handling, and module integration
without actually running Claude.
"""

import asyncio
import sys
import os
from pathlib import Path
import tempfile
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.agents.claude_code.models import ClaudeCodeRunRequest
from automagik.agents.claude_code.sdk_execution_strategies import ExecutionStrategies
from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager


class WorkflowFlowTester:
    """Test workflow execution flow."""
    
    def __init__(self):
        self.env_manager = CLIEnvironmentManager()
        self.test_results = []
        
    async def test_parameter_validation(self):
        """Test that parameters are validated correctly."""
        print("\n🧪 Testing parameter validation...")
        
        test_cases = [
            # Valid cases
            {
                "name": "Valid simple request",
                "params": {
                    "message": "Test task",
                    "workflow_name": "builder"
                },
                "should_pass": True
            },
            {
                "name": "Valid with all parameters",
                "params": {
                    "message": "Complex task",
                    "workflow_name": "surgeon",
                    "max_turns": 50,
                    "timeout": 3600,
                    "git_branch": "feature/test",
                    "model": "sonnet",
                    "persistent": True
                },
                "should_pass": True
            },
            # Invalid cases
            {
                "name": "Empty message",
                "params": {
                    "message": "",
                    "workflow_name": "builder"
                },
                "should_pass": False
            },
            {
                "name": "Invalid workflow name",
                "params": {
                    "message": "Test",
                    "workflow_name": "invalid@workflow!"
                },
                "should_pass": False
            },
            {
                "name": "Temp workspace with git branch",
                "params": {
                    "message": "Test",
                    "workflow_name": "builder",
                    "temp_workspace": True,
                    "git_branch": "feature/test"
                },
                "should_pass": False
            }
        ]
        
        for test in test_cases:
            try:
                request = ClaudeCodeRunRequest(**test["params"])
                passed = True
                print(f"  ✅ {test['name']}: Created successfully")
            except Exception as e:
                passed = False
                print(f"  ❌ {test['name']}: {str(e)}")
                
            expected = test["should_pass"]
            if passed == expected:
                self.test_results.append(("Parameter Validation", test['name'], True))
            else:
                self.test_results.append(("Parameter Validation", test['name'], False))
                
    async def test_workflow_loading(self):
        """Test that workflows can be loaded correctly."""
        print("\n🧪 Testing workflow loading...")
        
        strategies = ExecutionStrategies(environment_manager=self.env_manager)
        
        workflows = ["builder", "surgeon", "guardian", "brain", "genie", "shipper", "lina"]
        
        for workflow in workflows:
            workspace = Path(f"automagik/agents/claude_code/workflows/{workflow}")
            
            if workspace.exists():
                try:
                    options = strategies.build_options(workspace)
                    
                    # Check if prompt was loaded
                    prompt_file = workspace / "prompt.md"
                    if prompt_file.exists():
                        has_prompt = hasattr(options, 'system_prompt') and options.system_prompt
                        print(f"  ✅ {workflow}: Loaded (prompt: {'yes' if has_prompt else 'no'})")
                        self.test_results.append(("Workflow Loading", workflow, True))
                    else:
                        print(f"  ⚠️  {workflow}: No prompt.md found")
                        self.test_results.append(("Workflow Loading", workflow, False))
                except Exception as e:
                    print(f"  ❌ {workflow}: Failed to load - {e}")
                    self.test_results.append(("Workflow Loading", workflow, False))
            else:
                print(f"  ❌ {workflow}: Directory not found")
                self.test_results.append(("Workflow Loading", workflow, False))
                
    async def test_execution_flow(self):
        """Test the execution flow with mocked Claude SDK."""
        print("\n🧪 Testing execution flow...")
        
        # Mock the Claude SDK query function
        mock_messages = [
            MagicMock(__class__=type('SystemMessage', (), {'__name__': 'SystemMessage'}), 
                     data={'session_id': 'test-session-123'}),
            MagicMock(__class__=type('AssistantMessage', (), {'__name__': 'AssistantMessage'}),
                     content=[MagicMock(text="Creating hello.py file...")]),
            MagicMock(__class__=type('ResultMessage', (), {'__name__': 'ResultMessage'}),
                     num_turns=2, duration_ms=1000, usage={'total_tokens': 500})
        ]
        
        async def mock_query(prompt, options):
            for msg in mock_messages:
                yield msg
                
        with patch('automagik.agents.claude_code.sdk_execution_strategies.query', mock_query):
            strategies = ExecutionStrategies(environment_manager=self.env_manager)
            
            request = ClaudeCodeRunRequest(
                message="Create hello.py",
                workflow_name="builder",
                run_id="test-flow-123",
                max_turns=10
            )
            
            context = {
                "workspace": tempfile.mkdtemp(),
                "user_id": "test-user"
            }
            
            try:
                result = await strategies.execute_simple(request, context)
                
                # Validate result structure
                checks = {
                    "has_success": 'success' in result,
                    "has_session_id": 'session_id' in result,
                    "has_result": 'result' in result,
                    "has_metadata": 'result_metadata' in result,
                    "correct_turns": result.get('result_metadata', {}).get('total_turns') == 2,
                    "correct_tokens": result.get('result_metadata', {}).get('total_tokens') == 500
                }
                
                for check, passed in checks.items():
                    if passed:
                        print(f"  ✅ {check}")
                    else:
                        print(f"  ❌ {check}")
                    self.test_results.append(("Execution Flow", check, passed))
                    
            except Exception as e:
                print(f"  ❌ Execution failed: {e}")
                import traceback
                traceback.print_exc()
                self.test_results.append(("Execution Flow", "execution", False))
                
    async def test_progress_tracking(self):
        """Test progress tracking functionality."""
        print("\n🧪 Testing progress tracking...")
        
        from automagik.agents.claude_code.sdk_progress_tracker import SDKProgressTracker
        
        tracker = SDKProgressTracker(
            run_id="test-progress-123",
            workflow_name="test_workflow",
            max_turns=10
        )
        
        # Test turn tracking
        tracker.track_turn('AssistantMessage')
        tracker.track_turn('UserMessage')  # Should not increment
        tracker.track_turn('AssistantMessage')
        
        assert tracker.turn_count == 2, f"Expected 2 turns, got {tracker.turn_count}"
        print("  ✅ Turn tracking works correctly")
        self.test_results.append(("Progress Tracking", "turn_tracking", True))
        
        # Test token tracking
        tracker.update_tokens({'total_tokens': 1500})
        assert tracker.token_count == 1500, f"Expected 1500 tokens, got {tracker.token_count}"
        print("  ✅ Token tracking works correctly")
        self.test_results.append(("Progress Tracking", "token_tracking", True))
        
        # Test metadata
        metadata = tracker.get_progress_metadata()
        assert metadata['current_turns'] == 2
        assert metadata['total_tokens'] == 1500
        assert metadata['workflow_name'] == 'test_workflow'
        print("  ✅ Progress metadata correct")
        self.test_results.append(("Progress Tracking", "metadata", True))
        
    async def test_message_injection(self):
        """Test message injection functionality."""
        print("\n🧪 Testing message injection...")
        
        from automagik.agents.claude_code.sdk_message_injection import SDKMessageInjector
        
        injector = SDKMessageInjector()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Test adding messages
            success = injector.add_message_to_queue(
                workspace,
                "Test message 1",
                {"priority": "high"}
            )
            assert success, "Failed to add message to queue"
            
            success = injector.add_message_to_queue(
                workspace,
                "Test message 2",
                {"priority": "normal"}
            )
            assert success, "Failed to add second message"
            
            print("  ✅ Messages added to queue")
            self.test_results.append(("Message Injection", "add_messages", True))
            
            # Test retrieving messages
            messages = await injector.check_and_process_pending_messages(workspace, "test-run")
            assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
            assert messages[0] == "Test message 1"
            assert messages[1] == "Test message 2"
            
            print("  ✅ Messages retrieved correctly")
            self.test_results.append(("Message Injection", "retrieve_messages", True))
            
            # Test that messages are marked as processed
            messages = await injector.check_and_process_pending_messages(workspace, "test-run-2")
            assert len(messages) == 0, f"Expected 0 messages (already processed), got {len(messages)}"
            
            print("  ✅ Messages marked as processed")
            self.test_results.append(("Message Injection", "process_tracking", True))
            
    async def test_cli_manager(self):
        """Test CLI manager functionality."""
        print("\n🧪 Testing CLI manager...")
        
        from automagik.agents.claude_code.sdk_cli_manager import SDKCLIManager
        
        manager = SDKCLIManager()
        
        # Test environment info
        env_info = manager.get_environment_info()
        required_keys = ['claude_in_path', 'node_path', 'python_executable', 'working_directory']
        
        for key in required_keys:
            if key in env_info:
                print(f"  ✅ {key}: {env_info[key]}")
                self.test_results.append(("CLI Manager", f"env_{key}", True))
            else:
                print(f"  ❌ {key}: Missing")
                self.test_results.append(("CLI Manager", f"env_{key}", False))
                
        # Test SDK validation
        can_import = manager.validate_claude_sdk_import()
        print(f"  {'✅' if can_import else '❌'} Claude SDK import: {can_import}")
        self.test_results.append(("CLI Manager", "sdk_import", can_import))
        
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 Workflow Flow Test Summary")
        print("="*60)
        
        # Group by category
        categories = {}
        for category, test, passed in self.test_results:
            if category not in categories:
                categories[category] = []
            categories[category].append((test, passed))
            
        total_passed = 0
        total_tests = 0
        
        for category, tests in categories.items():
            passed = sum(1 for _, p in tests if p)
            total = len(tests)
            total_passed += passed
            total_tests += total
            
            print(f"\n{category}: {passed}/{total} passed")
            for test, passed in tests:
                status = "✅" if passed else "❌"
                print(f"  {status} {test}")
                
        print(f"\n{'='*60}")
        print(f"Total: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("\n✅ All workflow flow tests passed!")
        else:
            print("\n❌ Some workflow flow tests failed.")
            
    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting workflow flow tests...\n")
        
        await self.test_parameter_validation()
        await self.test_workflow_loading()
        await self.test_execution_flow()
        await self.test_progress_tracking()
        await self.test_message_injection()
        await self.test_cli_manager()
        
        self.print_summary()


async def main():
    """Run workflow flow tests."""
    tester = WorkflowFlowTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())