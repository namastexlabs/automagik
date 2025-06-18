"""Custom transport for Claude SDK with environment variable injection.

This module provides a custom transport that can inject environment variables
into the subprocess when the SDK spawns the Claude CLI.
"""

import asyncio
import os
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class EnvironmentAwareTransport:
    """Custom transport that injects environment variables.
    
    This is a workaround until the SDK officially supports custom environment
    variable injection. Once SDK support is available, this can be replaced
    with the official mechanism.
    
    NOTE: This implementation assumes the SDK will eventually support custom
    transports. Currently, we fall back to process-level environment injection.
    """
    
    def __init__(self, custom_env: Optional[Dict[str, str]] = None):
        """Initialize transport with custom environment variables.
        
        Args:
            custom_env: Dictionary of environment variables to inject
        """
        self.custom_env = custom_env or {}
        self.original_env = {}
        
    def inject_environment(self):
        """Inject custom environment variables into current process.
        
        This is a temporary workaround that modifies os.environ directly.
        It stores the original values to allow restoration later.
        """
        for key, value in self.custom_env.items():
            # Store original value if it exists
            if key in os.environ:
                self.original_env[key] = os.environ[key]
            else:
                self.original_env[key] = None
            
            # Set new value
            os.environ[key] = value
            
        logger.debug(f"Injected {len(self.custom_env)} environment variables")
    
    def restore_environment(self):
        """Restore original environment variables.
        
        This undoes the changes made by inject_environment().
        """
        for key, original_value in self.original_env.items():
            if original_value is None:
                # Key didn't exist originally, remove it
                if key in os.environ:
                    del os.environ[key]
            else:
                # Restore original value
                os.environ[key] = original_value
                
        self.original_env.clear()
        logger.debug("Restored original environment variables")
    
    async def spawn_process(self, cmd: List[str], cwd: Optional[str] = None) -> asyncio.subprocess.Process:
        """Spawn a subprocess with custom environment variables.
        
        This method would be used if the SDK supported custom transports.
        
        Args:
            cmd: Command and arguments to execute
            cwd: Working directory for the subprocess
            
        Returns:
            The spawned subprocess
        """
        # Combine current environment with custom environment
        env = os.environ.copy()
        env.update(self.custom_env)
        
        # Create subprocess with custom environment
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        
        logger.info(f"Spawned process with custom environment: {' '.join(cmd)}")
        return process
    
    def __enter__(self):
        """Context manager entry: inject environment variables."""
        self.inject_environment()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: restore environment variables."""
        self.restore_environment()
        return False


class SDKEnvironmentInjector:
    """Helper class to manage environment injection for SDK calls.
    
    This provides a clean interface for using environment injection
    with the SDK until official support is available.
    """
    
    def __init__(self, env_manager):
        """Initialize with a CLIEnvironmentManager instance.
        
        Args:
            env_manager: CLIEnvironmentManager instance
        """
        self.env_manager = env_manager
        
    def create_transport(self, workspace: str) -> EnvironmentAwareTransport:
        """Create a transport with environment variables for the workspace.
        
        Args:
            workspace: Path to the workspace directory
            
        Returns:
            EnvironmentAwareTransport configured with workspace environment
        """
        custom_env = self.env_manager.as_dict(workspace)
        return EnvironmentAwareTransport(custom_env)
    
    async def execute_with_env(self, workspace: str, sdk_function, *args, **kwargs):
        """Execute an SDK function with environment injection.
        
        This is a convenience method that handles the environment injection
        lifecycle around an SDK call.
        
        Args:
            workspace: Path to the workspace directory
            sdk_function: The SDK function to call
            *args: Positional arguments for the SDK function
            **kwargs: Keyword arguments for the SDK function
            
        Returns:
            The result of the SDK function call
        """
        transport = self.create_transport(workspace)
        
        # Use context manager to inject/restore environment
        with transport:
            result = await sdk_function(*args, **kwargs)
            
        return result


# Workaround documentation for SDK enhancement request
SDK_ENHANCEMENT_REQUEST = """
SDK Enhancement Request: Custom Environment Variable Support

We need the ability to inject custom environment variables when the SDK
spawns the Claude CLI subprocess. This would enable better integration
with workflow systems and environment management.

Proposed API:

```python
class ClaudeCodeOptions:
    custom_env: Optional[Dict[str, str]] = None

# Or via custom transport
class CustomTransport(SubprocessCLITransport):
    def __init__(self, custom_env: Dict[str, str]):
        self.custom_env = custom_env
        
    async def _spawn_process(self, cmd: list[str]) -> asyncio.subprocess.Process:
        env = os.environ.copy()
        env.update(self.custom_env)
        return await asyncio.create_subprocess_exec(
            *cmd, env=env, ...
        )

# Usage
options = ClaudeCodeOptions(custom_env={"CLAUDE_WORKFLOW": "test"})
# or
transport = CustomTransport(custom_env={"CLAUDE_WORKFLOW": "test"})
await query(prompt, options, transport=transport)
```

Until this is available, we're using process-level environment injection
as a workaround.
"""