# Workflow Runs Epic Overview

## 🎯 Objective

Migrate from broken legacy workflow tracking to a comprehensive workflow_runs table that captures all Claude SDK execution data, leveraging existing sessions/messages tables for human interventions.

## 🔍 Problem Statement

The current workflow tracking system is broken and incomplete:
- Legacy log_manager system is non-functional
- No comprehensive tracking of Claude SDK workflow execution
- Missing git integration and change tracking
- Broken workspace management (persistent=false default)
- No cost/token tracking
- Human interventions not properly integrated

## 🎯 Solution Overview

Implement a complete workflow_runs table that:
- Captures all Claude SDK execution data
- Integrates with existing sessions/messages for human interventions
- Tracks git operations and code changes
- Fixes workspace management issues
- Provides cost and performance analytics
- Enables comprehensive workflow monitoring

## 📊 Key Benefits

- **Single Source of Truth**: Claude SDK only, no legacy systems
- **Human Intervention**: Leverages existing sessions/messages for interruption/resume
- **Chat UI Ready**: Direct integration with existing message infrastructure
- **Complete Git Tracking**: Commit hashes, diff stats, branch context
- **Workspace Management**: Fixes persistent workspace bugs
- **Performance**: Proper indexing and JSONB flexibility
- **Cost Tracking**: Token usage and API cost estimation
- **Extensible**: Metadata JSONB for future workflow data

## 🗂️ Epic Breakdown

### Phase 1: Database Schema (BUILDER)
- Create comprehensive workflow_runs table
- Add Pydantic models and repository layer
- Set up proper indexing and constraints

### Phase 2: Claude SDK Data Extraction (BUILDER)  
- Create WorkflowRunTracker service
- Hook into SDK workflow lifecycle
- Implement real-time status polling
- Extract all execution metadata

### Phase 3: Git Integration (BUILDER)
- Create git operations service
- Track commit hashes and diff statistics
- Parse git output for detailed change tracking
- Handle edge cases (no commits, etc.)

### Phase 4: Session Integration (BUILDER)
- Link workflows with sessions table
- Leverage message infrastructure for interventions
- Build resume functionality with context
- Create chat UI query functions

### Phase 5: Workspace Management Fix (SURGEON)
- Fix persistent=true default in SDK calls
- Implement workspace cleanup logic
- Track workspace lifecycle properly
- Fix ID assignment and reuse

### Phase 6: Legacy System Cleanup (SURGEON)
- Remove broken log_manager system
- Drop workflow_processes table
- Clean up dead message history code
- Update dependent code references

## 🔗 Technical Architecture

### Database Schema
Complete workflow_runs table with:
- Core identifiers (run_id, workflow_name, agent_type)
- Input/context (task_input, session_id, session_name)
- Git repository context (repo, branch, commit hashes, diff stats)
- Execution status (pending, running, completed, failed, killed)
- Timing/performance (created_at, completed_at, duration)
- Workspace management (workspace_id, persistent flag, cleanup status)
- Cost tracking (tokens, cost estimates)
- Extensible metadata (JSONB fields)

### Data Source Integration
- **Claude SDK**: Run status, timing, tokens, workspace info
- **Git Operations**: Commit tracking, diff statistics, branch context
- **Sessions/Messages**: Human intervention tracking and resume context
- **Environment**: User context, workspace paths, configuration

## 🔄 Human Intervention Flow

Utilizes existing sessions + messages infrastructure:
1. Workflow creates/reuses session
2. Initial message captures task input
3. Human interventions = new messages in same session
4. Resume with message context using Claude SDK
5. No workflow_runs table updates needed for interventions

## 📈 Success Criteria

- [ ] Complete workflow_runs table implementation
- [ ] Full Claude SDK integration and tracking
- [ ] Git operations fully integrated
- [ ] Sessions/messages integration complete
- [ ] Workspace management bugs fixed
- [ ] Legacy systems removed
- [ ] Chat UI queries functional
- [ ] Cost tracking operational
- [ ] Performance monitoring active

## 🎯 Dependencies

- Existing sessions/messages table structure
- Claude SDK automagik-workflows integration
- Git repository context
- User authentication system
- Database migration capabilities

## 📋 Completion Definition

Epic is complete when:
1. All 6 phases successfully implemented
2. Legacy workflow tracking removed
3. New system fully operational
4. Chat UI integration functional
5. All tests passing
6. Documentation updated
7. Performance benchmarks met

This epic establishes the foundation for comprehensive workflow orchestration and monitoring across all GENIE-managed development cycles.