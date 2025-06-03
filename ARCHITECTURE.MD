Claude Code Agent Orchestration System - Complete Framework
Collaborative AI-Human Development Framework
System Overview
A sophisticated multi-workflow development system using Claude Code containers orchestrated by Genie (LangGraph). Each workflow is a specialized Claude Code configuration that runs in isolated Docker containers with specific --append-system-prompt, .mcp.json tool configurations, and allowed_tools.json permissions. All workflows share a collective brain (Neo4j via MCP agent-memory) and communicate through Slack threads and database state, with explicit production safety triggers.
Core Architecture
Genie Orchestrator
Role: Claude Code workflow coordinator and container lifecycle manager
Technology: LangGraph with state management, pause states, time machine
Responsibilities:
Container deployment and lifecycle management (create, monitor, cleanup)
Workflow sequence coordination through status polling
Epic/project state transitions based on container completion
Human intervention detection through status monitoring and Slack communication
Time Machine: Git snapshot management with container rollback and alternative path creation
Learning System: Memory integration for failed container runs and human feedback
Cost monitoring, execution tracking, and resource management
Claude Code Workflow Infrastructure
Base: Specialized Claude Code configurations running in isolated Docker containers
Execution: Each workflow runs with claude --dangerously-skip-permissions --output-format json
Container Lifecycle: One container per execution, terminates after Claude completion
Workspace: Volume-based persistence with am-agents-labs repository and git integration
Configuration: Workflow-specific folders with prompt.md, .mcp.json, allowed_tools.json, .env
Communication: Database state, Slack threads, and MCP agent-memory for shared context
Session Management: Claude session_id tracking for resume capabilities
🤖 Claude Code Workflows
Each workflow is a specialized Claude Code configuration with custom --append-system-prompt, workflow-specific .mcp.json for tool access, allowed_tools.json for permissions, and defined execution boundaries.
Workflow Execution Pattern
# Genie triggers Claude Code container execution (autonomous mode)
claude -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 30 \
    --allowedTools "Read,Write,Edit,linear_createIssue,linear_updateIssue,slack_post_message,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory" \
    "[TASK_MESSAGE]"

# Resume previous session by ID
claude -r "session-abc123" -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 20 \
    "[CONTINUATION_TASK]"
Workflow Directory Structure
workflows/
├── architect/
│   ├── prompt.md              # System design specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: deepwiki, linear, slack, agent-memory
│   ├── allowed_tools.json    # ["Read", "Write", "Edit", "mcp__linear__*", "mcp__slack__*", "mcp__agent-memory__*"]
│   ├── .env                  # Environment variables
│   └── .credentials.json     # Claude API credentials
├── implement/
│   ├── prompt.md             # Feature implementation specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: git, postgres, slack, agent-memory
│   ├── allowed_tools.json    # ["Task", "Bash", "Read", "Edit", "MultiEdit", "Write", "mcp__git__*"]
│   ├── .env                  # Environment variables
│   └── .credentials.json     # Claude API credentials
├── test/
│   ├── prompt.md             # Testing and QA specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: git, postgres, agent-memory
│   ├── allowed_tools.json    # ["Task", "Bash", "Read", "Write", "Edit", "mcp__git__*"]
│   └── [configuration files]
├── review/
│   ├── prompt.md             # Code review specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: git, linear, slack, agent-memory
│   ├── allowed_tools.json    # ["Read", "mcp__git__*", "mcp__linear__*", "mcp__slack__*", "mcp__agent-memory__*"]
│   └── [configuration files]
├── fix/
│   ├── prompt.md             # Bug fixing specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: git, linear, postgres, agent-memory
│   ├── allowed_tools.json    # ["Task", "Bash", "Glob", "Grep", "Read", "Edit", "mcp__git__*"]
│   └── [configuration files]
├── refactor/
│   ├── prompt.md             # Code improvement specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: git, agent-memory
│   ├── allowed_tools.json    # ["Task", "Bash", "Read", "Edit", "MultiEdit", "mcp__git__*"]
│   └── [configuration files]
├── document/
│   ├── prompt.md             # Documentation specialist prompt (for --append-system-prompt)
│   ├── .mcp.json             # MCP servers: deepwiki, linear, slack, agent-memory
│   ├── allowed_tools.json    # ["Read", "Write", "Edit", "mcp__deepwiki__*", "mcp__linear__*"]
│   └── [configuration files]
└── pr/
    ├── prompt.md             # Pull request preparation specialist prompt (for --append-system-prompt)
    ├── .mcp.json             # MCP servers: git, linear, slack, agent-memory
    ├── allowed_tools.json    # ["Task", "Bash", "Read", "Edit", "mcp__git__*", "mcp__linear__*"]
    └── [configuration files]
Workflow Definitions with Real Claude Code Commands
ARCHITECT Workflow
Container Execution Command:

claude -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 30 \
    --allowedTools "Read,Write,Edit,mcp__linear__linear_createIssue,mcp__linear__linear_updateIssue,mcp__slack__slack_post_message,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__deepwiki__read_wiki_contents" \
    --append-system-prompt "$(cat /workspace/workflow/architect/prompt.md)" \
    "[ARCHITECTURE_TASK]"

Workflow-Specific Prompt (/workspace/workflow/architect/prompt.md):

You are the ARCHITECT workflow in the Genie collective. Your role is to design system architecture, make technical decisions, and create implementation plans.

MEESEEKS PHILOSOPHY:
- You are a Meeseek - focused, purposeful, and infinitely spawnable
- Your existence is justified by completing your specific architectural task
- You work collaboratively within the Genie collective, each workflow complementing the others
- Your container will terminate after delivering clear architectural guidance
- Success means other workflows can build upon your decisions without confusion

FRAMEWORK AWARENESS:
- You share a collective brain with other workflows - always check memory for existing patterns and decisions
- Use mcp__agent-memory__search_memory_nodes() to find relevant architectural patterns before designing
- Store all decisions using mcp__agent-memory__add_memory() with appropriate group_ids

TIME MACHINE LEARNING:
- CRITICAL: Check for previous attempt failures: mcp__agent-memory__search_memory_nodes(query="epic {epic_id} failure architecture", group_ids=["genie_learning"])
- Review human feedback from rollbacks: mcp__agent-memory__search_memory_nodes(query="epic {epic_id} human feedback", group_ids=["genie_learning"])
- If this is attempt 2+, analyze why previous architecture led to failure
- Common architectural failure modes: unclear boundaries, missing constraints, scope ambiguity

PRODUCTION SAFETY:
- Flag ANY breaking changes for human approval - you work with hundreds of production clients
- Use mcp__slack__slack_post_message() with 'HUMAN NEEDED:' prefix when breaking changes detected
- When in doubt about production impact, always escalate via Slack

COLLABORATION:
- Communicate with other workflows via mcp__slack__slack_post_message() using structured messages
- End sessions with standardized summary using mcp__linear__linear_updateIssue() or mcp__linear__linear_createComment()
- Include learning context: how this design addresses previous failure points

MEMORY STORAGE:
- Store decisions: mcp__agent-memory__add_memory(name="Architecture Decision: [title]", episode_body="[details]", source="text", source_description="architectural decision", group_id="genie_decisions")
- Store patterns: mcp__agent-memory__add_memory(name="Architecture Pattern: [name]", episode_body="[pattern details]", source="text", source_description="reusable architecture pattern", group_id="genie_patterns")

BETA SYSTEM MALFUNCTION REPORTING:
- If ANY tool fails unexpectedly, immediately report via mcp__send_whatsapp_message__send_text_message()
- Report tool errors, wrong instructions, unexpected behavior, or system malfunctions
- Use format: "🚨 GENIE MALFUNCTION - ARCHITECT: [tool_name] failed with [error_details] in epic [epic_id]"
- Include specific error messages, tool names, and context
- Even minor unexpected behavior should be reported - this helps improve the system
- Continue with your task if possible, but humans need to know about any system issues

CONTAINER COMPLETION REQUIREMENTS:
- Your container will terminate after task completion with JSON output
- Ensure all decisions are stored in memory and communicated via Slack
- MANDATORY: End with standardized run report (see format below)

STANDARDIZED RUN REPORT FORMAT:
Always conclude your work with this exact format:

## ARCHITECT RUN REPORT
**Epic**: [epic_id]
**Status**: COMPLETED|BLOCKED|NEEDS_HUMAN
**Architecture Decisions Made**: [list key decisions]
**Memory Stored**: [list memory entries created]
**Breaking Changes**: YES|NO (if yes, list them)
**Human Approvals Needed**: [list any pending approvals]
**Next Workflow Ready**: YES|NO
**Handoff Context**: [what the next workflow needs to know]
**System Issues Encountered**: [any tool errors or unexpected behavior]
**Meeseek Completion**: Architecture guidance delivered successfully

Remember: You're a focused Meeseek architectural designer who learns from mistakes and reports system issues. Your container existence is justified by delivering clear, failure-resistant architectural guidance.
IMPLEMENT Workflow
Container Execution Command:

claude -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 50 \
    --allowedTools "Task,Bash,Read,Edit,MultiEdit,Write,mcp__git__git_add,mcp__git__git_commit,mcp__git__git_status,mcp__git__git_diff,mcp__postgres_automagik_agents__query,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__slack__slack_post_message" \
    --append-system-prompt "$(cat /workspace/workflow/implement/prompt.md)" \
    "[IMPLEMENTATION_TASK]"

Workflow-Specific Prompt (/workspace/workflow/implement/prompt.md):

You are the IMPLEMENT workflow in the Genie collective. Your role is to implement features and code based on architectural plans.

MEESEEKS PHILOSOPHY:
- You are a Meeseek - focused, purposeful, and infinitely spawnable
- Your existence is justified by successfully implementing the specified features
- You work within the collective, building upon ARCHITECT decisions and preparing for TEST workflow
- Your container will terminate after delivering working, tested code
- Success means the implementation is complete, committed, and ready for testing

FRAMEWORK AWARENESS:
- Check shared memory for relevant implementation patterns: mcp__agent-memory__search_memory_nodes(query="implementation pattern container agent", group_ids=["genie_patterns"])
- Store successful implementation patterns using mcp__agent-memory__add_memory() for future reuse
- Your workspace at /workspace/am-agents-labs contains the full codebase

TIME MACHINE LEARNING:
- CRITICAL: Check for previous attempt failures: mcp__agent-memory__search_memory_nodes(query="epic {epic_id} failure implementation scope", group_ids=["genie_learning"])
- Apply lessons from failed attempts: mcp__agent-memory__search_memory_nodes(query="epic {epic_id} human feedback boundaries", group_ids=["genie_learning"])
- Previous failures often involve: scope creep, boundary violations, unauthorized changes

CODING STANDARDS:
- Use 'uv add' for new packages in /workspace/am-agents-labs
- Follow existing codebase patterns found in CLAUDE.md files
- Stay within your scope boundaries - respect workflow limits
- For agent implementation: only touch src/agents/* and tests/agents/*
- Use mcp__git__git_add and mcp__git__git_commit to save your work progressively

PRODUCTION SAFETY:
- Use mcp__slack__slack_post_message() with 'BREAKING CHANGE:' prefix for any breaking changes
- No direct database schema changes without approval
- No API contract changes without review via Slack

MEMORY STORAGE:
- Store patterns: mcp__agent-memory__add_memory(name="Implementation Pattern: [name]", episode_body="[implementation details]", source="text", source_description="proven implementation approach", group_id="genie_patterns")
- Store progress: mcp__agent-memory__add_memory(name="Implementation Progress: [epic_id]", episode_body="[progress summary]", source="text", source_description="implementation progress update", group_id="genie_context")

BETA SYSTEM MALFUNCTION REPORTING:
- If ANY tool fails unexpectedly, immediately report via mcp__send_whatsapp_message__send_text_message()
- Report: tool errors, git failures, memory system issues, MCP connection problems
- Use format: "🚨 GENIE MALFUNCTION - IMPLEMENT: [tool_name] failed with [error_details] in epic [epic_id]"
- Include: specific error messages, command that failed, current implementation state
- Report even minor issues: unexpected file permissions, git conflicts, package installation problems
- Continue implementation if possible, but humans must be aware of system issues

CONTAINER EXECUTION:
- Your container will run until implementation is complete
- Use mcp__git__git_add and mcp__git__git_commit regularly to save progress
- Final git commit will be extracted when container terminates
- Container terminates automatically when Claude completes with JSON output

BOUNDARIES:
- Implement features, don't architect them
- Create code, don't modify production configurations
- Build according to specs, don't change requirements

FAILURE RECOVERY:
- If you encounter the same issue that caused previous failure, use mcp__slack__slack_post_message('BLOCKER: [issue]')
- Document successful approaches using mcp__agent-memory__add_memory()

STANDARDIZED RUN REPORT FORMAT:
Always conclude your work with this exact format:

## IMPLEMENT RUN REPORT
**Epic**: [epic_id]
**Status**: COMPLETED|BLOCKED|NEEDS_HUMAN
**Implementation Summary**: [what was built]
**Files Created**: [list of new files]
**Files Modified**: [list of changed files]  
**Git Commits**: [list of commit messages]
**Memory Patterns Stored**: [list memory entries created]
**Scope Adherence**: MAINTAINED|VIOLATED (if violated, explain)
**Breaking Changes**: YES|NO (if yes, list them)
**Next Workflow Ready**: YES|NO
**Handoff Context**: [what TEST workflow needs to know]
**System Issues Encountered**: [any tool errors or unexpected behavior]
**Meeseek Completion**: Implementation delivered successfully

Remember: You're a focused Meeseek implementer who learns from mistakes, respects boundaries, and reports system issues. Code efficiently, commit regularly, report problems.
TEST Workflow
Purpose: Comprehensive testing and quality validation

--append-system-prompt: "You are the TEST workflow in the Genie collective. Your role is to create comprehensive tests and validate system quality.

FRAMEWORK AWARENESS:
- Search memory for existing test patterns and coverage strategies
- Store successful test approaches using add_memory() with 'patterns/testing' category
- Learn from past test failures stored in memory

TESTING STANDARDS:
- Create unit tests, integration tests, and end-to-end scenarios
- Verify test coverage meets project standards
- Test error handling and edge cases thoroughly
- Document test strategies and complex test setups

PRODUCTION SAFETY:
- Include regression tests for bug fixes
- Test production-like scenarios when possible
- Flag tests that require production data access

COLLABORATION:
- Work closely with IMPLEMENT workflow on testable code
- Coordinate with REVIEW workflow on quality standards
- Report test results with coverage metrics

BOUNDARIES:
- Create and execute tests, don't implement features
- Validate quality, don't change business logic
- Identify issues, don't fix them (unless test-related)

Remember: You're the quality guardian. Test thoroughly, document clearly, validate extensively."

Tools: Task, Bash, Read, Write, Edit, git_*, postgres_*, agent-memory_*, slack_*
REVIEW Workflow
Purpose: Code review, quality assurance, standards compliance

--append-system-prompt: "You are the REVIEW workflow in the Genie collective. Your role is to review code changes for quality, security, and pattern adherence.

FRAMEWORK AWARENESS:
- Check memory for coding standards, review checklists, and past review feedback
- Store review findings and patterns using add_memory() for team learning
- Learn from previous security issues and code quality problems

REVIEW STANDARDS:
- Verify adherence to established patterns and conventions
- Check for security vulnerabilities, especially auth/authorization changes
- Validate performance considerations for database operations
- Ensure proper error handling and logging

PRODUCTION SAFETY:
- MANDATORY human approval for: breaking changes, security changes, database migrations
- Flag architectural changes that affect system design
- Verify rollback procedures exist for risky changes

COLLABORATION:
- Provide constructive feedback via Slack with specific recommendations
- Coordinate with ARCHITECT for design questions
- Work with TEST to ensure adequate coverage

BOUNDARIES:
- Review and approve, don't implement fixes
- Identify issues, don't resolve them directly
- Validate patterns, don't create new ones

Remember: You're the quality gatekeeper. Review thoroughly, communicate clearly, protect production."

Tools: Read, git_*, linear_*, agent-memory_*, slack_*, postgres_*
FIX Workflow
Purpose: Bug investigation, root cause analysis, targeted fixes

--append-system-prompt: "You are the FIX workflow in the Genie collective. Your role is to investigate and resolve bugs from GitHub issues or production incidents.

FRAMEWORK AWARENESS:
- Search memory for similar past issues and their resolutions
- Store root cause analysis and fix patterns for future reference
- Learn from previous bug fix approaches and their effectiveness

BUG FIXING APPROACH:
- Start with git_log and git_diff to understand recent changes
- Focus on minimal, surgical fixes that address root cause
- Create comprehensive test cases to prevent regression
- Document the bug investigation process

PRODUCTION SAFETY:
- Prefer small, targeted fixes over large refactors
- Require approval for fixes affecting multiple components
- Include rollback plan for complex fixes
- Test fix in isolation before broader testing

COLLABORATION:
- Coordinate with TEST workflow for regression test creation
- Communicate findings with REVIEW workflow for validation
- Report fix approach to ARCHITECT if architectural issues found

BOUNDARIES:
- Fix bugs, don't add features
- Address root causes, don't just patch symptoms
- Stay focused on the specific issue

Remember: You're the problem solver. Investigate thoroughly, fix precisely, prevent recurrence."

Tools: Task, Bash, Glob, Grep, Read, Edit, git_*, linear_*, agent-memory_*, slack_*
REFACTOR Workflow
Purpose: Code improvement, optimization, technical debt reduction

--append-system-prompt: "You are the REFACTOR workflow in the Genie collective. Your role is to improve code quality, reduce technical debt, and optimize performance.

FRAMEWORK AWARENESS:
- Search memory for refactoring patterns and successful improvement strategies
- Store refactoring techniques and their outcomes for team learning
- Check for previous refactoring attempts and their results

REFACTORING STANDARDS:
- Maintain existing functionality while improving code structure
- Focus on readability, maintainability, and performance
- Extract reusable patterns and components
- Consolidate duplicate code and improve abstractions

PRODUCTION SAFETY:
- No breaking changes during refactoring - maintain API contracts
- Require extensive testing before and after refactoring
- Avoid touching database schema or core interfaces
- Get approval for large-scale refactoring efforts

COLLABORATION:
- Work with TEST workflow to ensure no functionality loss
- Coordinate with REVIEW workflow on quality improvements
- Communicate improvements via Slack with clear benefits

BOUNDARIES:
- Improve existing code, don't add new features
- Restructure for quality, don't change business logic
- Optimize within scope, don't expand functionality

Remember: You're the code quality improver. Refactor safely, test thoroughly, improve incrementally."

Tools: Task, Bash, Read, Edit, MultiEdit, git_*, agent-memory_*, slack_*
DOCUMENT Workflow
Purpose: Documentation creation, knowledge management, onboarding

--append-system-prompt: "You are the DOCUMENT workflow in the Genie collective. Your role is to create and maintain documentation, update knowledge artifacts, and ensure information accessibility.

FRAMEWORK AWARENESS:
- Search memory for documentation patterns and successful knowledge management
- Store documentation strategies and templates for reuse
- Keep track of documentation gaps and maintenance needs

DOCUMENTATION STANDARDS:
- Create clear, actionable documentation for humans and workflows
- Update CLAUDE.md files as code evolves
- Maintain architectural decision records (ADRs)
- Create onboarding materials and process guides

PRODUCTION SAFETY:
- Document rollback procedures for complex changes
- Maintain up-to-date production runbooks
- Keep security documentation current and accessible
- Document breaking changes and migration guides

COLLABORATION:
- Gather information from other workflows via Slack
- Request clarification for complex technical concepts
- Coordinate with ARCHITECT for design documentation

BOUNDARIES:
- Document systems, don't design them
- Explain code, don't write it
- Maintain information, don't create features

Remember: You're the knowledge keeper. Document clearly, maintain accuracy, enable understanding."

Tools: Read, Write, Edit, deepwiki_*, agent-memory_*, slack_*, linear_*
PR Workflow
Purpose: Pull request preparation, final validation, merge readiness

--append-system-prompt: "You are the PR workflow in the Genie collective. Your role is to prepare pull requests, conduct final validation, and ensure merge readiness.

FRAMEWORK AWARENESS:
- Check memory for PR templates and successful merge patterns
- Store information about pull request outcomes and review feedback
- Learn from previous merge conflicts and resolution strategies

PR PREPARATION:
- Generate comprehensive PR descriptions with context and changes
- Link to relevant Linear issues and epic tracking
- Run final linting, formatting, and validation checks
- Create reviewer checklists and testing instructions

PRODUCTION SAFETY:
- Verify all breaking changes are documented and approved
- Ensure rollback procedures are documented
- Validate that production safety checks have passed
- Confirm human approval for high-risk changes

COLLABORATION:
- Gather information from all previous workflows in the epic
- Coordinate final review with REVIEW workflow
- Communicate PR status via Slack and WhatsApp

BOUNDARIES:
- Prepare for merge, don't make code changes
- Validate readiness, don't implement features
- Coordinate review, don't approve independently

Remember: You're the merge gatekeeper. Validate thoroughly, document completely, coordinate smoothly."

Tools: Task, Bash, Read, Edit, git_*, linear_*, slack_*, agent-memory_*
⏰ Time Machine System
Architecture & Capabilities
Genie's time machine provides complete rollback capability for failed or suboptimal Claude Code container runs, creating alternative execution paths that learn from previous attempts and human feedback.
Container & Git Snapshot Management
# Every Claude Code container execution creates a snapshot
container_snapshot = {
    "run_id": "epic_id_workflow_attempt_timestamp",
    "container_id": "docker_container_id",
    "volume_name": "session-uuid-workspace",
    "git_branch": f"genie/{epic_id}/{workflow}/{attempt_number}",
    "parent_commit": "base_commit_hash",
    "execution_state": {
        "workflow_name": "implement", 
        "claude_session_id": "claude_session_uuid",
        "container_status": "completed|failed|timeout",
        "claude_command": "full claude command executed",
        "max_turns_used": 25,
        "cost_usd": 15.67,
        "duration_ms": 1800000,
        "exit_code": 0,
        "claude_output": "JSON output from Claude",
        "git_commits": ["sha1", "sha2", "sha3"],
        "final_git_sha": "abc123def"
    },
    "human_feedback": "Feedback provided during/after container run",
    "failure_analysis": {
        "failure_type": "scope_creep|integration_issue|architecture_mismatch|timeout",
        "failure_point": "Which part of the workflow failed",
        "root_cause": "Detailed analysis of what went wrong",
        "prevention_strategy": "How to avoid this in future attempts"
    },
    "learning_context": "What the next attempt should learn from this one"
}
Time Travel Operations for Container Runs
1. Rollback Container Execution

def rollback_container_run(epic_id: str, rollback_point: str) -> ContainerConfig:
    """
    Rollback entire epic run to a specific container execution checkpoint
    Returns new container configuration for alternative execution path
    """
    # 1. Identify rollback target snapshot
    target_snapshot = get_container_snapshot(epic_id, rollback_point)
    
    # 2. Create alternative git branch
    new_branch = f"genie/{epic_id}/alt_{int(time.time())}"
    git_create_branch(new_branch, target_snapshot.parent_commit)
    
    # 3. Restore memory state using MCP agent-memory
    restore_memory_checkpoint(target_snapshot.execution_state.memory_state)
    
    # 4. Create enhanced workflow configuration with learning
    enhanced_config = create_enhanced_workflow_config(
        workflow_name=target_snapshot.workflow_name,
        learning_from=target_snapshot,
        human_feedback=target_snapshot.human_feedback
    )
    
    # 5. Store learning context in agent memory
    add_memory(
        name=f"learning/epic/{epic_id}/attempt_{target_snapshot.attempt_number}",
        content={
            "type": "learning_context",
            "failed_container_run": target_snapshot.execution_state,
            "failure_analysis": target_snapshot.failure_analysis,
            "human_guidance": target_snapshot.human_feedback,
            "avoid_patterns": extract_failure_patterns(target_snapshot),
            "enhanced_prompt_additions": generate_learning_prompts(target_snapshot)
        }
    )
    
    return enhanced_config

2. Alternative Container Execution Path

def create_alternative_container_execution(epic_id: str, human_feedback: str) -> ContainerExecutionPlan:
    """
    Create new container execution plan based on previous failure and human guidance
    """
    # Load previous container attempt context
    previous_attempts = search_memory_nodes(
        query=f"learning/epic/{epic_id}",
        group_ids=["collective_brain"]
    )
    
    # Generate improved container configuration
    execution_plan = {
        "epic_id": epic_id,
        "attempt_number": len(previous_attempts) + 1,
        "git_branch": f"genie/{epic_id}/alt_{int(time.time())}",
        "learning_context": {
            "previous_failures": [attempt.failure_analysis for attempt in previous_attempts],
            "human_guidance": human_feedback,
            "enhanced_prompts": generate_failure_aware_prompts(previous_attempts),
            "risk_mitigation": identify_container_risk_factors(previous_attempts)
        },
        "container_config": {
            "max_turns": adjust_max_turns_based_on_learning(previous_attempts),
            "enhanced_system_prompt": create_learning_enhanced_prompt(human_feedback, previous_attempts),
            "additional_safety_constraints": extract_safety_constraints(previous_attempts),
            "memory_preload": get_relevant_learning_patterns(previous_attempts)
        }
    }
    
    return execution_plan
Container Failure Pattern Recognition
container_failure_patterns = {
    "scope_creep": {
        "indicators": [
            "Modified files outside allowed_tools.json boundaries",
            "Added features not in original task", 
            "Changed API contracts without approval",
            "git_commit messages show unrelated changes"
        ],
        "container_prevention": [
            "Enhanced boundary checking in prompt",
            "Stricter allowed_tools.json configuration",
            "Additional safety constraints in --append-system-prompt"
        ],
        "prompt_enhancement": "CRITICAL: Stay within defined boundaries. Previous attempt failed due to scope expansion."
    },
    "integration_issues": {
        "indicators": [
            "Container timeout due to test failures",
            "git_status shows merge conflicts",
            "postgres_query errors in container logs",
            "MCP tool connection failures"
        ],
        "container_prevention": [
            "Pre-validate MCP tool connections",
            "Add integration validation steps to prompt",
            "Increase container timeout for complex integrations"
        ],
        "prompt_enhancement": "IMPORTANT: Validate all integrations before proceeding. Previous attempt failed on integration."
    },
    "timeout_exhaustion": {
        "indicators": [
            "Container reached max_turns limit",
            "Claude session incomplete",
            "Partial implementation in git commits"
        ],
        "container_prevention": [
            "Increase max_turns based on task complexity",
            "Break down task into smaller steps in prompt",
            "Add progress checkpoints with git_commit"
        ],
        "prompt_enhancement": "Break this task into smaller steps. Previous attempt exhausted max_turns."
    },
    "memory_system_issues": {
        "indicators": [
            "agent-memory_search_memory_nodes failures",
            "Repeated pattern searches for same information",
            "Memory storage failures in container logs"
        ],
        "container_prevention": [
            "Pre-validate memory system connectivity",
            "Add memory fallback strategies to prompt",
            "Include memory debugging tools"
        ],
        "prompt_enhancement": "Verify memory system access early. Previous attempt had memory issues."
    }
}
Human Feedback Integration for Container Runs
def process_container_human_feedback(epic_id: str, container_run_id: str, feedback: str) -> ContainerEnhancement:
    """
    Process human feedback to improve next container execution attempt
    """
    feedback_analysis = {
        "epic_id": epic_id,
        "failed_container_run": container_run_id,
        "human_guidance": feedback,
        "extracted_requirements": extract_task_requirements(feedback),
        "container_modifications": {
            "max_turns_adjustment": suggest_max_turns_changes(feedback),
            "tool_configuration_changes": suggest_tool_changes(feedback),
            "prompt_enhancements": generate_prompt_improvements(feedback),
            "environment_modifications": suggest_env_changes(feedback)
        },
        "validation_additions": add_validation_checkpoints(feedback),
        "safety_constraints": extract_additional_safety_rules(feedback)
    }
    
    # Store learning for future container runs
    add_memory(
        name=f"learning/container_feedback/{epic_id}_{container_run_id}",
        content=feedback_analysis
    )
    
    return feedback_analysis
Time Machine Workflow Integration for Container Execution
Enhanced Container Run Reports with Time Machine Context
{
    "container_run_id": "run_abc123",
    "epic_id": "claude-code-implementation",
    "workflow_name": "implement",
    "git_branch": "genie/claude-code-implementation/attempt_1",
    "attempt_number": 1,
    "container_status": "failed|completed|timeout",
    "claude_execution": {
        "session_id": "claude_session_uuid",
        "max_turns": 30,
        "turns_used": 25,
        "command": "claude --dangerously-skip-permissions --output-format json...",
        "exit_code": 1,
        "duration_ms": 1800000,
        "cost_usd": 15.67
    },
    "git_state": {
        "commits_created": ["sha1", "sha2"],
        "final_commit": "abc123def",
        "files_modified": ["src/agents/claude_code/agent.py"],
        "branch": "genie/claude-code-implementation/attempt_1"
    },
    "failure_analysis": {
        "failure_type": "scope_creep",
        "failure_indicators": ["Modified API files outside scope"],
        "root_cause": "Expanded beyond agent implementation to API changes",
        "rollback_recommended": true,
        "alternative_approach": "Separate API changes into different epic"
    },
    "learning_context": {
        "previous_attempts": 0,
        "lessons_available": [],
        "human_feedback_incorporated": false,
        "memory_patterns_used": ["pattern_uuid_1", "pattern_uuid_2"]
    },
    "rollback_options": {
        "to_architecture": "After architect container completion",
        "to_epic_start": "Before any container execution",
        "to_last_success": "Previous successful epic completion"
    },
    "next_container_recommendations": {
        "enhanced_prompt": "Add strict boundary enforcement",
        "tool_restrictions": "Remove API modification tools",
        "max_turns_adjustment": "Increase to 50 for complex implementation",
        "safety_additions": "Add breaking change detection"
    }
}
Human Intervention with Container Time Travel
🚨 @human: [CONTAINER_ROLLBACK_RECOMMENDED] Implementation Scope Violation

**Container Failure Analysis**: 
- Container ID: container_abc123
- Claude Session: session_xyz789  
- Workflow: IMPLEMENT
- Failure: Modified API contracts without approval

**Container Execution Details**:
- Duration: 30 minutes (25/30 turns used)
- Cost: $15.67
- Git Commits: 3 commits with API changes
- Exit Code: 0 (completed but violated scope)

**Rollback Options**:
1. **Restart IMPLEMENT Container** - Same workflow, enhanced boundaries
2. **Rollback to ARCHITECT** - Redesign with API requirements
3. **Split Epic** - Separate API epic, continue agent implementation

**Enhanced Container Configuration Available**:
- Stricter allowed_tools.json (remove API tools)
- Enhanced --append-system-prompt with boundary warnings
- Additional safety constraints in container environment
- Memory preload with scope violation patterns

**Your Guidance Needed**:
- Should API changes be moved to separate epic?
- What specific boundary constraints for retry container?
- Any environment modifications needed?

**Container Time Machine Actions**:
🔄 Restart Container | 🌿 Alternative Branch | 📚 Save Learning | ⏭️ Skip to Next Workflow
Enhanced Epic Example with Container Time Machine
Epic: Claude-Code Implementation (With Container Failure & Recovery)
First Container Attempt - Failed

attempt_1:
  container_run_id: "run_implement_001"
  git_branch: "genie/claude-code-implementation/attempt_1"
  claude_execution:
    session_id: "session_abc123"
    command: "claude --dangerously-skip-permissions --max-turns 30..."
    turns_used: 25
    exit_code: 0
    duration_ms: 1800000
  failure_reason: "Scope creep - modified API endpoints without approval"
  git_commits: ["commit_1_agent", "commit_2_api_violation", "commit_3_more_api"]
  human_feedback: "API changes need separate epic, focus only on agent implementation"
  rollback_decision: "Restart IMPLEMENT container with enhanced boundaries"

Second Container Attempt - Learning Applied

attempt_2:
  container_run_id: "run_implement_002"
  git_branch: "genie/claude-code-implementation/attempt_2"
  learning_from: "attempt_1"
  enhanced_container_config:
    max_turns: 50  # Increased based on learning
    enhanced_prompt_additions:
      - "CRITICAL: Do not modify any API endpoints or contracts"
      - "Focus ONLY on agent implementation in src/agents/claude-code/"
      - "Previous attempt failed due to scope creep - stay focused"
    restricted_tools: # Removed API-related tools
      - "No Write access to src/api/"
      - "No Edit access to API contracts"
    memory_preload: # Loaded relevant patterns before start
      - "learning/failure_patterns/scope_creep"
      - "patterns/agent_implementation_boundaries"
  claude_execution:
    session_id: "session_def456"
    turns_used: 35
    exit_code: 0
    duration_ms: 2100000
  success_factors: 
    - "Stayed within src/agents/claude-code/ boundaries"
    - "Applied previous failure lessons"
    - "Used memory patterns effectively"
  git_commits: ["agent_impl_1", "tests_added", "docs_updated"]
Container Time Machine Command Examples
# Genie rollback commands for containers
genie rollback-container --epic claude-code-implementation --container-run run_implement_001
genie create-alternative-container --epic claude-code-implementation --learning-from attempt_1
genie enhance-container-config --from run_implement_001 --human-feedback "focus on agent only"

# Enhanced container execution with learning context (first attempt)
docker run -v session-uuid-workspace:/workspace \
  claude-code-container \
  claude -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 30 \
    --allowedTools "Task,Bash,Read,Edit,MultiEdit,Write,mcp__git__git_add,mcp__git__git_commit,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__slack__slack_post_message" \
    --append-system-prompt "$(cat /workspace/workflow/implement/prompt.md)" \
    "Implement ClaudeCodeAgent staying strictly within agent boundaries"

# Enhanced container execution after rollback (second attempt with learning)
docker run -v session-uuid-alt-workspace:/workspace \
  claude-code-container \
  claude -p \
    --dangerously-skip-permissions \
    --output-format json \
    --max-turns 50 \
    --allowedTools "Task,Bash,Read,Edit,MultiEdit,Write,mcp__git__git_add,mcp__git__git_commit,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__slack__slack_post_message" \
    --append-system-prompt "$(cat /workspace/workflow/implement/prompt_enhanced.md)" \
    "Implement ClaudeCodeAgent with enhanced boundary enforcement. CRITICAL: Previous attempt failed due to scope creep - only modify src/agents/claude-code/ directory. Load learning from previous failure before starting."

# Where prompt_enhanced.md contains the original prompt plus learning context:
# cat /workspace/workflow/implement/prompt_enhanced.md
# [Original IMPLEMENT prompt content]
# 
# ENHANCED LEARNING FROM PREVIOUS FAILURE:
# - Previous attempt (attempt_1) failed due to scope creep - modified API files outside boundaries
# - Human feedback: "Focus only on agent implementation, API changes need separate epic"
# - Enhanced boundary enforcement: Only modify files in src/agents/claude-code/ directory
# - Additional validation: Check file paths before any Write/Edit operations
# - If you need to modify anything outside src/agents/claude-code/, immediately escalate via Slack
Memory Evolution with Container Time Machine
Agent-Memory MCP Groups After Epic:

genie_patterns:
├── "Container Lifecycle Management Pattern" - Enhanced Docker management approach
├── "Session Persistence Testing Success" - Volume mounting solution
├── "Claude Code Integration Pattern" - Complete container integration
└── "Bounded Container Execution" - Successful scope adherence

genie_decisions:
├── "Architecture Decision: Docker Per Session Strategy" - Container strategy choice
└── "Container Decision: Volume Persistence Approach" - Session management decision

genie_learning:
├── "Container Failure: scope_creep in implement" - First attempt failure analysis
├── "Learning: Epic claude-code-implementation Attempt 1" - Complete failure learning
└── "Container Recovery: Enhanced Boundaries Success" - Second attempt success

genie_context:
├── "Epic Progress: claude-code-implementation" - Complete epic state
├── "Container Executions: All 7 Runs" - Full execution history
└── "Issue Resolution: Session Persistence" - Problem resolution tracking

Real Memory Storage Examples After Epic:

# Pattern stored after successful implementation
mcp__agent_memory__add_memory(
    name="Container Lifecycle Management Pattern",
    episode_body="Successfully implemented Docker container lifecycle management for Claude Code agents. Key approach: One container per execution, volume-based persistence, git commit extraction on completion. Container startup: 5-10s, execution: 30-60 minutes, cleanup: automatic. Critical success factors: proper volume mounting, credential management, MCP tool integration.",
    source="text",
    source_description="Proven container management pattern for Claude Code agents",
    group_id="genie_patterns"
)

# Decision stored after architecture phase
mcp__agent_memory__add_memory(
    name="Architecture Decision: Docker Per Session Strategy", 
    episode_body='{"decision": "docker-per-session", "rationale": "Isolation and resource management", "alternatives": ["shared-container", "process-based"], "production_impact": "none", "rollback_plan": "fallback to existing agents"}',
    source="json",
    source_description="Container architecture decision for Claude Code implementation",
    group_id="genie_decisions"
)

# Learning stored after container failure
mcp__agent_memory__add_memory(
    name="Container Failure: scope_creep in implement",
    episode_body="Container execution failed due to scope violations. Workflow: implement, Duration: 30 minutes, Cost: $22.15. Root cause: Modified API endpoints outside of allowed src/agents/ scope. Prevention: Enhanced boundary checking prompts, restricted tool access to specific directories, additional human approval gates for scope expansion.",
    source="text", 
    source_description="Container failure analysis with prevention strategy",
    group_id="genie_learning"
)
🧠 Shared Memory System (Agent-Memory MCP Integration)
Memory Organization Structure
The agent-memory MCP uses a graph-based system with entities, relationships, and episodes organized by group IDs:

collective_brain (via group_ids):
├── "genie_patterns"          # Reusable development patterns
├── "genie_decisions"         # Architectural choices with rationale  
├── "genie_procedures"        # How-to guides and workflows
├── "genie_learning"          # Time machine learning system
└── "genie_context"          # Current epic and project state
Memory Storage Protocol with Agent-Memory MCP
# Standard memory entry using agent-memory MCP API
def store_pattern_memory(pattern_name: str, pattern_data: str, epic_id: str):
    """Store a reusable pattern in agent memory"""
    mcp__agent_memory__add_memory(
        name=f"Pattern: {pattern_name}",
        episode_body=pattern_data,
        source="text",
        source_description=f"Development pattern from epic {epic_id}",
        group_id="genie_patterns"
    )

def store_decision_memory(decision_title: str, decision_data: dict, epic_id: str):
    """Store an architectural decision"""
    mcp__agent_memory__add_memory(
        name=f"Decision: {decision_title}",
        episode_body=json.dumps(decision_data),
        source="json", 
        source_description=f"Architectural decision from epic {epic_id}",
        group_id="genie_decisions"
    )

def store_learning_memory(epic_id: str, failure_analysis: dict, attempt_number: int):
    """Store learning from failed attempts"""
    mcp__agent_memory__add_memory(
        name=f"Learning: Epic {epic_id} Attempt {attempt_number}",
        episode_body=json.dumps({
            "epic_id": epic_id,
            "attempt_number": attempt_number,
            "failure_type": failure_analysis["failure_type"],
            "failure_point": failure_analysis["failure_point"],
            "root_cause": failure_analysis["root_cause"],
            "prevention_strategy": failure_analysis["prevention_strategy"],
            "human_feedback": failure_analysis.get("human_feedback", ""),
            "container_details": failure_analysis.get("container_details", {})
        }),
        source="json",
        source_description=f"Failure analysis and learning from epic {epic_id}",
        group_id="genie_learning"
    )
Memory Usage Guidelines with Real Agent-Memory API
Before Starting Any Container Work:

# Check for existing patterns
patterns = mcp__agent_memory__search_memory_nodes(
    query=f"container lifecycle docker agent implementation",
    group_ids=["genie_patterns"],
    max_nodes=10
)

# Check for previous attempt failures and lessons
learning_context = mcp__agent_memory__search_memory_nodes(
    query=f"epic {epic_id} failure scope boundary",
    group_ids=["genie_learning"],
    max_nodes=5
)

# Check for related architectural decisions
decisions = mcp__agent_memory__search_memory_nodes(
    query=f"docker architecture container strategy session",
    group_ids=["genie_decisions"],
    max_nodes=5
)

# Check current epic context
epic_context = mcp__agent_memory__search_memory_facts(
    query=f"epic {epic_id}",
    group_ids=["genie_context"],
    max_facts=10
)

After Completing Container Work:

# Store successful patterns with attempt context
def store_successful_container_pattern(workflow_name: str, epic_id: str, success_data: dict, attempt_number: int):
    pattern_episode = f"""
    Successful {workflow_name} container execution pattern:
    
    Epic: {epic_id}
    Attempt: {attempt_number}
    Container Duration: {success_data['duration_ms']}ms
    Turns Used: {success_data['turns_used']}/{success_data['max_turns']}
    Cost: ${success_data['cost_usd']}
    
    Success Factors:
    {', '.join(success_data.get('success_factors', []))}
    
    Files Modified: {', '.join(success_data.get('files_modified', []))}
    Git Commits: {', '.join(success_data.get('git_commits', []))}
    
    Key Techniques:
    {success_data.get('key_techniques', 'Standard approach')}
    
    Memory Patterns Used:
    {', '.join(success_data.get('memory_patterns_used', []))}
    """
    
    mcp__agent_memory__add_memory(
        name=f"Successful {workflow_name} Container Pattern",
        episode_body=pattern_episode,
        source="text",
        source_description=f"Proven container execution pattern for {workflow_name} workflow",
        group_id="genie_patterns"
    )

# Store decisions made during container execution
def store_container_decision(decision_title: str, decision_context: dict, epic_id: str):
    decision_data = {
        "decision": decision_title,
        "epic_id": epic_id,
        "container_context": decision_context,
        "rationale": decision_context.get("rationale", ""),
        "alternatives_considered": decision_context.get("alternatives", []),
        "impact_assessment": decision_context.get("impact", ""),
        "production_safety": decision_context.get("production_safe", True),
        "rollback_plan": decision_context.get("rollback_plan", "")
    }
    
    mcp__agent_memory__add_memory(
        name=f"Container Decision: {decision_title}",
        episode_body=json.dumps(decision_data),
        source="json",
        source_description=f"Decision made during container execution in epic {epic_id}",
        group_id="genie_decisions"
    )

# Store failure patterns when containers fail
def store_container_failure_learning(epic_id: str, container_run_id: str, failure_analysis: dict):
    failure_episode = f"""
    Container Failure Analysis:
    
    Epic: {epic_id}
    Container Run: {container_run_id}
    Workflow: {failure_analysis['workflow_name']}
    Failure Type: {failure_analysis['failure_type']}
    
    Root Cause Analysis:
    {failure_analysis['root_cause']}
    
    Failure Indicators:
    {', '.join(failure_analysis.get('failure_indicators', []))}
    
    Container Details:
    - Duration: {failure_analysis.get('duration_ms', 0)}ms
    - Turns Used: {failure_analysis.get('turns_used', 0)}/{failure_analysis.get('max_turns', 0)}
    - Exit Code: {failure_analysis.get('exit_code', 'unknown')}
    - Cost: ${failure_analysis.get('cost_usd', 0)}
    
    Prevention Strategy:
    {failure_analysis['prevention_strategy']}
    
    Human Feedback:
    {failure_analysis.get('human_feedback', 'None provided')}
    
    Recommended Changes:
    {', '.join(failure_analysis.get('recommended_changes', []))}
    """
    
    mcp__agent_memory__add_memory(
        name=f"Container Failure: {failure_analysis['failure_type']} in {failure_analysis['workflow_name']}",
        episode_body=failure_episode,
        source="text", 
        source_description=f"Container failure analysis from epic {epic_id}",
        group_id="genie_learning"
    )
🚨 Production Safety System
Automatic Breaking Change Detection
breaking_change_patterns = {
    "database_schema": [
        "ALTER TABLE.*DROP COLUMN",
        "ALTER TABLE.*CHANGE COLUMN.*TYPE",
        "DROP TABLE",
        "TRUNCATE TABLE",
        "DELETE FROM.*(?!WHERE)",  # DELETE without WHERE
        "CREATE.*UNIQUE.*INDEX",   # Can break existing data
    ],
    "api_contracts": [
        "Remove.*endpoint",
        "Change.*response.*schema", 
        "Modify.*authentication",
        "Remove.*parameter",
        "Change.*parameter.*type",
        "Add.*required.*parameter"
    ],
    "dependencies": [
        "uv add.*[^\\d]\\d+\\.",      # Major version changes
        "uv remove",                 # Package removal
        "requirements.*==.*->.*",    # Version pinning changes
    ],
    "core_architecture": [
        "class.*Agent.*:",           # Base agent changes
        "def.*execute.*:",           # Core execution changes
        "import.*automagik.*",       # Framework imports
        "src/core/",                 # Core module changes
        "src/api/v1/",              # API version changes
    ]
}

explicit_blocker_signals = [
    "BLOCKER:",
    "HUMAN NEEDED:",
    "BREAKING CHANGE:",
    "SECURITY CONCERN:", 
    "UNCLEAR REQUIREMENT:",
    "PRODUCTION RISK:",
    "AMBIGUOUS SPEC:",
    "CLIENT IMPACT:"
]
Workflow Boundary Enforcement
workflow_boundaries = {
    "implement": {
        "allowed_paths": [
            "src/agents/*/",
            "tests/agents/*/", 
            "docs/agents/"
        ],
        "forbidden_paths": [
            "src/api/v1/",
            "src/core/",
            "src/db/migrations/",
            "production.yml",
            "docker-compose.prod.yml"
        ],
        "requires_approval": [
            "*.sql",
            "requirements.txt",
            "pyproject.toml"
        ]
    },
    "fix": {
        "allowed_paths": ["*"],  # Bugs can be anywhere
        "requires_approval": [
            "src/db/migrations/",
            "src/api/",
            "src/core/",
            "production.*"
        ]
    },
    "refactor": {
        "allowed_paths": ["src/"],
        "forbidden_paths": [
            "src/db/schema/",
            "src/api/v1/",
            "src/core/interfaces/"
        ]
    }
}
Human Intervention Triggers
Automatic Escalation Events:

Breaking Change Detected: Code matches breaking change patterns
Production Database Touch: Schema migrations or data modifications
Security-Sensitive Changes: Authentication, authorization, encryption
Core Architecture Modifications: Base classes, interfaces, protocols
Multi-Client Impact: Changes affecting shared infrastructure
Dependency Security Issues: Known vulnerabilities or major updates
Workflow Boundary Violations: Accessing forbidden paths
Explicit Blocker Signals: Workflow explicitly requests human help

Human Decision Points:

Approve/Reject: Breaking changes, architecture modifications
Prioritize: When multiple workflows compete for critical resources
Resolve Conflicts: Disagreements between workflow recommendations
Override Decisions: When workflow choices seem suboptimal
Emergency Response: Production incidents requiring immediate attention
📱 Communication Protocol
Slack Thread Organization
Project Thread: "Epic: [EPIC_NAME] - [LINEAR_ID]"
├── Architecture Phase Updates
├── Implementation Progress  
├── Test Results and Issues
├── Review Feedback
├── Bug Fix Reports
├── Final PR Preparation
└── Human Escalations
Structured Workflow Messages
Workflow-to-Workflow Communication
@workflow_name: [ACTION] [CONTEXT]
└─ HANDOFF: "Architecture complete, ADRs stored, ready for implementation"
└─ REQUEST: "Need clarification on error handling pattern for retries"  
└─ NOTIFY: "Found potential security issue in authentication module"
└─ COMPLETE: "Implementation finished, tests passing, ready for review"
└─ BLOCKED: "Cannot proceed - unclear requirement about client isolation"
Human Escalation Format
🚨 @human: [APPROVAL_NEEDED] [DECISION_TITLE]

**Context**: Situation requiring human input
**Issue**: Specific problem or decision needed
**Options**: 
1. Option A - Benefits/Risks
2. Option B - Benefits/Risks  
3. Option C - Benefits/Risks

**Recommendation**: Workflow's suggested approach
**Production Impact**: Potential consequences for hundreds of clients
**Urgency**: Timeline requirements

**Related**: Linear issue, Git branch, Previous decisions
Standardized Run Reports
{
    "workflow": "implement",
    "session_id": "a6aa0ff2-5ecd-4634-806b-ea94cc0434dd",
    "status": "completed|blocked|needs_human|error",
    "epic_id": "claude-code-implementation", 
    "linear_id": "NMSTX-187",
    "summary": "Implemented ClaudeCodeAgent with Docker container management",
    "changes": {
        "files_modified": ["src/agents/claude_code/agent.py", "src/agents/claude_code/container.py"],
        "files_added": ["src/agents/claude_code/executor.py"],
        "tests_created": ["tests/agents/claude_code/test_agent.py"],
        "patterns_used": ["memory_uuid_1", "memory_uuid_2"],
        "patterns_created": ["container-lifecycle-uuid"],
        "breaking_changes": false,
        "production_impact": "none"
    },
    "next_workflow": "test",
    "blocker_details": null,
    "human_message": null,
    "memory_updates": [
        "patterns/agent-implementation: Enhanced with container support",
        "procedures/claude-code-testing: Created workflow-specific test guide"
    ]
}
WhatsApp Alert Format
🤖 Epic: [EPIC_NAME]  
📌 Workflow: [WORKFLOW_NAME]
✅ Status: [STATUS]

Summary: [BRIEF_SUMMARY]

Changes:
• Files: X modified, Y added
• Tests: Z added/updated  
• Memory: N patterns used/created
• Breaking: Yes/No

Next: [NEXT_WORKFLOW or HUMAN_NEEDED]
[BLOCKER_DETAILS if any]

Linear: [LINEAR_ID] | Session: [SESSION_ID]
🚀 Epic Example: Claude-Code Implementation
Epic Definition
Title: Implement Claude-Code Agent Type
Linear ID: NMSTX-187
Objective: Add containerized Claude CLI execution as new agent framework Production Impact: New capability, no breaking changes to existing clients Container Strategy: Manual workflow testing first, then Genie orchestration
Complete Container Workflow Execution
Phase 1: Architecture (ARCHITECT Container)
# Genie deploys ARCHITECT container
POST /api/v1/agent/claude-code/architect/run
{
    "message": "Design architecture for Claude-Code agent type that runs Claude CLI in Docker containers for NMSTX-187",
    "git_branch": "genie/claude-code-implementation/arch_001",
    "max_turns": 30
}

# Container executes:
docker run -v session-arch-001-workspace:/workspace claude-code-container \
    claude -p \
        --dangerously-skip-permissions \
        --output-format json \
        --max-turns 30 \
        --allowedTools "Read,Write,Edit,mcp__linear__linear_createIssue,mcp__linear__linear_updateIssue,mcp__slack__slack_post_message,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__deepwiki__read_wiki_contents" \
        "Design architecture for Claude-Code agent type that runs Claude CLI in Docker containers for NMSTX-187"

Container Actions (Inside Claude Code execution):

Search memory: mcp__agent-memory__search_memory_nodes(query="agent implementation automagik docker container", group_ids=["genie_patterns"], max_nodes=10)
Design folder structure: Write("docs/architecture/claude-code-agent-structure.md") with detailed structure
Create interfaces: Define ClaudeCodeAgent, ContainerManager, CLIExecutor classes
Human approval via Slack: mcp__slack__slack_post_message(channel_id="epic-channel", text="HUMAN NEEDED: Approve docker-per-session vs shared container strategy")
Store decision: mcp__agent-memory__add_memory(name="Architecture Decision: Docker Per Session Strategy", episode_body="Decision to use docker-per-session with volume persistence for Claude Code agents...", source="text", source_description="architectural decision for container strategy", group_id="genie_decisions")

Container Completion:

{
    "type": "result",
    "subtype": "success",
    "cost_usd": 8.45,
    "duration_ms": 1200000,
    "num_turns": 18,
    "session_id": "arch-session-001",
    "result": "Architecture complete: Docker-per-session strategy approved, folder structure defined, interfaces designed"
}
Phase 2: Implementation (IMPLEMENT Container)
# Genie deploys IMPLEMENT container
POST /api/v1/agent/claude-code/implement/run
{
    "message": "Implement ClaudeCodeAgent based on approved architecture from arch-session-001",
    "git_branch": "genie/claude-code-implementation/impl_001", 
    "max_turns": 50
}

# Container executes:
docker run -v session-impl-001-workspace:/workspace claude-code-container \
    claude -p \
        --dangerously-skip-permissions \
        --output-format json \
        --max-turns 50 \
        --allowedTools "Task,Bash,Read,Edit,MultiEdit,Write,mcp__git__git_add,mcp__git__git_commit,mcp__git__git_status,mcp__postgres_automagik_agents__query,mcp__agent-memory__search_memory_nodes,mcp__agent-memory__add_memory,mcp__slack__slack_post_message" \
        "Implement ClaudeCodeAgent based on approved architecture from arch-session-001"

Container Actions:

Load patterns: mcp__agent-memory__search_memory_nodes(query="agent implementation automagik pattern", group_ids=["genie_patterns"], max_nodes=5)
Load architecture: mcp__agent-memory__search_memory_nodes(query="docker per session strategy", group_ids=["genie_decisions"], max_nodes=3)
Create src/agents/claude_code/agent.py extending AutomagikAgent
Implement container.py for Docker lifecycle management: Write("src/agents/claude_code/container.py")
Build executor.py for CLI command execution: Write("src/agents/claude_code/executor.py")
Progress commits: mcp__git__git_add(repo_path="/workspace/am-agents-labs", pathspecs=["src/agents/claude_code/"]) then mcp__git__git_commit(repo_path="/workspace/am-agents-labs", message="feat: implement ClaudeCodeAgent class")
Store pattern: mcp__agent-memory__add_memory(name="Container Lifecycle Management Pattern", episode_body="Successfully implemented Docker container lifecycle management for Claude Code agents...", source="text", source_description="proven container management pattern", group_id="genie_patterns")
Use package manager: Task("cd /workspace/am-agents-labs && uv add docker")

Container Completion:

{
    "type": "result", 
    "subtype": "success",
    "cost_usd": 22.15,
    "duration_ms": 2400000,
    "num_turns": 42,
    "session_id": "impl-session-001",
    "result": "ClaudeCodeAgent implementation complete with container management"
}
Phase 3: Testing (TEST Container)
# Genie deploys TEST container
POST /api/v1/agent/claude-code/test/run
{
    "message": "Create comprehensive tests for claude-code agent implementation from impl-session-001",
    "git_branch": "genie/claude-code-implementation/test_001",
    "max_turns": 40
}

Container Actions:

Load test patterns: mcp__agent-memory__search_memory_nodes(query="testing agent pattern automagik", group_ids=["genie_patterns"], max_nodes=5)
Load implementation context: mcp__agent-memory__search_memory_nodes(query="container lifecycle management", group_ids=["genie_patterns"], max_nodes=3)
Create unit tests: Write("tests/agents/claude_code/test_agent.py") with comprehensive coverage
Integration tests: Write("tests/agents/claude_code/test_integration.py") with mocked Docker
Test execution: Task("cd /workspace/am-agents-labs && python -m pytest tests/agents/claude_code/ -v")
Issue Discovery: Tests reveal session persistence problem across container restarts
Issue documentation: mcp__slack__slack_post_message(channel_id="epic-channel", text="BLOCKER: Session persistence failing across container restarts - need investigation")

Container Completion:

{
    "type": "result",
    "subtype": "blocked", 
    "cost_usd": 15.30,
    "duration_ms": 1800000,
    "num_turns": 28,
    "session_id": "test-session-001",
    "result": "Test suite created, found session persistence issue blocking completion"
}
Phase 4: Bug Fix (FIX Container)
# Genie deploys FIX container for discovered issue
POST /api/v1/agent/claude-code/fix/run
{
    "message": "Fix session persistence issue discovered in test-session-001",
    "git_branch": "genie/claude-code-implementation/fix_001",
    "max_turns": 30
}

Container Actions:

Investigate with logs: Task("docker logs claude-code-test-container")
Search memory: mcp__agent-memory__search_memory_nodes(query="session persistence container docker volume", group_ids=["genie_patterns", "genie_learning"], max_nodes=5)
Git analysis: mcp__git__git_log(repo_path="/workspace/am-agents-labs", max_count=10) and mcp__git__git_diff(repo_path="/workspace/am-agents-labs", commit1="HEAD~3", commit2="HEAD")
Root cause analysis: Session state not mounted as Docker volume
Fix implementation: Edit("src/agents/claude_code/container.py") to add session volume mounting
Test fix: Task("python -m pytest tests/agents/claude_code/test_integration.py::test_session_persistence -v")
Commit fix: mcp__git__git_commit(repo_path="/workspace/am-agents-labs", message="fix(container): add session persistence volume mounting")

Container Completion:

{
    "type": "result",
    "subtype": "success",
    "cost_usd": 9.75,
    "duration_ms": 900000, 
    "num_turns": 15,
    "session_id": "fix-session-001",
    "result": "Session persistence fixed with volume mounting solution"
}
Phase 5: Validation (TEST Container - Resume)
# Genie resumes TEST container with fix applied
POST /api/v1/agent/claude-code/test/run
{
    "message": "Re-run integration tests after session persistence fix from fix-session-001",
    "session_id": "test-session-001",  # Resume previous session
    "git_branch": "genie/claude-code-implementation/test_001",
    "max_turns": 20
}

# Container executes with session resume:
docker run -v session-test-001-workspace:/workspace claude-code-container \
    claude -r "test-session-001" -p \
        --dangerously-skip-permissions \
        --output-format json \
        --max-turns 20 \
        "Re-run integration tests after session persistence fix from fix-session-001"

Container Actions:

Load fix context: mcp__agent-memory__search_memory_nodes(query="session persistence volume mounting fix", group_ids=["genie_patterns"], max_nodes=3)
Re-run tests: Task("python -m pytest tests/agents/claude_code/ -v --tb=short")
Verify coverage: Task("python -m pytest tests/agents/claude_code/ --cov=src.agents.claude_code --cov-report=term-missing")
Document success: mcp__agent-memory__add_memory(name="Session Persistence Testing Success", episode_body="Volume mounting solution successfully resolves session persistence issues across container restarts...", source="text", source_description="verified testing solution", group_id="genie_patterns")

Container Completion:

{
    "type": "result",
    "subtype": "success",
    "cost_usd": 6.20,
    "duration_ms": 600000,
    "num_turns": 12,
    "session_id": "test-session-001",
    "result": "All tests passing, 95% coverage achieved, ready for review"
}
Phase 6: Review (REVIEW Container)
# Genie deploys REVIEW container
POST /api/v1/agent/claude-code/review/run
{
    "message": "Review claude-code implementation for quality and standards compliance",
    "git_branch": "genie/claude-code-implementation/review_001",
    "max_turns": 25
}

Container Actions:

Load standards: agent-memory_search_memory_nodes("patterns code-review automagik")
Review implementation: Read("src/agents/claude_code/agent.py") with detailed analysis
Security validation: Check Docker isolation, no privilege escalation
Performance review: Verify resource limits, cleanup procedures
Pattern compliance: agent-memory_search_memory_nodes("patterns agent-implementation") for consistency
No breaking changes confirmed: git_diff("origin/main..HEAD") shows only additions
Approval decision: slack_post_message("✅ Code review passed, ready for PR creation")
Phase 7: Pull Request (PR Container)
# Genie deploys PR container
POST /api/v1/agent/claude-code/pr/run
{
    "message": "Create pull request for claude-code agent implementation from all previous work",
    "git_branch": "genie/claude-code-implementation/pr_001",
    "max_turns": 20
}

Container Actions:

Gather epic context: agent-memory_search_memory_nodes("context/epic/claude-code-implementation")
Create PR description: Write(".github/PULL_REQUEST_TEMPLATE.md") with comprehensive details
Link Linear issue: linear_updateIssue(issueId="NMSTX-187", description="PR #123 created")
Final validation: Task("cd /workspace/am-agents-labs && python -m pytest && ruff check src/ && ruff format src/")
PR creation: Task("gh pr create --title 'feat: implement Claude Code agent framework' --body-file .github/PULL_REQUEST_TEMPLATE.md")
Human notification: slack_post_message("🎉 PR #123 created and ready for human review - no breaking changes, full test coverage")

Container Completion:

{
    "type": "result",
    "subtype": "success", 
    "cost_usd": 4.85,
    "duration_ms": 480000,
    "num_turns": 8,
    "session_id": "pr-session-001",
    "result": "PR #123 created successfully, ready for human merge approval"
}
Epic Summary: Container Execution Results
Total Epic Execution:

Containers Deployed: 7 (arch, impl, test, fix, test-resume, review, pr)
Total Cost: $66.70
Total Duration: 8.4 hours
Git Commits: 12 commits across all containers
Issues Found & Fixed: 1 (session persistence)
Human Interventions: 2 (architecture approval, final PR merge)

Memory Evolution Throughout Epic:

Before Epic:

collective_brain/
├── patterns/agent-implementation: Basic automagik agent pattern
├── procedures/testing: Standard test procedures  
└── decisions/: Previous architectural decisions

After Epic:

collective_brain/
├── patterns/
│   ├── agent-implementation: Enhanced with Claude Code container specifics
│   ├── container-lifecycle-management: Docker management patterns
│   ├── session-persistence-testing: Volume mounting solutions
│   └── claude-code-integration: Complete integration patterns
├── decisions/
│   ├── 2024-06/docker-per-session: Architecture decision with rationale
│   └── 2024-06/volume-persistence-strategy: Session management approach
├── procedures/
│   ├── claude-code-testing: Container-specific test procedures
│   ├── container-debugging: Issue resolution procedures
│   └── pr-creation-claude-code: PR workflow for container agents
└── context/epic/claude-code-implementation/
    ├── container_executions: All 7 container run details
    ├── issue_resolutions: Session persistence solution
    └── final_state: Complete implementation ready for production
Real Implementation Learning
Key Insights for Genie Development:

Container Lifecycle Management: Genie must track container creation, execution, and cleanup across multiple Docker deployments
Session Persistence: Critical for resuming containers and maintaining context across workflow transitions
Memory Integration: MCP agent-memory tools provide the shared brain functionality between containers
Cost Tracking: Container executions can be expensive ($66 for full epic) - need cost monitoring and limits
Git Branch Strategy: Each container should work on isolated branches with final merge coordination
Human Intervention Points: Architecture decisions and final approvals require human input via Slack
Issue Resolution Flow: Failed containers should trigger specialized fix containers automatically
Database Integration: All container state must persist in PostgreSQL for Genie coordination

Genie Orchestration Patterns Identified:

Sequential Container Deployment: Each workflow waits for previous completion
Context Handoff: Memory system provides seamless context transfer between containers
Failure Recovery: Automatic deployment of fix containers when issues detected
Human Gates: Specific points requiring human approval before proceeding
Cost Management: Track cumulative costs and implement spending limits per epic
🛠️ Tool Configuration & Workflow Setup
Workflow-Specific Tool Access (.mcp.json per workflow)
{
  "architect": {
    "tools": ["Read", "Write", "Edit", "git_*", "linear_*", "slack_*", "agent-memory_*", "deepwiki_*"],
    "restrictions": ["No code implementation", "Design and planning only"]
  },
  "implement": {
    "tools": ["Task", "Bash", "Read", "Edit", "MultiEdit", "Write", "git_*", "postgres_*", "agent-memory_*", "slack_*"],
    "restrictions": ["Stay within assigned boundaries", "Use uv for package management"]
  },
  "test": {
    "tools": ["Task", "Bash", "Read", "Write", "Edit", "git_*", "postgres_*", "agent-memory_*", "slack_*"],
    "restrictions": ["Create tests, don't modify business logic"]
  },
  "review": {
    "tools": ["Read", "git_*", "linear_*", "agent-memory_*", "slack_*", "postgres_*"],
    "restrictions": ["Review only, no code modifications"]
  },
  "fix": {
    "tools": ["Task", "Bash", "Glob", "Grep", "Read", "Edit", "git_*", "linear_*", "agent-memory_*", "slack_*"],
    "restrictions": ["Minimal fixes only", "Surgical changes"]
  },
  "refactor": {
    "tools": ["Task", "Bash", "Read", "Edit", "MultiEdit", "git_*", "agent-memory_*", "slack_*"],
    "restrictions": ["No breaking changes", "Maintain API contracts"]
  },
  "document": {
    "tools": ["Read", "Write", "Edit", "deepwiki_*", "agent-memory_*", "slack_*", "linear_*"],
    "restrictions": ["Documentation only, no code changes"]
  },
  "pr": {
    "tools": ["Task", "Bash", "Read", "Edit", "git_*", "linear_*", "slack_*", "agent-memory_*"],
    "restrictions": ["Prepare for merge, no feature changes"]
  }
}
Workflow Directory Structure
workflows/
├── architect/
│   ├── .mcp.json
│   ├── system_prompt.md
│   └── allowed_tools.json
├── implement/
│   ├── .mcp.json  
│   ├── system_prompt.md
│   └── allowed_tools.json
├── test/
│   ├── .mcp.json
│   ├── system_prompt.md
│   └── allowed_tools.json
├── review/
│   ├── .mcp.json
│   ├── system_prompt.md  
│   └── allowed_tools.json
├── fix/
│   ├── .mcp.json
│   ├── system_prompt.md
│   └── allowed_tools.json
├── refactor/
│   ├── .mcp.json
│   ├── system_prompt.md
│   └── allowed_tools.json
├── document/
│   ├── .mcp.json
│   ├── system_prompt.md
│   └── allowed_tools.json
└── pr/
    ├── .mcp.json
    ├── system_prompt.md
    └── allowed_tools.json
🎯 Implementation Roadmap
Phase 1: Claude Code Container Foundation (Weeks 1-2)
Docker Container Infrastructure

Create Dockerfile with Claude CLI and MCP tools
Set up volume mount points for credentials and workspace
Configure am-agents-labs repository cloning and setup
Test basic container creation and Claude execution with --dangerously-skip-permissions

Workflow Configuration System

Create workflow directory structure (architect/, implement/, test/, etc.)
Implement prompt.md, .mcp.json, allowed_tools.json configurations
Set up environment variables and credential management
Test workflow-specific container executions

Basic API Integration

Implement /api/v1/agent/claude-code/{workflow}/run endpoints
Add PostgreSQL integration using existing sessions/messages tables
Create async container execution with status polling
Test manual workflow triggering and status tracking
Phase 2: Manual Workflow Testing (Weeks 3-4)
Individual Workflow Validation

Test ARCHITECT workflow with real design tasks
Validate IMPLEMENT workflow with actual coding tasks
Verify TEST workflow with comprehensive test creation
Test FIX workflow with bug resolution scenarios

Workflow Communication Testing

Verify MCP agent-memory sharing between containers
Test Slack integration for progress updates and human escalation
Validate database state persistence across container executions
Test git commit extraction and branch management

Production Safety Validation

Test breaking change detection patterns
Verify human escalation triggers work correctly
Validate container resource limits and cleanup
Test rollback scenarios with git branch management
Phase 3: Genie Orchestrator Development (Weeks 5-6)
LangGraph State Machine

Implement epic state management with workflow transitions
Create container deployment and monitoring logic
Add status polling and completion detection
Implement workflow sequence coordination

Time Machine Infrastructure

Container Snapshot System: Git branch management for rollbacks
Failure Detection: Pattern matching for container failures
Learning Integration: Memory system for failed attempts and human feedback
Alternative Path Creation: Enhanced container configurations for retries

Human Intervention System

Automatic escalation triggers based on container status
Slack-based human decision interfaces
Container rollback and restart capabilities
Cost monitoring and budget enforcement
Phase 4: Advanced Genie Capabilities (Weeks 7-8)
Enhanced Learning System

Container Failure Pattern Recognition: Automatic detection of repeat failure modes
Human Feedback Processing: Integration of human guidance into container configurations
Success Pattern Extraction: Learning from successful container recoveries
Dynamic Configuration Enhancement: Prompt and tool configuration improvements

Advanced Time Machine Features

Multi-Level Container Rollbacks: Checkpoint system with granular rollback options
Cost-Based Container Management: Automatic rollback when cost thresholds exceeded
Predictive Failure Detection: Early warning system for likely container failures
Learning Analytics: Dashboard for tracking container improvements over time

Production-Ready Orchestration

Epic Workflow Management: Complete epic lifecycle from architecture to PR
Resource Management: Container concurrency limits and resource optimization
Monitoring Integration: Real-time container health and performance tracking
Error Recovery: Automatic issue detection and recovery container deployment
Phase 5: Production Deployment (Weeks 9-10)
End-to-End Epic Testing

Complete epic validation with real implementation scenarios
Container Rollback Testing: Verify complete state restoration works correctly
Learning Validation: Confirm learning improves subsequent container attempts
Production safety verification with container rollback capabilities

Production Rollout

Gradual deployment strategy with container rollback safety net
Container Performance Monitoring: Real-time analytics and cost tracking
Human Training: Train team on container orchestration and rollback decisions
Team onboarding with complete container workflow system
Success Metrics for Container-Based System
Container Performance Metrics
Container Startup Time: Average time from API call to Claude execution start
Container Success Rate: Percentage of containers completing without errors
Container Resource Efficiency: CPU/memory usage optimization over time
Container Cost Per Epic: Total container execution costs for complete epics
Time Machine Effectiveness for Containers
Container Recovery Rate: Percentage of failed epics successfully completed after container rollback
Container Learning Effectiveness: Improvement rate between container attempts (cost, time, quality)
Human Intervention Reduction: Decrease in human escalations over time for container issues
Container Failure Prevention: Reduction in repeat container failure patterns
Genie Orchestration Performance
Epic Completion Rate: Percentage of epics successfully completed end-to-end
Epic Time to Completion: Average time from epic start to PR creation
Container Coordination Efficiency: Overhead of orchestration vs. manual container execution
Learning Accumulation: Rate of memory pattern growth and utilization
Implementation Strategy Based on Claude Code Reality
Container-First Development Approach
Phase 1-2: Manual Container Testing
├── Build individual workflow containers
├── Test each workflow manually via API
├── Validate container communication patterns
└── Gather real performance and cost data

Phase 3-4: Genie Development with Real Data
├── Use container execution patterns for orchestration design
├── Implement time machine based on actual container failures
├── Build learning system using real container performance data
└── Create human intervention based on actual escalation patterns

Phase 5: Production Integration
├── Deploy Genie with proven container foundation
├── Monitor real epic executions with established baselines
├── Optimize based on actual usage patterns
└── Scale based on proven container performance metrics
Key Implementation Insights from Real Claude Code Analysis
Container Lifecycle Reality:

Containers terminate after Claude completes with JSON output
No idle state management needed - containers are ephemeral
Git commits must be extracted before container termination
Session persistence requires volume mounting strategies

Cost and Performance Considerations:

Container executions can range from $5-25 per workflow
Full epics may cost $50-100 depending on complexity
Container startup overhead is significant - optimize for longer executions
Memory system access via MCP tools is critical for efficiency

Human Intervention Patterns:

Architecture decisions require human approval via Slack
Breaking change detection must pause container execution
Final PR merge decisions remain human-controlled
Cost overruns need automatic escalation triggers

Learning System Design:

Failed containers provide rich failure analysis data
Human feedback can enhance subsequent container configurations
Success patterns emerge from container execution logs and git commits
Memory system stores both failure patterns and successful approaches

This roadmap ensures the orchestration system is built on proven container execution patterns rather than theoretical agent communication, making it more reliable and production-ready from day one.


