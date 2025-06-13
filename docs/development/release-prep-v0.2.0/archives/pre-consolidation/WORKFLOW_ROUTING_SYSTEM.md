# Genie Collective Workflow Routing System

## Overview

This document defines the enhanced workflow routing system for the Genie collective, ensuring seamless handoffs between workflows with proper epic-based document organization and standardized communication protocols.

## Workflow Routing Protocol

### 1. Workflow Sequence Patterns

#### Standard Epic Flow
```
ARCHITECT → IMPLEMENT → TEST → PR
     ↓         ↓         ↓      ↓
  Design    Code      QA    Merge
```

#### Alternative Flows
```
ARCHITECT → DOCUMENT → IMPLEMENT → TEST → PR
ARCHITECT → IMPLEMENT → FIX → TEST → PR  
ARCHITECT → REFACTOR → TEST → PR
ARCHITECT → REVIEW → FIX → TEST → PR
```

### 2. Handoff Requirements

#### Every Workflow Must Provide
1. **Epic Folder Organization**: `docs/development/{epic_id}/`
2. **Completion Status**: Clear success/failure indication
3. **Next Workflow Recommendation**: Specific routing instruction
4. **Context Handoff**: Detailed information for next workflow
5. **Blocking Issues**: Any issues preventing next workflow

#### Standard Handoff Document Structure
```bash
docs/development/{epic_id}/
├── {WORKFLOW}_COMPLETION_REPORT.md    # Main handoff document
├── {WORKFLOW}_FINDINGS.md             # Detailed findings
├── {WORKFLOW}_CONTEXT.md              # Context for next workflow
└── WORKFLOW_ROUTING.md                # Routing instructions
```

## Workflow-Specific Routing Specifications

### ARCHITECT → Next Workflow
**Output Documents**:
- `ARCHITECTURE.md` - System design
- `TECHNICAL_DECISIONS.md` - Decision records
- `IMPLEMENTATION_ROADMAP.md` - Implementation plan
- `ARCHITECT_COMPLETION_REPORT.md` - Handoff summary

**Routing Logic**:
```python
if breaking_changes_detected:
    next_workflow = "IMPLEMENT"
    priority = "high"
    message = f"ARCHITECT→IMPLEMENT: Breaking changes detected. Implement with careful migration planning. Epic: {epic_id}"
elif documentation_heavy:
    next_workflow = "DOCUMENT" 
    priority = "medium"
    message = f"ARCHITECT→DOCUMENT: Documentation-heavy epic. Create comprehensive docs before implementation. Epic: {epic_id}"
else:
    next_workflow = "IMPLEMENT"
    priority = "medium" 
    message = f"ARCHITECT→IMPLEMENT: Standard implementation required. Follow architecture specifications. Epic: {epic_id}"
```

### IMPLEMENT → Next Workflow  
**Output Documents**:
- `IMPLEMENTATION_REPORT.md` - Implementation summary
- `CODE_CHANGES.md` - Detailed code changes
- `INTEGRATION_NOTES.md` - Integration points

**Routing Logic**:
```python
if implementation_issues_found:
    next_workflow = "FIX"
    priority = "high"
    message = f"IMPLEMENT→FIX: Implementation issues detected. Fix before testing. Epic: {epic_id}. Issues: {issue_list}"
elif major_refactoring_needed:
    next_workflow = "REFACTOR"
    priority = "medium"
    message = f"IMPLEMENT→REFACTOR: Code quality improvements needed. Refactor then test. Epic: {epic_id}"
else:
    next_workflow = "TEST"
    priority = "medium"
    message = f"IMPLEMENT→TEST: Implementation complete. Comprehensive testing required. Epic: {epic_id}"
```

### TEST → Next Workflow
**Output Documents**:
- `TEST_REPORT.md` - Test execution summary
- `QUALITY_METRICS.md` - Coverage and quality data
- `TEST_FINDINGS.md` - Issues discovered

**Routing Logic**:
```python
if test_failures_found:
    next_workflow = "FIX" 
    priority = "high"
    message = f"TEST→FIX: Test failures detected. Fix critical issues. Epic: {epic_id}. Failures: {failure_count}"
elif code_quality_issues:
    next_workflow = "REFACTOR"
    priority = "medium"
    message = f"TEST→REFACTOR: Code quality issues found. Refactor for maintainability. Epic: {epic_id}"
elif all_tests_pass:
    next_workflow = "PR"
    priority = "medium"
    message = f"TEST→PR: All tests passing. Ready for pull request preparation. Epic: {epic_id}"
```

### FIX → Next Workflow
**Output Documents**:
- `FIX_REPORT.md` - Fix summary and root cause analysis
- `REGRESSION_PREVENTION.md` - Prevention measures

**Routing Logic**:
```python
if fixes_complete and tests_needed:
    next_workflow = "TEST"
    priority = "high"
    message = f"FIX→TEST: Fixes applied. Comprehensive testing required to validate. Epic: {epic_id}"
elif fixes_complete and ready_for_pr:
    next_workflow = "PR"
    priority = "medium"
    message = f"FIX→PR: Critical fixes applied and validated. Ready for PR. Epic: {epic_id}"
```

### REFACTOR → Next Workflow
**Output Documents**:
- `REFACTOR_REPORT.md` - Refactoring summary
- `CODE_QUALITY_IMPROVEMENTS.md` - Quality metrics

**Routing Logic**:
```python
if refactoring_complete:
    next_workflow = "TEST"
    priority = "medium"
    message = f"REFACTOR→TEST: Refactoring complete. Validate no regressions introduced. Epic: {epic_id}"
```

### REVIEW → Next Workflow
**Output Documents**:
- `REVIEW_FINDINGS.md` - Review results
- `QUALITY_ASSESSMENT.md` - Quality metrics

**Routing Logic**:
```python
if critical_issues_found:
    next_workflow = "FIX"
    priority = "high"
    message = f"REVIEW→FIX: Critical issues identified. Address before proceeding. Epic: {epic_id}"
elif review_passed:
    next_workflow = "PR"
    priority = "medium"  
    message = f"REVIEW→PR: Review passed. Ready for pull request. Epic: {epic_id}"
```

### DOCUMENT → Next Workflow
**Output Documents**:
- `DOCUMENTATION_REPORT.md` - Documentation summary
- `USER_GUIDES.md` - User documentation
- `API_DOCUMENTATION.md` - API docs

**Routing Logic**:
```python
if documentation_complete:
    next_workflow = "IMPLEMENT"
    priority = "medium"
    message = f"DOCUMENT→IMPLEMENT: Documentation complete. Proceed with implementation. Epic: {epic_id}"
```

### PR → Epic Completion
**Output Documents**:
- `PR_COMPLETION_REPORT.md` - Final epic summary
- `DEPLOYMENT_NOTES.md` - Deployment instructions
- `ROLLBACK_PLAN.md` - Emergency procedures

**Routing Logic**:
```python
# PR is terminal workflow - completes epic
epic_status = "COMPLETED"
message = f"PR→HUMAN: Epic {epic_id} ready for review and merge. PR #{pr_number} created."
```

## Standardized Routing Messages

### Message Format
```
{SOURCE_WORKFLOW}→{TARGET_WORKFLOW}: {BRIEF_DESCRIPTION}. Epic: {epic_id}. {ADDITIONAL_CONTEXT}
```

### Priority Levels
- **critical**: Blocking issues, immediate attention required
- **high**: Important issues, handle within hours
- **medium**: Standard workflow progression
- **low**: Optimization or enhancement opportunities

### Context Handoff Template
```markdown
## Workflow Handoff Context

**From**: {SOURCE_WORKFLOW}  
**To**: {TARGET_WORKFLOW}  
**Epic**: {epic_id}  
**Priority**: {priority}  
**Status**: {status}

### Work Completed
- {achievement_1}
- {achievement_2}
- {achievement_3}

### Context for Next Workflow
- **Primary Focus**: {main_focus}
- **Key Requirements**: {requirements}
- **Success Criteria**: {success_criteria}
- **Constraints**: {constraints}

### Files Modified
- {file_1}: {description}
- {file_2}: {description}

### Epic Folder Contents
- `docs/development/{epic_id}/{WORKFLOW}_COMPLETION_REPORT.md`
- `docs/development/{epic_id}/{WORKFLOW}_FINDINGS.md`  
- Additional documents: {additional_docs}

### Issues/Blockers
- {issue_1}: {severity} - {description}
- {issue_2}: {severity} - {description}

### Next Steps
1. {step_1}
2. {step_2}
3. {step_3}

### Quality Metrics
- **Success Rate**: {success_percentage}%
- **Issues Found**: {issue_count}
- **Time Spent**: {duration}
- **Cost**: ${cost}
```

## Routing Decision Logic

### Automatic Routing Rules
1. **Architecture Complete** → IMPLEMENT (standard path)
2. **Implementation Issues** → FIX (error handling)
3. **Test Failures** → FIX (quality gate)
4. **All Tests Pass** → PR (success path)
5. **Breaking Changes** → Higher priority routing
6. **Security Issues** → Immediate escalation

### Human Escalation Triggers
- Multiple workflow failures in sequence
- Budget overruns (>$150 per epic)
- Breaking changes requiring approval
- Security vulnerabilities detected
- Timeline delays > 50%

## Implementation in Workflow Prompts

### Required Additions to Each Workflow
```markdown
## WORKFLOW ROUTING PROTOCOL

### Completion Requirements
Before routing to next workflow, ensure:
- [ ] Epic folder `docs/development/{epic_id}/` contains all required documents
- [ ] Completion report generated with next workflow recommendation
- [ ] Context handoff document created
- [ ] Any blocking issues documented

### Routing Message Format
**Final message must follow this pattern**:
```
ROUTING: {SOURCE}→{TARGET}: {DESCRIPTION}. Epic: {epic_id}. {CONTEXT}

Epic Folder: docs/development/{epic_id}/
Status: {COMPLETED|BLOCKED|NEEDS_HUMAN}
Priority: {critical|high|medium|low}
Next Workflow: {WORKFLOW_NAME}
```

### Standard Routing Decision Tree
[Include workflow-specific decision logic]
```

## Quality Assurance

### Routing Validation
- Epic folder structure compliance
- Document completeness check
- Context handoff quality assessment
- Message format validation

### Success Metrics
- **Routing Accuracy**: 95%+ correct next workflow selection
- **Context Preservation**: 100% essential context transferred
- **Document Organization**: 100% compliance with epic folder structure
- **Handoff Quality**: Clear, actionable guidance for next workflow

This routing system ensures seamless workflow transitions while maintaining epic-based organization and comprehensive context preservation.