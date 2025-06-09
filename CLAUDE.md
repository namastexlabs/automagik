# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automagik Agents is a production-ready AI agent framework built on Pydantic AI by Namastex Labs that provides:
- 🤖 Extensible agent system with template-based creation
- 💾 Persistent memory with PostgreSQL and optional Neo4j/Graphiti knowledge graphs
- 🔧 Production-ready FastAPI with authentication and health monitoring
- 🔗 Multi-LLM support (OpenAI, Gemini, Claude, Groq)
- 📦 Zero-config deployment via Docker or systemd
- 🛠️ Comprehensive CLI for agent management and interaction
- 🔌 MCP (Model Context Protocol) integration for tool discovery

## 🎯 Core Development Principles

### Primary Objectives
- Develop, maintain, and extend automagik-agents framework following established patterns
- Always **EXTEND** `AutomagikAgent`, never modify base classes
- Follow patterns from existing agents in `src/agents/pydanticai/`
- Use provided tools/infrastructure vs reinventing

### Critical Procedures

#### 1. **ALWAYS Search Memory First**
Before starting any task, search for established patterns and preferences:
```bash
# Search for task-specific patterns and preferences with correct function names
mcp__agent-memory__search_memory_nodes query="task keywords" entity="Procedure"
mcp__agent-memory__search_memory_nodes query="preferences" entity="Preference"
mcp__agent-memory__search_memory_facts query="dependencies relationships"

# Search for previous failures (Time Machine Learning)
mcp__agent-memory__search_memory_nodes query="epic [ID] failure" group_ids='["genie_learning"]' max_nodes=10
mcp__agent-memory__search_memory_nodes query="human feedback" group_ids='["genie_learning"]' max_nodes=5
```

#### 2. **Use Linear for Task Management**
Create Linear tasks for all development work and use Linear IDs in branch names and commits.

**Known Linear Configuration**:
```bash
# Team and Project IDs
TEAM_ID="2c6b21de-9db7-44ac-9666-9079ff5b9b84"
PROJECT_ID="dbb25a78-ffce-45ba-af9c-898b35255896"

# Issue States
TRIAGE="84b8b554-a562-4858-9802-0b834857c016"
TODO="c1c6cf41-7115-459b-bce9-024ab46ee0ba"
IN_PROGRESS="99291eb9-7768-4d3b-9778-d69d8de3f333"
IN_REVIEW="14df4fc4-5dff-497b-8b01-6cc3835c1e62"
DONE="1551da4c-03c1-4169-9690-8688f95f9e87"
```

#### 3. **Store Successful Patterns**
After implementing solutions, store them in memory for future reuse:
```bash
# Store with proper JSON escaping for structured data
mcp__agent-memory__add_memory name="Pattern: [Name]" episode_body="pattern details" source="text"
mcp__agent-memory__add_memory name="Architecture Decision: [Name]" episode_body="{\"decision\": \"[choice]\", \"rationale\": \"[why]\"}" source="json"
```

#### 4. **CRITICAL: Always Use UV Run**
This project uses UV as the package manager. **NEVER** use direct Python commands:

❌ **WRONG**:
```bash
python -m pytest tests/
pytest tests/
ruff check src/
python script.py
```

✅ **CORRECT**:
```bash
uv run pytest tests/
uv run ruff check src/
uv run python script.py
uv run ruff format src/
```

## 🛠️ Common Development Commands

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/agents/test_simple_agent.py -v

# Run tests with specific marker
uv run pytest -m "not integration" tests/

# Run single test function
uv run pytest tests/agents/test_simple_agent.py::test_agent_creation -v

# Run tests in parallel
uv run pytest tests/ -n auto

# Generate test coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
# Lint code (with auto-fix)
uv run ruff check src/ --fix

# Format code
uv run ruff format src/

# Check without fixing
uv run ruff check src/

# Type checking (if mypy is configured)
uv run mypy src/
```

### Running the Application
```bash
# Start development server with hot reload
make dev
# OR
AM_FORCE_DEV_ENV=1 uv run python -m src --reload

# Run without hot reload
uv run python -m src

# Run specific scripts
uv run python scripts/test_slack_integration.py

# Alternative startup modes
make install          # Auto-detects best installation mode
make install-dev      # Install development environment (local Python + venv)
make install-docker   # Docker development stack
make install-prod     # Production Docker stack
make install-service  # Systemd service installation
```

### Database Management
```bash
# Initialize database and apply all migrations
automagik agents db init

# Force reinitialize (drops all tables and recreates with migrations)
automagik agents db init --force

# Clear database (caution! deletes all data but keeps schema)
automagik agents db clear --yes

# Note: Migration system automatically applies SQL files from src/db/migrations/
```

### Agent Management
```bash
# Create new agent from template
automagik agents create -n my_agent -t simple
# OR full command: automagik agents agent create -n my_agent -t simple

# Chat with an agent
automagik agents chat -a simple
# OR full command: automagik agents agent chat -a simple

# Run agent with specific message
automagik agents run -a simple -m "Hello, how are you?"
# OR full command: automagik agents agent run -a simple -m "Hello, how are you?"

# Note: No 'list' command exists for agents

# Start development server (with debug output)
automagik agents dev

# Start production server
automagik agents start
```

### MCP Server Management
```bash
# List available MCP servers
automagik agents mcp list

# Start MCP server
automagik agents mcp start <server-name>

# Check MCP server status
uv run python scripts/check_mcp_status.py
```

## 🧠 Memory System Protocol

### Memory Organization Structure
The system uses a graph-based memory with organized group IDs:
```
collective_brain (via group_ids):
├── "genie_patterns"      # Reusable development patterns
├── "genie_decisions"     # Architectural choices with rationale  
├── "genie_procedures"    # How-to guides and workflows
├── "genie_learning"      # Time machine learning from failures
└── "genie_context"       # Current epic and project state
```

### Memory Search Patterns (MANDATORY Before Any Task)
```python
# 1. Search for existing patterns FIRST
patterns = mcp__agent-memory__search_memory_nodes(
    query="[relevant keywords] pattern procedure",
    entity="Procedure",
    max_nodes=10
)

# 2. Check for architectural decisions
decisions = mcp__agent-memory__search_memory_nodes(
    query="architecture decision [domain]",
    group_ids=["genie_decisions"],
    max_nodes=5
)

# 3. Look for previous failures (Time Machine Learning)
failures = mcp__agent-memory__search_memory_nodes(
    query="epic [ID] failure [component]",
    group_ids=["genie_learning"],
    max_nodes=10
)

# 4. Find human feedback
feedback = mcp__agent-memory__search_memory_nodes(
    query="human feedback [feature]",
    group_ids=["genie_learning"],
    max_nodes=5
)

# 5. Load current epic context and facts
context = mcp__agent-memory__search_memory_nodes(
    query="epic [ID] context",
    group_ids=["genie_context"],
    max_nodes=5
)
facts = mcp__agent-memory__search_memory_facts(
    query="epic [ID]",
    group_ids=["genie_context"],
    max_facts=10
)
```

### Memory Storage Patterns
```python
# Store architectural decisions with rich context
mcp__agent-memory__add_memory(
    name="Architecture Decision: [title]",
    episode_body='{"decision": "[choice]", "rationale": "[why]", "alternatives": ["opt1", "opt2"], "production_impact": "[impact]", "rollback_plan": "[plan]", "epic_id": "[epic_id]", "confidence": "high|medium|low"}',
    source="json",
    source_description="architectural decision for [component] in epic [epic_id]",
    group_id="genie_decisions"
)

# Store reusable patterns with implementation context
mcp__agent-memory__add_memory(
    name="Architecture Pattern: [name]",
    episode_body="Pattern Name: [name]\n\nContext: [when to use]\n\nProblem: [what problem this solves]\n\nSolution: [detailed approach]\n\nExample:\n```python\n[code]\n```\n\nBenefits:\n- [benefit 1]\n- [benefit 2]\n\nTradeoffs:\n- [tradeoff 1]\n\nSuccess Metrics:\n- [how to measure if working]",
    source="text",
    group_id="genie_patterns"
)

# Store procedures for future architects/developers
mcp__agent-memory__add_memory(
    name="Procedure: [Architecture Design for X]",
    episode_body="Step-by-step procedure:\n1. [Step 1 with specific actions]\n2. [Step 2 with validation criteria]\n\nChecklist:\n- [ ] [Verification item 1]\n- [ ] [Verification item 2]\n\nCommon Pitfalls:\n- [Pitfall 1 and how to avoid]\n\nRequired Artifacts:\n- [Artifact 1]",
    source="text",
    group_id="genie_procedures"
)

# Store learning from failures (Time Machine)
mcp__agent-memory__add_memory(
    name="Learning: Epic [epic_id] Attempt [number]",
    episode_body='{"epic_id": "[id]", "attempt": 1, "failure_type": "scope_creep", "root_cause": "[analysis]", "prevention": "[strategy]", "human_feedback": "[feedback]"}',
    source="json",
    group_id="genie_learning"
)

# Update epic progress
mcp__agent-memory__add_memory(
    name="Epic Progress: [epic_id] - [Phase]",
    episode_body='{"epic_id": "[id]", "phase": "architecture", "status": "completed", "decisions_made": ["uuid1"], "next_workflow": "implement", "risks": ["risk1"]}',
    source="json",
    group_id="genie_context"
)
```

## 📋 Linear Integration

### Epic Creation Pattern (with Component Breakdown)
```python
# Create epic with full component task breakdown
epic = mcp__linear__linear_createIssue(
    title="📋 Epic: [Feature Name]",
    description="""
## 🎯 Epic Overview
[Description]

## 📋 Components
- Core: Agent implementation
- API: FastAPI endpoints
- Tools: External integrations
- Tests: Quality assurance

## 🔄 Coordination Strategy
Progressive integration with isolated development
    """,
    teamId="2c6b21de-9db7-44ac-9666-9079ff5b9b84",
    projectId="dbb25a78-ffce-45ba-af9c-898b35255896",
    priority=2,
    labelIds=["b7099189-1c48-4bc6-b329-2f75223e3dd1"]  # Feature label
)

# Create component tasks
core_task = mcp__linear__linear_createIssue(
    title="🔸 Core: [Feature] - Agent Implementation",
    parentId=epic.id,
    labelIds=["b7099189-1c48-4bc6-b329-2f75223e3dd1", "500151c3-202d-4e32-80b8-82f97a3ffd0f"]  # Feature + Agent
)
```

### Linear Task Updates
```python
# Update task status
mcp__linear__linear_updateIssue(
    id="NMSTX-123",
    stateId="99291eb9-7768-4d3b-9778-d69d8de3f333",  # In Progress
    description="Updated: [progress details]"
)

# Add labels
mcp__linear__linear_addIssueLabel(
    issueId="NMSTX-123", 
    labelId="d551b383-7342-437a-8171-7cea73ac02fe"  # Urgent
)
```

### Known Linear Label IDs
```python
# Type Labels (choose one)
FEATURE = "b7099189-1c48-4bc6-b329-2f75223e3dd1"
BUG = "8b4eb347-3278-4844-9a9a-bbe724fb5684"
IMPROVEMENT = "78180790-d131-4210-ba0b-117620f345d3"

# Component Labels
AGENT = "500151c3-202d-4e32-80b8-82f97a3ffd0f"
TOOL = "537dac03-bbd9-4367-93cd-daaa291db627"
API = "f7f8e07e-24ad-43cc-b8e9-46e1cf785ef8"
MEMORY = "a494ab47-6a08-4677-ae42-1dfc522d3af3"
TESTING = "70383b36-310f-4ce0-9595-5fec6193c1fb"

# Priority Labels
URGENT = "d551b383-7342-437a-8171-7cea73ac02fe"
RESEARCH = "f7bf2f0f-1a55-4a3d-bc61-783ebb3b3f6e"
```

## 🏗️ Architecture & Patterns

### Framework-Agnostic Architecture

The agent system is built with a framework-agnostic architecture supporting multiple AI frameworks:

```
src/agents/
├── models/                    # Core framework code
│   ├── automagik_agent.py    # Base agent class with framework abstraction
│   ├── ai_frameworks/        # AI framework adapters
│   │   ├── base.py          # Framework interface
│   │   ├── pydantic_ai.py   # PydanticAI implementation
│   │   └── future_frameworks.py  # LangChain, Agno, etc.
│   └── agent_factory.py     # Multi-framework agent discovery
├── pydanticai/               # PydanticAI agents (current production)
├── agno/                     # Agno framework agents (future)
├── claude_code/              # Claude Code workflow agent
└── channels/                 # Channel handlers (WhatsApp, Discord, etc.)
    ├── base.py              # Channel interface
    ├── evolution.py         # WhatsApp/Evolution handler
    └── registry.py          # Auto-detection system
```

### Agent Structure
All agents must follow this structure:
```
src/agents/{framework}/agent_name/
├── __init__.py          # Factory function: create_agent()
├── agent.py             # Main class extending AutomagikAgent
├── prompts/
│   ├── __init__.py
│   └── prompt.py        # AGENT_PROMPT constant
├── specialized/         # Optional: Domain-specific tools
└── models.py           # Optional: Agent-specific models
```

### Creating New Agents

1. **Use the CLI** (recommended):
```bash
automagik agents create -n new_agent -t simple
```

2. **Framework-specific creation**:
```python
# For PydanticAI agents (default)
from src.agents.models.agent_factory import AgentFactory
agent = AgentFactory.create_agent("simple", framework="pydanticai")

# For future frameworks
agent = AgentFactory.create_agent("simple", framework="agno")
default_agent = AgentFactory.get_default_agent("pydanticai")
```

3. **Manual creation**:
```python
# agent.py
from src.agents.models.automagik_agent import AutomagikAgent
from .prompts.prompt import AGENT_PROMPT

class NewAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config, framework_type="pydanticai")
        self._code_prompt_text = AGENT_PROMPT
        
        # Set dependencies using the convenience method
        self.dependencies = self.create_default_dependencies()
        
        # Register default tools (now handled automatically by framework)
        self.tool_registry.register_default_tools(self.context)
```

### Tool Registration
```python
# Register default tools (handled automatically by framework)
self.tool_registry.register_default_tools(self.context)

# Register custom tool
@self.agent.tool
async def my_custom_tool(ctx: RunContext, param: str) -> str:
    """Tool description"""
    return f"Result: {param}"
```

### Channel Handler System

The framework includes a channel handler system for omnichannel support:

```python
# Channel handlers are automatically detected and used
from src.channels.registry import get_channel_handler

# WhatsApp/Evolution example
handler = await get_channel_handler(channel_payload=whatsapp_payload)
# Returns EvolutionHandler with WhatsApp-specific tools and processing

# Handlers provide:
# - preprocess_in(): Extract channel-specific context 
# - postprocess_out(): Format responses for channel limits
# - get_tools(): Channel-specific tools (send_text, send_media, etc.)
# - validate_payload(): Auto-detect channel type
```

**Supported Channels**:
- ✅ **WhatsApp** (via Evolution API) - Full support with media, groups, contacts
- 🔄 **Discord** (future) - Planned channel handler
- 🔄 **Telegram** (future) - Planned channel handler

**Creating Channel Handlers**:
```python
# src/channels/my_channel.py
from src.channels.base import ChannelHandler

class MyChannelHandler(ChannelHandler):
    async def preprocess_in(self, input_text, channel_payload, context):
        # Extract channel-specific user info, metadata
        return {"input_text": input_text, "context": context}
    
    async def postprocess_out(self, response, context):
        # Format for channel (length limits, special formatting)
        return response
    
    def get_tools(self):
        # Return channel-specific tools
        return [my_channel_send_tool, my_channel_delete_tool]
```

### Memory Integration
Prompts support `{{variable}}` substitution:
```python
AGENT_PROMPT = """
You are {{agent_name}}, a helpful assistant.
User preferences: {{user_preferences}}
Recent context: {{recent_messages}}
"""
```

## 📁 Project Structure

```
am-agents-labs/
├── src/
│   ├── agents/
│   │   ├── models/           # Framework-agnostic core
│   │   │   ├── automagik_agent.py      # Base agent class
│   │   │   ├── ai_frameworks/          # AI framework adapters
│   │   │   │   ├── base.py            # Framework interface
│   │   │   │   ├── pydantic_ai.py     # PydanticAI adapter
│   │   │   │   └── future.py          # Future frameworks
│   │   │   ├── agent_factory.py       # Multi-framework discovery
│   │   │   └── state_manager.py       # State management
│   │   ├── pydanticai/       # PydanticAI agents (production)
│   │   ├── agno/             # Agno framework (future)
│   │   ├── claude_code/      # Claude Code workflows
│   │   ├── common/           # Shared utilities
│   │   └── simple/           # Deprecated (shim to pydanticai)
│   ├── channels/             # Channel handlers
│   │   ├── base.py          # Channel interface
│   │   ├── evolution.py     # WhatsApp/Evolution
│   │   └── registry.py      # Auto-detection
│   ├── api/                  # FastAPI routes
│   ├── db/                   # Database layer
│   ├── tools/                # Tool implementations
│   ├── mcp/                  # MCP integration
│   └── cli/                  # CLI commands
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
└── docs/                     # Documentation
```

## 🔍 Debugging Tips

1. **Enable debug logging**:
```bash
export AM_LOG_LEVEL=DEBUG
uv run python -m src
```

2. **Check registered tools**:
```python
logger.debug(f"Tools: {self.tool_registry.list_tools()}")
```

3. **Test prompt rendering**:
```python
rendered = self._render_prompt({"key": "value"})
logger.debug(f"Prompt: {rendered}")
```

4. **Database queries**:
```bash
# Enable SQL logging
export AM_LOG_SQL=true
```

## ⚡ Quick Recipes

### Run Tests for Modified Files Only
```bash
# Using git to find changed files
uv run pytest $(git diff --name-only HEAD | grep test_ | grep .py$)
```

### Profile Performance
```bash
# Run with profiling
uv run python -m cProfile -o profile.stats -m src

# Analyze results
uv run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Clean Development Environment
```bash
# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Clean test artifacts  
rm -rf .pytest_cache htmlcov .coverage

# Reset UV cache (if needed)
uv cache clean
```

### Monitor Application Status
```bash
# PM2-style status table
make status

# Quick one-line status
make status-quick

# Check health endpoints
make health

# View logs with auto-detection
make logs

# Follow logs in real-time
make logs-f

# Show specific number of log lines
make logs N=200
```

## 🔄 Git Workflow & Best Practices

### Commit Message Format
```bash
# Feature commits
feat(NMSTX-123): implement Discord agent with memory integration

# Bug fixes
fix(NMSTX-456): resolve authentication issue in API endpoints

# Component-specific commits (for parallel development)
feat(NMSTX-789-core): implement base Discord agent class
feat(NMSTX-789-api): add Discord webhook endpoints
feat(NMSTX-789-tools): integrate Discord API client
```

### Git Operations with MCP
```python
# Check status
status = mcp__git__git_status(repo_path="/root/prod/am-agents-labs")

# Stage files
mcp__git__git_add(
    repo_path="/root/prod/am-agents-labs",
    files=["src/agents/pydanticai/discord/", "tests/agents/test_discord.py"]
)

# Commit with Linear reference
mcp__git__git_commit(
    repo_path="/root/prod/am-agents-labs",
    message="feat(NMSTX-123): implement Discord agent base functionality"
)

# Check differences
diff = mcp__git__git_diff_staged(repo_path="/root/prod/am-agents-labs")
```

## 🤖 Claude Code Workflow System

### Workflow Phases & Boundaries
Each Claude Code workflow has specific responsibilities and tool access:

| Workflow | Purpose | Key Tools | Boundaries |
|----------|---------|-----------|------------|
| **ARCHITECT** | System design, technical decisions | Read, Write, Linear, Slack, Memory | Design only, no implementation |
| **IMPLEMENT** | Feature coding based on architecture | Task, Bash, Edit, Git, Memory | Stay within src/agents/*, use approved design |
| **TEST** | Comprehensive testing | Task, Bash, Read, Write, Git | Test only, don't modify business logic |
| **REVIEW** | Code review, quality checks | Read, Git, Linear, Memory | Review only, no code changes |
| **FIX** | Bug investigation and fixes | Task, Bash, Grep, Edit, Git | Minimal fixes, surgical changes |
| **REFACTOR** | Code improvement | Task, Read, Edit, Git | No breaking changes, maintain contracts |
| **DOCUMENT** | Documentation updates | Read, Write, Edit, Memory | Documentation only |
| **PR** | Pull request preparation | Task, Bash, Git, Linear | Prepare merge, no feature changes |

### Workflow Execution Pattern
```python
# Before ANY workflow task:
# 1. Create todo list
TodoWrite(todos=[
    {"id": "1", "content": "Load context and check for failures", "status": "pending", "priority": "high"},
    {"id": "2", "content": "Read architecture documents", "status": "pending", "priority": "high"},
    {"id": "3", "content": "Check Slack thread for updates", "status": "pending", "priority": "high"},
    {"id": "4", "content": "Plan implementation approach", "status": "pending", "priority": "high"},
    {"id": "5", "content": "Implement/test/review", "status": "pending", "priority": "high"},
    {"id": "6", "content": "Commit changes", "status": "pending", "priority": "high"},
    {"id": "7", "content": "Update memory with patterns", "status": "pending", "priority": "high"},
    {"id": "8", "content": "Generate run report", "status": "pending", "priority": "high"}
])

# 2. Check for previous failures (Time Machine)
failures = mcp__agent-memory__search_memory_nodes(
    query="epic [epic_id] failure [workflow]",
    group_ids=["genie_learning"],
    max_nodes=10
)

# 3. Load architecture/context
decisions = mcp__agent-memory__search_memory_nodes(
    query="Architecture Decision epic [epic_id]",
    group_ids=["genie_decisions"],
    max_nodes=10
)

# 4. Read design documents (for IMPLEMENT)
Read("ARCHITECTURE.md")
Read("DECISIONS.md")
Read("TECHNICAL_DECISIONS.md")
```

### Standardized Run Report (MANDATORY at workflow end)
```markdown
## [WORKFLOW] RUN REPORT
**Epic**: [epic_id]
**Run ID**: [run_id]
**Session ID**: [claude_session_id]
**Status**: COMPLETED|BLOCKED|NEEDS_HUMAN

**Work Summary**: 
- [Key accomplishment 1]
- [Key accomplishment 2]

**Memory Entries Created**:
Decisions (genie_decisions):
- "Architecture Decision: [exact title]"

Patterns (genie_patterns):
- "Pattern: [exact name]"

Learning (genie_learning):
- "Learning: [failure analysis]"

**Files Modified**: [list]
**Git Commits**: [list]
**Breaking Changes**: YES|NO (if yes, list with approval status)
**Human Approvals Needed**: [list any pending]
**Next Workflow Ready**: YES|NO
**System Issues Encountered**: [tool failures, report via WhatsApp if critical]
```

## 🔌 Slack Integration for Coordination

### Thread-Based Communication (Epic-Level)
```python
# Find or create epic thread
thread_search = mcp__agent-memory__search_memory_nodes(
    query="Epic Thread [EPIC_ID]",
    group_ids=["genie_context"],
    max_nodes=1
)

# Create new thread if not found
if not thread_found:
    response = mcp__slack__slack_post_message(
        channel_id="C08UF878N3Z",
        text="🏗️ **EPIC STARTED**: [EPIC_ID] - [Title]\n\nWorkflow: ARCHITECT\nStatus: INITIALIZING"
    )
    # Store thread_ts in memory
    mcp__agent-memory__add_memory(
        name="Epic Thread: [EPIC_ID]",
        episode_body=f"epic_id=[EPIC_ID] thread_ts={response.ts} channel_id=C08UF878N3Z",
        source="text",
        group_id="genie_context"
    )

# Post workflow updates in thread
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts="[stored_thread_ts]",
    text="📊 **ARCHITECT UPDATE**\n\nProgress: Architecture design complete\nDecisions Made:\n- Docker per-session strategy\n- Volume persistence approach\n\nMemory Updated: 2 decisions, 1 pattern"
)

# Request human approval
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts="[thread_ts]",
    text="🚨 **HUMAN NEEDED**: Breaking Change Detected\n\nChange: API contract modification\nImpact: Existing clients need update\nRecommendation: Version the endpoint\n\nPlease reply in thread with decision."
)

# Check thread for human messages
replies = mcp__slack__slack_get_thread_replies(
    channel_id="C08UF878N3Z",
    thread_ts="[thread_ts]"
)
# Parse for human messages (non-bot users)
```

## 🚨 Production Safety & Breaking Changes

### Automatic Breaking Change Detection
These patterns trigger mandatory human approval:
```python
breaking_change_patterns = {
    "database_schema": [
        "ALTER TABLE.*DROP COLUMN",
        "ALTER TABLE.*CHANGE COLUMN.*TYPE",
        "DROP TABLE", "TRUNCATE TABLE"
    ],
    "api_contracts": [
        "Remove.*endpoint", "Change.*response.*schema",
        "Modify.*authentication", "Remove.*parameter"
    ],
    "dependencies": [
        "uv add.*[^\\d]\\d+\\.",  # Major version changes
        "uv remove"               # Package removal
    ],
    "core_architecture": [
        "class.*Agent.*:",        # Base agent changes
        "src/core/", "src/api/v1/"  # Core module changes
    ]
}
```

### Human Escalation Triggers
Use these prefixes for immediate human attention:
- `HUMAN NEEDED:` - Requires approval before proceeding
- `BREAKING CHANGE:` - Production impact detected
- `BLOCKER:` - Cannot proceed without clarification
- `SECURITY CONCERN:` - Security-sensitive changes
- `PRODUCTION RISK:` - May affect live clients

## 🔄 Failure Patterns & Recovery (Time Machine)

### Common Failure Patterns to Check
```python
# Before starting work, check for these failure types:
failure_patterns = {
    "scope_creep": {
        "indicators": ["Modified files outside boundaries", "Added unrelated features"],
        "prevention": "Stay within workflow boundaries, check allowed paths"
    },
    "integration_issues": {
        "indicators": ["Test failures", "Import errors", "API mismatches"],
        "prevention": "Validate interfaces early, test integrations"
    },
    "memory_failures": {
        "indicators": ["Memory search errors", "Missing context"],
        "prevention": "Verify memory access early, have fallback strategies"
    }
}
```

### Recovery from Failures
When previous attempts failed:
1. Search for failure analysis: `mcp__agent-memory__search_memory_nodes(query="epic [ID] failure", group_ids=["genie_learning"])`
2. Read human feedback carefully
3. Apply prevention strategies
4. Document what you're doing differently

## 🚀 Workflow-Specific Guidelines

### ARCHITECT Workflow
- Create design documents (ARCHITECTURE.md, DECISIONS.md)
- Store all major decisions in memory
- Flag breaking changes for human approval
- Never write implementation code

### IMPLEMENT Workflow
- Read architecture documents first
- Stay within src/agents/* boundaries
- Commit regularly with clear messages
- Store successful patterns

### TEST Workflow
- Create comprehensive test suites
- Don't modify business logic
- Report coverage metrics
- Document test strategies

## 🚨 Critical Reminders

1. **Always use `uv run`** - The project uses UV for dependency management
2. **Never modify base classes** - Always extend `AutomagikAgent`
3. **Follow existing patterns** - Check similar agents before implementing
4. **Search memory first** - Before any task, search for existing patterns
5. **Use Linear for tasks** - Create tasks and reference them in commits
6. **Store successful patterns** - Help future development by storing what works
7. **Check for failures** - Learn from previous attempts using Time Machine
8. **Respect workflow boundaries** - Each workflow has specific responsibilities
9. **Use thread-based Slack** - All epic communication in dedicated threads
10. **Report system issues** - Use WhatsApp for critical tool failures

## 📚 Additional Resources

- Main documentation: `/docs/`
- Architecture details: `/ARCHITECTURE.MD`
- API documentation: `http://localhost:8881/api/v1/docs` (when running)
- Agent examples: `/src/agents/pydanticai/`
- Cursor rules: `/.cursor/rules/` (additional development guidelines)

## 🔧 Environment Variables

Key environment variables to configure:
```bash
# LLM Provider Keys (at least one required)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...

# Application Configuration
AM_PORT=8881                    # API server port
AM_LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)
AM_LOG_SQL=false               # Enable SQL query logging
AM_FORCE_DEV_ENV=1             # Force development environment

# Database Configuration
DATABASE_TYPE=sqlite            # Database type: "sqlite" (default) or "postgresql"

# SQLite Configuration (default)
SQLITE_DATABASE_PATH=./data/automagik_agents.db

# PostgreSQL Configuration (optional)
DATABASE_URL=postgresql://user:pass@localhost/automagik
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=automagik
POSTGRES_PASSWORD=password
POSTGRES_DB=automagik
POSTGRES_POOL_MIN=10
POSTGRES_POOL_MAX=25

# Optional: Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## 🎭 Parallel Development Architecture

The project uses a revolutionary 5-agent parallel development system:

| Agent | Role | Worktree | MCP Port | Memory Prefix |
|-------|------|----------|----------|---------------|
| **Alpha** | Orchestrator | main | 5010 | [P-EPIC] |
| **Beta** | Core/Agent Dev | core_agent | 5011 | [P-CORE] |
| **Delta** | API Dev | api_endpoints | 5012 | [P-API] |
| **Epsilon** | Tools/Integrations | tool_integrations | 5013 | [P-TOOLS] |
| **Gamma** | Testing/Quality | testing_quality | 5014 | [P-TESTS] |

### Coordination Protocol
- Morning sync: Status and blockers
- Integration checkpoints: Before merging work
- Memory sharing: Prefix-based search patterns
- Interface contracts: Stored in shared memory

## 🏃 Quick Start Guide

### Initial Setup
```bash
# Clone and install
git clone <repo>
cd am-agents-labs
make install  # Installs with uv in development mode

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
automagik agents db init

# Start development server
make dev  # Runs with hot reload
```

### Common Workflows

#### Creating a New Agent
```bash
# Using CLI (recommended)
automagik agents create -n my_agent -t simple

# Test the agent
automagik agents chat -a my_agent
```

#### Running Tests
```bash
# All tests
uv run pytest tests/ -v

# Specific component tests
uv run pytest tests/agents/test_my_agent.py -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

#### Docker Development
```bash
# Start full stack
make docker

# Production stack
make prod

# View logs
make logs FOLLOW=1
```

## 🔐 Security & Production Considerations

1. **Never commit secrets** - Use environment variables
2. **Database migrations** - Always test in development first
3. **Breaking changes** - Require human approval via Slack
4. **Container costs** - Be aware that epic runs can cost $50-100
5. **Memory limits** - Monitor PostgreSQL and Neo4j usage

## 🐛 Common Issues & Solutions

### UV Package Manager Issues
```bash
# If uv is not found
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear UV cache if corrupted
uv cache clean
```

### Database Connection Errors
```bash
# Check PostgreSQL status
make status

# Clear database (CAUTION: deletes all data)
automagik agents db clear
```

### Memory Search Failures
```bash
# Verify MCP server is running
uv run python scripts/check_mcp_status.py

# Check agent-memory connection
automagik agents mcp list
```

## 📊 Performance Optimization

1. **Enable SQL logging for debugging**:
   ```bash
   export AM_LOG_SQL=true
   ```

2. **Profile slow operations**:
   ```bash
   uv run python -m cProfile -o profile.stats -m src
   ```

3. **Monitor container resources**:
   ```bash
   docker stats
   ```

## 🎯 Development Best Practices

1. **Component Isolation**: Each agent works on their specific domain
2. **Interface-First**: Define contracts before implementation  
3. **Memory Documentation**: Store all decisions and patterns
4. **Test Coverage**: Maintain >80% coverage for new code
5. **Progressive Integration**: Merge small, working increments

## 🚦 Status Commands

```bash
# Beautiful PM2-style status
make status

# Check all services
make health

# View colorized logs
make logs N=100 FOLLOW=1

# View all available make commands
make help
```