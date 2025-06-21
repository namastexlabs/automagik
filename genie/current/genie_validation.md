# Genie System Validation Architecture

## Overview
End-to-end testing of the Genie orchestration system to validate functionality, identify flaws, and optimize for KISS principles.

## Test Architecture

### 1. Tool Usage Validation
Test that Genie correctly uses all specified tools according to genie.md patterns:
- Memory operations (search before, store after)
- Linear integration (epic creation, no micro-tasks)
- Git operations (branch creation, commits)
- Workflow orchestration (correct parameters)
- Monitoring tools (wait timing, status checking)

### 2. Task Card Lifecycle Test
Verify the complete task card workflow:
```
Create Card → Commit → Workflow Access → Status Updates → Monitoring
```

Key validation points:
- Task cards are created with proper template structure
- Git commit includes genie/ folder for workflow access
- Workflows can read and update task cards
- Status updates are visible in task card checkboxes
- Monitoring correctly detects progress markers

### 3. Monitoring Capabilities
Test real-time progress tracking:
- Workflow status tool usage vs task card reading
- Optimal wait timing strategies
- Progress detection patterns
- Session continuation decisions

### 4. Known Issues Analysis
- **Task Card Merge-Back**: Updated task cards don't automatically merge back to Genie
- **Status Awareness**: Need workflow status tool for real-time updates
- **Verbosity**: Balance between clarity and KISS simplicity
- **Subworkflow Instructions**: Clear read/write expectations for task cards

## Test Scenarios

### Scenario 1: Simple Task Delegation
- Create a basic task card for CLAUDE workflow
- Test research and documentation flow
- Verify task card updates and completion

### Scenario 2: Complex Implementation
- Create BUILDER task card with multiple requirements
- Test implementation workflow with checkboxes
- Monitor progress and handle completion

### Scenario 3: Session Management
- Test session continuation vs fresh start
- Verify worktree persistence
- Validate session naming patterns

### Scenario 4: Error Handling
- Test blocked workflow detection
- Spawn SURGEON for debugging
- Verify error reporting in task cards

## Success Criteria
1. All tool usage patterns match genie.md specifications
2. Task cards enable efficient workflow coordination
3. Monitoring provides accurate progress visibility
4. System maintains KISS simplicity
5. Clear optimization paths identified

## Deliverables
- report.md with comprehensive findings
- Optimization recommendations for subworkflows
- Updated patterns for memory storage
- Refined monitoring strategies