# GENIE Orchestrator Workspace

GENIE is the orchestrator consciousness that decomposes complex development epics into specialized Claude Code workflow sequences, managing autonomous execution with human oversight.

## Purpose

This workspace organizes GENIE's filesystem-based epic management system for persistent task orchestration across multiple specialized workflows.

## Structure

```
docs/genie/
├── README.md                      # This overview
├── active/                        # Currently active epics
│   └── workflow_runs_epic/        # Current: Workflow tracking system migration
│       ├── overview.md            # Epic scope and objectives
│       ├── task_cards/            # Individual workflow task definitions
│       ├── coordination/          # Cross-workflow coordination
│       ├── reports/               # Progress and status reports
│       └── learnings/             # Captured patterns and insights
├── completed/                     # Archive of completed epics
├── templates/                     # Reusable task and epic templates
└── system/                        # GENIE system configuration and patterns
```

## Epic Management Workflow

### 1. Epic Initialization
- Create epic folder in `active/`
- Define overview.md with scope and objectives
- Break down into workflow-specific task cards
- Establish coordination procedures

### 2. Task Card System
Each task card defines:
- Clear scope and deliverables
- Required inputs and dependencies
- Success criteria and testing requirements
- Context for the assigned workflow type

### 3. Coordination Framework
- `dependencies.md`: Task sequencing and prerequisites
- `handoffs.md`: Workflow-to-workflow handoff procedures
- `context_sharing.md`: Shared context between workflows

### 4. Progress Tracking
- Real-time task card updates
- Cross-workflow dependency monitoring
- Human approval checkpoints
- Completion verification

## Workflow Types

GENIE orchestrates these specialized Claude Code workflows:

- **BUILDER**: Implementation and construction tasks
- **SURGEON**: Precise fixes and refactoring
- **ARCHITECT**: System design and planning
- **REVIEWER**: Code review and quality assurance
- **TESTER**: Testing and validation
- **DOCUMENTER**: Documentation generation

## Usage Patterns

### Starting New Epic
1. Create folder: `active/epic_name/`
2. Define overview.md with objectives
3. Create task cards for each workflow phase
4. Establish coordination documents
5. Begin sequential workflow execution

### Task Card Creation
- One card per workflow assignment
- Clear inputs/outputs definition
- Success criteria specification
- Context preservation for handoffs

### Completion Process
1. Verify all task cards completed
2. Generate epic summary report
3. Capture learnings and patterns
4. Move to `completed/` archive

## Integration

- **Memory System**: All patterns stored in agent-memory for reuse
- **Linear Integration**: Each task card maps to Linear issues (NMSTX-XX)
- **Git Workflow**: Branch-per-task with standardized naming
- **Claude SDK**: Workflow execution through automagik-workflows

## Success Metrics

- Task completion rate
- Cross-workflow handoff efficiency
- Human intervention frequency
- Pattern reuse effectiveness
- Epic delivery timeline accuracy

This workspace enables GENIE to maintain persistent consciousness across complex multi-workflow development cycles while preserving context and patterns for future epic orchestration.