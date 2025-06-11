# NMSTX-258 Subagent Dispatch & Linear Status Architecture

## 🎯 Epic Overview

Design and implement a coordinated subagent dispatch system for evaluating the NMSTX-253 MCP Refactor Epic subtasks and updating Linear task statuses based on current system state.

## 🔍 Current Epic Status Assessment

### NMSTX-253: MCP System Refactor Epic 
**Status**: Todo → **Updated to Todo** (Ready for sequential execution)

#### Component Breakdown:
1. **NMSTX-254** (Core: Database Schema) - Triage → **Updated to In Progress** 
2. **NMSTX-255** (API: Streamlined Endpoints) - Triage → **Updated to In Progress**
3. **NMSTX-256** (Integration: PydanticAI) - Triage → **Updated to Todo** 
4. **NMSTX-257** (Migration: Data Preservation) - Triage → **Updated to Todo**
5. **NMSTX-258** (Testing: Validation Suite) - Triage → **Updated to Todo**

## 🏗️ Subagent Dispatch Architecture

### 1. Multi-Agent Coordination Pattern

Based on existing architectural patterns in memory, we leverage the **"multi-agent coordination patterns"** with sequential execution and checkpoint validation.

#### Core Principles:
- **Sequential Execution**: Components must be completed in dependency order
- **State Checkpoints**: Each component validates prerequisites before starting
- **Failure Recovery**: Rollback capability at each checkpoint
- **Production Safety**: Breaking change detection and human approval

### 2. Dispatch System Design

```
Architect (Orchestrator)
├── Status Evaluator Agent
├── Core Component Agent (NMSTX-254)
├── API Component Agent (NMSTX-255) 
├── Integration Agent (NMSTX-256)
├── Migration Agent (NMSTX-257)
└── Testing Agent (NMSTX-258)
```

#### Dispatch Workflow:
1. **Status Evaluation Phase** - Assess current system state and blockers
2. **Sequential Component Execution** - Execute in dependency order
3. **Checkpoint Validation** - Verify completion criteria before next component
4. **Integration Testing** - Validate end-to-end functionality
5. **Production Readiness** - Final validation and rollback preparation

### 3. Component Execution Strategy

#### Phase 1: Core Foundation (NMSTX-254)
**Agent**: `claude_code:architect`
**Focus**: Database schema migration and models
**Dependencies**: None
**Validation**: New schema created, data backed up

#### Phase 2: API Layer (NMSTX-255) 
**Agent**: `claude_code:implement`
**Focus**: 4 streamlined API endpoints
**Dependencies**: NMSTX-254 completed
**Validation**: API endpoints functional, backward compatibility

#### Phase 3: Integration Layer (NMSTX-256)
**Agent**: `claude_code:implement` 
**Focus**: PydanticAI MCPServer classes
**Dependencies**: NMSTX-254, NMSTX-255 completed
**Validation**: Tool registration working, .mcp.json loading

#### Phase 4: Migration Strategy (NMSTX-257)
**Agent**: `claude_code:architect` + `claude_code:implement`
**Focus**: Data preservation and rollback
**Dependencies**: NMSTX-254, NMSTX-255, NMSTX-256 completed
**Validation**: Zero data loss, rollback tested

#### Phase 5: Testing Validation (NMSTX-258)
**Agent**: `claude_code:test`
**Focus**: Comprehensive test suite
**Dependencies**: All previous components
**Validation**: 95%+ coverage, performance benchmarks

### 4. Coordination Protocol

#### Status Communication:
- **Linear Updates**: Real-time status updates in Linear tasks
- **Memory Storage**: Decisions and progress stored in collective brain
- **Slack Threading**: Epic progress communicated in dedicated thread
- **Human Escalation**: Breaking changes flagged for approval

#### Checkpoint Gates:
```
NMSTX-254 Complete → API Development Gate
NMSTX-255 Complete → Integration Gate  
NMSTX-256 Complete → Migration Gate
NMSTX-257 Complete → Testing Gate
NMSTX-258 Complete → Production Gate
```

## 🔧 Technical Implementation

### 1. Subagent Dispatch Mechanism

```python
class SubagentDispatcher:
    def __init__(self):
        self.agents = {
            'architect': ClaudeCodeAgent('architect'),
            'implement': ClaudeCodeAgent('implement'), 
            'test': ClaudeCodeAgent('test'),
            'review': ClaudeCodeAgent('review')
        }
    
    async def dispatch_epic(self, epic_id: str):
        """Coordinate epic execution across multiple agents"""
        components = await self.get_epic_components(epic_id)
        
        for component in components:
            agent = self.select_agent(component.type)
            result = await agent.execute(component)
            
            if not result.success:
                await self.handle_failure(component, result)
                break
                
            await self.update_checkpoint(component, result)
```

### 2. Status Synchronization System

```python
class LinearStatusSync:
    async def evaluate_component_status(self, component_id: str):
        """Evaluate current state and update Linear accordingly"""
        current_state = await self.assess_implementation_state(component_id)
        linear_state = await self.get_linear_status(component_id)
        
        if current_state != linear_state:
            await self.update_linear_status(component_id, current_state)
            await self.notify_stakeholders(component_id, current_state)
```

### 3. Breaking Change Detection

Based on the **"Production Safety Requirements"** pattern:

```python
class BreakingChangeDetector:
    BREAKING_PATTERNS = {
        'database_schema': ['ALTER TABLE.*DROP', 'DROP TABLE'],
        'api_contracts': ['Remove.*endpoint', 'Change.*response'],
        'configuration': ['Remove.*config', 'Change.*format']
    }
    
    async def scan_for_breaking_changes(self, component):
        """Detect and flag breaking changes for human approval"""
        changes = await self.analyze_changes(component)
        
        for change in changes:
            if self.is_breaking_change(change):
                await self.request_human_approval(change)
```

## 🚨 Production Safety Measures

### 1. Breaking Change Management
- **Automatic Detection**: Scan for schema, API, and config changes
- **Human Approval Required**: All breaking changes need approval
- **Rollback Strategy**: Each component has rollback plan
- **Feature Flags**: Gradual rollout with toggle capability

### 2. Data Preservation Protocol
- **Backup Before Changes**: All data backed up before migration
- **Validation Checks**: Zero data loss verification
- **Integrity Testing**: Configuration count and mapping verification
- **Performance Monitoring**: Regression detection (>20% degradation triggers rollback)

### 3. Testing Requirements
- **95%+ Coverage**: New code must meet coverage threshold
- **Performance Benchmarks**: >50% improvement target
- **Edge Case Validation**: Network failures, invalid configs, agent restarts
- **Production Data Testing**: Migration scripts tested with sample production data

## 📊 Success Metrics

### Component-Level Metrics:
- **NMSTX-254**: Schema migrated, data preserved, rollback tested
- **NMSTX-255**: 4 endpoints functional, <100ms response time, N+1 queries eliminated
- **NMSTX-256**: PydanticAI integration working, hot reload functional
- **NMSTX-257**: Zero data loss, rollback capability verified
- **NMSTX-258**: 95%+ coverage, performance benchmarks met

### Epic-Level Metrics:
- **Code Reduction**: 87% reduction achieved (~300 lines vs 2000+)
- **Performance**: >50% improvement in response times
- **Maintainability**: Single table vs complex junction tables
- **Developer Experience**: Simplified API (4 endpoints vs 15+)

## 🔄 Coordination Timeline

### Week 1: Foundation & Assessment
- Complete status evaluation and Linear updates
- Begin NMSTX-254 (Core) development
- Establish epic thread communication

### Week 2: Core & API Development  
- Complete NMSTX-254 (Core) with checkpoint validation
- Begin NMSTX-255 (API) development
- Continuous integration testing

### Week 3: Integration & Migration
- Complete NMSTX-255 (API) with validation
- Execute NMSTX-256 (Integration) and NMSTX-257 (Migration)
- Human approval for breaking changes

### Week 4: Testing & Production Readiness
- Complete NMSTX-258 (Testing) with comprehensive validation
- Final epic integration testing
- Production deployment preparation

## 🧠 Memory Integration

### Decisions to Store:
- **Architecture Decision**: Subagent dispatch coordination strategy
- **Architecture Decision**: Sequential execution with checkpoint validation
- **Architecture Decision**: Breaking change detection and human approval workflow

### Patterns to Preserve:
- **Pattern**: Multi-component epic coordination
- **Pattern**: Claude Code workflow orchestration
- **Pattern**: Linear status synchronization system

### Learning Opportunities:
- Document coordination challenges and solutions
- Capture effective checkpoint validation strategies
- Record breaking change detection effectiveness

## 🎯 Next Steps

1. **Immediate**: Complete Linear status updates (Done ✅)
2. **Phase 1**: Deploy Status Evaluator Agent for NMSTX-254
3. **Phase 2**: Begin Core component development with architect workflow
4. **Phase 3**: Establish checkpoint validation and testing protocols
5. **Phase 4**: Human approval workflow for breaking changes

## 🔗 Integration Points

### Claude Code Workflow Integration:
- **Architect**: System design and breaking change analysis
- **Implement**: Component development and integration
- **Test**: Comprehensive validation and benchmarking
- **Review**: Code quality and production readiness

### Linear Integration:
- Real-time status updates as work progresses
- Dependency tracking between components
- Progress visibility for stakeholders

### Slack Integration:
- Epic thread for coordination communication
- Human approval requests for breaking changes
- Progress reporting and milestone notifications

---

This architecture provides a comprehensive framework for coordinating the MCP refactor epic through intelligent subagent dispatch, ensuring production safety while maintaining development velocity.