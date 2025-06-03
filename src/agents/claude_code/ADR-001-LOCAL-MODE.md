# ADR-001: Local Execution Mode for Claude Code Agent

## Status
Proposed

## Context
The current Claude Code agent implementation exclusively uses Docker containers for executing Claude CLI. While this provides excellent isolation and consistency, it introduces overhead and complexity that may not be necessary for all use cases:

1. **Docker Overhead**: ~5 seconds startup time per execution
2. **Docker Dependency**: Requires Docker daemon running
3. **Development Friction**: Slower iteration during development
4. **Resource Usage**: Higher memory/CPU footprint
5. **CI/CD Complexity**: Some environments don't support Docker-in-Docker

## Decision
Implement a dual-mode execution system that supports both Docker (existing) and Local (new) execution modes, selectable via environment variable `CLAUDE_CODE_MODE`.

### Key Design Choices:

1. **Strategy Pattern**: Use abstract base class `ExecutorBase` with two implementations:
   - `DockerExecutor` (existing `ClaudeExecutor` renamed)
   - `LocalExecutor` (new implementation)

2. **Mode Selection**: Environment-based configuration
   ```bash
   CLAUDE_CODE_MODE=local|docker  # Default: docker
   ```

3. **Workspace Location**: Local mode uses `/tmp/claude-workspace-{session_id}`

4. **Process Management**: Direct subprocess execution instead of containers

5. **Shared Components**: Both modes use identical workflow configurations

## Consequences

### Positive
- **Faster Development**: 50% faster execution for short tasks
- **Reduced Dependencies**: Can run without Docker
- **Lower Resource Usage**: No container overhead
- **Easier Debugging**: Direct process access
- **Backward Compatible**: No breaking changes

### Negative
- **Reduced Isolation**: Less security isolation in local mode
- **Environment Inconsistency**: Potential "works on my machine" issues
- **Additional Complexity**: Two execution paths to maintain
- **Resource Management**: Harder to enforce limits in local mode

### Neutral
- **Testing Burden**: Need to test both modes
- **Documentation**: Must document both modes clearly
- **Configuration**: More options to understand

## Alternatives Considered

1. **Local-Only Mode**: Rejected due to loss of isolation benefits
2. **Separate Agent Type**: Rejected as too much code duplication
3. **Kubernetes Jobs**: Rejected as even more complex than Docker
4. **VM-based Isolation**: Rejected due to resource overhead

## Implementation Notes

1. **Phased Rollout**: Start with feature flag, gradually enable
2. **Default to Docker**: Maintain current behavior by default
3. **Clear Mode Indication**: Log which mode is active
4. **Cleanup Strategy**: Configurable workspace retention

## References
- Original Claude Code implementation plan
- Docker performance benchmarks
- Security requirements documentation