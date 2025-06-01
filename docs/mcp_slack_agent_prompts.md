# MCP Slack Agent Prompts Guide

## Overview

This guide provides the complete set of MCP Slack-integrated prompts for all LangGraph agents. These prompts enable agents to communicate effectively through Slack using the MCP (Model Context Protocol) tools.

## Available MCP Slack Tools

All agents have access to these Slack MCP tools:

### Communication Tools
- `mcp__slack__slack_post_message` - Post new messages to channels
- `mcp__slack__slack_reply_to_thread` - Reply to existing threads
- `mcp__slack__slack_add_reaction` - Add emoji reactions

### Monitoring Tools  
- `mcp__slack__slack_get_channel_history` - Get recent channel messages
- `mcp__slack__slack_get_thread_replies` - Get all replies in a thread
- `mcp__slack__slack_list_channels` - List available channels

### Team Tools
- `mcp__slack__slack_get_users` - Get team member information
- `mcp__slack__slack_get_user_profile` - Get detailed user profiles

## Agent-Specific Prompts

### 🎯 Alpha (Orchestrator)
**File**: `src/agents/langgraph/alpha/prompts/mcp_slack_prompt.py`

Alpha creates orchestration threads and coordinates the team:
```python
# Create orchestration thread
response = mcp__slack__slack_post_message(
    channel_id="C08UF878N3Z",
    text="🚀 **New Orchestration Session**..."
)
thread_ts = response["ts"]  # Save for all replies!

# Assign tasks
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🎯 **ALPHA**: Task assignments:..."
)
```

### 🔨 Beta (Core Builder)
**File**: `src/agents/langgraph/beta/prompts/mcp_slack_prompt.py`

Beta acknowledges tasks and shares implementations:
```python
# Acknowledge and share approach
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🔨 **BETA**: Acknowledged! Starting User model..."
)

# Share code for coordination
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🔨 **BETA**: @delta Model ready!\\n```python\\n..."
)
```

### 🏗️ Delta (API Builder)
**File**: `src/agents/langgraph/delta/prompts/mcp_slack_prompt.py`

Delta designs APIs and coordinates with Beta:
```python
# Share API design
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🏗️ **DELTA**: API Design:\\n```yaml\\n..."
)

# Request dependencies
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🏗️ **DELTA**: @beta Need User model interface..."
)
```

### 🔧 Epsilon (Tool Builder)
**File**: `src/agents/langgraph/epsilon/prompts/mcp_slack_prompt.py`

Epsilon builds tools and shares interfaces:
```python
# Share tool interface
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🔧 **EPSILON**: @delta JWT interface ready!\\n```python\\n..."
)

# Offer additional tools
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="💡 **EPSILON**: Can also build rate limiting..."
)
```

### 🧪 Gamma (Quality Engineer)
**File**: `src/agents/langgraph/gamma/prompts/mcp_slack_prompt.py`

Gamma reports test results and issues:
```python
# Report test results
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🧪 **GAMMA**: Test Results - 15/18 passing..."
)

# Report specific issue
mcp__slack__slack_reply_to_thread(
    channel_id="C08UF878N3Z",
    thread_ts=thread_ts,
    text="🐛 **GAMMA**: @beta Issue: Duplicate emails allowed..."
)
```

## Communication Patterns

### 1. Thread Management
- **Alpha** creates the main thread with `slack_post_message`
- **All agents** use `slack_reply_to_thread` with the same `thread_ts`
- **Never** create multiple threads for one orchestration

### 2. Message Formatting
```python
# Use emoji for visual scanning
"🎯 **ALPHA**: ..."     # Orchestrator
"🔨 **BETA**: ..."      # Core Builder
"🏗️ **DELTA**: ..."     # API Builder
"🔧 **EPSILON**: ..."   # Tool Builder
"🧪 **GAMMA**: ..."     # Quality Engineer

# Status indicators
"✅ Complete"
"🔄 In progress"
"❌ Failed"
"⚠️ Warning"
"❓ Question"
```

### 3. Mentions and Coordination
```python
# Direct mention
"@beta Please implement..."

# Multiple mentions
"@delta @epsilon Coordination needed..."

# Human escalation
"@channel Need human input on..."
```

### 4. Code Sharing
```python
# Always use code blocks
text="Code example:\\n```python\\nclass User:\\n    pass\\n```"

# Escape newlines properly
text="Line 1\\nLine 2\\nLine 3"
```

## Best Practices

### 1. Always Save thread_ts
```python
# Alpha creates thread
response = mcp__slack__slack_post_message(...)
thread_ts = response["ts"]  # SAVE THIS!

# Pass to all agents for replies
config = {"slack_thread_ts": thread_ts}
```

### 2. Structured Updates
```python
# Progress format
"**Status Update:**\\n" +
"✅ Task 1 complete\\n" +
"🔄 Task 2 in progress\\n" +
"⏳ Task 3 pending"
```

### 3. Clear Task Acknowledgment
```python
# Acknowledge with plan
"Acknowledged! Will [action]. Approach:\\n" +
"• Step 1\\n" +
"• Step 2\\n" +
"ETA: [time]"
```

### 4. Effective Questions
```python
# Specific questions with options
"❓ Question about [topic]:\\n" +
"1️⃣ Option A\\n" +
"2️⃣ Option B\\n" +
"Please advise."
```

## Integration with Orchestration

### 1. Update Agent Initialization
```python
# In orchestrator.py
def initialize_agent(agent_name, thread_ts):
    # Load MCP Slack prompt
    from prompts.mcp_slack_prompt import AGENT_MCP_SLACK_PROMPT
    
    # Configure with thread
    config = {
        "slack_thread_ts": thread_ts,
        "slack_channel_id": "C08UF878N3Z"
    }
    
    # Agent uses MCP tools with config
    return Agent(prompt=AGENT_MCP_SLACK_PROMPT, config=config)
```

### 2. Message Flow
1. Alpha creates orchestration thread
2. Alpha assigns tasks via thread replies
3. Agents acknowledge in thread
4. Agents post progress updates
5. Agents coordinate via @mentions
6. Gamma posts test results
7. Alpha posts completion summary

### 3. Error Handling
```python
try:
    response = mcp__slack__slack_reply_to_thread(...)
except Exception as e:
    # Log error but continue
    print(f"Slack error: {e}")
    # Fall back to database messaging
```

## Channel Configuration

All agents use the same channel:
- **Channel ID**: `C08UF878N3Z`
- **Channel Name**: `group-chat`
- **Thread Management**: One thread per orchestration

## Summary

The MCP Slack integration provides:
1. **Transparent Communication** - All agent interactions visible
2. **Human Collaboration** - Team can guide and assist
3. **Structured Coordination** - Clear patterns for different scenarios
4. **Tool Reusability** - Same MCP tools for all agents

Each agent has a specialized prompt that defines:
- Their communication style and emoji
- Specific message templates
- Coordination patterns with other agents
- How to use MCP Slack tools effectively

By following these prompts and patterns, agents can collaborate effectively through Slack while maintaining clear, organized communication that humans can follow and participate in.