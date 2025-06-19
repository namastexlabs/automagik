# Environment Bridge Implementation Guide

## Overview

This document describes the implementation of Epic C - Environment Manager Bridge, which refactors the `CLIEnvironmentManager` to work with the SDK executor by exposing environment data instead of CLI flags.

## Implementation Status

### Completed Components

1. **CLIEnvironmentManager.as_dict() Method**
   - Added method to expose environment variables as a dictionary
   - Supports all existing environment features:
     - Core Claude environment (workspace, session ID)
     - Git information (repo path, branch, commit)
     - Workflow context (name, run ID)
     - API endpoints and authentication tokens
     - MCP server endpoints
     - Feature flags (citations, artifacts)
     - Workspace metadata

2. **Custom Transport for Environment Injection**
   - Created `EnvironmentAwareTransport` class for environment variable injection
   - Implements workaround for current SDK limitations
   - Provides context manager for safe injection/restoration
   - Supports subprocess spawning with custom environment

3. **SDK Executor with Environment Support**
   - Created `ClaudeSDKExecutor` that uses the SDK instead of CLI
   - Integrates with `CLIEnvironmentManager` for environment data
   - Uses transport workaround until SDK supports native env injection
   - Maintains compatibility with existing executor interface

4. **Comprehensive Test Suite**
   - Tests for `as_dict()` method with various configurations
   - Transport injection and restoration tests
   - Integration tests verifying subprocess environment
   - Edge case handling and cleanup verification

## Usage

### Basic Usage

```python
from src.agents.claude_code.cli_environment import CLIEnvironmentManager
from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor

# Create environment manager with context
env_mgr = CLIEnvironmentManager(
    workflow_name="my-workflow",
    session_id="session-123",
    enable_citations=True
)

# Create SDK executor
executor = ClaudeSDKExecutor(env_mgr)

# Execute task - environment variables are automatically injected
result = await executor.execute_claude_task(request, context)
```

### Environment Variables Exposed

The `as_dict()` method exposes the following environment variables:

- `CLAUDE_WORKSPACE`: Current workspace directory
- `CLAUDE_SESSION_ID`: Claude session identifier
- `CLAUDE_GIT_REPO`: Git repository path
- `CLAUDE_GIT_BRANCH`: Current git branch
- `CLAUDE_GIT_COMMIT`: Current commit hash
- `CLAUDE_WORKFLOW`: Workflow name
- `CLAUDE_WORKFLOW_RUN_ID`: Unique workflow run identifier
- `CLAUDE_API_BASE`: API base URL
- `CLAUDE_AUTH_*`: Authentication tokens (prefixed)
- `CLAUDE_MCP_SERVERS`: MCP endpoints as JSON
- `CLAUDE_ENABLE_CITATIONS`: Feature flag for citations
- `CLAUDE_ENABLE_ARTIFACTS`: Feature flag for artifacts
- `CLAUDE_WORKSPACE_ROOT`: Root workspace directory
- `CLAUDE_TEMP_DIR`: Temporary directory for workspace

## Current Workaround

Since the Claude Code SDK doesn't yet support custom environment injection, we use a process-level workaround:

```python
# Temporary workaround - inject into current process
transport = EnvironmentAwareTransport(custom_env)
with transport:
    # Environment variables are injected
    result = await sdk_function()
    # Environment is automatically restored
```

This approach:
- Temporarily modifies `os.environ`
- Stores original values for restoration
- Uses context manager for safety
- Restores environment after execution

## SDK Enhancement Request

We've documented the need for native SDK support:

```python
# Proposed SDK API
class ClaudeCodeOptions:
    custom_env: Optional[Dict[str, str]] = None

# Usage
options = ClaudeCodeOptions(
    custom_env=env_mgr.as_dict(workspace)
)
await query(prompt, options)
```

## Migration Path

1. **Phase 1 (Current)**: Use process-level environment injection
2. **Phase 2**: When SDK supports custom_env in options, update executor
3. **Phase 3**: Remove workaround code, use native SDK feature

## Testing

Run the test suite:

```bash
pytest tests/test_environment_bridge.py -v
```

Key test scenarios:
- Environment variable generation with various configurations
- Injection and restoration of environment variables
- Context manager behavior
- Integration with subprocess execution
- Multiple concurrent transports
- Edge cases and error handling

## Security Considerations

- Authentication tokens are passed as environment variables
- Environment restoration ensures no token leakage
- Process isolation maintained through worktree system
- No persistent environment modifications

## Performance Impact

- Minimal overhead from environment manipulation
- Context manager ensures quick restoration
- No impact on SDK execution performance
- Compatible with concurrent executions

## Future Improvements

1. **Native SDK Support**: Remove workaround when SDK adds environment support
2. **Enhanced Logging**: Add detailed environment injection logging
3. **Validation**: Add environment variable validation
4. **Metrics**: Track environment injection performance

## Troubleshooting

### Environment Not Injected
- Verify `as_dict()` is being called with correct workspace
- Check transport is used with context manager
- Ensure SDK executor is using environment manager

### Environment Not Restored
- Verify context manager exits properly
- Check for exceptions during execution
- Use try/finally for manual restoration if needed

### Variable Conflicts
- Check for existing environment variables
- Verify restoration logic handles all cases
- Use unique prefixes for Claude variables

## References

- [Epic C Specification](./epic-c-environment-bridge.md)
- [SDK Documentation](https://github.com/anthropics/claude-code-sdk)
- [Environment Variables Best Practices](https://12factor.net/config)