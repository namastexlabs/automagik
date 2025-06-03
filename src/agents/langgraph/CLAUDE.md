# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## LangGraph Orchestrator - Genie Implementation

This directory contains the Genie orchestrator implementation using LangGraph. Genie coordinates Claude Code workflow containers to execute complex development epics with time machine (checkpointing/rollback) and human-in-the-loop capabilities.

## Architecture Overview

### System Context
Genie is part of a larger system where:
- **Claude Code Agent** (`src/agents/claude_code/`) runs workflow containers (architect, implement, test, etc.)
- **Genie Orchestrator** (this directory) coordinates these containers using LangGraph
- **Workflows** execute in Docker containers with specific tools and prompts
- **Communication** happens via Slack threads and shared memory (agent-memory MCP)

### Core Components

1. **LangGraph Orchestrator** (`shared/orchestrator.py`)
   - StateGraph implementation with checkpointing
   - Controls workflow container execution sequence
   - Manages state persistence and rollback
   - Integrates with Claude Code agent for container execution

2. **CLI Node** (`shared/cli_node.py`)
   - Executes Claude Code agent API calls
   - Monitors container execution status
   - Extracts results and git commits
   - Handles container lifecycle events

3. **State Management** (`shared/state_store.py`)
   - PostgreSQL-backed orchestration state
   - Tracks workflow progression
   - Stores container execution history
   - Enables recovery from failures

4. **Git Manager** (`shared/git_manager.py`)
   - Creates snapshots before workflow execution
   - Manages rollback branches
   - Tracks changes across containers
   - Enables time travel to previous states

5. **Process Manager** (`shared/process_manager.py`)
   - Monitors running containers
   - Implements kill switches
   - Tracks resource usage
   - Manages cleanup operations

## Development Commands

### Installation
```bash
# Install LangGraph and dependencies
cd /root/workspace/am-agents-labs
source .venv/bin/activate
uv add langgraph langchain-core langgraph-checkpoint-postgres

# Install development dependencies
uv add --dev pytest pytest-asyncio pytest-mock
```

### Running Tests
```bash
# Run all LangGraph tests
pytest tests/agents/langgraph/ -v

# Run specific test categories
pytest tests/agents/langgraph/test_orchestrator.py -v
pytest tests/agents/langgraph/test_cli_node.py -v
pytest tests/agents/langgraph/test_state_management.py -v

# Run with coverage
pytest tests/agents/langgraph/ --cov=src.agents.langgraph --cov-report=term-missing
```

### Local Development
```bash
# Start required services (PostgreSQL, Neo4j)
docker-compose up -d postgres neo4j

# Run orchestration locally
python -m src.agents.langgraph.genie.agent \
    --epic "Implement new feature" \
    --workflows "architect,implement,test"
```

## Implementation Guide

### Current State
The orchestrator structure exists but requires implementation of:
1. LangGraph StateGraph with proper state schema
2. Integration with Claude Code container execution
3. Checkpointing and rollback mechanisms
4. Human-in-the-loop interrupts
5. MCP tool integration for communication

### Key Integration Points

#### 1. Claude Code Container Execution
```python
# Genie calls Claude Code API to run workflow containers
POST /api/v1/agent/claude-code/{workflow}/run
{
    "message": "Task description",
    "session_id": "epic-session-id",
    "config": {
        "max_turns": 30,
        "git_branch": "genie/epic-id/workflow-name"
    }
}
```

#### 2. State Schema
```python
class OrchestrationState(TypedDict):
    # Core identifiers
    epic_id: str
    session_id: str
    thread_id: str
    
    # Workflow tracking
    current_workflow: str
    completed_workflows: List[str]
    workflow_results: Dict[str, Any]
    
    # Container execution
    active_container_id: Optional[str]
    container_history: Annotated[List[Dict], add]
    
    # Git state
    git_snapshots: Dict[str, str]  # workflow -> commit_sha
    rollback_points: List[Dict]
    
    # Human interaction
    human_feedback: Optional[str]
    waiting_for_human: bool
    
    # Messages and communication
    messages: Annotated[List[Dict], add]
    slack_thread_ts: Optional[str]
```

#### 3. Workflow Definitions
Available workflows from Claude Code implementation:
- **architect**: System design and planning
- **implement**: Feature implementation
- **test**: Testing and validation
- **review**: Code review
- **fix**: Bug fixing
- **refactor**: Code improvement
- **document**: Documentation
- **pr**: Pull request preparation

#### 4. MCP Tool Usage
```python
# Check for previous failures
await mcp__agent_memory__search_memory_nodes(
    query=f"epic {epic_id} failure",
    group_ids=["genie_learning"],
    max_nodes=5
)

# Post Slack updates
await mcp__slack__slack_post_message(
    channel_id="C08UF878N3Z",
    text=f"Starting {workflow} for epic {epic_id}"
)

# Update Linear tracking
await mcp__linear__linear_updateIssue(
    issueId="NMSTX-XXX",
    description=f"Workflow {workflow} completed"
)
```

## Implementation Patterns

### 1. Basic Graph Structure
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

# Define the graph
workflow = StateGraph(OrchestrationState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("architect", execute_architect_workflow)
workflow.add_node("implement", execute_implement_workflow)
workflow.add_node("test", execute_test_workflow)
workflow.add_node("human_review", human_review_node)

# Add edges
workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    route_to_workflow,
    {
        "architect": "architect",
        "implement": "implement",
        "test": "test",
        "human": "human_review",
        "end": END
    }
)

# Compile with checkpointer
checkpointer = PostgresSaver(connection_string=DATABASE_URL)
app = workflow.compile(checkpointer=checkpointer)
```

### 2. Workflow Execution Node
```python
async def execute_architect_workflow(state: OrchestrationState) -> Dict:
    """Execute architect workflow container via Claude Code API."""
    # Take git snapshot
    snapshot = await git_manager.create_snapshot(state["epic_id"])
    
    # Call Claude Code API
    result = await claude_code_client.run_workflow(
        workflow="architect",
        message=state["current_task"],
        session_id=state["session_id"],
        config={
            "max_turns": 30,
            "git_branch": f"genie/{state['epic_id']}/architect"
        }
    )
    
    # Update state
    return {
        "completed_workflows": [*state["completed_workflows"], "architect"],
        "workflow_results": {**state["workflow_results"], "architect": result},
        "git_snapshots": {**state["git_snapshots"], "architect": snapshot},
        "messages": [{"role": "architect", "content": result["summary"]}]
    }
```

### 3. Human-in-the-Loop Pattern
```python
from langgraph.prebuilt import interrupt

async def human_review_node(state: OrchestrationState) -> Dict:
    """Wait for human input via Slack."""
    # Post to Slack
    await mcp__slack__slack_post_message(
        channel_id=state["slack_channel_id"],
        thread_ts=state["slack_thread_ts"],
        text="🚨 Human review needed for epic"
    )
    
    # Interrupt and wait
    human_input = interrupt("Waiting for human decision")
    
    # Process feedback
    return {
        "human_feedback": human_input,
        "waiting_for_human": False,
        "messages": [{"role": "human", "content": human_input}]
    }
```

### 4. Rollback Implementation
```python
async def rollback_to_checkpoint(state: OrchestrationState, checkpoint_id: str) -> Dict:
    """Rollback to a previous git state."""
    # Get rollback point
    rollback_point = next(
        (p for p in state["rollback_points"] if p["id"] == checkpoint_id),
        None
    )
    
    if rollback_point:
        # Perform git rollback
        await git_manager.rollback_to_commit(rollback_point["commit_sha"])
        
        # Store learning
        await mcp__agent_memory__add_memory(
            name=f"Rollback: Epic {state['epic_id']}",
            episode_body=f"Rolled back from {state['current_workflow']} to {rollback_point['workflow']}",
            group_id="genie_learning"
        )
        
        # Update state
        return {
            "current_workflow": rollback_point["workflow"],
            "messages": [{"role": "system", "content": f"Rolled back to {rollback_point['workflow']}"}]
        }
    
    return {}
```

## Testing Strategy

### Unit Tests
```python
# Test state transitions
async def test_workflow_progression():
    state = OrchestrationState(
        epic_id="test-epic",
        current_workflow="architect",
        completed_workflows=[]
    )
    
    # Execute workflow
    result = await execute_architect_workflow(state)
    
    # Verify state update
    assert "architect" in result["completed_workflows"]
    assert "architect" in result["workflow_results"]
```

### Integration Tests
```python
# Test full orchestration flow
async def test_epic_orchestration():
    # Initialize graph
    app = create_orchestration_graph()
    
    # Run epic
    config = {"configurable": {"thread_id": "test-thread"}}
    result = await app.ainvoke(
        {
            "epic_id": "test-epic",
            "workflows": ["architect", "implement", "test"]
        },
        config
    )
    
    # Verify completion
    assert len(result["completed_workflows"]) == 3
```

## Common Patterns

### 1. Checking Previous Attempts
```python
# Before starting any workflow
previous_failures = await mcp__agent_memory__search_memory_nodes(
    query=f"epic {epic_id} failure {workflow}",
    group_ids=["genie_learning"]
)

if previous_failures:
    # Enhance prompt with learning
    enhanced_message = f"{original_message}\n\nPrevious attempt failed: {previous_failures[0]['summary']}"
```

### 2. Workflow Communication
```python
# Post workflow handoff
await mcp__slack__slack_post_message(
    channel_id=channel_id,
    thread_ts=thread_ts,
    text=f"✅ {current_workflow} complete. Starting {next_workflow}"
)
```

### 3. Cost Tracking
```python
# Track container costs
total_cost = sum(
    result.get("cost_usd", 0) 
    for result in state["workflow_results"].values()
)

if total_cost > COST_LIMIT:
    # Trigger human review
    return "human_review"
```

## Next Steps

1. **Implement Core StateGraph**: Create the main orchestration graph with proper state management
2. **Integrate Claude Code API**: Connect to existing Claude Code endpoints for container execution
3. **Add Checkpointing**: Implement PostgreSQL-based checkpointing for persistence
4. **Human-in-the-Loop**: Add interrupt points for human decisions
5. **Testing**: Create comprehensive test suite for orchestration flows

## References

- Claude Code Implementation: `src/agents/claude_code/`
- LangGraph Docs: https://github.com/langchain-ai/langgraph
- MCP Tools: Available via `mcp__` prefix in tool calls
- Database Schema: Uses existing sessions/messages tables with JSONB metadata