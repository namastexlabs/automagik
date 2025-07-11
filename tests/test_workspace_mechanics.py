#!/usr/bin/env python3
"""Test workspace mechanics - actual workspace creation, repo cloning, and branch management.

This validates the core workflow behavior: how workspaces are set up, repositories cloned,
branches switched, and paths managed based on different parameters.
"""

import asyncio
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.agents.claude_code.models import ClaudeCodeRunRequest
from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager


class WorkspaceMechanicsValidator:
    """Validate workspace creation, repository handling, and branch management."""
    
    def __init__(self):
        self.env_manager = CLIEnvironmentManager()
        self.test_results = []
        self.created_workspaces = []  # Track for cleanup
        
    def log_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}: {details}")
        self.test_results.append((category, test_name, passed, details))
        
    async def cleanup_workspaces(self):
        """Clean up test workspaces."""
        for workspace_path in self.created_workspaces:
            if workspace_path.exists():
                try:
                    shutil.rmtree(workspace_path)
                    print(f"🧹 Cleaned up workspace: {workspace_path}")
                except Exception as e:
                    print(f"⚠️ Failed to cleanup {workspace_path}: {e}")
                    
    async def test_worktree_workspace_creation(self):
        """Test worktree workspace creation for local development."""
        print(f"\n🧪 Testing worktree workspace creation...")
        
        # Test 1: Basic worktree creation
        run_id = f"test-worktree-{datetime.now().timestamp()}"
        try:
            workspace_path = await self.env_manager.create_workspace(
                run_id=run_id,
                workflow_name="builder",
                persistent=True,
                git_branch=None  # Should auto-generate
            )
            
            self.created_workspaces.append(workspace_path)
            
            # Validate workspace exists
            exists = workspace_path.exists()
            self.log_result("Worktree Creation", "workspace_exists", exists, str(workspace_path))
            
            # Validate it's a git repository
            git_dir = workspace_path / ".git"
            is_git_repo = git_dir.exists()
            self.log_result("Worktree Creation", "is_git_repository", is_git_repo)
            
            # Validate worktree directory structure
            expected_pattern = "main-builder-" + run_id[:8]
            name_correct = expected_pattern in workspace_path.name
            self.log_result("Worktree Creation", "correct_naming_pattern", name_correct, workspace_path.name)
            
            # Check current branch
            if is_git_repo:
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    current_branch = result.stdout.strip()
                    has_branch = len(current_branch) > 0
                    self.log_result("Worktree Creation", "has_valid_branch", has_branch, current_branch)
                except subprocess.CalledProcessError as e:
                    self.log_result("Worktree Creation", "has_valid_branch", False, f"git error: {e}")
                    
        except Exception as e:
            self.log_result("Worktree Creation", "creation_success", False, str(e))
            
    async def test_custom_branch_handling(self):
        """Test custom branch creation and checkout."""
        print(f"\n🧪 Testing custom branch handling...")
        
        test_branch = f"feature/test-branch-{datetime.now().timestamp()}"
        run_id = f"test-branch-{datetime.now().timestamp()}"
        
        try:
            workspace_path = await self.env_manager.create_workspace(
                run_id=run_id,
                workflow_name="surgeon",
                persistent=True,
                git_branch=test_branch
            )
            
            self.created_workspaces.append(workspace_path)
            
            # Validate workspace was created
            exists = workspace_path.exists()
            self.log_result("Custom Branch", "workspace_created", exists)
            
            if exists:
                # Check if we're on the correct branch
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    current_branch = result.stdout.strip()
                    correct_branch = test_branch in current_branch
                    self.log_result("Custom Branch", "correct_branch_checkout", correct_branch, 
                                  f"Expected: {test_branch}, Got: {current_branch}")
                    
                    # Check if branch exists in git
                    result = subprocess.run(
                        ["git", "branch", "--list"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    branch_exists = test_branch in result.stdout or current_branch in result.stdout
                    self.log_result("Custom Branch", "branch_created", branch_exists)
                    
                except subprocess.CalledProcessError as e:
                    self.log_result("Custom Branch", "git_operations", False, str(e))
                    
        except Exception as e:
            self.log_result("Custom Branch", "creation_with_custom_branch", False, str(e))
            
    async def test_temp_workspace_creation(self):
        """Test temporary workspace creation (no git integration)."""
        print(f"\n🧪 Testing temporary workspace creation...")
        
        # Create a request with temp_workspace=True
        request = ClaudeCodeRunRequest(
            message="Test temporary workspace",
            workflow_name="builder",
            temp_workspace=True,
            persistent=False
        )
        
        run_id = f"test-temp-{datetime.now().timestamp()}"
        
        try:
            workspace_path = await self.env_manager.create_workspace(
                run_id=run_id,
                workflow_name=request.workflow_name,
                persistent=request.persistent,
                temp_workspace=request.temp_workspace
            )
            
            self.created_workspaces.append(workspace_path)
            
            # Validate workspace exists
            exists = workspace_path.exists()
            self.log_result("Temp Workspace", "workspace_created", exists, str(workspace_path))
            
            # Validate it's in temp directory
            in_temp = "/tmp" in str(workspace_path)
            self.log_result("Temp Workspace", "in_temp_directory", in_temp)
            
            # Validate it's NOT a git repository (temp workspaces should be isolated)
            git_dir = workspace_path / ".git"
            is_not_git_repo = not git_dir.exists()
            self.log_result("Temp Workspace", "not_git_repository", is_not_git_repo)
            
            # Test that temp workspace parameters are validated
            try:
                # This should fail - temp_workspace with git_branch
                invalid_request = ClaudeCodeRunRequest(
                    message="Test",
                    workflow_name="builder",
                    temp_workspace=True,
                    git_branch="feature/test"
                )
                self.log_result("Temp Workspace", "parameter_validation", False, "Should have failed validation")
            except Exception:
                self.log_result("Temp Workspace", "parameter_validation", True, "Correctly rejected invalid params")
                
        except Exception as e:
            self.log_result("Temp Workspace", "temp_creation", False, str(e))
            
    async def test_external_repository_handling(self):
        """Test external repository cloning."""
        print(f"\n🧪 Testing external repository handling...")
        
        # Test with a public repository
        test_repo_url = "https://github.com/octocat/Hello-World.git"
        run_id = f"test-external-{datetime.now().timestamp()}"
        
        try:
            # Note: This might take time to clone, so we'll use a timeout
            workspace_path = await asyncio.wait_for(
                self.env_manager.create_workspace(
                    run_id=run_id,
                    workflow_name="builder",
                    persistent=True,
                    repository_url=test_repo_url
                ),
                timeout=30.0  # 30 second timeout for clone
            )
            
            self.created_workspaces.append(workspace_path)
            
            # Validate workspace exists
            exists = workspace_path.exists()
            self.log_result("External Repo", "workspace_created", exists, str(workspace_path))
            
            if exists:
                # Validate it's a git repository
                git_dir = workspace_path / ".git"
                is_git_repo = git_dir.exists()
                self.log_result("External Repo", "is_git_repository", is_git_repo)
                
                # Check if files from the repository exist
                readme_exists = (workspace_path / "README").exists()
                self.log_result("External Repo", "repo_files_present", readme_exists)
                
                # Check remote URL
                if is_git_repo:
                    try:
                        result = subprocess.run(
                            ["git", "remote", "get-url", "origin"],
                            cwd=workspace_path,
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        remote_url = result.stdout.strip()
                        correct_remote = test_repo_url in remote_url
                        self.log_result("External Repo", "correct_remote_url", correct_remote, remote_url)
                    except subprocess.CalledProcessError as e:
                        self.log_result("External Repo", "remote_check", False, str(e))
                        
        except asyncio.TimeoutError:
            self.log_result("External Repo", "clone_timeout", False, "Clone took longer than 30 seconds")
        except Exception as e:
            self.log_result("External Repo", "external_clone", False, str(e))
            
    async def test_workspace_persistence(self):
        """Test workspace persistence behavior."""
        print(f"\n🧪 Testing workspace persistence...")
        
        # Test 1: Persistent workspace (should remain after cleanup)
        run_id_persistent = f"test-persistent-{datetime.now().timestamp()}"
        try:
            persistent_workspace = await self.env_manager.create_workspace(
                run_id=run_id_persistent,
                workflow_name="builder",
                persistent=True
            )
            
            exists_after_creation = persistent_workspace.exists()
            self.log_result("Persistence", "persistent_workspace_created", exists_after_creation)
            
            # Manually track for cleanup since it's persistent
            self.created_workspaces.append(persistent_workspace)
            
        except Exception as e:
            self.log_result("Persistence", "persistent_creation", False, str(e))
            
        # Test 2: Non-persistent workspace behavior 
        run_id_temp = f"test-nonpersistent-{datetime.now().timestamp()}"
        try:
            temp_workspace = await self.env_manager.create_workspace(
                run_id=run_id_temp,
                workflow_name="builder", 
                persistent=False
            )
            
            exists_after_creation = temp_workspace.exists()
            self.log_result("Persistence", "nonpersistent_workspace_created", exists_after_creation)
            
            # Note: Non-persistent workspaces should be cleaned up by the system
            # We'll still track for manual cleanup if needed
            self.created_workspaces.append(temp_workspace)
            
        except Exception as e:
            self.log_result("Persistence", "nonpersistent_creation", False, str(e))
            
    async def test_workspace_environment_setup(self):
        """Test workspace environment configuration."""
        print(f"\n🧪 Testing workspace environment setup...")
        
        run_id = f"test-env-{datetime.now().timestamp()}"
        try:
            workspace_path = await self.env_manager.create_workspace(
                run_id=run_id,
                workflow_name="brain",
                persistent=True
            )
            
            self.created_workspaces.append(workspace_path)
            
            # Test environment dictionary generation
            env_dict = self.env_manager.as_dict()
            
            # Validate essential environment variables
            has_workspace_path = 'WORKSPACE_PATH' in env_dict
            self.log_result("Environment", "has_workspace_path", has_workspace_path)
            
            has_run_id = 'RUN_ID' in env_dict
            self.log_result("Environment", "has_run_id", has_run_id)
            
            has_workflow_name = 'WORKFLOW_NAME' in env_dict
            self.log_result("Environment", "has_workflow_name", has_workflow_name)
            
            # Validate workspace path points to created workspace
            if has_workspace_path:
                env_workspace = Path(env_dict['WORKSPACE_PATH'])
                paths_match = env_workspace.resolve() == workspace_path.resolve()
                self.log_result("Environment", "workspace_path_correct", paths_match, 
                              f"Env: {env_workspace}, Actual: {workspace_path}")
                
        except Exception as e:
            self.log_result("Environment", "environment_setup", False, str(e))
            
    async def test_concurrent_workspace_creation(self):
        """Test concurrent workspace creation (race condition handling)."""
        print(f"\n🧪 Testing concurrent workspace creation...")
        
        base_run_id = f"test-concurrent-{datetime.now().timestamp()}"
        
        async def create_workspace_task(task_id: int):
            """Create a workspace in a concurrent task."""
            try:
                run_id = f"{base_run_id}-{task_id}"
                workspace_path = await self.env_manager.create_workspace(
                    run_id=run_id,
                    workflow_name="builder",
                    persistent=True
                )
                self.created_workspaces.append(workspace_path)
                return workspace_path, None
            except Exception as e:
                return None, str(e)
                
        # Create multiple workspaces concurrently
        tasks = [create_workspace_task(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_creations = sum(1 for workspace, error in results if workspace is not None)
        all_unique = len(set(str(w) for w, e in results if w is not None)) == successful_creations
        
        self.log_result("Concurrency", "all_workspaces_created", successful_creations == 3)
        self.log_result("Concurrency", "all_workspaces_unique", all_unique)
        
        # Check for race condition errors
        race_condition_errors = [e for w, e in results if e and "already exists" in e]
        no_race_conditions = len(race_condition_errors) == 0
        self.log_result("Concurrency", "no_race_conditions", no_race_conditions)
        
    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*60)
        print("📊 Workspace Mechanics Test Summary")
        print("="*60)
        
        # Group by category
        categories = {}
        for category, test, passed, details in self.test_results:
            if category not in categories:
                categories[category] = []
            categories[category].append((test, passed, details))
            
        total_passed = 0
        total_tests = 0
        
        for category, tests in categories.items():
            passed = sum(1 for _, p, _ in tests if p)
            total = len(tests)
            total_passed += passed
            total_tests += total
            
            print(f"\n{category}: {passed}/{total} passed")
            for test, passed, details in tests:
                status = "✅" if passed else "❌"
                detail_str = f" - {details}" if details else ""
                print(f"  {status} {test}{detail_str}")
                
        print(f"\n{'='*60}")
        print(f"Total: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("\n✅ All workspace mechanics tests passed!")
        else:
            print(f"\n❌ {total_tests - total_passed} workspace mechanics tests failed.")
            
        # Show workspace locations for manual inspection
        if self.created_workspaces:
            print(f"\n📁 Created workspaces for inspection:")
            for workspace in self.created_workspaces:
                if workspace.exists():
                    print(f"  📂 {workspace}")
                    
    async def run_all_tests(self):
        """Run all workspace mechanics tests."""
        print("🚀 Starting workspace mechanics validation...\n")
        
        try:
            await self.test_worktree_workspace_creation()
            await self.test_custom_branch_handling()
            await self.test_temp_workspace_creation()
            await self.test_workspace_persistence()
            await self.test_workspace_environment_setup()
            await self.test_concurrent_workspace_creation()
            
            # Note: External repo test disabled by default due to network dependency
            # Uncomment to test external repository cloning:
            # await self.test_external_repository_handling()
            
        finally:
            self.print_summary()
            
            # Ask user if they want to clean up workspaces
            print(f"\n🧹 Clean up {len(self.created_workspaces)} test workspaces? (y/n): ", end="")
            try:
                response = input()
                if response.lower() == 'y':
                    await self.cleanup_workspaces()
                else:
                    print("Workspaces preserved for manual inspection.")
            except (EOFError, KeyboardInterrupt):
                print("\nWorkspaces preserved for manual inspection.")


async def main():
    """Run workspace mechanics validation."""
    validator = WorkspaceMechanicsValidator()
    await validator.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())