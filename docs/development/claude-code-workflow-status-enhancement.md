# Claude Code Workflow Status Endpoint Enhancement Plan

## Current State Analysis

The existing `/api/v1/workflows/claude-code/run/{run_id}/status` endpoint provides basic status information but lacks detailed step-by-step progress tracking and proper final result extraction.

### Current Issues Identified:

1. **Missing Step-by-Step Progress**: No granular visibility into individual workflow steps
2. **Incomplete Final Result**: The `result` field is often `null` even for completed workflows
3. **Limited Progress Context**: Current `progress_indicator` is generic ("Turn 51, 22 tools used")
4. **No Structured Steps**: No way to track completed vs pending workflow phases

## Enhancement Plan

### Phase 1: Enhanced Response Structure for Ongoing Workflows

#### New Response Fields for Running Status:
```json
{
  "run_id": "run_08ac1de6fa8d",
  "status": "running",
  "workflow_steps": {
    "current_step": 3,
    "total_steps": 10,
    "steps": [
      {
        "step_id": 1,
        "name": "Initial Analysis",
        "status": "completed",
        "started_at": "2025-06-13T20:13:49Z",
        "completed_at": "2025-06-13T20:14:12Z",
        "duration_seconds": 23,
        "result": "Analyzed codebase structure",
        "tools_used": ["Read", "Glob", "Grep"],
        "tool_calls": 5,
        "cost": 0.0245
      },
      {
        "step_id": 2,
        "name": "Requirements Gathering",
        "status": "completed",
        "started_at": "2025-06-13T20:14:12Z",
        "completed_at": "2025-06-13T20:14:45Z",
        "duration_seconds": 33,
        "result": "Identified key requirements",
        "tools_used": ["TodoWrite", "Read"],
        "tool_calls": 3,
        "cost": 0.0189
      },
      {
        "step_id": 3,
        "name": "Implementation Phase",
        "status": "in_progress",
        "started_at": "2025-06-13T20:14:45Z",
        "completed_at": null,
        "duration_seconds": 64,
        "result": null,
        "tools_used": ["Edit", "Write"],
        "tool_calls": 8,
        "cost": 0.0321
      }
    ]
  },
  "progress_summary": {
    "completion_percentage": 30,
    "estimated_completion": "2025-06-13T20:18:00Z",
    "current_phase": "Implementation Phase",
    "recent_activity": "Editing configuration files"
  }
}
```

### Phase 2: Enhanced Response Structure for Completed Workflows

#### New Response Fields for Completed Status:
```json
{
  "run_id": "run_08ac1de6fa8d",
  "status": "completed",
  "final_result": "## 🎯 **Workflow Orchestration Complete - Summary Report**\n\n### **📊 Execution Overview**\n- **Total Steps**: 10/10 ✅\n- **Status**: Successfully Completed\n- **Duration**: All steps executed systematically...",
  "workflow_summary": {
    "total_steps_completed": 10,
    "success_rate": 100,
    "major_achievements": [
      "Successfully implemented workflow status endpoint",
      "Added comprehensive progress tracking",
      "Integrated with existing monitoring systems"
    ],
    "files_modified": 5,
    "tests_passed": 12,
    "deployment_ready": true
  },
  "step_by_step_results": [
    {
      "step_id": 1,
      "name": "Initial Analysis",
      "status": "completed",
      "result": "Analyzed codebase structure and identified enhancement opportunities",
      "duration_seconds": 23,
      "success": true
    }
    // ... all 10 steps
  ]
}
```

## Implementation Strategy

### 1. Data Model Enhancements

#### New Models to Add:
```python
class WorkflowStep(BaseModel):
    step_id: int
    name: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    result: Optional[str]
    tools_used: List[str]
    tool_calls: int
    cost: Optional[float]
    error: Optional[str]

class WorkflowSteps(BaseModel):
    current_step: int
    total_steps: int
    steps: List[WorkflowStep]

class ProgressSummary(BaseModel):
    completion_percentage: float
    estimated_completion: Optional[datetime]
    current_phase: str
    recent_activity: str

class WorkflowSummary(BaseModel):
    total_steps_completed: int
    success_rate: float
    major_achievements: List[str]
    files_modified: int
    tests_passed: int
    deployment_ready: bool

class EnhancedClaudeCodeStatusResponse(ClaudeCodeStatusResponse):
    # For running workflows
    workflow_steps: Optional[WorkflowSteps] = None
    progress_summary: Optional[ProgressSummary] = None
    
    # For completed workflows
    final_result: Optional[str] = None
    workflow_summary: Optional[WorkflowSummary] = None
    step_by_step_results: Optional[List[WorkflowStep]] = None
```

### 2. Enhanced Completion Tracking

#### Step Detection Logic:
```python
class EnhancedCompletionTracker(CompletionTracker):
    
    async def _detect_workflow_steps(self, log_entries: List[Dict]) -> List[WorkflowStep]:
        """Extract workflow steps from log entries using pattern matching."""
        steps = []
        
        # Pattern 1: TodoWrite entries indicate step planning
        todo_entries = [e for e in log_entries if e.get("tool_name") == "TodoWrite"]
        
        # Pattern 2: Major tool usage patterns indicate step transitions
        major_transitions = self._detect_step_transitions(log_entries)
        
        # Pattern 3: Claude's own step indicators in responses
        claude_steps = self._extract_claude_step_indicators(log_entries)
        
        return self._merge_step_indicators(todo_entries, major_transitions, claude_steps)
    
    async def _extract_final_result_from_logs(self, log_entries: List[Dict]) -> Optional[str]:
        """Extract the final result from Claude's last substantial response."""
        
        # Look for final summary patterns
        final_patterns = [
            r"## 🎯.*Summary Report",
            r"## .*Complete.*",
            r"## Summary",
            r"## Results",
            r"## Conclusion"
        ]
        
        # Get last few substantial claude responses
        claude_responses = [
            e for e in reversed(log_entries) 
            if e.get("event_type") == "claude_response" 
            and len(e.get("data", {}).get("message", "")) > 200
        ][:5]
        
        for response in claude_responses:
            message = response.get("data", {}).get("message", "")
            for pattern in final_patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return message
        
        # Fallback: return last substantial response
        return claude_responses[0].get("data", {}).get("message") if claude_responses else None
```

### 3. API Route Enhancements

#### Enhanced Status Endpoint:
```python
@router.get("/workflows/claude-code/run/{run_id}/status")
async def get_enhanced_claude_code_run_status(
    run_id: str,
    include_steps: bool = Query(True, description="Include detailed step information"),
    include_logs: bool = Query(False, description="Include execution logs"),
    db: Session = Depends(get_db)
) -> EnhancedClaudeCodeStatusResponse:
    """
    Get enhanced status of a Claude Code workflow run with step-by-step progress.
    """
    
    # ... existing session lookup logic ...
    
    # Enhanced processing based on status
    if metadata.get("run_status") == "running":
        # For running workflows, extract current step progress
        workflow_steps = await enhanced_tracker.get_current_workflow_steps(run_id)
        progress_summary = await enhanced_tracker.calculate_progress_summary(workflow_steps)
        
        return EnhancedClaudeCodeStatusResponse(
            **base_response,
            workflow_steps=workflow_steps,
            progress_summary=progress_summary
        )
    
    elif metadata.get("run_status") == "completed":
        # For completed workflows, extract final results and summary
        final_result = await enhanced_tracker.extract_final_result(run_id)
        workflow_summary = await enhanced_tracker.generate_workflow_summary(run_id)
        step_results = await enhanced_tracker.get_all_step_results(run_id)
        
        return EnhancedClaudeCodeStatusResponse(
            **base_response,
            final_result=final_result,
            workflow_summary=workflow_summary,
            step_by_step_results=step_results
        )
    
    else:
        # For pending/failed, return basic response
        return EnhancedClaudeCodeStatusResponse(**base_response)
```

## Implementation Timeline

### Week 1: Data Model & Core Infrastructure
- [ ] Add new Pydantic models for enhanced responses
- [ ] Extend CompletionTracker with step detection logic
- [ ] Create EnhancedCompletionTracker class
- [ ] Add final result extraction methods

### Week 2: API Endpoint Enhancement
- [ ] Modify existing status endpoint to support enhanced responses
- [ ] Add backward compatibility for existing clients
- [ ] Implement query parameters for response customization
- [ ] Add comprehensive error handling

### Week 3: Step Detection & Progress Tracking
- [ ] Implement TodoWrite-based step detection
- [ ] Add tool usage pattern analysis
- [ ] Create progress estimation algorithms
- [ ] Add recent activity tracking

### Week 4: Final Result Extraction & Testing
- [ ] Implement final result extraction from log patterns
- [ ] Add workflow summary generation
- [ ] Create comprehensive test suite
- [ ] Performance optimization and documentation

## Backward Compatibility

### Approach:
1. **Additive Changes Only**: New fields are optional and don't break existing clients
2. **Query Parameters**: Enhanced features are opt-in via query parameters
3. **Fallback Behavior**: If enhanced processing fails, fall back to current behavior
4. **Version Header**: Optional API version header for future breaking changes

### Migration Strategy:
```python
# Clients can opt-in to enhanced features
GET /api/v1/workflows/claude-code/run/{run_id}/status?include_steps=true
GET /api/v1/workflows/claude-code/run/{run_id}/status?enhanced=true

# Existing clients continue to work unchanged
GET /api/v1/workflows/claude-code/run/{run_id}/status
```

## Testing Strategy

### Unit Tests:
- [ ] Step detection logic with various log patterns
- [ ] Final result extraction from different workflow types
- [ ] Progress calculation accuracy
- [ ] Error handling for malformed logs

### Integration Tests:
- [ ] End-to-end workflow with step tracking
- [ ] Backward compatibility with existing clients
- [ ] Performance under high load
- [ ] Real-time progress update accuracy

### Performance Considerations:
- [ ] Lazy loading of step details
- [ ] Caching of processed step information
- [ ] Efficient log parsing with streaming
- [ ] Memory usage optimization for large workflows

## Success Metrics

### Functional:
- [ ] 100% of workflows show step-by-step progress
- [ ] 95% of completed workflows have meaningful final_result
- [ ] Progress estimation accuracy within 20%
- [ ] Zero breaking changes for existing clients

### Performance:
- [ ] Status endpoint response time < 200ms
- [ ] Memory usage increase < 10%
- [ ] Real-time update latency < 5 seconds
- [ ] Handling 100+ concurrent status requests

This enhancement plan provides comprehensive step-by-step visibility and proper final result extraction while maintaining full backward compatibility with existing clients.