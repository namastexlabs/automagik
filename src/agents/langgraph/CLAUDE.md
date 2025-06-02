# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## LangGraph Orchestrator for Multi-Agent Coordination

This directory contains the LangGraph-based orchestration system for coordinating multiple Claude Code agents working on complex epics. The system implements a supervisor pattern with state management, rollback capabilities, and human-in-the-loop coordination.

## Architecture Overview

### Core Orchestration Components

1. **LangGraph Orchestrator** (`shared/orchestrator.py`)
   - Main orchestration engine using LangGraph StateGraph
   - Implements supervisor pattern with intelligent routing
   - Manages state persistence and checkpointing
   - Handles rollback and error recovery

2. **Supervisor Nodes** (`shared/supervisor_nodes.py`)
   - Intelligent routing based on MCP tool context
   - Monitors Slack, Linear, and Git for real-time decisions
   - Human-in-the-loop coordination with WhatsApp alerts
   - Automatic stall detection and intervention

3. **CLI Node** (`shared/cli_node.py`)
   - Executes Claude Code agents via subprocess
   - Streams output with real-time monitoring
   - Manages Claude session persistence
   - Process kill switch for emergency stops

### Agent Implementations

Each agent specializes in specific aspects of development:

- **Alpha**: Epic orchestrator - breaks down tasks and coordinates team
- **Beta**: Core implementation specialist  
- **Gamma**: Quality assurance and testing
- **Delta**: API development and integration
- **Epsilon**: Tools and external integrations
- **Genie**: Main orchestrator for complex workflows

### State Management

The system uses `OrchestrationState` TypedDict for comprehensive state tracking:
- Session and process identifiers
- Git snapshot tracking for rollback
- Agent handoffs and routing decisions
- Slack/Linear integration state
- Human feedback tracking

## Development Commands

### Running Tests

```bash
# Run specific LangGraph orchestration tests
pytest tests/agents/langgraph/test_orchestrator.py -v

# Run supervisor node tests
pytest tests/agents/langgraph/test_supervisor.py -v

# Run integration tests with mock MCP
pytest tests/agents/langgraph/ -m integration -v
```

### Starting the Orchestrator

```python
from src.agents.langgraph.shared.orchestrator import LangGraphOrchestrator

# Initialize orchestrator
orchestrator = LangGraphOrchestrator()

# Execute orchestration
result = await orchestrator.execute_orchestration(
    session_id=uuid.uuid4(),
    agent_name="genie",
    task_message="Implement user authentication system",
    orchestration_config={
        "target_agents": ["alpha", "beta", "gamma"],
        "max_rounds": 3,
        "enable_rollback": True,
        "slack_channel_id": "C08UF878N3Z",
        "linear_project_id": "your-project-id"
    }
)
```

## Key Workflows

### 1. Epic Orchestration Flow
```
User Request → Genie → Alpha (task breakdown) → Beta/Delta/Epsilon (parallel work) → Gamma (testing) → Completion
```

### 2. Supervisor Decision Flow
```
Slack Monitor → Progress Monitor → Supervisor → Route to Agent/Wait/Rollback
```

### 3. Human-in-the-Loop
- Supervisor monitors for stalls (>30 min no progress)
- Checks Slack for human feedback
- Sends WhatsApp alerts for urgent decisions
- Waits for human input when needed

## MCP Tool Integration

The supervisor uses MCP tools for intelligent context gathering:

### Available MCP Servers
- `slack`: Monitor threads, post updates
- `linear`: Check task status, update progress
- `git`: Status, log, rollback operations
- `agent-memory`: Store/retrieve patterns
- `send_whatsapp_message`: Urgent alerts

### Tool Usage in Routing
```python
# Supervisor checks Linear before routing
linear_tasks = await execute_mcp_tool("mcp__linear__linear_searchIssues", {
    "teamId": "team-id",
    "states": ["Todo", "In Progress"]
})

# Post Slack update when switching agents
await execute_mcp_tool("mcp__slack__slack_post_message", {
    "channel_id": "C08UF878N3Z",
    "thread_ts": thread_ts,
    "text": f"Routing to {next_agent}: {reason}"
})
```

## State Store and Messaging

### State Persistence
- Uses PostgreSQL for orchestration session storage
- Tracks all state changes and agent handoffs
- Enables recovery from failures

### Group Chat Messaging
- Agents communicate via group chat sessions
- Messages stored with orchestration context
- Supervisor monitors chat for coordination

## Process Management

### Claude Process Monitoring
- Tracks PID of running Claude processes
- Kill switch for emergency stops
- Automatic cleanup on completion/failure

### Git Integration
- Automatic snapshots before agent execution
- Rollback capability to any snapshot
- Tracks changes across workspace

## Configuration

### Orchestration Config Options
```python
{
    "target_agents": ["alpha", "beta", "gamma"],  # Agents to coordinate
    "max_rounds": 3,                              # Max orchestration rounds
    "enable_rollback": True,                       # Enable git rollback
    "process_monitoring": {
        "check_interval": 30,                      # Process check interval
        "shutdown_timeout": 10                     # Graceful shutdown timeout
    },
    "slack_channel_id": "C08UF878N3Z",           # Slack channel for updates
    "slack_thread_ts": "1234567890.123456",      # Specific thread to monitor
    "linear_project_id": "project-uuid",          # Linear project ID
    "recursion_limit": 50                         # LangGraph recursion limit
}
```

## Error Handling and Recovery

### Rollback Mechanism
1. Git snapshot taken before each agent run
2. On failure, supervisor can initiate rollback
3. Workspace restored to previous state
4. Agent retries with rollback context

### Error States
- `CLIExecutionError`: Agent execution failed
- `GitOperationError`: Git operations failed  
- Process monitoring detects crashes
- Supervisor handles gracefully

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock MCP tools and external dependencies
- Verify state transitions

### Integration Tests
- Test full orchestration flows
- Use mock Claude processes
- Verify supervisor routing logic

### Ping-Pong Test Mode
Special test mode for verifying agent handoffs:
```
genie → alpha → beta → gamma → delta → epsilon → genie (repeat)
```

## Best Practices

1. **Always use orchestration for multi-agent workflows** - Don't run agents independently
2. **Monitor Slack threads** - Human feedback is critical for success
3. **Enable rollback for risky operations** - Git snapshots prevent data loss
4. **Use appropriate recursion limits** - Prevent infinite loops
5. **Check Linear task status** - Ensure work aligns with project tracking

## Common Issues and Solutions

### Issue: Agent process hangs
**Solution**: Use kill switch via supervisor
```python
state["kill_requested"] = True
state["active_process_pid"] = pid_to_kill
```

### Issue: Orchestration gets stuck
**Solution**: Check Slack monitoring and stall detection
- Supervisor will alert after 30 min of no progress
- Human can intervene via Slack

### Issue: Git conflicts after rollback
**Solution**: Supervisor includes rollback context
- Next agent receives information about failed attempt
- Can resolve conflicts intelligently

## Future Enhancements

1. **Dynamic agent selection** - ML-based routing decisions
2. **Parallel execution** - Run independent agents simultaneously  
3. **Advanced checkpointing** - Resume from any workflow state
4. **Performance metrics** - Track orchestration efficiency