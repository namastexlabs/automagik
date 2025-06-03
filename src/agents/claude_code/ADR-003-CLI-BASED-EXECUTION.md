# ADR-003: CLI-Based Workflow Execution

## Status
Proposed

## Context

The current Claude Code implementation uses Docker containers for workflow execution. While this provides excellent isolation, we've discovered that Claude CLI offers native session management capabilities that could simplify our architecture and provide better integration with Genie orchestration.

Key observations:
- Claude CLI supports session resumption via `-r` flag
- Streaming JSON output provides real-time visibility
- Direct CLI execution reduces infrastructure complexity
- Session state persists across invocations

## Decision

We will implement a CLI-based execution mode for Claude Code workflows that:

1. **Uses Claude CLI directly** instead of containerized execution
2. **Leverages native session management** for context preservation
3. **Executes in isolated `/tmp` workspaces** for safety
4. **Streams JSON output** for real-time monitoring
5. **Integrates as a Genie tool** for orchestration

## Consequences

### Positive
- **Simplified Architecture**: No container orchestration needed
- **Native Session Support**: Built-in context preservation
- **Real-time Visibility**: JSON streaming for monitoring
- **Faster Startup**: No container overhead (~5-10s saved)
- **Better Integration**: Direct tool interface for Genie

### Negative
- **Less Isolation**: Process-level vs container isolation
- **Resource Management**: Harder to enforce limits
- **Dependency on CLI**: Requires Claude CLI installation
- **Security Surface**: Direct filesystem access

### Mitigation Strategies

1. **Process Isolation**: Use separate user/group for execution
2. **Resource Limits**: OS-level limits (ulimit, cgroups)
3. **Workspace Cleanup**: Aggressive cleanup policies
4. **Input Validation**: Strict validation of branches/messages

## Alternatives Considered

### 1. Enhanced Container Integration
- Add session persistence to containers
- **Rejected**: Complex state management

### 2. Hybrid Approach
- Containers for isolation, CLI for execution
- **Rejected**: Worst of both worlds

### 3. Custom Session Management
- Build our own session layer
- **Rejected**: Reinventing the wheel

## Implementation Plan

1. **Phase 1**: Basic CLI executor
2. **Phase 2**: Session management
3. **Phase 3**: Streaming integration
4. **Phase 4**: Genie tool interface

## Review Notes

This ADR requires review for:
- Security implications of process-based execution
- Resource management strategies
- Integration with existing monitoring