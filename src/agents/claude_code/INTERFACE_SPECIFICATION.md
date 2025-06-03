# Claude Code Local Mode Interface Specification

## Critical Interfaces for Implementation

### 1. ExecutorBase Abstract Class

```python
# executor_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from .models import ClaudeCodeRunRequest

class ExecutorBase(ABC):
    """Abstract base class for Claude executors.
    
    All executors must implement these methods to ensure compatibility
    with the ClaudeCodeAgent.
    """
    
    @abstractmethod
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude CLI task.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results:
            {
                'success': bool,
                'session_id': str,
                'result': str,
                'exit_code': int,
                'execution_time': float,
                'logs': str,
                'error': Optional[str],
                'git_commits': List[str],
                'container_id': Optional[str],  # Only for Docker
                'workspace_path': Optional[str]  # Only for Local
            }
        """
        pass
    
    @abstractmethod
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Container ID (Docker) or Session ID (Local)
            
        Returns:
            Execution logs as string
        """
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Container ID (Docker) or Session ID (Local)
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up all resources."""
        pass
```

### 2. LocalExecutor Implementation Structure

```python
# local_executor.py
import asyncio
import subprocess
import os
import shutil
from typing import Dict, Any, Optional
from .executor_base import ExecutorBase

class LocalExecutor(ExecutorBase):
    """Executes Claude CLI directly on the host system."""
    
    def __init__(
        self, 
        workspace_base: str = "/tmp/claude-workspace",
        cleanup_on_complete: bool = True,
        git_cache_enabled: bool = False
    ):
        """Initialize the local executor.
        
        Args:
            workspace_base: Base directory for workspaces
            cleanup_on_complete: Whether to cleanup after execution
            git_cache_enabled: Whether to cache git repositories
        """
        self.workspace_base = workspace_base
        self.cleanup_on_complete = cleanup_on_complete
        self.git_cache_enabled = git_cache_enabled
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.workspace_paths: Dict[str, str] = {}
```

### 3. ExecutorFactory Interface

```python
# executor_factory.py
from typing import Optional
from .executor_base import ExecutorBase
from .container import ContainerManager

class ExecutorFactory:
    """Factory for creating appropriate executor based on configuration."""
    
    @staticmethod
    def create_executor(
        mode: Optional[str] = None,
        container_manager: Optional[ContainerManager] = None,
        **kwargs
    ) -> ExecutorBase:
        """Create an executor based on the specified mode.
        
        Args:
            mode: Execution mode ('docker' or 'local'). 
                  If None, reads from CLAUDE_CODE_MODE env var.
            container_manager: Required for Docker mode
            **kwargs: Additional arguments for the executor
            
        Returns:
            ExecutorBase instance
            
        Raises:
            ValueError: If mode is invalid or required args missing
        """
        pass
```

### 4. Modified ClaudeCodeAgent Constructor

```python
# agent.py (modified section)
class ClaudeCodeAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Determine execution mode
        self.execution_mode = settings.config.get("CLAUDE_CODE_MODE", "docker").lower()
        logger.info(f"ClaudeCodeAgent initializing in {self.execution_mode} mode")
        
        # Initialize appropriate executor
        try:
            self.executor = ExecutorFactory.create_executor(
                mode=self.execution_mode,
                container_manager=self._create_container_manager() if self.execution_mode == "docker" else None,
                workspace_base=settings.config.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
                cleanup_on_complete=settings.config.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
            )
        except ValueError as e:
            logger.error(f"Failed to create executor: {e}")
            raise
```

### 5. Configuration Interface

```python
# Environment variables to add to settings.py
CLAUDE_CODE_SETTINGS = {
    # Execution mode
    "CLAUDE_CODE_MODE": {
        "default": "docker",
        "choices": ["docker", "local"],
        "description": "Execution mode for Claude Code agent"
    },
    
    # Local mode settings
    "CLAUDE_LOCAL_WORKSPACE": {
        "default": "/tmp/claude-workspace",
        "description": "Base directory for local workspaces"
    },
    "CLAUDE_LOCAL_CLEANUP": {
        "default": "true",
        "choices": ["true", "false"],
        "description": "Clean up workspace after execution"
    },
    "CLAUDE_LOCAL_GIT_CACHE": {
        "default": "false",
        "choices": ["true", "false"],
        "description": "Cache git repositories between executions"
    },
    "CLAUDE_LOCAL_MAX_PROCESSES": {
        "default": "5",
        "type": int,
        "description": "Maximum concurrent local processes"
    },
    
    # Shared settings (both modes)
    "CLAUDE_CODE_TIMEOUT": {
        "default": "7200",
        "type": int,
        "description": "Maximum execution time in seconds"
    }
}
```

### 6. Local Runner Script Interface

```bash
#!/bin/bash
# local_runner.sh

# Required environment variables:
# - WORKSPACE_DIR: Directory containing cloned repository
# - WORKFLOW_DIR: Directory containing workflow configuration
# - CLAUDE_MESSAGE: The task message for Claude
# - GIT_BRANCH: Git branch to work on
# - SESSION_ID: Unique session identifier

# Expected workflow structure:
# $WORKFLOW_DIR/
# ├── prompt.md         # System prompt
# ├── .mcp.json        # MCP configuration
# ├── allowed_tools.json # Allowed tools list
# ├── .env             # Environment variables
# └── .credentials.json # Claude credentials

# Output format (JSON to stdout):
# {
#   "session_id": "string",
#   "result": "string",
#   "exit_code": number,
#   "git_commits": ["sha1", "sha2"]
# }
```

### 7. Critical Methods to Implement

#### LocalExecutor._create_workspace
```python
async def _create_workspace(self, session_id: str) -> str:
    """Create a workspace directory for the session.
    
    Returns:
        Full path to the created workspace
        
    Raises:
        OSError: If workspace creation fails
    """
```

#### LocalExecutor._setup_repository
```python
async def _setup_repository(
    self, 
    workspace_dir: str, 
    git_branch: str,
    repository_url: str = "https://github.com/namastexlabs/am-agents-labs.git"
) -> None:
    """Clone and setup the repository in the workspace.
    
    Raises:
        subprocess.CalledProcessError: If git operations fail
    """
```

#### LocalExecutor._run_claude_process
```python
async def _run_claude_process(
    self,
    workspace_dir: str,
    message: str,
    env: Dict[str, str],
    timeout: int
) -> Dict[str, Any]:
    """Run Claude CLI as a subprocess.
    
    Returns:
        Execution result dictionary
        
    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
    """
```

## Error Handling Requirements

All implementations must handle these error cases:

1. **Workspace Errors**
   - Permission denied
   - Disk full
   - Directory already exists

2. **Git Errors**
   - Authentication failure
   - Network timeout
   - Invalid branch

3. **Process Errors**
   - Claude CLI not found
   - Process timeout
   - Signal termination

4. **Resource Errors**
   - Too many concurrent processes
   - Memory exhaustion
   - File descriptor limits

## Testing Requirements

Each interface must have corresponding tests:

1. **Unit Tests**
   - Mock subprocess for process testing
   - Mock file system for workspace testing
   - Test error conditions

2. **Integration Tests**
   - Real Claude CLI execution
   - Real git operations
   - End-to-end workflow execution

3. **Performance Tests**
   - Measure startup time
   - Monitor resource usage
   - Concurrent execution limits