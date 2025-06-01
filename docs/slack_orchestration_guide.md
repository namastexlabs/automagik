# Slack-Integrated Agent Orchestration Guide

## Overview

The automagik-agents orchestration system now supports Slack as the primary communication channel for multi-agent coordination. This allows both AI agents and human team members to collaborate in real-time through a shared Slack channel.

## Architecture

### Components

1. **Slack Channel Adapter** (`src/agents/langgraph/shared/slack_messenger.py`)
   - Manages Slack API communication
   - Creates orchestration threads
   - Handles message routing

2. **Port Manager** (`src/agents/langgraph/shared/port_manager.py`)
   - Allocates unique ports for each agent server
   - Manages environment configuration
   - Prevents port conflicts

3. **Enhanced Messaging** (`src/agents/langgraph/shared/messaging_slack.py`)
   - Integrates Slack with existing database messaging
   - Provides bidirectional sync
   - Maintains message history

4. **Agent Server Manager** (`scripts/start_agent_servers.py`)
   - Starts multiple agent servers
   - Configures Slack integration
   - Monitors agent health

## Setup

### Prerequisites

1. Slack workspace with bot token configured
2. Docker installed (for Slack MCP server)
3. Automagik-agents environment set up

### Configuration

The Slack integration uses these environment variables (already configured in `/root/workspace/.env`):

```bash
SLACK_BOT_TOKEN=xoxb-5623053499716-8993096493953-Fc50mQbITECgtUQDWJK3CbSW
SLACK_TEAM_ID=T05JB1KEPM2
SLACK_CHANNEL_IDS=C08UF878N3Z
```

### Starting the Slack MCP Server

The Slack MCP server must be running for the integration to work:

```bash
docker run -d --name mcp-slack \
  -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
  -e SLACK_TEAM_ID=$SLACK_TEAM_ID \
  -e SLACK_CHANNEL_IDS=$SLACK_CHANNEL_IDS \
  mcp/slack
```

## Usage

### Starting Agent Servers

1. **Start all agents with Slack integration:**
   ```bash
   cd /root/prod/am-agents-labs
   python scripts/start_agent_servers.py --epic-name "User Authentication" --epic-id "NMSTX-127"
   ```

2. **Start specific agents:**
   ```bash
   python scripts/start_agent_servers.py alpha beta delta --epic-name "API Development" --epic-id "NMSTX-128"
   ```

3. **Start without Slack (fallback mode):**
   ```bash
   python scripts/start_agent_servers.py --no-slack
   ```

4. **Check agent status:**
   ```bash
   python scripts/start_agent_servers.py --status
   ```

### Agent Communication in Slack

Each agent can:
- Send messages to the team channel
- Mention specific agents with @mentions
- Post status updates
- Ask questions that humans can answer
- Share code snippets and results

### Message Types

1. **Task Assignment**
   ```
   @beta Please implement the User model with email validation and bcrypt password hashing
   ```

2. **Status Update**
   ```
   📊 Status: Completed API endpoint design, starting implementation
   ```

3. **Question**
   ```
   @channel Should we use JWT or session-based authentication?
   ```

4. **Coordination**
   ```
   @delta I've finished the User model, it's ready for your API endpoints
   ```

## Port Allocation

Each agent runs on a unique port:

| Agent | Default Port | Role |
|-------|-------------|------|
| Orchestrator | 8881 | Main orchestration |
| Alpha | 8882 | Task coordinator |
| Beta | 8883 | Core builder |
| Delta | 8884 | API builder |
| Epsilon | 8885 | Tool builder |
| Gamma | 8886 | Quality engineer |

Ports are automatically allocated and managed by the PortManager.

## Integration with LangGraph Orchestration

The Slack integration enhances the existing LangGraph orchestration by:

1. **Transparent Communication**: All agent interactions visible in Slack
2. **Human Oversight**: Team members can guide and correct agents
3. **Persistent History**: Slack threads provide audit trail
4. **Real-time Collaboration**: Agents can coordinate synchronously

### Orchestration Flow

1. **Initialization**
   - Create Slack thread for the orchestration session
   - Post epic details and agent roster
   - Verify all agents are online

2. **Execution**
   - Agents communicate via Slack mentions
   - Status updates posted regularly
   - Questions directed to team or specific agents

3. **Completion**
   - Summary posted to Slack thread
   - Results and metrics shared
   - Thread preserved for reference

## Troubleshooting

### Common Issues

1. **Slack MCP server not running**
   ```bash
   docker ps | grep mcp-slack
   # If not running, start it:
   docker start mcp-slack
   ```

2. **Port conflicts**
   ```bash
   # Check port allocations
   cat /root/prod/am-agents-labs/.agent_ports.json
   
   # Reset port allocations
   rm /root/prod/am-agents-labs/.agent_ports.json
   ```

3. **Agent not receiving Slack messages**
   - Verify agent name matches Slack mentions
   - Check Slack thread timestamp in agent env
   - Ensure MCP server is connected

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export AM_LOG_LEVEL=DEBUG
python scripts/start_agent_servers.py --epic-name "Debug Test" --epic-id "TEST-001"
```

## Best Practices

1. **Clear Communication**
   - Use @mentions for directed messages
   - Post regular status updates
   - Ask questions early and clearly

2. **Error Handling**
   - Agents should report errors to Slack immediately
   - Include error details and context
   - Suggest solutions when possible

3. **Human Integration**
   - Monitor Slack channel during orchestration
   - Provide guidance when agents ask questions
   - Correct course when needed

4. **Performance**
   - Batch related messages when possible
   - Use threads for detailed discussions
   - Keep main channel focused on coordination

## Example Orchestration Session

```python
# 1. Start orchestration with Slack
from src.agents.langgraph.shared.messaging_slack import SlackOrchestrationMessenger

# Create orchestration session
session_id = uuid.uuid4()
thread_ts = await SlackOrchestrationMessenger.create_slack_orchestration(
    orchestration_session_id=session_id,
    agent_ids=[1, 2, 3, 4, 5],
    agent_names=["alpha", "beta", "delta", "epsilon", "gamma"],
    epic_name="User Authentication System",
    epic_id="NMSTX-127"
)

# 2. Agents communicate via Slack-enabled messengers
messenger = SlackOrchestrationMessenger.get_slack_enabled_messenger(
    session_id=session_id,
    agent_id=1,
    agent_name="alpha",
    slack_thread_ts=thread_ts
)

# Send message to team
await messenger.send_message_async(
    message="Starting user authentication implementation. Beta, please begin with the User model.",
    target_agent_name="beta",
    message_type="task"
)

# 3. Complete orchestration with summary
await SlackOrchestrationMessenger.complete_orchestration_with_slack(
    session_id=session_id,
    slack_thread_ts=thread_ts,
    summary={
        "status": "completed",
        "duration": "4 hours",
        "results": {
            "beta": {"success": True, "summary": "User model implemented"},
            "delta": {"success": True, "summary": "API endpoints created"},
            # ...
        }
    }
)
```

## Future Enhancements

1. **Slack Slash Commands**: `/orchestrate epic-name` to start orchestration
2. **Rich Message Formatting**: Code blocks, buttons, and interactive elements
3. **Workflow Automation**: Slack workflows for common orchestration patterns
4. **Analytics Dashboard**: Slack app for orchestration metrics
5. **Voice Integration**: Slack Huddles for real-time agent coordination

## Conclusion

The Slack integration transforms agent orchestration from a black-box process to a transparent, collaborative workflow where AI agents and humans work together seamlessly. This approach provides better oversight, faster issue resolution, and improved outcomes for complex development tasks.