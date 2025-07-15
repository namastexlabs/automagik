#!/usr/bin/env python3
"""Workflow validation scenarios for Claude Code execution.

This module defines test scenarios to validate that workflows execute correctly
with different parameter combinations and handle various outcomes properly.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import tempfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.agents.claude_code.models import ClaudeCodeRunRequest
from automagik.agents.claude_code.sdk_execution_strategies import ExecutionStrategies
from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager
from automagik.db.models import WorkflowRunCreate, WorkflowRunUpdate
from automagik.db.repository.workflow_run import (
    create_workflow_run,
    get_workflow_run_by_run_id,
    update_workflow_run_by_run_id
)


class WorkflowTestScenario:
    """Base class for workflow test scenarios."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.request: Optional[ClaudeCodeRunRequest] = None
        self.expected_outcomes: List[str] = []
        self.validation_points: Dict[str, Any] = {}
        
    def build_request(self) -> ClaudeCodeRunRequest:
        """Build the request for this scenario."""
        raise NotImplementedError
        
    def validate_pre_execution(self, context: Dict[str, Any]) -> bool:
        """Validate conditions before execution."""
        return True
        
    def validate_during_execution(self, progress: Dict[str, Any]) -> bool:
        """Validate progress during execution."""
        return True
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Validate results after execution."""
        return True


class SimpleTaskScenario(WorkflowTestScenario):
    """Test scenario for a simple task with minimal parameters."""
    
    def __init__(self):
        super().__init__(
            "Simple Task",
            "Basic workflow execution with minimal parameters"
        )
        self.expected_outcomes = [
            "Workflow completes successfully",
            "File is created",
            "Turns < 10",
            "Execution time < 60s"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Create a simple hello.py file that prints 'Hello from workflow test'",
            workflow_name="builder",
            max_turns=10,
            timeout=300,
            persistent=True
        )
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if hello.py was created."""
        workspace = Path(result.get('workspace_path', ''))
        hello_file = workspace / "hello.py"
        
        validations = {
            "success": result.get('success', False),
            "file_exists": hello_file.exists(),
            "turns_limit": result.get('result_metadata', {}).get('total_turns', 0) < 10,
            "execution_time": result.get('execution_time', 999) < 60
        }
        
        print(f"  Validations: {json.dumps(validations, indent=2)}")
        return all(validations.values())


class SessionContinuationScenario(WorkflowTestScenario):
    """Test scenario for continuing a previous session."""
    
    def __init__(self, previous_session_id: str):
        super().__init__(
            "Session Continuation",
            "Test continuing work from a previous session"
        )
        self.previous_session_id = previous_session_id
        self.expected_outcomes = [
            "Session continues from previous state",
            "Context is maintained",
            "New work builds on previous"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Add a function called greet(name) to the hello.py file",
            workflow_name="builder",
            session_id=self.previous_session_id,
            max_turns=10,
            timeout=300
        )
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if function was added to existing file."""
        workspace = Path(result.get('workspace_path', ''))
        hello_file = workspace / "hello.py"
        
        if hello_file.exists():
            content = hello_file.read_text()
            return "def greet(name)" in content
        return False


class TurnLimitScenario(WorkflowTestScenario):
    """Test scenario for handling turn limits."""
    
    def __init__(self):
        super().__init__(
            "Turn Limit",
            "Test workflow behavior when reaching turn limit"
        )
        self.expected_outcomes = [
            "Workflow stops at turn limit",
            "Status indicates limit reached",
            "Partial work is saved",
            "Can continue with session"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Create a complex web application with user authentication, database, and API endpoints",
            workflow_name="builder",
            max_turns=3,  # Very low limit to force hitting it
            timeout=600,
            persistent=True
        )
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if turn limit was respected."""
        metadata = result.get('result_metadata', {})
        turns = metadata.get('total_turns', 0)
        
        validations = {
            "turn_limit_respected": turns <= 3,
            "has_session_id": bool(result.get('session_id')),
            "partial_work_exists": Path(result.get('workspace_path', '')).exists()
        }
        
        print(f"  Turn limit validations: {json.dumps(validations, indent=2)}")
        return all(validations.values())


class TempWorkspaceScenario(WorkflowTestScenario):
    """Test scenario for temporary workspace execution."""
    
    def __init__(self):
        super().__init__(
            "Temporary Workspace",
            "Test isolated execution in temporary workspace"
        )
        self.expected_outcomes = [
            "Workspace is created in temp directory",
            "No git integration",
            "Work is isolated from main codebase"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Experiment with a new architecture pattern using dependency injection",
            workflow_name="builder",
            temp_workspace=True,
            max_turns=20,
            timeout=900,
            persistent=False
        )
        
    def validate_pre_execution(self, context: Dict[str, Any]) -> bool:
        """Ensure temp workspace parameters are valid."""
        request = context.get('request')
        if not request:
            return False
            
        # Should not have git-related parameters
        return not any([
            request.git_branch,
            request.repository_url,
            request.auto_merge
        ])
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if workspace was in temp directory."""
        workspace_path = result.get('workspace_path', '')
        temp_dir = tempfile.gettempdir()
        
        return temp_dir in workspace_path


class MessageInjectionScenario(WorkflowTestScenario):
    """Test scenario for message injection during execution."""
    
    def __init__(self):
        super().__init__(
            "Message Injection",
            "Test injecting additional instructions during execution"
        )
        self.expected_outcomes = [
            "Initial task starts",
            "Injected message is processed",
            "Final result includes both tasks"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Create a calculator.py file with add and subtract functions",
            workflow_name="builder",
            max_turns=30,
            timeout=600,
            persistent=True
        )
        
    def inject_message(self, workspace_path: Path, run_id: str) -> bool:
        """Inject additional message during execution."""
        from automagik.agents.claude_code.sdk_message_injection import SDKMessageInjector
        
        injector = SDKMessageInjector()
        return injector.add_message_to_queue(
            workspace_path,
            "Also add multiply and divide functions to the calculator",
            {"run_id": run_id, "injected_at": datetime.utcnow().isoformat()}
        )
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if all functions were created."""
        workspace = Path(result.get('workspace_path', ''))
        calc_file = workspace / "calculator.py"
        
        if calc_file.exists():
            content = calc_file.read_text()
            functions = ["def add", "def subtract", "def multiply", "def divide"]
            return all(func in content for func in functions)
        return False


class ErrorHandlingScenario(WorkflowTestScenario):
    """Test scenario for error handling."""
    
    def __init__(self):
        super().__init__(
            "Error Handling",
            "Test workflow behavior with invalid requests"
        )
        self.expected_outcomes = [
            "Invalid workspace handled gracefully",
            "Error is logged",
            "Status reflects failure"
        ]
        
    def build_request(self) -> ClaudeCodeRunRequest:
        return ClaudeCodeRunRequest(
            message="Work on a non-existent project",
            workflow_name="builder",
            repository_url="https://github.com/nonexistent/repo.git",
            max_turns=10,
            timeout=300
        )
        
    def validate_post_execution(self, result: Dict[str, Any]) -> bool:
        """Check if error was handled properly."""
        return not result.get('success', True)  # Should fail


class WorkflowValidationRunner:
    """Runner for workflow validation scenarios."""
    
    def __init__(self):
        self.env_manager = CLIEnvironmentManager()
        self.strategies = ExecutionStrategies(environment_manager=self.env_manager)
        self.results: Dict[str, Dict[str, Any]] = {}
        
    async def run_scenario(self, scenario: WorkflowTestScenario) -> Dict[str, Any]:
        """Run a single test scenario."""
        print(f"\n🧪 Running scenario: {scenario.name}")
        print(f"   {scenario.description}")
        
        # Build request
        request = scenario.build_request()
        request.run_id = f"test-{scenario.name.lower().replace(' ', '-')}-{datetime.utcnow().timestamp()}"
        
        # Create context
        context = {
            "workspace": os.path.expanduser("~/test_workflows"),
            "user_id": "test-user",
            "request": request
        }
        
        # Pre-execution validation
        if not scenario.validate_pre_execution(context):
            return {"success": False, "error": "Pre-execution validation failed"}
            
        try:
            # Create workflow run in database
            workflow_run = WorkflowRunCreate(
                run_id=request.run_id,
                user_id=context["user_id"],
                workflow_name=request.workflow_name,
                status="running",
                started_at=datetime.utcnow(),
                input_data=request.message
            )
            create_workflow_run(workflow_run)
            
            # Execute workflow
            print(f"   Executing with run_id: {request.run_id}")
            result = await self.strategies.execute_simple(request, context)
            
            # Post-execution validation
            validation_passed = scenario.validate_post_execution(result)
            
            result["validation_passed"] = validation_passed
            result["scenario"] = scenario.name
            
            print(f"   Result: {'✅ Passed' if validation_passed else '❌ Failed'}")
            
            return result
            
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "scenario": scenario.name,
                "validation_passed": False
            }
            
    async def run_all_scenarios(self):
        """Run all test scenarios."""
        print("🚀 Starting workflow validation scenarios...")
        
        # Define scenarios
        scenarios = [
            SimpleTaskScenario(),
            TurnLimitScenario(),
            TempWorkspaceScenario(),
            ErrorHandlingScenario()
        ]
        
        # Run scenarios
        for scenario in scenarios:
            result = await self.run_scenario(scenario)
            self.results[scenario.name] = result
            
            # If simple task succeeded, test session continuation
            if scenario.name == "Simple Task" and result.get('success'):
                session_id = result.get('session_id')
                if session_id:
                    continuation = SessionContinuationScenario(session_id)
                    cont_result = await self.run_scenario(continuation)
                    self.results[continuation.name] = cont_result
                    
        # Summary
        self.print_summary()
        
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 Workflow Validation Summary")
        print("="*60)
        
        passed = sum(1 for r in self.results.values() if r.get('validation_passed'))
        total = len(self.results)
        
        for name, result in self.results.items():
            status = "✅" if result.get('validation_passed') else "❌"
            print(f"{status} {name}: {result.get('error', 'Success')}")
            
        print(f"\nTotal: {passed}/{total} scenarios passed")
        
        if passed == total:
            print("\n✅ All workflow validations passed!")
        else:
            print("\n❌ Some workflow validations failed.")


async def main():
    """Run workflow validation."""
    runner = WorkflowValidationRunner()
    await runner.run_all_scenarios()


if __name__ == "__main__":
    # Note: This requires Claude CLI to be installed and configured
    print("⚠️  Note: This validation requires Claude CLI to be installed and configured.")
    print("For unit tests without Claude CLI, run the refactoring tests instead.\n")
    
    response = input("Do you want to proceed with live workflow validation? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(main())
    else:
        print("Skipping live validation. Run unit tests instead.")