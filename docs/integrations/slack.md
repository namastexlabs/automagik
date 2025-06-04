# Slack Integration Guide

## Overview

The Automagik Agents framework includes comprehensive Slack integration that enables AI agents to collaborate with humans through Slack channels. This integration supports both LangGraph orchestration and MCP (Model Context Protocol) based communication.

## 🏗️ Architecture Components

### 1. MCP Slack Integration
- **Real-time communication** via MCP slack tools
- **Thread-based orchestration** for organized conversations  
- **Emoji reactions** for status updates
- **Team member lookup** and notifications

### 2. LangGraph Slack Adapter
- **SlackOrchestrationMessenger**: Creates and manages orchestration threads
- **SlackAgentAdapter**: Per-agent Slack interface with @mentions
- **Port Management**: Unique port allocation for agent servers
- **Bidirectional sync**: Database and Slack message synchronization

## 🔧 Setup & Configuration

### Prerequisites

1. **Slack Workspace** with bot token configured
2. **Docker** installed (for Slack MCP server)
3. **Automagik Agents** environment configured

### Environment Variables

Configure these variables in your `.env` file:

```bash
# Required Slack configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_TEAM_ID=T05JB1KEPM2
SLACK_CHANNEL_IDS=C08UF878N3Z

# Optional MCP configuration
MCP_SLACK_ENABLED=true
```

### Starting Slack Integration

#### Option 1: MCP Slack Server (Recommended)
```bash
# Start the Slack MCP server
automagik agents mcp start slack

# Verify MCP server status
uv run python scripts/check_mcp_status.py
```

#### Option 2: LangGraph Slack Orchestration
```bash
# Start multiple agent servers with Slack integration
uv run python scripts/start_agent_servers.py

# Monitor agent health
make status
```

## 🤖 Agent Communication Patterns

### MCP Slack Tools Available

All agents have access to these MCP tools:

#### Communication Tools
- `mcp__slack__slack_post_message` - Post new messages to channels
- `mcp__slack__slack_reply_to_thread` - Reply to existing threads
- `mcp__slack__slack_add_reaction` - Add emoji reactions

#### Monitoring Tools
- `mcp__slack__slack_get_channel_history` - Get recent channel messages
- `mcp__slack__slack_get_thread_replies` - Get all replies in a thread
- `mcp__slack__slack_list_channels` - List available channels

#### Team Tools
- `mcp__slack__slack_get_users` - Get team member information
- `mcp__slack__slack_get_user_profile` - Get detailed user profiles

### Communication Examples

#### Creating an Orchestration Thread
```python
# Alpha orchestrator starts a new epic
response = mcp__slack__slack_post_message(
    channel_id="C08UF878N3Z",
    text="🎯 **NEW EPIC STARTED**: NMSTX-456 - Discord Agent Implementation\n\nTeam: @beta @gamma @delta\nStatus: Initializing\nEstimated Duration: 4 hours"
)
thread_ts = response.ts
```

#### Agent Status Updates
```python
# Beta posts implementation progress
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z", 
    thread_ts=thread_ts,
    text="🔧 **Beta Update**: Core agent structure complete\n✅ Base class implemented\n✅ Dependencies configured\n⏳ Working on prompt integration"
)

# Add reaction for quick status
mcp__slack__slack_add_reaction(
    channel_id="C08UF878N3Z",
    timestamp=message_ts,
    reaction="white_check_mark"
)
```

#### Human Collaboration
```python
# Check for human messages in thread
replies = mcp__slack__slack_get_thread_replies(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts
)

# Filter for human messages (non-bot users)
human_messages = [
    msg for msg in replies 
    if not msg.get('bot_id') and msg.get('user') != 'U05JB1KHW8L'
]
```

## 🎯 Agent-Specific Prompts

### Alpha (Orchestrator)
**File**: `src/agents/langgraph/alpha/prompts/mcp_slack_prompt.py`

Alpha creates orchestration threads and coordinates the team:
- Posts epic initialization messages
- Assigns tasks to team members with @mentions
- Tracks overall progress and blockers
- Escalates issues requiring human input

### Beta (Core/Agent Development)
- Posts implementation progress updates
- Requests code reviews from team
- Reports integration issues
- Shares component completion status

### Gamma (Testing/Quality)
- Reports test results and coverage
- Identifies integration failures
- Posts quality metrics
- Requests additional test scenarios

### Delta (API/Endpoints)
- Updates on API endpoint development
- Reports interface changes
- Requests documentation reviews
- Shares API testing results

### Epsilon (Tools/Integrations)
- Updates on external tool integrations
- Reports connection issues
- Shares tool testing results
- Requests configuration assistance

## 🔄 Workflow Integration

### Epic Orchestration Flow

1. **Initialization**: Alpha creates thread with epic details
2. **Task Distribution**: Alpha assigns work with @mentions
3. **Progress Updates**: Each agent posts status updates
4. **Human Check-ins**: Team can review and provide feedback
5. **Integration Points**: Agents coordinate handoffs
6. **Completion**: Alpha posts final summary

### Message Types

#### Status Updates
Use consistent emoji prefixes:
- 🎯 Epic/Project level updates
- 🔧 Implementation progress
- ✅ Completed tasks
- ⏳ In progress items
- 🚨 Blockers or issues
- 📊 Metrics and reports

#### @Mentions for Coordination
- `@alpha` - For orchestration decisions
- `@beta` - For core implementation questions
- `@gamma` - For testing and quality issues
- `@delta` - For API/endpoint concerns
- `@epsilon` - For tool integration help

## 🛠️ Advanced Features

### Port Management System
The LangGraph integration includes automatic port allocation:

```python
from src.agents.langgraph.shared.port_manager import PortManager

# Allocate unique ports for agent servers
port_manager = PortManager()
beta_port = port_manager.allocate_port("beta")
gamma_port = port_manager.allocate_port("gamma")
```

### Bidirectional Message Sync
Messages are synchronized between Slack and the database:

```python
from src.agents.langgraph.shared.messaging_slack import SlackEnabledAgentMessenger

messenger = SlackEnabledAgentMessenger(
    session_id=session_id,
    slack_thread_ts=thread_ts
)
# Posts to both Slack and database
await messenger.post_message("Implementation complete")
```

### Health Monitoring
Monitor agent health through Slack:

```bash
# Check agent server status
make status

# View logs with Slack integration
make logs-f
```

## 🔍 Troubleshooting

### Common Issues

#### MCP Server Connection
```bash
# Check MCP server status
automagik agents mcp list

# Restart if needed
automagik agents mcp start slack
```

#### Missing Slack Messages
```bash
# Verify environment variables
echo $SLACK_BOT_TOKEN | head -c 10

# Check channel permissions
uv run python scripts/test_slack_integration.py
```

#### Port Conflicts
```bash
# Clear port allocations
rm -f .agent_ports.json

# Restart agent servers
uv run python scripts/start_agent_servers.py
```

### Debug Mode
Enable detailed Slack logging:

```bash
export AM_LOG_LEVEL=DEBUG
export SLACK_DEBUG=true
uv run python -m src
```

## 📊 Best Practices

### Thread Organization
- One thread per epic for focused discussion
- Use consistent naming: "🎯 **EPIC**: NMSTX-XXX - Description"
- Pin important threads for easy access

### Message Formatting
- Use emoji prefixes for message types
- Include relevant Linear issue IDs
- Use code blocks for technical details
- @mention relevant team members

### Human Collaboration
- Check for human messages before major decisions
- Escalate breaking changes via Slack
- Provide context in status updates
- Use reactions for quick acknowledgments

### Performance Considerations
- Batch related messages when possible
- Use reactions instead of messages for simple confirmations
- Monitor Slack API rate limits
- Archive completed epic threads

## 🔗 Related Documentation

- **[MCP Integration](./mcp.md)** - Complete MCP setup guide
- **[Architecture](../architecture/overview.md)** - System architecture overview
- **[API Documentation](../development/api.md)** - REST API endpoints
- **[Agent Overview](../development/agents-overview.md)** - Agent system details

## 📝 Implementation Files

### Core Implementation
- `src/agents/langgraph/shared/slack_messenger.py` - Slack communication adapter
- `src/agents/langgraph/shared/port_manager.py` - Port allocation system
- `src/agents/langgraph/shared/messaging_slack.py` - Message synchronization
- `scripts/start_agent_servers.py` - Agent server manager

### Agent Prompts
- `src/agents/langgraph/alpha/prompts/mcp_slack_prompt.py` - Alpha orchestrator
- `src/agents/langgraph/*/prompts/slack_prompt.py` - Agent-specific prompts

### Testing & Utilities
- `scripts/test_slack_integration.py` - Integration testing
- `scripts/check_mcp_status.py` - MCP server health check

---

**Last Updated**: January 2025  
**Status**: Production Ready ✅