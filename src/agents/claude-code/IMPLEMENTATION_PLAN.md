# Claude-Code Agent Implementation Plan

## Executive Summary

This plan outlines the implementation of a new `claude-code` agent type that runs Claude CLI in isolated Docker containers while maintaining full integration with the Automagik Agents framework. The agent will support all Claude CLI parameters, session persistence, and enable agent-to-agent communication.

**Linear Context**: This work will be tracked in a new Linear project separate from NMSTX-187. All code and commits will be made to the `NMSTX-187-langgraph-orchestrator-migration` branch. This expands the agent capabilities by adding Claude-Code as a new agent framework type alongside existing pydanticai and langgraph agents.

### Key Improvements in This Version
1. **Measurable Tests**: Every implementation step includes specific tests and verification using MCP tools
2. **No Breaking Changes**: All modifications use existing JSONB fields, no schema changes
3. **Semantic Commits**: Uses Claude itself to generate meaningful commit messages (no generic commits)
4. **Slack Communication**: Agents communicate via Slack channels, not direct API calls
5. **Workflow Examples**: Added PR reviewer, bug fixer, and general code task configurations
6. **MCP Tool Integration**: Comprehensive guidelines for using postgres, memory, slack, git, and linear tools throughout implementation
7. **Autonomous Operation**: Uses `--dangerously-skip-permissions` for uninterrupted workflow execution

## Architecture Overview

### Key Design Decisions

1. **Container Strategy**: One container per session, kept alive between turns for state persistence
2. **Volume-based Workspaces**: Each session gets a dedicated volume for file persistence
3. **Credential Mounting**: Host credentials mounted read-only at container start
4. **Git Integration**: Workspace volumes are git repos, commits extracted on completion
5. **Database Integration**: Full session/message tracking in PostgreSQL with JSON metadata

### Container Lifecycle Strategy

```
Session Start → Create Container → Mount Volumes → Keep Alive → Multiple Turns → Extract Commits → Stop Container
                                   ↓                                               ↑
                                   └─────────── Resume Session ────────────────────┘
```

**Key Points:**
- Containers stay alive during a session (not recreated per turn)
- Workspace volume persists all file edits
- On session completion: git commits are extracted before container stops
- Resume: Same container if alive, or new container with same volume

## Simplified Project Structure

```
src/agents/
├── pydanticai/                # Existing PydanticAI-based agents
├── langgraph/                 # Existing LangGraph orchestration agents
└── claude-code/               # New Claude CLI container-based agents
    ├── __init__.py
    ├── agent.py               # Main ClaudeCodeAgent class
    ├── docker/
    │   ├── Dockerfile         # Debian-based Claude container
    │   ├── docker-compose.yml # Development setup
    │   └── entrypoint.sh      # Container initialization script
    ├── container.py           # Docker container management
    ├── executor.py            # Claude CLI execution logic
    ├── models.py              # Request/Response schemas
    ├── workflows/             # Different claude-code agent configurations
│   ├── bug-fixer/
│   │   ├── prompt.md          # Bug fixing specialist prompt
│   │   ├── .mcp.json          # MCP server configuration
│   │   ├── allowed_tools.json # Tool permissions
│   │   ├── .env               # Environment variables (GITHUB_TOKEN, etc.)
│   │   └── .credentials.json  # Claude credentials
│   └── feature-dev/
│       └── ...
└── README.md                  # Documentation
```

This follows the existing agent pattern while supporting multiple workflow configurations.

## Persistence Architecture

### How Files Are Saved

1. **Workspace Volume**: Each session creates a dedicated Docker volume mounted at `/workspace`
2. **Am-Agents-Labs Repository**: Clone private repo into `/workspace/am-agents-labs`
   - Repository: `https://github.com/namastexlabs/am-agents-labs` (requires auth)
3. **Development Install**: Use existing docker-compose setup for installation
4. **File Edits**: Claude edits code directly (persisted in volume)
5. **Container Lifecycle**: Container runs until Claude CLI exits with JSON result, then:
   - Commits changes
   - Updates message table with results
   - Pushes to GitHub
   - Container terminates

### Container State Management

```python
# Container states and transitions
CONTAINER_CREATED → RUNNING → IDLE (between turns) → RUNNING → STOPPED
                     ↑                                    ↓
                     └──────── Resume Session ────────────┘
```

**Container Lifecycle:**
- Container starts when API request received
- Claude CLI runs with `--output-format json` and blocks until completion
- When Claude exits with final JSON result:
  - Parse JSON output for session_id and result
  - Store in messages table using existing schema
  - Commit and push changes
  - Container terminates immediately
- No idle state - container always terminates after Claude completes

## Implementation Tasks

### Task Group 1: Docker Foundation

#### 1.1 Docker Setup
- [ ] Create Dockerfile from Anthropic reference
- [ ] Add claude installation with --dangerously-skip-permissions support
- [ ] Set up volume mount points for credentials and workspace
- [ ] Configure docker-compose.yml for development
- [ ] Test basic container creation and Claude execution

#### 1.2 Container Management
- [ ] Implement `ContainerManager` class in `container.py`
- [ ] Add container lifecycle methods (create, start, stop, remove)
- [ ] Implement idle timeout mechanism
- [ ] Add container health checks
- [ ] Create volume management for workspaces

### Task Group 2: Core Agent Implementation

#### 2.1 Agent Structure
- [ ] Create `ClaudeCodeAgent` extending `AutomagikAgent`
  - **Test**: Agent class imports without errors
  - **Verify**: `isinstance(agent, AutomagikAgent)` returns True
- [ ] Implement agent registration in factory
  - **Test**: Factory.create_agent('claude-code') returns ClaudeCodeAgent instance
  - **Verify**: Use MCP postgres to confirm agent registered in agents table
- [ ] Add configuration for Docker settings
  - **Test**: Agent config includes docker_image, container_timeout fields
  - **Verify**: Config validation passes with required fields
- [ ] Create agent-specific dependencies
  - **Test**: Dependencies include container_manager, executor instances
  - **Verify**: All dependencies properly injected and accessible
- [ ] Add tool registration (if needed)
  - **Test**: Agent has access to configured tools from workflow
  - **Verify**: Tool calls execute successfully in test environment

#### 2.2 Execution Logic
- [ ] Create `ClaudeExecutor` class in `executor.py`
- [ ] Implement command building with all CLI parameters
- [ ] Add async subprocess execution within container
- [ ] Implement output streaming from container
- [ ] Add timeout and cancellation support

#### 2.3 Models and Schemas
- [ ] Define request/response models in `models.py`
- [ ] Add validation for all Claude parameters
- [ ] Create metadata schemas for database storage
- [ ] Add error response models
- [ ] Document all fields with examples

### Task Group 3: Session and Persistence

#### 3.1 Session Management
- [ ] Implement session creation with container assignment
  - **Test**: New session creates container and stores container_id
  - **Verify**: Use MCP postgres to query sessions.metadata->>'container_id'
- [ ] Add session-to-container mapping in database
  - **Test**: Session metadata contains container_id and volume_name
  - **Verify**: `docker ps` shows container with matching ID
- [ ] Create resume logic (check container state first)
  - **Test**: Resume uses existing container if running, creates new if stopped
  - **Verify**: Session history preserved across resume operations
- [ ] Add session cleanup on expiration
  - **Test**: Expired sessions remove containers and volumes
  - **Verify**: No orphaned containers after cleanup using `docker ps -a`
- [ ] Implement concurrent session limits
  - **Test**: Cannot exceed MAX_CONCURRENT_SESSIONS (configurable)
  - **Verify**: 429 error returned when limit reached

#### 3.2 Git Integration
- [ ] Initialize git repo in workspace volumes
- [ ] Configure git user for commits
- [ ] Implement commit extraction before container stop
- [ ] Add optional push to remote repository
- [ ] Handle merge conflicts on resume

#### 3.3 Database Integration
- [ ] Use existing session/message repositories (no new tables/fields)
  - **Test**: session_repo.create_session() stores metadata correctly
  - **Verify**: Use MCP postgres to query `SELECT metadata FROM sessions WHERE id = ?`
- [ ] Store container ID, volume name in sessions.metadata JSONB
  - **Test**: metadata->>'container_id' retrieves correct value
  - **Verify**: No schema changes, only JSONB content
- [ ] Track execution parameters in messages.context and raw_payload
  - **Test**: message_repo.create_message() with all claude data
  - **Verify**: Query messages and confirm all data preserved
- [ ] Create performance indexes only if needed (after load testing)
  - **Test**: Query performance with 1000+ sessions
  - **Verify**: Only add GIN indexes if queries > 100ms
- [ ] No migration scripts needed (using existing schema)
  - **Test**: All operations use existing columns
  - **Verify**: No ALTER TABLE statements required

### Task Group 4: API Integration

#### 4.1 Endpoint Implementation
- [ ] Add route handler in existing API structure
  - **Test**: Routes registered in FastAPI app.routes
  - **Verify**: `/docs` shows new endpoints with correct schemas
- [ ] Implement `/api/v1/agent/claude-code/{workflow_name}/run` endpoint (async)
  - **Test**: POST request returns 200 with run_id immediately
  - **Verify**: Use MCP postgres to confirm message created with status='pending'
- [ ] Create `/api/v1/agent/claude-code/run/{run_id}/status` endpoint
  - **Test**: Returns current status while running, full result when complete
  - **Verify**: Status transitions: pending → running → completed
- [ ] Implement background task processing for container execution
  - **Test**: Container runs asynchronously after API returns
  - **Verify**: Use MCP slack to monitor progress in designated channel
- [ ] Add proper async job queue for long-running containers
  - **Test**: Multiple concurrent runs execute without blocking
  - **Verify**: Queue metrics show proper task distribution

#### 4.2 Request Handling
- [ ] Parse all Claude CLI parameters from request
- [ ] Validate tool lists and MCP configs
- [ ] Handle file uploads for workspace initialization
- [ ] Support both sync and async responses
- [ ] Add request queuing for resource limits

### Task Group 5: Advanced Features

#### 5.1 Credential Management
- [ ] Mount ~/.claude/.credentials.json securely
- [ ] Add GitHub SSH key mounting
- [ ] Implement credential rotation
- [ ] Add audit logging for credential access
- [ ] Support multiple credential sets

#### 5.2 Agent Communication
- [ ] Store each run in database messages table
- [ ] Agents communicate via Slack threads
- [ ] Share context through agent memory system
- [ ] No direct agent-to-agent API calls
- [ ] Each agent run is independent

#### 5.3 Monitoring
- [ ] Add container resource monitoring
- [ ] Track execution times and costs
- [ ] Implement health check endpoint
- [ ] Add alerting for stuck containers
- [ ] Create debugging tools

## Technical Specifications

### Docker Configuration

```dockerfile
# Dockerfile - Based on project's existing Alpine setup
FROM python:3.11-alpine

# System dependencies (matching project's docker/Dockerfile)
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev libffi-dev \
    && apk add --no-cache postgresql-client curl bash libc6-compat git openssh-client \
    nodejs npm jq \
    && pip install --no-cache-dir uv

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# No additional Python packages needed - using Claude for commit generation

# Create workspace and claude user
RUN adduser -D claude
WORKDIR /workspace

# Install docker and docker-compose for running automagik-agents
RUN apk add --no-cache docker docker-compose

# Copy scripts
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER claude

ENTRYPOINT ["/entrypoint.sh"]
```

### API Schema

```python
class ClaudeCodeRunRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    max_turns: int = Field(default=30, ge=1, le=100)
    git_branch: str = Field(default="NMSTX-187-langgraph-orchestrator-migration", description="Branch to work on")
    timeout: Optional[int] = Field(default=3600, ge=60, le=7200)
    # Note: workflow_name comes from URL path
    
class ClaudeCodeRunResponse(BaseModel):
    """Initial response when run is started"""
    run_id: str
    status: Literal["pending", "running", "completed", "failed"]
    message: str = "Container deployment initiated"
    session_id: str
    started_at: datetime
    
class ClaudeCodeStatusResponse(BaseModel):
    """Status endpoint response"""
    run_id: str
    status: Literal["pending", "running", "completed", "failed"]
    session_id: str
    started_at: datetime
    updated_at: datetime
    container_id: Optional[str] = None
    execution_time: Optional[float] = None
    
    # Only populated when status is "completed" or "failed"
    result: Optional[str] = None
    exit_code: Optional[int] = None
    git_commits: List[str] = []
    git_sha_end: Optional[str] = None
    error: Optional[str] = None
    logs: Optional[str] = None
```

### Database Usage

Using existing PostgreSQL tables without any schema modifications:

**Sessions Table (existing columns):**
- `id` (uuid): Primary key
- `metadata` (jsonb): Store claude-code specific data
- `agent_id` (integer): Reference to agents table
- `user_id` (uuid): User who created the session

**Messages Table (existing columns):**
- `id` (uuid): Primary key
- `session_id` (uuid): Link to session
- `raw_payload` (jsonb): Store request/response data
- `context` (jsonb): Execution metadata
- `tool_calls` (jsonb): Claude's tool usage
- `role` (varchar): 'user' or 'assistant'

**Repository Usage:**
```python
from src.db.repository import session as session_repo
from src.db.repository import message as message_repo

# Create session with claude-code metadata
metadata = {
    "agent_type": "claude-code",
    "workflow_name": "bug-fixer",
    "container_id": "abc123...",
    "workspace_volume": "session-uuid-workspace",
    "git_branch": "fix/session-timeout",
    "claude_config": {
        "max_turns": 30,
        "skip_permissions": True,
        "allowed_tools": ["Read", "Write", "Bash"]
    }
}
session = session_repo.create_session(
    agent_id=agent_id,
    name=f"claude-code-{workflow_name}",
    metadata=metadata
)

# Store message with execution details
message_repo.create_message(
    session_id=session.id,
    role="assistant",
    text_content=claude_result,
    raw_payload={
        "request": {
            "message": user_message,
            "workflow": workflow_name
        },
        "response": {
            "claude_session_id": claude_session_id,
            "result": claude_result
        }
    },
    context={
        "execution": {
            "container_id": container_id,
            "exit_code": exit_code,
            "execution_time": elapsed_time,
            "git_commits": commit_shas
        }
    }
)
```

**Performance Optimization (Optional Migration):**
```sql
-- Only if query performance becomes an issue
-- Create GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_sessions_metadata_agent_type 
ON sessions USING GIN ((metadata->'agent_type'));

CREATE INDEX IF NOT EXISTS idx_messages_context_container 
ON messages USING GIN ((context->'execution'->'container_id'));
```

## MCP Tool Usage Guidelines

Throughout implementation, agents should actively use MCP tools to verify progress:

### Database Verification (mcp__postgres)
- After creating sessions: `SELECT id, metadata FROM sessions WHERE metadata->>'agent_type' = 'claude-code'`
- Check message storage: `SELECT id, raw_payload, context FROM messages WHERE session_id = ? ORDER BY created_at`
- Verify container tracking: `SELECT metadata->>'container_id' as container_id FROM sessions WHERE id = ?`
- Check execution details: `SELECT context->'execution' FROM messages WHERE session_id = ?`

### Memory System (mcp__agent-memory)
- Store implementation patterns: `add_memory(name="Pattern: Docker Container Lifecycle", ...)`
- Search for patterns: `search_memory_nodes(query="docker container management")`
- Track decisions: `add_memory(name="Decision: Commit Generation Method", ...)`

### Communication (mcp__slack)
- Post progress updates: `slack_post_message(channel_id="C...", text="Phase 1 complete")`
- Create threads for discussions: `slack_reply_to_thread(...)`
- Monitor agent runs: `slack_get_channel_history(channel_id="C...", limit=50)`

### Git Operations (mcp__git)
- Check implementation status: `git_status(repo_path="/root/prod/am-agents-labs")`
- Review changes: `git_diff_unstaged(repo_path="...")`
- Track commits: `git_log(repo_path="...", max_count=10)`

### Linear Integration (mcp__linear)
- Create implementation tasks: `linear_createIssue(title="Implement Docker container manager", ...)`
- Update progress: `linear_updateIssue(issueId="...", stateId="in_progress")`
- Add implementation notes: `linear_createComment(issueId="...", body="Test results: ...")`

## Implementation Strategy

### Initial Implementation

#### Phase 1: Proof of Concept
- Start with `bug-fixer` workflow as proof of concept
  - **Test**: Fix a simple typo in comments
  - **Verify**: Commit shows semantic message like "fix(docs): correct typo in auth.py"
- Focus on core functionality first
  - **Test**: Container lifecycle (create, run, commit, cleanup)
  - **Verify**: No resource leaks after 10 sequential runs
- Test with simple bug fix tasks
  - **Test**: Fix a linting error
  - **Test**: Add missing import statement
  - **Test**: Fix a failing unit test
- Iterate based on results
  - **Measure**: Time to fix vs manual approach
  - **Measure**: Success rate on different bug types
  - **Measure**: Resource usage (CPU, memory, disk)

#### Phase 2: Workflow Expansion
- Implement PR reviewer workflow
  - **Test**: Review a small PR with 5-10 file changes
  - **Verify**: Review posted to Linear issue as comment
- Implement general code task workflow
  - **Test**: Add a new API endpoint with tests
  - **Verify**: All tests pass, lint/format clean
- Performance optimization
  - **Test**: Handle 10 concurrent sessions
  - **Verify**: Average response time < 5s for status checks

### Key Implementation Details

1. **Async Container Execution**
   - API returns immediately with run_id after starting container
   - Container runs in background (can take 1+ hours)
   - Client polls status endpoint to check progress
   - When complete, status endpoint includes full results
   - No streaming needed - just polling

2. **Autonomous Mode Benefits**
   - Claude runs uninterrupted with `--dangerously-skip-permissions`
   - No permission prompts or manual confirmations needed
   - Ideal for CI/CD pipelines and automated workflows
   - Complete tasks like fixing lint errors without supervision
   - Enables true end-to-end automation

3. **Database Integration**
   - Use existing `sessions` and `messages` tables via repositories
   - Store workflow metadata in `sessions.metadata` JSONB
   - Store request/response in `messages.raw_payload` JSONB
   - No schema changes required - only use existing repository functions
   - Performance indexes only after proven need with load testing

4. **Docker-in-Docker**
   - Claude container needs Docker access to run automagik-agents
   - Mount Docker socket or use Docker-in-Docker (dind)
   - Security considerations for production

## Breaking Change Prevention

### Guidelines for Implementation
1. **No modifications to existing schemas** - Use JSONB metadata fields only
2. **Preserve existing APIs** - New endpoints only, no changes to existing ones
3. **Backward compatibility** - All changes must work with existing agents
4. **Test before merge** - Run full test suite before any PR
5. **Feature flags** - New features behind configuration flags initially

### Verification Steps
- Before any performance indexes: Test query performance first
- Before API changes: Run integration tests for all existing agents
- Before merging: Full regression test suite must pass
- After deployment: Monitor error rates and rollback if needed

### Required Tests Before Human Authorization
1. **Existing functionality**: All current tests must pass
2. **Integration tests**: Verify no impact on other agents
3. **Performance tests**: No degradation in response times
4. **Resource tests**: Memory/CPU usage within limits
5. **Security tests**: No new vulnerabilities introduced

## Risk Mitigation

### Security Risks
- **Container Isolation**: Environment already secured at infrastructure level
- **Credential Exposure**: Mount as read-only, use temporary credentials
- **Autonomous Mode**: Using --dangerously-skip-permissions for uninterrupted workflow

### Operational Risks
- **Resource Exhaustion**: Implement container limits, monitoring
- **Data Loss**: Regular volume backups, git push on completion
- **Service Disruption**: Graceful degradation, circuit breakers

### Technical Risks
- **Docker Dependency**: Provide fallback to direct execution
- **Performance**: Optimize container startup, reuse when possible
- **Complexity**: Comprehensive documentation, training

## Container Persistence Details

### Volume Structure
```
/workspace (Docker Volume: session-{uuid}-workspace)
├── am-agents-labs/            # Cloned private repository
│   ├── .git/                  # Git repository
│   ├── src/                   # Source code Claude edits
│   ├── tests/                 # Tests Claude can run/modify
│   ├── docker/                # Docker configuration
│   ├── .env                   # Configured from workflow .env
│   └── [all project files]    # Full am-agents-labs codebase
└── workflow/                  # Mounted workflow configuration
    ├── prompt.md              # Agent-specific prompt
    ├── .mcp.json             # MCP server configuration
    ├── allowed_tools.json    # Tool permissions
    ├── .env                  # Environment variables
    └── .credentials.json     # Claude credentials

/home/claude/
├── .claude/                   # Claude configuration directory
│   └── .credentials.json     # Symlink to /workspace/workflow/.credentials.json
└── .ssh/                     # SSH keys for git operations
```

### Workflow Folder Example - Bug Fixer

```
workflows/bug-fixer/
├── prompt.md               # Bug fixing specialist prompt
├── .mcp.json              # MCP servers configuration
├── allowed_tools.json     # ["Read", "Write", "Edit", "Bash", "Grep", ...]
├── .env                   # Environment configuration
│   # GITHUB_TOKEN=ghp_xxxxx
│   # AM_LABS_REPO=https://github.com/namastexlabs/am-agents-labs
│   # POSTGRES_HOST=host.docker.internal
│   # POSTGRES_PORT=5432
│   # POSTGRES_DB=automagik_agents
│   # AM_API_KEY=xxx
│   # OPENAI_API_KEY=sk-xxx
└── .credentials.json      # Claude API credentials
```

### Workflow Examples

#### PR Reviewer Workflow
```
workflows/pr-reviewer/
├── prompt.md               # Specialized for code review
│   # You are a senior code reviewer. Analyze pull requests for:
│   # - Code quality and best practices
│   # - Security vulnerabilities
│   # - Performance implications
│   # - Test coverage
│   # - Breaking changes
│   # Provide constructive feedback with specific suggestions.
├── .mcp.json
│   {
│     "servers": {
│       "git": { "command": "mcp-git", "args": ["--repo", "/workspace/am-agents-labs"] },
│       "linear": { "command": "mcp-linear", "env": { "LINEAR_API_KEY": "${LINEAR_API_KEY}" } },
│       "postgres": { "command": "mcp-postgres", "args": ["--connection-url", "${DATABASE_URL}"] }
│     }
│   }
├── allowed_tools.json
│   ["Read", "Write", "WebFetch", "git_diff", "git_log", "git_show", 
│    "linear_getIssueById", "linear_createComment", "postgres_query"]
├── review_template.md      # Output format for reviews
│   ## PR Review: {{pr_title}}
│   ### Summary
│   ### Code Quality
│   ### Security Considerations
│   ### Suggestions
│   ### Verdict: [APPROVE/REQUEST_CHANGES/COMMENT]
└── .env
    # GITHUB_TOKEN=ghp_xxx
    # LINEAR_API_KEY=lin_api_xxx
    # DATABASE_URL=postgresql://...
```

#### Bug Fixer Workflow
```
workflows/bug-fixer/
├── prompt.md
│   # You are a bug fixing specialist. When given a bug report:
│   # 1. Use MCP tools to understand the issue (postgres queries, memory search)
│   # 2. Locate the root cause using grep/read tools
│   # 3. Fix the issue with minimal changes
│   # 4. Add tests to prevent regression
│   # 5. Verify fix using existing test suite
├── .mcp.json
│   {
│     "servers": {
│       "postgres": { "command": "mcp-postgres", "args": ["--connection-url", "${DATABASE_URL}"] },
│       "agent-memory": { "command": "mcp-agent-memory", "args": ["--db-path", "/workspace/.memory.db"] }
│     }
│   }
├── allowed_tools.json
│   ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", 
│    "postgres_query", "agent-memory_search_memory_nodes", 
│    "agent-memory_add_memory", "TodoWrite", "TodoRead"]
└── .env
```

#### Code Task Workflow
```
workflows/code-task/
├── prompt.md
│   # You are a versatile software engineer. Follow these principles:
│   # - Search memory for established patterns before implementing
│   # - Use Linear for task tracking (create/update issues)
│   # - Write comprehensive tests for new features
│   # - Follow existing code conventions
│   # - Store successful patterns in memory for reuse
├── .mcp.json
│   {
│     "servers": {
│       "all": "enabled"  # Enable all available MCP servers
│     }
│   }
├── allowed_tools.json     # Configurable per task
├── task_config.json
│   {
│     "default_branch": "NMSTX-187-langgraph-orchestrator-migration",
│     "test_command": "pytest",
│     "lint_command": "ruff check --fix src/ && ruff format src/",
│     "memory_group_id": "code-patterns"
│   }
└── .env
```

### Database Usage

Using existing PostgreSQL schema without modifications. The claude-code agent stores all data in existing JSONB columns:

**Sessions Table:**
```json
{
  "metadata": {
    "agent_type": "claude-code",
    "workflow_name": "bug-fixer",
    "git_branch": "fix/session-timeout",
    "container_id": "abc123...",
    "volume_name": "session-uuid-workspace"
  }
}
```

**Messages Table:**
```json
{
  "raw_payload": {
    "request": {
      "message": "Fix the session timeout issue",
      "git_branch": "fix/session-timeout"
    },
    "response": {
      "claude_session_id": "uuid",
      "exit_code": 0,
      "git_commits": ["sha1", "sha2"]
    }
  },
  "context": {
    "execution_time": 45.2,
    "container_logs": "..."
  }
}
```

### Container Entrypoint Script

```bash
#!/bin/bash
# entrypoint.sh - Initialize container environment

# Load workflow configuration
WORKFLOW_DIR="/workspace/workflow"
source "$WORKFLOW_DIR/.env"

# Clone am-agents-labs repository (private, requires auth)
cd /workspace
git clone -b ${GIT_BRANCH:-NMSTX-187-langgraph-orchestrator-migration} "https://oauth2:${GITHUB_TOKEN}@github.com/namastexlabs/am-agents-labs.git" am-agents-labs
cd am-agents-labs
git config user.name "Claude Code Agent"
git config user.email "claude@automagik-agents.ai"

# Set up environment
cp "$WORKFLOW_DIR/.env" .env

# Start automagik-agents using docker-compose
docker-compose -f docker/docker-compose.yml up -d
sleep 20  # Wait for services to be ready

# Execute Claude with workflow configuration in autonomous mode
cd /workspace/am-agents-labs
claude \
  --dangerously-skip-permissions \
  --mcp-config "$WORKFLOW_DIR/.mcp.json" \
  --allowedTools "$(cat $WORKFLOW_DIR/allowed_tools.json | jq -r 'join(",")')" \
  --append-system-prompt "$(cat $WORKFLOW_DIR/prompt.md)" \
  --output-format json \
  "$@" > /tmp/claude-output.json

# Parse Claude output
CLAUDE_EXIT_CODE=$?
CLAUDE_SESSION_ID=$(jq -r '.session_id' /tmp/claude-output.json)
CLAUDE_RESULT=$(jq -r '.result' /tmp/claude-output.json)

# Generate commit message using Claude inside the container
git add -A

# Use Claude with --max-turns 1 to generate and apply commit
claude \
  --dangerously-skip-permissions \
  --max-turns 1 \
  --output-format json \
  --append-system-prompt "You are a git commit message generator. Analyze the staged changes using 'git diff --cached' and commit them with a semantic commit message following conventional commits format (type(scope): description). Use the Bash tool to run git diff, analyze the changes, then commit with an appropriate message." \
  "Generate a commit message for the staged changes and commit them" > /tmp/commit-result.json

# Extract result
COMMIT_EXIT_CODE=$?
COMMIT_RESULT=$(jq -r '.result' /tmp/commit-result.json)

# Push changes
git push origin ${GIT_BRANCH:-NMSTX-187-langgraph-orchestrator-migration}

# Store result in database (handled by agent.py)
echo "{\"session_id\": \"$CLAUDE_SESSION_ID\", \"result\": \"$CLAUDE_RESULT\", \"exit_code\": $CLAUDE_EXIT_CODE}"

# Cleanup
docker-compose -f docker/docker-compose.yml down
exit $CLAUDE_EXIT_CODE
```

## Success Criteria

1. **Functional Requirements**
   - All Claude CLI parameters supported
   - Session persistence across container restarts
   - Git commits extracted and attributed
   - Agent-to-agent communication working
   - API fully integrated

2. **Performance Requirements**
   - Container startup < 5 seconds
   - No more than 10% overhead vs direct execution
   - Support 50+ concurrent sessions
   - Stream output with < 100ms latency

3. **Security Requirements**
   - No credential leaks
   - Network isolation enforced
   - Audit trail complete
   - Resource limits enforced

4. **Operational Requirements**
   - 99.9% uptime
   - Automated health checks
   - Comprehensive monitoring
   - Easy debugging tools

## Commit Message Generation

### Claude-based Commit Message Generation

We use Claude itself to analyze changes and create semantic commits, leveraging its ability to understand code context and generate appropriate messages.

**Implementation:**
1. After task completion, stage all changes with `git add -A`
2. Run Claude with `--max-turns 1` and a specialized prompt
3. Claude uses the Bash tool to:
   - Run `git diff --cached` to see staged changes
   - Analyze the changes for type, scope, and impact
   - Execute `git commit -m "message"` with semantic format
4. Push changes to the remote repository

**Benefits:**
- No additional dependencies or scripts needed
- Claude understands the full context of changes
- Automatic semantic versioning compliance
- Single tool for both development and commits

**The Append System Prompt:**
```
You are a git commit message generator. Analyze the staged changes using 'git diff --cached' 
and commit them with a semantic commit message following conventional commits format 
(type(scope): description). Use the Bash tool to run git diff, analyze the changes, 
then commit with an appropriate message.
```

**Example outputs generated by Claude:**
- `fix(session): resolve timeout issue in agent controller`
- `feat(memory): add regex support to memory search tool`
- `test(langgraph): add integration tests for orchestrator`
- `refactor(claude-code): extract container management to separate module`
- `docs(api): update endpoint documentation for async operations`

**Key Point:** This approach is simpler and more integrated - Claude handles the entire commit process using its existing tools, no external scripts required.

## API Usage Examples

### Starting a Bug Fix Run
```bash
# 1. Start the run (returns immediately)
POST /api/v1/agent/claude-code/bug-fixer/run
{
    "message": "Fix the session timeout issue in agent controller",
    "git_branch": "fix/session-timeout",
    "max_turns": 50
}

Response:
{
    "run_id": "run_abc123",
    "status": "pending",
    "message": "Container deployment initiated",
    "session_id": "session_xyz789",
    "started_at": "2024-01-15T10:00:00Z"
}

# 2. Check status (poll this endpoint)
GET /api/v1/agent/claude-code/run/run_abc123/status

Response (while running):
{
    "run_id": "run_abc123",
    "status": "running",
    "session_id": "session_xyz789",
    "started_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:05:00Z",
    "container_id": "container_def456",
    "execution_time": 300.5
}

Response (when complete):
{
    "run_id": "run_abc123",
    "status": "completed",
    "session_id": "session_xyz789",
    "started_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "container_id": "container_def456",
    "execution_time": 3600.2,
    "result": "Successfully fixed session timeout issue",
    "exit_code": 0,
    "git_commits": ["sha1", "sha2"],
    "git_sha_end": "def456",
    "logs": "..."
}
```

## Implementation Order

Since we're using AI to implement, tasks can be parallelized:

**Parallel Track 1: Docker Infrastructure**
- Dockerfile and security setup
- Container management implementation
- Volume persistence testing

**Parallel Track 2: Agent Core**
- ClaudeCodeAgent class
- Executor implementation
- Models and schemas

**Parallel Track 3: Integration**
- Database schema updates
- API endpoint creation
- Session management

**Sequential: Final Integration**
- Connect all components
- End-to-end testing
- Documentation

## Next Steps

1. Review and approve this plan
2. Create new Linear project for Claude-Code Agent implementation
3. Create the folder structure in `NMSTX-187-langgraph-orchestrator-migration` branch
4. Start parallel implementation tracks
5. Set up development Docker environment
6. Begin implementation with AI assistance

## Linear Project Management

This implementation will be managed as follows:
- **New Linear Project**: Create a dedicated project for Claude-Code Agent implementation
- **Git Branch**: All commits go to `NMSTX-187-langgraph-orchestrator-migration` branch
- **Framework Integration**: Adding a third agent framework type (claude-code) alongside pydanticai and langgraph
- **Capabilities**: Providing containerized execution for long-running autonomous tasks
- **Orchestration**: Enabling true multi-framework agent orchestration capabilities

All work should be tracked in the new Linear project, with subtasks created for each major implementation component.


 --important, stop and call the human in case any tool call fails, it means your instructions or tools need adjustment before doing actual job. working properly now is MORE IMPORTANT THAN THE TASK ITSELF, IT SHOULD BE PAUSED, IF ANYTHING HAPPENS