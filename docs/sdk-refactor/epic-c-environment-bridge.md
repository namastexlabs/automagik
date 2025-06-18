# Epic C - Environment Manager Bridge

## Owner: @builder-workflow
## Branch: feature/sdk-migration (after Epic B started)
## Priority: THIRD - Can run parallel with Epic B

## Objective
Refactor `CLIEnvironmentManager` to work with the SDK executor, exposing environment data instead of CLI flags.

## Detailed Implementation Steps

### C1. Refactor CLIEnvironmentManager
Add method to expose pure environment data:

```python
# In /src/agents/claude_code/cli_environment.py

def as_dict(self, workspace: Path) -> dict[str, str]:
    """
    Return environment variables to inject into subprocess.
    
    This replaces the old CLI flag generation with pure data
    that can be used by the SDK executor.
    """
    env = {}
    
    # Core Claude environment
    env['CLAUDE_WORKSPACE'] = str(workspace)
    env['CLAUDE_SESSION_ID'] = self.session_id or ''
    
    # Git information
    if self.git_info:
        env['CLAUDE_GIT_REPO'] = self.git_info.repo_path
        env['CLAUDE_GIT_BRANCH'] = self.git_info.current_branch
        env['CLAUDE_GIT_COMMIT'] = self.git_info.current_commit
    
    # Workflow context
    if self.workflow_name:
        env['CLAUDE_WORKFLOW'] = self.workflow_name
        env['CLAUDE_WORKFLOW_RUN_ID'] = self.workflow_run_id or ''
    
    # API endpoints (if configured)
    if self.api_base_url:
        env['CLAUDE_API_BASE'] = self.api_base_url
    
    # Authentication tokens
    if self.auth_tokens:
        for key, value in self.auth_tokens.items():
            env[f'CLAUDE_AUTH_{key.upper()}'] = value
    
    # MCP server endpoints
    if self.mcp_endpoints:
        env['CLAUDE_MCP_SERVERS'] = json.dumps(self.mcp_endpoints)
    
    # Feature flags
    env['CLAUDE_ENABLE_CITATIONS'] = str(self.enable_citations).lower()
    env['CLAUDE_ENABLE_ARTIFACTS'] = str(self.enable_artifacts).lower()
    
    # Workspace metadata
    env['CLAUDE_WORKSPACE_ROOT'] = str(self.workspace_root)
    env['CLAUDE_TEMP_DIR'] = str(workspace / '.claude-temp')
    
    return env
```

### C2. SDK Executor Integration
Update the SDK executor to use environment data:

```python
# In /src/agents/claude_code/sdk_executor.py

class ClaudeSDKExecutor:
    def __init__(self, environment_manager: CLIEnvironmentManager):
        self.env_mgr = environment_manager
        self._claude = ClaudeCode()
    
    async def _create_subprocess_with_env(
        self, 
        options: ClaudeCodeOptions,
        workspace: Path
    ) -> ClaudeCodeOptions:
        """
        Enhance options with custom environment variables.
        
        NOTE: This requires SDK support for custom env injection.
        Current approach: Document and prepare for SDK enhancement.
        """
        # Get environment variables
        custom_env = self.env_mgr.as_dict(workspace)
        
        # TODO: When SDK supports custom env, use:
        # options.custom_env = custom_env
        # 
        # For now, we'll need to monkey-patch or wait for SDK update
        
        # Temporary workaround - set process env before SDK spawn
        # This is not ideal but maintains functionality
        for key, value in custom_env.items():
            os.environ[key] = value
        
        return options
```

### C3. Enhanced Subprocess Handling
Create a custom transport if SDK allows:

```python
# In /src/agents/claude_code/sdk_transport.py

from claude_code.transport import SubprocessCLITransport
import os
from typing import Dict, Optional

class EnvironmentAwareTransport(SubprocessCLITransport):
    """Custom transport that injects environment variables."""
    
    def __init__(self, *args, custom_env: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_env = custom_env or {}
    
    async def _spawn_process(self, cmd: list[str]) -> asyncio.subprocess.Process:
        """Override to inject custom environment."""
        env = os.environ.copy()
        env.update(self.custom_env)
        
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=self.cwd
        )
```

### C4. Update Executor to Use Custom Transport

```python
# In sdk_executor.py
async def execute(self, prompt: str, *, workspace: Path, **kwargs) -> CLIResult:
    """Execute with custom environment injection."""
    options = self._build_options(workspace, **kwargs)
    
    # Get custom environment
    custom_env = self.env_mgr.as_dict(workspace)
    
    # Create transport with env injection
    transport = EnvironmentAwareTransport(custom_env=custom_env)
    
    # Use transport with SDK
    # NOTE: This assumes SDK can accept custom transport
    # If not, we need to request this feature
    
    messages = []
    async for message in query(prompt, options, transport=transport):
        messages.append(message)
    
    return CLIResult(success=True, messages=messages)
```

### C5. Unit Tests

```python
# tests/test_environment_bridge.py
import pytest
from pathlib import Path

def test_env_manager_as_dict(tmp_path):
    """Test environment manager returns correct dict."""
    env_mgr = CLIEnvironmentManager(
        workspace_root=tmp_path,
        workflow_name="test-workflow",
        session_id="test-123"
    )
    
    env_dict = env_mgr.as_dict(tmp_path)
    
    assert env_dict['CLAUDE_WORKSPACE'] = /tmp_path
    assert env_dict['CLAUDE_WORKFLOW'] == 'test-workflow'
    assert env_dict['CLAUDE_SESSION_ID'] == 'test-123'

@pytest.mark.asyncio
async def test_env_injection(tmp_path, monkeypatch):
    """Test environment variables are injected into subprocess."""
    # Create test script that prints env var
    test_script = tmp_path / "test_env.py"
    test_script.write_text("""
import os
print(f"CLAUDE_WORKFLOW={os.environ.get('CLAUDE_WORKFLOW', 'NOT_SET')}")
    """)
    
    env_mgr = CLIEnvironmentManager(workflow_name="epic-test")
    executor = ClaudeSDKExecutor(env_mgr)
    
    # Execute and verify env var was set
    result = await executor.execute(
        f"Run python {test_script}",
        workspace=tmp_path
    )
    
    assert "CLAUDE_WORKFLOW=epic-test" in str(result.messages)
```

## Success Criteria
- [ ] CLIEnvironmentManager has `as_dict()` method returning env vars
- [ ] SDK executor can inject custom environment variables
- [ ] All existing environment features work with SDK
- [ ] Git worktree integration maintained
- [ ] Session management preserved
- [ ] Tests verify env injection works

## Implementation Priority
1. Implement `as_dict()` method first (non-breaking)
2. Create temporary workaround for env injection
3. Test with simple env vars
4. Document SDK enhancement request
5. Implement proper solution when SDK supports it

## SDK Enhancement Request
Submit PR to claude-code-sdk for:
```python
class ClaudeCodeOptions:
    custom_env: Optional[Dict[str, str]] = None
```

## Files to Modify
- `/src/agents/claude_code/cli_environment.py`
- `/src/agents/claude_code/sdk_executor.py`
- `/src/agents/claude_code/sdk_transport.py` (new)
- `/tests/test_environment_bridge.py` (new)

## Rollback Considerations
- Keep original CLI flag methods until fully migrated
- Ensure `as_dict()` doesn't break existing code
- Test thoroughly with production workloads