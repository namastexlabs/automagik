# NMSTX-230: Technical Decision Records

## ADR-001: PydanticAI with Embedded LangGraph Architecture

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
We need to implement Genie as a PydanticAI agent that orchestrates Claude Code workflow containers. The system requires state management, checkpointing, rollback capabilities, and human-in-the-loop coordination.

### Decision
Implement Genie as a PydanticAI agent that extends AutomagikAgent with an embedded LangGraph StateGraph for orchestration logic.

### Rationale
1. **Framework Compatibility**: Maintains compatibility with existing AutomagikAgent infrastructure
2. **Clean API Surface**: Single `/api/v1/agent/genie/run` endpoint for natural language control
3. **State Management**: LangGraph provides built-in state persistence and checkpointing
4. **Proven Pattern**: Similar to Archon pattern but adapted for our workflow needs

### Alternatives Considered
1. **Standalone LangGraph Service**: Rejected - adds complexity and separate deployment
2. **Direct Workflow Calling**: Rejected - lacks orchestration intelligence and state management
3. **Custom State Machine**: Rejected - reinventing what LangGraph already provides

### Consequences
- **Positive**: Unified agent interface, reusable infrastructure, clean architecture
- **Negative**: Dependency on LangGraph, learning curve for team
- **Risk**: LangGraph API changes could require refactoring

### Implementation Impact
- No breaking changes to existing agent infrastructure
- New dependency: langgraph and langchain-core
- Requires PostgreSQL for state persistence

---

## ADR-002: Claude Code API Integration for Workflow Execution

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Genie needs to execute 8 different Claude Code workflows (architect, implement, test, etc.) as part of epic orchestration.

### Decision
Execute workflows via the existing Claude Code API (`/api/v1/agent/claude-code/{workflow}/run`) rather than direct container management.

### Rationale
1. **Existing Infrastructure**: Leverages already-built Claude Code agent and container management
2. **Isolation**: Each workflow runs in its own container with proper resource limits
3. **Monitoring**: Claude Code API provides execution tracking and logging
4. **Consistency**: Same execution path as direct Claude Code usage

### Alternatives Considered
1. **Direct Docker Container Management**: Rejected - duplicates existing functionality
2. **Subprocess Execution**: Rejected - loses container isolation benefits
3. **Embedded Workflow Logic**: Rejected - workflows need full Claude CLI environment

### Consequences
- **Positive**: Reuses robust infrastructure, proper isolation, existing monitoring
- **Negative**: Network overhead for API calls, dependency on Claude Code service
- **Risk**: Claude Code API availability affects Genie operation

### Implementation Impact
- Requires Claude Code service to be running
- API client implementation needed in GenieAgent
- Async execution pattern for long-running workflows

---

## ADR-003: Dual State Persistence Strategy

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Genie needs to persist both operational state (for orchestration) and learning/patterns (for improvement).

### Decision
Use PostgreSQL for operational state via LangGraph checkpointer and MCP agent-memory for learning and patterns.

### Rationale
1. **Separation of Concerns**: Operational vs knowledge data have different requirements
2. **LangGraph Native**: PostgreSQL checkpointer is built-in and tested
3. **Learning System**: MCP agent-memory designed for pattern storage and retrieval
4. **Recovery**: Can rebuild from either system if needed

### Alternatives Considered
1. **Single Database**: Rejected - mixes transactional and graph data
2. **All in Agent-Memory**: Rejected - not optimized for checkpoint/recovery
3. **Custom Storage**: Rejected - unnecessary complexity

### Consequences
- **Positive**: Optimized storage for each use case, existing tools
- **Negative**: Two systems to maintain and monitor
- **Risk**: Potential consistency issues between systems

### Implementation Impact
- PostgreSQL required for LangGraph checkpointer
- Neo4j required for agent-memory (if Graphiti enabled)
- Clear boundaries needed between operational and learning data

---

## ADR-004: Natural Language Routing Architecture

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Genie receives natural language epic descriptions and must intelligently route to appropriate workflows.

### Decision
Implement a two-phase approach: 1) PydanticAI analyzes and plans the epic, 2) LangGraph executes the planned workflow sequence.

### Rationale
1. **Leverage LLM Strength**: Natural language understanding via PydanticAI
2. **Deterministic Execution**: LangGraph follows the planned sequence
3. **Flexibility**: Can adjust plan based on intermediate results
4. **Explainability**: Clear planning phase before execution

### Alternatives Considered
1. **Single-Phase LLM Routing**: Rejected - less predictable and harder to debug
2. **Rule-Based Routing**: Rejected - too rigid for natural language
3. **ML Classifier**: Rejected - requires training data we don't have

### Consequences
- **Positive**: Intelligent routing, explainable decisions, flexible execution
- **Negative**: Two-phase complexity, potential planning errors
- **Risk**: Poor epic analysis leads to wrong workflow selection

### Implementation Impact
- Epic analysis prompt engineering required
- Workflow selection logic in GenieAgent
- Clear handoff between planning and execution phases

---

## ADR-005: Human Approval Breakpoints

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Certain operations require human approval: breaking changes, new endpoints, folder creation, strategy changes, and cost overruns.

### Decision
Implement approval checkpoints using LangGraph interrupts with Slack notifications for human decisions.

### Rationale
1. **Production Safety**: Prevents autonomous breaking changes
2. **LangGraph Native**: Built-in interrupt/resume functionality
3. **Existing Channel**: Team already uses Slack for communication
4. **Audit Trail**: All approvals tracked in state

### Alternatives Considered
1. **Email Approvals**: Rejected - slower and less integrated
2. **Web UI**: Rejected - additional interface to build
3. **Automatic Approval**: Rejected - too risky for production

### Consequences
- **Positive**: Human oversight, production safety, audit trail
- **Negative**: Execution delays for approvals, requires human availability
- **Risk**: Approval bottlenecks could slow epic completion

### Implementation Impact
- Slack integration via MCP tools
- Approval state tracking in OrchestrationState
- Timeout handling for pending approvals

---

## ADR-006: Cost Control Implementation

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Epic execution must stay within a $50 budget limit with proper tracking and enforcement.

### Decision
Implement pre-execution cost estimation with runtime tracking and automatic pausing before limit exceeded.

### Rationale
1. **Predictability**: Users know costs before execution
2. **Safety**: Automatic stopping prevents overruns
3. **Flexibility**: Can request approval for overages
4. **Transparency**: Clear cost tracking throughout

### Alternatives Considered
1. **Hard Stop at Limit**: Rejected - could leave epic incomplete
2. **Post-Execution Billing**: Rejected - surprises users
3. **No Limits**: Rejected - financial risk

### Consequences
- **Positive**: Cost predictability, user control, financial safety
- **Negative**: Estimation complexity, potential epic interruption
- **Risk**: Poor estimates could stop epics prematurely

### Implementation Impact
- Cost estimation logic for each workflow
- Runtime cost tracking from Claude Code API
- Cost state management in OrchestrationState
- Approval flow for overages

---

## ADR-007: Rollback and Recovery Strategy

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Failed workflows need rollback capability to recover and retry with different approaches.

### Decision
Implement git-based snapshots before each workflow with LangGraph checkpoint coordination for state rollback.

### Rationale
1. **Data Safety**: Git snapshots preserve code state
2. **Coordination**: LangGraph checkpoints preserve orchestration state
3. **Learning**: Failed attempts stored in agent-memory
4. **Flexibility**: Can rollback to any workflow boundary

### Alternatives Considered
1. **Database Rollback Only**: Rejected - doesn't handle file system changes
2. **Container Snapshots**: Rejected - too resource intensive
3. **No Rollback**: Rejected - no recovery from failures

### Consequences
- **Positive**: Full recovery capability, learning from failures
- **Negative**: Git repository overhead, complexity
- **Risk**: Git conflicts on rollback need handling

### Implementation Impact
- Git snapshot management before each workflow
- Checkpoint creation at workflow boundaries
- Rollback UI/API for human decisions
- Conflict resolution strategies

---

## ADR-008: Async Execution Pattern

**Status**: Approved  
**Date**: 2025-06-03  
**Decision Makers**: Architecture Team

### Context
Epic execution can take hours, requiring async patterns for API responsiveness.

### Decision
Implement immediate epic ID return with status polling endpoint while LangGraph orchestrates in background.

### Rationale
1. **API Responsiveness**: Immediate response to users
2. **Long Running**: Epics can take hours to complete
3. **Progress Tracking**: Users can check status anytime
4. **Standard Pattern**: Common async API design

### Alternatives Considered
1. **Synchronous Execution**: Rejected - times out on long epics
2. **Webhooks Only**: Rejected - requires client endpoint
3. **WebSocket Streaming**: Rejected - complexity for initial version

### Consequences
- **Positive**: Responsive API, progress visibility, standard pattern
- **Negative**: Polling overhead, state management complexity
- **Risk**: Lost epic tracking if service restarts

### Implementation Impact
- Background task management
- Status API endpoint
- Epic state persistence
- Progress calculation logic

---

## Risk Assessment Summary

### High Priority Risks
1. **LangGraph API Stability**: Mitigation - Pin versions, abstract interface
2. **Claude Code Service Dependency**: Mitigation - Health checks, circuit breakers
3. **Cost Estimation Accuracy**: Mitigation - Conservative estimates, monitoring

### Medium Priority Risks
1. **Approval Bottlenecks**: Mitigation - Timeout handling, escalation
2. **State Consistency**: Mitigation - Transaction boundaries, validation
3. **Git Conflicts**: Mitigation - Conflict resolution strategies

### Low Priority Risks
1. **Performance at Scale**: Mitigation - Caching, optimization
2. **Learning Quality**: Mitigation - Pattern validation, human review

---

## Decision Review Schedule

- **3 Months**: Review cost estimation accuracy
- **6 Months**: Evaluate LangGraph stability and performance
- **12 Months**: Assess overall architecture fitness

---

## Approval Sign-offs

- Architecture Team: ✅ Approved
- Engineering Lead: ✅ Approved  
- Product Owner: ✅ Approved
- Security Review: ⏳ Pending (no breaking changes identified)