# Agent Orchestration Patterns

## Overview

This document describes proven architectural patterns for orchestrating multiple AI agents in complex workflows. These patterns have been extracted from production implementations and provide reusable solutions for agent coordination.

## Core Orchestration Patterns

### 1. PydanticAI + LangGraph Integration Pattern

**Problem**: Need structured agent interactions with stateful workflow orchestration.

**Solution**: Embed LangGraph StateGraph within PydanticAI agents for dual-level orchestration.

**Implementation**:
```python
from pydantic_ai import Agent
from langgraph.graph import StateGraph

class OrchestratorAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)
        workflow.add_node("analyze", self.analyze_task)
        workflow.add_node("route", self.route_to_agent)
        workflow.add_node("execute", self.execute_workflow)
        workflow.add_conditional_edges("analyze", self.should_continue)
        return workflow.compile(checkpointer=self.checkpointer)
```

**Benefits**:
- Structured agent interactions via PydanticAI
- Stateful workflow management via LangGraph
- Persistent state across interruptions
- Clear separation of concerns

### 2. Dual State Persistence Pattern

**Problem**: Need both operational state and learning/memory across agent sessions.

**Solution**: Use PostgreSQL for operational state and MCP agent-memory for accumulated knowledge.

**Architecture**:
```
┌─────────────────────┐    ┌─────────────────────┐
│   PostgreSQL        │    │   MCP Memory        │
│   (Operational)     │    │   (Learning)        │
├─────────────────────┤    ├─────────────────────┤
│ • Session state     │    │ • Pattern storage   │
│ • Workflow progress │    │ • Decision history  │
│ • Message history   │    │ • Failure analysis  │
│ • Agent assignments │    │ • Success patterns  │
└─────────────────────┘    └─────────────────────┘
```

**Implementation**:
- Operational state: Database repositories for sessions, workflows, progress
- Learning state: MCP agent-memory for patterns, decisions, retrospectives
- Sync points: After major workflow transitions

### 3. Natural Language Routing Pattern

**Problem**: Route tasks to appropriate agents without rigid rule systems.

**Solution**: Two-phase natural language analysis: task decomposition + agent selection.

**Process**:
1. **Analysis Phase**: Decompose request into structured components
2. **Routing Phase**: Match components to agent capabilities
3. **Validation Phase**: Confirm routing decisions with rationale

**Example**:
```python
async def route_task(self, task: str) -> AgentAssignment:
    # Phase 1: Decompose task
    analysis = await self.analyze_task(task)
    
    # Phase 2: Select agents
    assignments = await self.select_agents(analysis)
    
    # Phase 3: Validate routing
    validated = await self.validate_routing(assignments)
    
    return validated
```

### 4. Human Approval Checkpoint Pattern

**Problem**: Ensure human oversight for critical decisions and breaking changes.

**Solution**: LangGraph interrupts with Slack notifications for human approval.

**Implementation**:
```python
def add_human_approval_node(workflow: StateGraph, condition: str):
    workflow.add_node(f"approval_{condition}", create_approval_request)
    workflow.add_node(f"wait_{condition}", wait_for_human_response)
    workflow.add_conditional_edges(
        f"wait_{condition}", 
        lambda state: "approved" if check_approval(state) else "rejected"
    )
```

**Approval Triggers**:
- Breaking changes to APIs
- Database schema modifications
- Production deployments
- Major architectural changes
- Budget/cost threshold exceeded

### 5. Cost Control and Monitoring Pattern

**Problem**: Track and control computational costs across multi-agent workflows.

**Solution**: Pre-execution estimation with runtime tracking and circuit breakers.

**Architecture**:
```python
class CostController:
    def __init__(self, budget_limit: float):
        self.budget_limit = budget_limit
        self.current_spend = 0.0
    
    async def estimate_cost(self, workflow: WorkflowPlan) -> CostEstimate:
        # Estimate tokens, API calls, compute time
        pass
    
    async def track_execution(self, step: WorkflowStep) -> bool:
        cost = await self.measure_step_cost(step)
        self.current_spend += cost
        
        if self.current_spend > self.budget_limit:
            await self.trigger_cost_circuit_breaker()
            return False
        return True
```

**Cost Tracking Points**:
- LLM API calls (tokens in/out)
- External tool usage
- Database operations
- Human time estimates

### 6. Rollback and Recovery Pattern

**Problem**: Safely recover from failed workflow states without losing progress.

**Solution**: Git snapshots + LangGraph checkpoints for multi-level recovery.

**Recovery Levels**:
1. **Step Recovery**: Retry individual workflow steps
2. **State Recovery**: Restore to last known good state
3. **Snapshot Recovery**: Git reset to working codebase
4. **Full Recovery**: Complete workflow restart

**Implementation**:
```python
class RecoveryManager:
    def create_snapshot(self, workflow_id: str) -> str:
        # Git commit current state
        snapshot_id = git.create_snapshot(f"workflow_{workflow_id}")
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str):
        # Git reset to snapshot
        git.restore_snapshot(snapshot_id)
    
    def restore_checkpoint(self, checkpoint_id: str):
        # LangGraph state recovery
        return self.checkpointer.get_tuple(checkpoint_id)
```

### 7. Async Execution Pattern

**Problem**: Long-running workflows need non-blocking execution with status updates.

**Solution**: Return execution ID immediately, provide polling endpoints for status.

**Flow**:
1. Client submits workflow request
2. System returns workflow ID immediately
3. Client polls status endpoint for updates
4. System provides detailed progress information
5. Client receives completion notification

**API Design**:
```python
# Submit workflow
POST /api/v1/workflows
Response: {"workflow_id": "wf_123", "status": "queued"}

# Check status  
GET /api/v1/workflows/wf_123
Response: {
    "workflow_id": "wf_123",
    "status": "running",
    "progress": 0.6,
    "current_step": "implementation",
    "estimated_completion": "2024-01-15T14:30:00Z"
}
```

## Orchestration Architectures

### Centralized Orchestration

**When to Use**: Single complex workflow with clear dependencies.

**Pattern**: One orchestrator agent manages all other agents.

```
┌─────────────────┐
│   Orchestrator  │
│     (Alpha)     │
└─────────┬───────┘
          │
    ┌─────┼─────┐
    │     │     │
┌───▼─┐ ┌─▼─┐ ┌─▼───┐
│Beta │ │Gamma│ │Delta│
└─────┘ └───┘ └─────┘
```

### Distributed Orchestration

**When to Use**: Independent workflows with loose coupling.

**Pattern**: Multiple orchestrators coordinate specific domains.

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Core    │    │ API     │    │ Testing │
│ Orchest.│    │ Orchest.│    │ Orchest.│
└─────────┘    └─────────┘    └─────────┘
```

### Hierarchical Orchestration

**When to Use**: Complex workflows with sub-workflows.

**Pattern**: Tree structure with parent-child orchestrators.

```
      ┌─────────────┐
      │   Master    │
      │ Orchestrator│
      └──────┬──────┘
             │
      ┌──────┼──────┐
      │      │      │
  ┌───▼─┐ ┌──▼─┐ ┌──▼───┐
  │Sub1 │ │Sub2│ │ Sub3 │
  └─────┘ └────┘ └──────┘
```

## Communication Patterns

### Thread-Based Communication

Use Slack threads for organized multi-agent discussions:

```python
# Start epic thread
thread_response = slack_post_message(
    channel_id=COORDINATION_CHANNEL,
    text="🎯 **EPIC STARTED**: Feature Implementation\n\nTeam: @beta @gamma @delta"
)

# All subsequent updates in thread
slack_reply_to_thread(
    channel_id=COORDINATION_CHANNEL,
    thread_ts=thread_response.ts,
    text="🔧 **Beta**: Core implementation complete"
)
```

### Status Broadcasting

Regular status updates with consistent formatting:

```python
def post_status_update(agent: str, status: str, details: str):
    emoji = {"in_progress": "⏳", "completed": "✅", "blocked": "🚨"}
    message = f"{emoji[status]} **{agent}**: {details}"
    return slack_post_message(channel_id, message)
```

### Human Escalation

Structured escalation for critical decisions:

```python
def escalate_decision(decision: str, context: str, urgency: str):
    escalation_text = f"""
🚨 **HUMAN DECISION REQUIRED** ({urgency})

**Decision**: {decision}
**Context**: {context}
**Required By**: {deadline}

Please reply with: APPROVE or REJECT
"""
    return slack_post_message(ESCALATION_CHANNEL, escalation_text)
```

## Error Handling Patterns

### Graceful Degradation

When agents fail, continue with reduced functionality:

```python
async def execute_with_fallback(primary_agent: str, fallback_agent: str, task: dict):
    try:
        return await execute_agent(primary_agent, task)
    except AgentFailure:
        logger.warning(f"{primary_agent} failed, falling back to {fallback_agent}")
        return await execute_agent(fallback_agent, task)
```

### Circuit Breaker Pattern

Prevent cascade failures by temporarily disabling failing agents:

```python
class AgentCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure = None
        self.state = "closed"  # closed, open, half_open
```

### Retry with Backoff

Intelligent retry for transient failures:

```python
async def execute_with_retry(agent: str, task: dict, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await execute_agent(agent, task)
        except TransientFailure:
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
    raise MaxRetriesExceeded()
```

## Performance Optimization

### Parallel Execution

Execute independent tasks concurrently:

```python
async def execute_parallel_tasks(tasks: List[Task]):
    # Group by dependencies
    independent_tasks = group_independent_tasks(tasks)
    
    # Execute groups in parallel
    results = []
    for task_group in independent_tasks:
        group_results = await asyncio.gather(*[
            execute_agent(task.agent, task.payload) 
            for task in task_group
        ])
        results.extend(group_results)
    
    return results
```

### Resource Pool Management

Manage shared resources (tokens, rate limits):

```python
class ResourcePool:
    def __init__(self, max_concurrent: int):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(calls_per_minute=60)
    
    async def acquire(self):
        async with self.semaphore:
            await self.rate_limiter.acquire()
            yield
```

### Caching and Memoization

Cache expensive operations:

```python
@lru_cache(maxsize=100)
async def cached_agent_analysis(task_hash: str):
    # Expensive analysis operation
    return await perform_analysis(task_hash)
```

## Monitoring and Observability

### Workflow Metrics

Track key orchestration metrics:

```python
class OrchestrationMetrics:
    def track_workflow_duration(self, workflow_id: str, duration: float):
        metrics.histogram("workflow.duration", duration, tags={"workflow_id": workflow_id})
    
    def track_agent_performance(self, agent: str, success: bool, duration: float):
        metrics.increment("agent.calls", tags={"agent": agent, "success": success})
        metrics.histogram("agent.duration", duration, tags={"agent": agent})
```

### Health Checks

Monitor agent and system health:

```python
async def health_check():
    checks = {
        "database": await check_database_health(),
        "agents": await check_agent_health(),
        "memory": await check_memory_health(),
        "slack": await check_slack_health(),
    }
    return {"status": "healthy" if all(checks.values()) else "degraded", "checks": checks}
```

## Best Practices

### Workflow Design
- Keep workflows stateless where possible
- Design for interruption and resumption
- Implement clear rollback strategies
- Use timeouts for all operations

### Agent Coordination
- Establish clear agent boundaries
- Use typed interfaces between agents
- Implement health checks for all agents
- Plan for agent failures

### Human Integration
- Design clear escalation paths
- Provide sufficient context for decisions
- Implement approval timeouts
- Maintain audit trails

### Performance
- Profile workflow execution
- Optimize critical paths
- Implement caching strategies
- Monitor resource usage

## Related Documentation

- **[Architecture](./overview.md)** - System architecture overview
- **[Agents Overview](../development/agents-overview.md)** - Agent system details
- **[Slack Integration](../integrations/slack.md)** - Communication patterns
- **[Memory Management](./memory.md)** - State persistence patterns

---

**Last Updated**: January 2025  
**Status**: Production Ready ✅