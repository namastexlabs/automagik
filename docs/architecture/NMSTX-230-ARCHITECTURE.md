# NMSTX-230: PydanticAI Genie Orchestrator Architecture

## Executive Summary

The PydanticAI Genie Orchestrator is a natural language-driven orchestration system that combines PydanticAI's agent framework with LangGraph's state management to enable automated epic execution through intelligent workflow routing. The system accepts natural language requests and orchestrates 8 specialized Claude Code workflows to complete complex development tasks.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Natural Language API                        │
│                 POST /api/v1/agent/genie/run                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GenieAgent (PydanticAI)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Natural Language Processing                  │   │
│  │           - Intent Analysis & Classification              │   │
│  │           - Epic Decomposition & Planning                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Embedded LangGraph Engine                    │   │
│  │         - StateGraph for Workflow Orchestration          │   │
│  │         - Checkpointing & State Persistence              │   │
│  │         - Conditional Routing & Decision Making          │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Workflow Execution Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │architect │ │implement │ │   test   │ │  review  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   fix    │ │ refactor │ │ document │ │    pr    │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│               Supporting Infrastructure                          │
│  ┌────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Claude Code API│ │  MCP Agent Memory│ │ Slack Integration│   │
│  └────────────────┘ └─────────────────┘ └─────────────────┘   │
│  ┌────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │  Cost Tracking │ │ Human Approvals  │ │State Persistence│   │
│  └────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

1. **GenieAgent (PydanticAI Layer)**
   - Extends AutomagikAgent base class
   - Natural language understanding and decomposition
   - Epic planning and workflow selection
   - Cost tracking and budget enforcement ($50 limit)
   - API endpoint handling

2. **LangGraph Orchestration Engine**
   - Embedded StateGraph for workflow management
   - Conditional routing based on epic analysis
   - State persistence and checkpointing
   - Human approval breakpoints
   - Rollback and recovery management

3. **Workflow Executors**
   - 8 specialized Claude Code workflows
   - Each workflow has distinct responsibilities
   - Executed via Claude Code API
   - Container-based isolation

4. **Integration Points**
   - MCP agent-memory for learning and patterns
   - Slack for human communication
   - PostgreSQL for state persistence
   - Claude Code API for workflow execution

## Data Flow Architecture

### Request Processing Flow

```
1. Natural Language Request
   └─> GenieAgent.run()
       └─> Epic Analysis
           ├─> Intent Classification
           ├─> Complexity Assessment
           └─> Workflow Selection

2. Orchestration Planning
   └─> LangGraph StateGraph
       ├─> Initial State Creation
       ├─> Workflow Sequence Planning
       └─> Cost Estimation

3. Workflow Execution
   └─> Sequential/Parallel Execution
       ├─> Architect → Design Phase
       ├─> Implement → Code Phase
       ├─> Test → Validation Phase
       └─> PR → Completion Phase

4. State Management
   └─> Checkpoint After Each Step
       ├─> Success → Continue
       ├─> Failure → Rollback Option
       └─> Human Needed → Pause & Alert
```

### State Schema

```python
class EpicState(TypedDict):
    # Core Identifiers
    epic_id: str
    session_id: str
    user_id: Optional[str]
    
    # Epic Details
    original_request: str
    epic_title: str
    epic_description: str
    complexity_score: int  # 1-10
    
    # Workflow Planning
    planned_workflows: List[str]
    completed_workflows: List[str]
    current_workflow: Optional[str]
    workflow_results: Dict[str, Any]
    
    # Cost Management
    cost_accumulated: float
    cost_limit: float
    cost_estimates: Dict[str, float]
    
    # Human Approval Tracking
    approval_points: List[ApprovalPoint]
    pending_approvals: List[str]
    approval_history: Dict[str, ApprovalDecision]
    
    # Execution State
    phase: Literal["planning", "executing", "reviewing", "complete", "failed"]
    error_count: int
    rollback_points: List[RollbackPoint]
    
    # Learning & Patterns
    applied_patterns: List[str]
    discovered_patterns: List[str]
    failure_reasons: List[str]
```

## Workflow Integration Architecture

### Workflow Routing Logic

```python
class WorkflowRouter:
    """Intelligent routing based on epic analysis"""
    
    WORKFLOW_PATTERNS = {
        "architect": ["design", "architecture", "planning", "system"],
        "implement": ["build", "create", "develop", "feature"],
        "test": ["test", "validate", "verify", "check"],
        "fix": ["bug", "fix", "repair", "issue"],
        "refactor": ["refactor", "improve", "optimize", "cleanup"],
        "document": ["document", "docs", "readme", "explain"],
        "review": ["review", "analyze", "audit", "inspect"],
        "pr": ["pr", "pull request", "merge", "complete"]
    }
    
    def select_workflows(self, epic_analysis: Dict) -> List[str]:
        """Select and sequence workflows based on epic analysis"""
        # Complex logic for workflow selection
        # Returns ordered list of workflows to execute
```

### Human Approval Integration

```python
class ApprovalManager:
    """Manages human approval checkpoints"""
    
    APPROVAL_TRIGGERS = {
        "breaking_changes": "Architecture includes breaking changes",
        "new_endpoints": "New API endpoints detected",
        "folder_creation": "New top-level folders planned",
        "strategy_change": "Major strategy deviation detected",
        "cost_threshold": "Approaching cost limit"
    }
    
    async def check_approval_needed(self, state: EpicState) -> Optional[ApprovalRequest]:
        """Determine if human approval is needed"""
        # Returns approval request if needed
```

## Technical Design Decisions

### 1. PydanticAI + Embedded LangGraph Pattern
**Decision**: Embed LangGraph within PydanticAI agent rather than wrapping
**Rationale**: 
- Maintains AutomagikAgent compatibility
- Provides clean API surface
- Allows natural language control
- Enables state management without external orchestration

**Implementation**:
```python
class GenieAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(config)
        self.workflow_graph = self._create_orchestration_graph()
    
    def _create_orchestration_graph(self) -> StateGraph:
        # Build LangGraph with workflow nodes
```

### 2. Workflow Execution via Claude Code API
**Decision**: Execute workflows through Claude Code API, not direct containers
**Rationale**:
- Leverages existing Claude Code infrastructure
- Provides isolation and resource management
- Enables proper logging and monitoring
- Supports existing workflow configurations

### 3. State Persistence Strategy
**Decision**: Dual persistence - PostgreSQL for state, memory for learning
**Rationale**:
- PostgreSQL for transactional state (via LangGraph checkpointer)
- MCP agent-memory for patterns and learning
- Separation of operational and knowledge data

### 4. Cost Control Architecture
**Decision**: Pre-execution estimation with runtime tracking
**Rationale**:
- Estimate costs before workflow execution
- Track actual usage during execution
- Pause before exceeding limits
- Request human approval for overages

## Integration Interfaces

### API Contract

```typescript
// Request
POST /api/v1/agent/genie/run
{
    "message": "Create a new authentication system with OAuth2",
    "context": {
        "budget_limit": 50.0,
        "require_pr": true,
        "require_tests": true,
        "approval_mode": "auto" | "manual"
    }
}

// Response
{
    "epic_id": "epic_123abc",
    "status": "executing",
    "planned_workflows": ["architect", "implement", "test", "pr"],
    "estimated_cost": 35.50,
    "approval_required": false,
    "tracking_url": "/api/v1/agent/genie/status/epic_123abc"
}
```

### Claude Code API Integration

```python
class ClaudeCodeExecutor:
    """Executes workflows via Claude Code API"""
    
    async def execute_workflow(
        self, 
        workflow_name: str,
        task_context: str,
        epic_state: EpicState
    ) -> WorkflowResult:
        # Call Claude Code API with workflow
        # Monitor execution
        # Return results
```

### MCP Memory Integration

```python
class GenieMemoryManager:
    """Manages learning and pattern storage"""
    
    async def store_epic_learning(self, epic_state: EpicState):
        # Store successful patterns
        # Record failure modes
        # Update workflow preferences
        
    async def retrieve_relevant_patterns(self, epic_description: str):
        # Search for similar epics
        # Find applicable patterns
        # Return guidance
```

## Rollback and Recovery

### Checkpoint Strategy
- Checkpoint after each workflow completion
- Store workflow artifacts and state
- Enable rollback to any checkpoint
- Preserve learning even on rollback

### Failure Handling
```python
class FailureHandler:
    """Manages failures and recovery"""
    
    RETRY_STRATEGIES = {
        "timeout": "retry_with_extended_time",
        "api_error": "retry_with_backoff",
        "workflow_error": "analyze_and_reroute",
        "approval_denied": "revise_approach"
    }
```

## Security Considerations

### Input Validation
- Sanitize natural language inputs
- Validate workflow parameters
- Enforce role-based access control
- Audit all epic executions

### Resource Limits
- CPU/Memory limits per workflow
- Concurrent execution limits
- Rate limiting per user
- Storage quotas

## Performance Optimization

### Caching Strategy
- Cache workflow templates
- Cache cost estimates
- Cache pattern matches
- Invalidate on updates

### Parallel Execution
- Identify independent workflows
- Execute in parallel where safe
- Maintain dependency ordering
- Optimize for throughput

## Monitoring and Observability

### Metrics
- Epic completion rate
- Average cost per epic
- Workflow success rates
- Human intervention frequency
- Pattern application effectiveness

### Logging
- Structured logging for all decisions
- Workflow execution traces
- State transition history
- Cost accumulation logs

## Migration Path

### Phase 1: Core Implementation
- GenieAgent with basic LangGraph
- Single workflow execution
- Manual workflow selection

### Phase 2: Intelligence Layer
- Natural language analysis
- Automatic workflow routing
- Pattern learning

### Phase 3: Advanced Features
- Parallel execution
- Complex approval flows
- Advanced cost optimization
- Multi-epic coordination

## Success Criteria

1. **Functional Requirements**
   - Natural language epic execution
   - All 8 workflows integrated
   - Human approval flows working
   - $50 cost limit enforced
   - Learning from failures implemented

2. **Performance Requirements**
   - Epic planning < 5 seconds
   - Workflow routing < 2 seconds
   - State checkpoint < 1 second
   - API response < 500ms

3. **Quality Requirements**
   - 95%+ epic completion rate
   - <5% human intervention rate
   - Zero data loss on failures
   - Full audit trail maintained