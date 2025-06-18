"""Regression tests to prevent legacy CLI executor code reintroduction.

These tests ensure that the SDK migration remains complete and prevents
accidental reintroduction of legacy CLI executor code.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock
import os


class TestNoLegacyCode:
    """Test suite to prevent legacy code reintroduction."""
    
    def test_cli_executor_cannot_be_imported(self):
        """Ensure CLI executor cannot be imported directly."""
        with pytest.raises(ImportError):
            from agents.claude_code.cli_executor import ClaudeCLIExecutor
    
    def test_cli_executor_package_import_blocked(self):
        """Ensure CLI executor is blocked at package level."""
        from agents.claude_code import __getattr__ as claude_getattr
        
        with pytest.raises(ImportError, match="ClaudeCLIExecutor has been removed"):
            claude_getattr('ClaudeCLIExecutor')
    
    def test_executor_factory_defaults_to_sdk(self):
        """Ensure factory returns SDK executor by default."""
        from agents.claude_code.executor_factory import ExecutorFactory
        from agents.claude_code.sdk_executor import ClaudeSDKExecutor
        
        # Mock the environment manager since we just want to test factory logic
        with pytest.patch('agents.claude_code.executor_factory.LocalEnvironmentManager'):
            executor = ExecutorFactory.create_executor()
            assert isinstance(executor, ClaudeSDKExecutor)
    
    def test_executor_factory_mode_parameter_ignored(self):
        """Ensure deprecated mode parameter is ignored (always returns SDK)."""
        from agents.claude_code.executor_factory import ExecutorFactory
        from agents.claude_code.sdk_executor import ClaudeSDKExecutor
        
        # Mock the environment manager
        with pytest.patch('agents.claude_code.executor_factory.LocalEnvironmentManager'):
            # Even if mode is explicitly set to 'local', should return SDK
            executor = ExecutorFactory.create_executor(mode='local')
            assert isinstance(executor, ClaudeSDKExecutor)
            
            # SDK mode should still work
            executor = ExecutorFactory.create_executor(mode='sdk')
            assert isinstance(executor, ClaudeSDKExecutor)
    
    def test_no_legacy_override_support(self):
        """Test that legacy override is no longer supported."""
        from agents.claude_code.executor_factory import ExecutorFactory
        from agents.claude_code.sdk_executor import ClaudeSDKExecutor
        
        # Set legacy flag - should be ignored
        original_env = os.environ.get('FORCE_LEGACY_EXECUTOR')
        os.environ['FORCE_LEGACY_EXECUTOR'] = '1'
        
        try:
            with pytest.patch('agents.claude_code.executor_factory.CLIEnvironmentManager'):
                executor = ExecutorFactory.create_executor()
                # Should always return SDK executor now
                assert isinstance(executor, ClaudeSDKExecutor)
        finally:
            # Clean up environment
            if original_env is None:
                os.environ.pop('FORCE_LEGACY_EXECUTOR', None)
            else:
                os.environ['FORCE_LEGACY_EXECUTOR'] = original_env
    
    def test_legacy_files_removed(self):
        """Ensure legacy files have been removed from filesystem."""
        legacy_files = [
            'src/agents/claude_code/cli_executor.py',
            'src/agents/claude_code/local_executor.py',
            'src/agents/claude_code/utils/find_claude_executable.py',
        ]
        
        project_root = Path(__file__).parent.parent
        
        for file_path in legacy_files:
            full_path = project_root / file_path
            assert not full_path.exists(), f"Legacy file still exists: {file_path}"
    
    def test_no_cli_executor_references_in_active_code(self):
        """Ensure no problematic references to CLI executor remain in active code."""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / 'src'
        
        if not src_dir.exists():
            pytest.skip("Source directory not found")
        
        try:
            # Search for ClaudeCLIExecutor references
            result = subprocess.run(
                ['grep', '-r', 'ClaudeCLIExecutor', str(src_dir), '--exclude-dir=__pycache__'],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                problematic_refs = []
                
                for line in lines:
                    # Skip acceptable references (deprecation handlers, migration docs)
                    if any(keyword in line.lower() for keyword in [
                        'deprecated', 'legacy', 'remove', 'migration', 
                        '__getattr__', 'importerror', 'has been removed'
                    ]):
                        continue
                    problematic_refs.append(line)
                
                assert len(problematic_refs) == 0, (
                    f"Found {len(problematic_refs)} problematic CLI executor references:\n" +
                    "\n".join(problematic_refs[:10])  # Show first 10
                )
        except FileNotFoundError:
            pytest.skip("grep command not available")
    
    def test_sdk_executor_available(self):
        """Ensure SDK executor can be imported and instantiated."""
        from agents.claude_code.sdk_executor import ClaudeSDKExecutor
        
        # Should be able to create instance (even with None environment manager)
        executor = ClaudeSDKExecutor(environment_manager=None)
        assert executor is not None
        assert hasattr(executor, 'execute_claude_task')
    
    def test_package_exports_updated(self):
        """Ensure package exports only include SDK executor."""
        from agents.claude_code import __all__
        
        # Should include SDK executor
        assert 'ClaudeSDKExecutor' in __all__
        
        # Should NOT include CLI executor
        assert 'ClaudeCLIExecutor' not in __all__
    
    @pytest.mark.skipif(
        not Path(__file__).parent.parent.joinpath('scripts/verify_sdk_migration.py').exists(),
        reason="Migration verification script not found"
    )
    def test_migration_verification_script_passes(self):
        """Ensure the migration verification script passes."""
        project_root = Path(__file__).parent.parent
        script_path = project_root / 'scripts' / 'verify_sdk_migration.py'
        
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        assert result.returncode == 0, (
            f"Migration verification failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )


class TestLegacyCompatibility:
    """Test that legacy code doesn't accidentally get reintroduced."""
    
    def test_no_find_claude_executable_imports(self):
        """Ensure find_claude_executable utility is not imported anywhere."""
        try:
            from agents.claude_code.utils.find_claude_executable import find_claude_executable
            pytest.fail("find_claude_executable should not be importable")
        except ImportError:
            pass  # Expected
    
    def test_cli_environment_only_has_shared_functionality(self):
        """Ensure CLI environment manager only retains shared functionality."""
        from agents.claude_code.cli_environment import CLIEnvironmentManager
        
        # Should have shared functionality
        assert hasattr(CLIEnvironmentManager, 'as_dict')
        
        # Should NOT have CLI-specific methods (if they were removed)
        cli_specific_methods = ['get_cli_args', '_build_cli_flags']
        for method in cli_specific_methods:
            if hasattr(CLIEnvironmentManager, method):
                pytest.fail(f"CLI-specific method {method} should have been removed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])