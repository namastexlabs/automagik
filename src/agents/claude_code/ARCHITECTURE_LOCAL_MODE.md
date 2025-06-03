# Claude Code Agent Local Mode Architecture

## Executive Summary

This document outlines the architecture for adding a local execution mode to the Claude Code agent, allowing it to run directly on the host system without Docker containers. The design maintains backward compatibility while providing a faster, simpler execution option for development and environments where Docker is not available.

## Design Goals

1. **Dual Mode Operation**: Support both Docker and Local execution modes
2. **Configuration-Driven**: Use environment variable to switch between modes
3. **Code Reuse**: Maximize reuse of existing workflow and execution logic
4. **Backwards Compatible**: No breaking changes to existing Docker mode
5. **Performance**: Faster startup and execution in local mode
6. **Simplicity**: Minimal additional complexity

## Architecture Overview

### Mode Selection

The execution mode will be determined by an environment variable:
```bash
CLAUDE_CODE_MODE=local|docker  # Default: docker
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ClaudeCodeAgent                         │
│  - Determines execution mode from environment               │
│  - Routes to appropriate executor                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌───────▼────────┐
│ DockerExecutor │         │ LocalExecutor  │
│ (existing)     │         │ (new)          │
├────────────────┤         ├────────────────┤
│ ContainerMgr   │         │ ProcessMgr     │
│ Docker API     │         │ Subprocess     │
│ Volume Mounts  │         │ File System    │
└────────────────┘         └────────────────┘
```

### Key Design Decisions

1. **Strategy Pattern**: Use strategy pattern to switch between executors
2. **Shared Workflow Logic**: Both modes use same workflow configurations
3. **Process Management**: Local mode uses subprocess for Claude CLI
4. **Workspace Management**: Local mode uses `/tmp/claude-workspace-{session_id}`
5. **Environment Isolation**: Local mode uses process environment variables

## Implementation Design

### 1. Abstract Executor Interface

Create a base executor interface that both Docker and Local executors implement:

```python
# executor_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from .models import ClaudeCodeRunRequest

class ExecutorBase(ABC):
    """Abstract base class for Claude executors."""
    
    @abstractmethod
    async def execute_claude_task(self, request: ClaudeCodeRunRequest, 
                                 agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Claude task."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
```

### 2. Local Executor Implementation

```python
# local_executor.py
class LocalExecutor(ExecutorBase):
    """Executes Claude CLI directly on the host system."""
    
    def __init__(self, workspace_base: str = "/tmp/claude-workspace"):
        self.workspace_base = workspace_base
        self.active_processes = {}
    
    async def execute_claude_task(self, request, agent_context):
        # 1. Create workspace directory
        workspace_dir = self._create_workspace(request.session_id)
        
        # 2. Clone repository to workspace
        await self._setup_repository(workspace_dir, request.git_branch)
        
        # 3. Copy workflow configuration
        await self._setup_workflow(workspace_dir, request.workflow_name)
        
        # 4. Build environment variables
        env = self._build_environment(request, agent_context)
        
        # 5. Execute Claude CLI
        result = await self._run_claude_process(
            workspace_dir, request.message, env
        )
        
        # 6. Handle git operations
        await self._handle_git_operations(workspace_dir)
        
        # 7. Cleanup (optional based on config)
        if self.cleanup_on_complete:
            await self._cleanup_workspace(workspace_dir)
        
        return result
```

### 3. Executor Factory

```python
# executor_factory.py
from src.config import settings

class ExecutorFactory:
    """Factory for creating appropriate executor based on configuration."""
    
    @staticmethod
    def create_executor(container_manager=None):
        mode = settings.config.get("CLAUDE_CODE_MODE", "docker").lower()
        
        if mode == "local":
            from .local_executor import LocalExecutor
            return LocalExecutor()
        else:
            from .executor import ClaudeExecutor
            return ClaudeExecutor(container_manager)
```

### 4. Modified Agent Class

Update `ClaudeCodeAgent` to use the factory:

```python
# agent.py
class ClaudeCodeAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Determine execution mode
        self.execution_mode = settings.config.get("CLAUDE_CODE_MODE", "docker").lower()
        
        # Initialize appropriate executor
        if self.execution_mode == "local":
            self.executor = LocalExecutor()
            self.container_manager = None
        else:
            self.container_manager = ContainerManager(...)
            self.executor = ClaudeExecutor(self.container_manager)
```

## Local Mode Implementation Details

### Workspace Structure

```
/tmp/claude-workspace-{session_id}/
├── am-agents-labs/          # Cloned repository
│   ├── .git/                # Git repository
│   ├── src/                 # Source code
│   └── ...                  # Other project files
├── workflow/                # Workflow configuration (copied)
│   ├── prompt.md
│   ├── .mcp.json
│   ├── allowed_tools.json
│   └── .env
└── .claude/                 # Claude configuration
    └── .credentials.json    # Symlink or copy
```

### Process Execution Flow

1. **Workspace Creation**
   - Create unique directory in `/tmp`
   - Set appropriate permissions

2. **Repository Setup**
   - Clone repository with sparse checkout if needed
   - Configure git user
   - Checkout specified branch

3. **Workflow Configuration**
   - Copy workflow files to workspace
   - Set up environment variables
   - Configure Claude credentials

4. **Claude Execution**
   - Build Claude CLI command
   - Execute via subprocess
   - Capture output and monitor progress
   - Handle timeouts and cancellation

5. **Post-Execution**
   - Generate and commit changes
   - Push to remote if configured
   - Clean up workspace (optional)

### Local Execution Script

Create `local_runner.sh` to mirror Docker entrypoint functionality:

```bash
#!/bin/bash
# local_runner.sh - Execute Claude locally

# Similar logic to entrypoint.sh but adapted for local execution
# Key differences:
# - No Docker operations
# - Direct file system access
# - Process-based service management
```

## Configuration

### Environment Variables

```bash
# Execution mode
CLAUDE_CODE_MODE=local|docker

# Local mode specific
CLAUDE_LOCAL_WORKSPACE=/tmp/claude-workspace
CLAUDE_LOCAL_CLEANUP=true|false
CLAUDE_LOCAL_GIT_CACHE=true|false

# Shared configuration
CLAUDE_CODE_TIMEOUT=7200
CLAUDE_CODE_MAX_CONCURRENT=10
```

### Workflow Compatibility

Both modes will use identical workflow configurations:
- `prompt.md` - System prompts
- `.mcp.json` - MCP server configuration
- `allowed_tools.json` - Tool permissions
- `.env` - Environment variables

## Security Considerations

### Local Mode Security

1. **Process Isolation**
   - Run Claude process with limited permissions
   - Use temporary directories with restrictive permissions
   - Clean up sensitive data after execution

2. **Credential Management**
   - Never copy credentials, use symlinks or environment variables
   - Ensure credentials are not persisted in workspace
   - Clear environment variables after use

3. **Resource Limits**
   - Implement process timeouts
   - Monitor memory and CPU usage
   - Limit concurrent executions

### Docker Mode (Existing)

- Container isolation remains unchanged
- Security benefits of containerization preserved
- No impact on existing security model

## Testing Strategy

### Unit Tests

1. **LocalExecutor Tests**
   - Workspace creation and cleanup
   - Process execution and monitoring
   - Error handling and timeouts
   - Git operations

2. **ExecutorFactory Tests**
   - Mode selection logic
   - Executor instantiation
   - Configuration handling

### Integration Tests

1. **Mode Switching**
   - Verify both modes work independently
   - Test mode selection via environment
   - Ensure no cross-mode interference

2. **Workflow Execution**
   - Test same workflows in both modes
   - Verify identical results
   - Performance comparison

## Migration Path

### Phase 1: Implementation
1. Implement LocalExecutor
2. Add ExecutorFactory
3. Update ClaudeCodeAgent
4. Create local_runner.sh

### Phase 2: Testing
1. Unit test coverage
2. Integration testing
3. Performance benchmarking
4. Security audit

### Phase 3: Rollout
1. Feature flag for local mode
2. Documentation update
3. Gradual rollout
4. Monitor for issues

## Performance Considerations

### Local Mode Advantages
- No container startup overhead (~5 seconds saved)
- Direct file system access
- Lower memory footprint
- Faster for small tasks

### Docker Mode Advantages
- Better isolation for long-running tasks
- Consistent environment
- Resource limits enforced
- Better for production use

## Rollback Plan

If local mode causes issues:
1. Set `CLAUDE_CODE_MODE=docker` to revert
2. No code changes required
3. Existing Docker mode unaffected
4. Can disable local mode via feature flag

## Success Metrics

1. **Performance**
   - Local mode 50% faster for tasks < 5 minutes
   - No regression in Docker mode performance

2. **Reliability**
   - Same success rate as Docker mode
   - Proper cleanup in all scenarios

3. **Compatibility**
   - All workflows function in both modes
   - No breaking changes to API

4. **Adoption**
   - Developer productivity improved
   - Reduced friction for local development