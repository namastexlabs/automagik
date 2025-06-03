# Claude-Code Agent Technical Decisions

## ADR-001: Container-Based Execution Model

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Need to run Claude CLI with full system access for hours-long autonomous tasks

**Decision**: Use Docker containers with one container per session

**Rationale**:
- Provides complete isolation between sessions
- Enables resource limits and monitoring
- Simplifies cleanup and recovery
- Supports state persistence via volumes

**Alternatives Considered**:
1. Direct process execution - Rejected due to security/isolation concerns
2. Kubernetes Jobs - Rejected due to complexity and infrastructure requirements
3. Serverless functions - Rejected due to execution time limits

**Consequences**:
- (+) Strong security isolation
- (+) Easy resource management
- (+) Clean failure recovery
- (-) Container startup overhead
- (-) Higher resource usage

---

## ADR-002: Async API with Polling

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Claude executions can take hours to complete

**Decision**: Implement async API that returns run_id immediately, with status polling endpoint

**Rationale**:
- Simple, stateless design
- Works with existing HTTP infrastructure
- No websocket complexity
- Clear separation of concerns

**Implementation**:
```
POST /api/v1/agent/claude-code/{workflow}/run -> { run_id }
GET /api/v1/agent/claude-code/run/{run_id}/status -> { status, result }
```

**Consequences**:
- (+) Simple client implementation
- (+) Scales horizontally
- (+) Works through proxies/firewalls
- (-) Polling overhead
- (-) Potential delay in status updates

---

## ADR-003: Use Existing Database Schema

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Need to store claude-code execution data

**Decision**: Store all data in existing JSONB columns without schema changes

**Rationale**:
- Zero migration risk
- No breaking changes
- Flexibility for evolving data structures
- Leverages PostgreSQL JSONB performance

**Storage Locations**:
- `sessions.metadata` - Container and workflow information
- `messages.raw_payload` - Request/response data
- `messages.context` - Execution metadata

**Consequences**:
- (+) No database migrations needed
- (+) Backward compatible
- (+) Flexible data evolution
- (-) No strict schema validation
- (-) Potential for data inconsistency

---

## ADR-004: Git-Based Persistence

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Need to persist code changes from Claude sessions

**Decision**: Each container clones am-agents-labs repo and pushes changes

**Rationale**:
- Natural version control
- Enables collaboration
- Audit trail of all changes
- Rollback capability

**Implementation**:
- Clone repo at container start
- Configure git user as "Claude Code Agent"
- Use Claude to generate commit messages
- Push to specified branch

**Consequences**:
- (+) Full change history
- (+) Multi-user collaboration
- (+) Easy rollback
- (-) Requires git credentials
- (-) Potential merge conflicts

---

## ADR-005: Claude Self-Commit Messages

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Need semantic commit messages for changes

**Decision**: Use Claude itself to analyze and commit changes

**Rationale**:
- No additional dependencies
- Claude understands context
- Consistent commit format
- Single tool for everything

**Implementation**:
```bash
claude --max-turns 1 --dangerously-skip-permissions \
  --append-system-prompt "Generate commit message..." \
  "Analyze staged changes and commit"
```

**Consequences**:
- (+) High-quality commit messages
- (+) No external scripts needed
- (+) Context-aware messages
- (-) Additional Claude invocation
- (-) Slightly slower completion

---

## ADR-006: Workflow-Based Configuration

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: Different use cases require different Claude configurations

**Decision**: Use filesystem-based workflow configurations

**Rationale**:
- Version controlled configurations
- Easy to add new workflows
- Clear separation from code
- Environment-specific overrides

**Structure**:
```
workflows/
├── bug-fixer/
│   ├── prompt.md
│   ├── .mcp.json
│   ├── allowed_tools.json
│   └── .env
└── pr-reviewer/
    └── ...
```

**Consequences**:
- (+) Flexible configuration
- (+) Git-reviewable changes
- (+) Easy workflow creation
- (-) File management overhead
- (-) Potential misconfigurations

---

## ADR-007: Feature Flag Protection

**Status**: Accepted  
**Date**: 2025-06-03  
**Context**: New agent type needs safe rollout

**Decision**: Gate claude-code behind AM_ENABLE_CLAUDE_CODE flag

**Rationale**:
- Safe gradual rollout
- Quick disable if issues
- No impact when disabled
- Testing in production

**Implementation**:
- Check flag in agent factory
- Return 404 if disabled
- Default to false

**Consequences**:
- (+) Safe deployment
- (+) Quick rollback
- (+) Gradual adoption
- (-) Additional configuration
- (-) Flag management overhead