# Workflow Routing Template

## Standard Routing Section to Add to Each Workflow

Add this section to each workflow prompt near the end, before the run report:

```markdown
## WORKFLOW ROUTING PROTOCOL

### Completion Requirements
Before routing to next workflow, ensure:
- [ ] Epic folder `docs/development/{epic_id}/` contains all required documents
- [ ] Completion report generated with next workflow recommendation
- [ ] Context handoff document created with detailed guidance
- [ ] Any blocking issues clearly documented and prioritized
- [ ] Success criteria met or escalation path defined

### Routing Decision Logic
**Standard Decision Tree**:
1. **If critical issues found**: Route to FIX workflow with high priority
2. **If implementation needed**: Route to IMPLEMENT workflow
3. **If testing required**: Route to TEST workflow  
4. **If documentation gaps**: Route to DOCUMENT workflow
5. **If code quality issues**: Route to REFACTOR workflow
6. **If review needed**: Route to REVIEW workflow
7. **If ready for PR**: Route to PR workflow
8. **If human approval needed**: Escalate with detailed context

### Final Routing Message Format
**MANDATORY**: Last message must follow this exact pattern:

```
🔄 **WORKFLOW ROUTING**

**From**: {CURRENT_WORKFLOW}
**To**: {NEXT_WORKFLOW}  
**Epic**: {epic_id}
**Priority**: {critical|high|medium|low}
**Status**: {COMPLETED|NEEDS_HUMAN|BLOCKED}

**Message**: {CURRENT_WORKFLOW}→{NEXT_WORKFLOW}: {Brief description of what next workflow should do}. Epic: {epic_id}. {Additional context}

**Epic Folder**: `docs/development/{epic_id}/`
**Key Documents**: 
- {CURRENT_WORKFLOW}_COMPLETION_REPORT.md
- {Additional workflow-specific documents}

**Context for Next Workflow**:
- **Primary Focus**: {What the next workflow should focus on}
- **Success Criteria**: {How to measure success}
- **Constraints**: {Any limitations or requirements}
- **Files Modified**: {List of modified files}

**Blocking Issues**: {None|List of blockers}
**Human Approval Needed**: {None|List of approvals required}
```

### Context Handoff Requirements
Create comprehensive handoff document at:
`docs/development/{epic_id}/{CURRENT_WORKFLOW}_COMPLETION_REPORT.md`

Must include:
- Work completed summary
- Issues discovered and resolved
- Quality metrics and validation results
- Recommendations for next workflow
- Risk assessment and mitigation strategies
- Timeline and budget impact
```

## Workflow-Specific Routing Logic

### ARCHITECT Routing
```python
if breaking_changes_detected:
    next_workflow = "IMPLEMENT"
    priority = "high"
    message = "ARCHITECT→IMPLEMENT: Breaking changes detected. Implement with migration planning."
elif documentation_needed:
    next_workflow = "DOCUMENT"
    priority = "medium"
    message = "ARCHITECT→DOCUMENT: Documentation required before implementation."
else:
    next_workflow = "IMPLEMENT"
    priority = "medium"
    message = "ARCHITECT→IMPLEMENT: Standard implementation following architecture."
```

### IMPLEMENT Routing
```python
if implementation_issues:
    next_workflow = "FIX"
    priority = "high"
    message = "IMPLEMENT→FIX: Implementation issues detected. Fix before testing."
elif refactoring_needed:
    next_workflow = "REFACTOR"
    priority = "medium"
    message = "IMPLEMENT→REFACTOR: Code quality improvements needed."
else:
    next_workflow = "TEST"
    priority = "medium"
    message = "IMPLEMENT→TEST: Implementation complete. Comprehensive testing required."
```

### TEST Routing
```python
if test_failures:
    next_workflow = "FIX"
    priority = "high"
    message = "TEST→FIX: Test failures detected. Fix critical issues."
elif quality_issues:
    next_workflow = "REFACTOR"
    priority = "medium"
    message = "TEST→REFACTOR: Code quality issues found."
else:
    next_workflow = "PR"
    priority = "medium"
    message = "TEST→PR: All tests passing. Ready for pull request."
```

### FIX Routing
```python
if fixes_need_testing:
    next_workflow = "TEST"
    priority = "high"
    message = "FIX→TEST: Fixes applied. Comprehensive testing required."
elif ready_for_pr:
    next_workflow = "PR"
    priority = "medium"
    message = "FIX→PR: Critical fixes applied and validated."
```

### REFACTOR Routing
```python
if refactoring_complete:
    next_workflow = "TEST"
    priority = "medium"
    message = "REFACTOR→TEST: Refactoring complete. Validate no regressions."
```

### REVIEW Routing
```python
if critical_issues:
    next_workflow = "FIX"
    priority = "high"
    message = "REVIEW→FIX: Critical issues identified."
else:
    next_workflow = "PR"
    priority = "medium"
    message = "REVIEW→PR: Review passed. Ready for PR."
```

### DOCUMENT Routing
```python
if documentation_complete:
    next_workflow = "IMPLEMENT"
    priority = "medium"
    message = "DOCUMENT→IMPLEMENT: Documentation complete. Proceed with implementation."
```

### PR Routing
```python
# PR is terminal - completes epic
epic_status = "COMPLETED"
message = "PR→HUMAN: Epic ready for review and merge."
```