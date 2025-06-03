# NMSTX-230: Implementation Roadmap

## Overview
This roadmap outlines the phased implementation of the PydanticAI Genie Orchestrator over a 10-day timeline.

## Timeline Summary

```
Week 1: Foundation (Days 1-5)
├─ Days 1-2: PydanticAI Agent Structure
├─ Days 3-4: LangGraph Integration  
└─ Day 5: Basic Workflow Execution

Week 2: Intelligence & Polish (Days 6-10)
├─ Days 6-7: Natural Language & Routing
├─ Days 8-9: Human Approvals & Cost Control
└─ Day 10: Testing & Documentation
```

## Detailed Implementation Phases

### Phase 1: PydanticAI Agent Structure (Days 1-2)

#### Day 1: Project Setup & Base Structure
**Morning (4 hours)**
- [ ] Create directory structure: `src/agents/pydanticai/genie/`
- [ ] Implement `GenieAgent` class extending `AutomagikAgent`
- [ ] Set up basic `__init__.py` with `create_agent()` factory
- [ ] Create placeholder `prompts/prompt.py` with Genie personality

**Afternoon (4 hours)**
- [ ] Implement basic `run()` method with epic parsing
- [ ] Add natural language request handling
- [ ] Create `models.py` with data structures:
  - `EpicRequest`, `EpicState`, `WorkflowResult`
- [ ] Write initial unit tests for agent creation

**Deliverables**: 
- Basic GenieAgent that can receive and parse natural language requests
- Passing unit tests for agent initialization

#### Day 2: API Integration & Context Management
**Morning (4 hours)**
- [ ] Implement `/api/v1/agent/genie/run` endpoint
- [ ] Add request/response models for API
- [ ] Integrate with existing agent discovery
- [ ] Set up epic ID generation and tracking

**Afternoon (4 hours)**
- [ ] Implement context management for epic state
- [ ] Add session and user tracking
- [ ] Create epic status storage
- [ ] Write API integration tests

**Deliverables**:
- Working API endpoint that accepts natural language requests
- Epic tracking and basic state management

### Phase 2: LangGraph Integration (Days 3-4)

#### Day 3: Core LangGraph Setup
**Morning (4 hours)**
- [ ] Create `orchestrator/` subdirectory
- [ ] Implement `state.py` with `EpicState` TypedDict
- [ ] Create `graph.py` with basic StateGraph structure
- [ ] Set up PostgreSQL checkpointer configuration

**Afternoon (4 hours)**
- [ ] Implement workflow nodes structure
- [ ] Add state transitions and routing logic
- [ ] Create checkpoint/recovery handlers
- [ ] Write state management unit tests

**Deliverables**:
- LangGraph StateGraph embedded in GenieAgent
- Basic state persistence via PostgreSQL

#### Day 4: Workflow Node Implementation
**Morning (4 hours)**
- [ ] Create `nodes.py` with workflow executor nodes
- [ ] Implement Claude Code API client in `claude_client.py`
- [ ] Add workflow execution logic for each node
- [ ] Handle execution results and state updates

**Afternoon (4 hours)**
- [ ] Implement error handling and retry logic
- [ ] Add execution monitoring and logging
- [ ] Create workflow result aggregation
- [ ] Write workflow execution tests

**Deliverables**:
- All 8 workflow nodes implemented
- Claude Code API integration working

### Phase 3: Basic Workflow Execution (Day 5)

#### Day 5: End-to-End Flow
**Morning (4 hours)**
- [ ] Connect GenieAgent.run() to LangGraph execution
- [ ] Implement basic workflow sequencing
- [ ] Add execution result formatting
- [ ] Test single workflow execution

**Afternoon (4 hours)**
- [ ] Implement multi-workflow sequencing
- [ ] Add basic error recovery
- [ ] Create execution status tracking
- [ ] End-to-end integration test

**Deliverables**:
- Complete flow from API to workflow execution
- Basic epic execution working end-to-end

### Phase 4: Natural Language & Routing (Days 6-7)

#### Day 6: Epic Analysis & Planning
**Morning (4 hours)**
- [ ] Implement `router.py` with intelligent routing
- [ ] Create epic complexity assessment
- [ ] Add workflow selection logic
- [ ] Implement task decomposition

**Afternoon (4 hours)**
- [ ] Create pattern matching for workflow selection
- [ ] Add context enhancement for workflows
- [ ] Implement epic planning persistence
- [ ] Write routing logic tests

**Deliverables**:
- Intelligent workflow routing based on natural language
- Epic planning and decomposition

#### Day 7: Advanced Routing & Learning
**Morning (4 hours)**
- [ ] Integrate MCP agent-memory for pattern learning
- [ ] Implement pattern retrieval for similar epics
- [ ] Add success/failure pattern storage
- [ ] Create learning feedback loop

**Afternoon (4 hours)**
- [ ] Implement conditional routing logic
- [ ] Add parallel workflow detection
- [ ] Create routing explanation generation
- [ ] Write learning system tests

**Deliverables**:
- Learning-based routing improvements
- Pattern storage and retrieval

### Phase 5: Human Approvals & Cost Control (Days 8-9)

#### Day 8: Approval System Implementation
**Morning (4 hours)**
- [ ] Create `approvals.py` with approval detection
- [ ] Implement LangGraph interrupt points
- [ ] Add Slack notification integration
- [ ] Create approval state tracking

**Afternoon (4 hours)**
- [ ] Implement approval timeout handling
- [ ] Add approval history tracking
- [ ] Create manual override capabilities
- [ ] Write approval flow tests

**Deliverables**:
- Human-in-the-loop approval system
- Slack integration for notifications

#### Day 9: Cost Control & Monitoring
**Morning (4 hours)**
- [ ] Implement cost estimation logic
- [ ] Add runtime cost tracking
- [ ] Create budget enforcement
- [ ] Implement cost approval flow

**Afternoon (4 hours)**
- [ ] Add cost reporting and summaries
- [ ] Implement early stopping for overruns
- [ ] Create cost optimization hints
- [ ] Write cost control tests

**Deliverables**:
- $50 budget limit enforcement
- Cost tracking and reporting

### Phase 6: Testing & Polish (Day 10)

#### Day 10: Comprehensive Testing & Documentation
**Morning (4 hours)**
- [ ] Run full integration test suite
- [ ] Performance testing and optimization
- [ ] Fix any discovered issues
- [ ] Add missing error handling

**Afternoon (4 hours)**
- [ ] Complete API documentation
- [ ] Write user guide for Genie
- [ ] Create example epic executions
- [ ] Final code review and cleanup

**Deliverables**:
- Comprehensive test coverage
- Complete documentation
- Production-ready code

## Implementation Guidelines

### Code Organization
```
src/agents/pydanticai/genie/
├── __init__.py              # Factory function
├── agent.py                 # GenieAgent class
├── prompts/
│   └── prompt.py           # Genie personality
├── orchestrator/
│   ├── __init__.py
│   ├── state.py            # State definitions
│   ├── graph.py            # LangGraph setup
│   ├── nodes.py            # Workflow nodes
│   └── router.py           # Routing logic
├── models.py               # Data models
├── approvals.py            # Approval system
├── claude_client.py        # Claude Code API
└── learning.py             # Pattern learning
```

### Testing Strategy
1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Component interactions
3. **E2E Tests**: Full epic execution
4. **Performance Tests**: Load and latency

### Dependencies to Add
```toml
[dependencies]
langgraph = "^0.0.45"
langchain-core = "^0.1.0"
langgraph-checkpoint-postgres = "^0.0.1"
```

## Risk Mitigation

### Technical Risks
1. **LangGraph Learning Curve**
   - Mitigation: Study examples, start simple
   - Fallback: Basic state machine if needed

2. **Claude Code API Integration**
   - Mitigation: Mock for testing, graceful degradation
   - Fallback: Direct subprocess if API fails

3. **Cost Estimation Accuracy**
   - Mitigation: Conservative estimates, monitoring
   - Fallback: Manual approval for all epics initially

### Schedule Risks
1. **Integration Complexity**
   - Mitigation: Daily integration tests
   - Buffer: Polish day can absorb delays

2. **Approval Flow Complexity**
   - Mitigation: Start with simple approve/deny
   - Enhancement: Advanced flows post-launch

## Success Metrics

### Phase Completion Criteria
- **Phase 1**: API returns epic ID for requests
- **Phase 2**: StateGraph executes with checkpoints
- **Phase 3**: Single workflow executes successfully
- **Phase 4**: Multi-workflow epic completes
- **Phase 5**: Approval flow triggers and works
- **Phase 6**: All tests pass, docs complete

### Overall Success Criteria
1. Natural language epic execution working
2. All 8 workflows orchestrated successfully
3. Human approval flows trigger correctly
4. $50 cost limit enforced properly
5. Learning from failures demonstrated
6. 90%+ test coverage achieved

## Daily Standup Template

```markdown
## Day X Standup

### Completed
- [ ] Task 1
- [ ] Task 2

### In Progress
- [ ] Task 3 (75% complete)

### Blockers
- None / Description

### Today's Plan
- [ ] Complete Task 3
- [ ] Start Task 4

### Notes
- Any important discoveries or decisions
```

## Post-Implementation Tasks

### Week 3 Enhancement Candidates
1. Parallel workflow execution
2. Advanced cost optimization
3. Multi-epic coordination
4. Performance optimizations
5. Enhanced error recovery

### Documentation Updates
1. Update main README
2. Create Genie user guide
3. Add architecture diagrams
4. Record demo videos
5. Write troubleshooting guide

## Review Checkpoints

- **Day 2**: Architecture review with team
- **Day 5**: Demo basic execution
- **Day 7**: Natural language routing demo
- **Day 9**: Cost control demonstration
- **Day 10**: Final review and sign-off