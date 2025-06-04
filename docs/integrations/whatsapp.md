# WhatsApp Integration (Evolution API)

This document describes the WhatsApp integration capabilities available in Automagik Agents through the Evolution API, enabling agents to send and receive WhatsApp messages.

## Overview

Both **Simple** and **Sofia** agents support WhatsApp integration through Evolution API, enabling them to:

- Receive WhatsApp messages and extract user context
- Send text messages to WhatsApp users
- Send reactions to WhatsApp messages
- Handle both individual and group chats
- Persist user information for personalized responses
- Auto-fill phone numbers and JIDs from context

## Supported Agents

| Agent | WhatsApp Support | Evolution Tools | Group Chat | User Persistence |
|-------|------------------|-----------------|------------|------------------|
| **Simple** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes |
| **Sofia** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes |

## Evolution API Integration

### Payload Structure

Agents receive Evolution payloads containing WhatsApp message context:

```python
from src.agents.common.evolution import EvolutionMessagePayload

# Example payload structure
evolution_payload = {
    "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",  # Individual chat
        "fromMe": False,
        "id": "message_id"
    },
    "message": {
        "conversation": "Hello, how are you?"
    },
    "messageTimestamp": 1640995200,
    "pushName": "John Doe",
    "participant": "5511999999999@s.whatsapp.net"  # Group chat sender
}
```

### Group Chat Detection

Agents automatically detect group vs individual chats:

```python
# Group chat JID format
"120363123456789012@g.us"  # Group chat

# Individual chat JID format  
"5511999999999@s.whatsapp.net"  # Individual chat
```

## Usage

### API Request with Evolution Context

```json
{
  "user_input": "Help me with my order",
  "channel_payload": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false
    },
    "message": {
      "conversation": "Help me with my order"
    },
    "pushName": "Customer Name"
  }
}
```

### Python SDK Usage

```python
from src.agents.simple.simple.agent import SimpleAgent
from src.agents.common.evolution import EvolutionMessagePayload

agent = SimpleAgent({"model_name": "openai:gpt-4"})

# Evolution payload from WhatsApp
evolution_payload = EvolutionMessagePayload(
    key={"remoteJid": "5511999999999@s.whatsapp.net"},
    message={"conversation": "Hello!"},
    pushName="John Doe"
)

response = await agent.run(
    "Hello!",
    channel_payload=evolution_payload
)
```

### CLI Usage

```bash
# Using automagik CLI with Evolution payload
automagik agents run simple \
  --input "Hello there" \
  --channel-payload '{"key":{"remoteJid":"5511999999999@s.whatsapp.net"},"pushName":"User"}'
```

## Available Tools

### Send Text Message

Send text messages to WhatsApp users:

```python
# Tool automatically fills phone number from context
await agent.run("Send a welcome message to the user")

# Manual usage
from src.tools.evolution import send_text_to_user

await send_text_to_user(
    phone_number="5511999999999",
    message="Welcome to our service!"
)
```

### Send Reaction

Send emoji reactions to WhatsApp messages:

```python
# Tool automatically fills JID from context
await agent.run("React with a thumbs up")

# Manual usage
from src.tools.evolution import send_reaction

await send_reaction(
    jid="5511999999999@s.whatsapp.net",
    message_id="message_id",
    reaction="👍"
)
```

## Context-Aware Tool Wrappers

Both agents include intelligent tool wrappers that auto-fill Evolution context:

### Send Text Wrapper

```python
def _create_send_text_wrapper(self):
    """Create wrapper that auto-fills phone number from Evolution context."""
    
    def send_text_to_user_wrapper(message: str) -> str:
        """Send text message to WhatsApp user.
        
        Args:
            message: Text message to send
            
        Returns:
            Success confirmation
        """
        # Extract phone number from Evolution context
        phone_number = self.context.get("user_phone_number")
        
        if not phone_number:
            return "Error: No phone number available in context"
            
        # Send message using Evolution API
        result = send_text_to_user(phone_number, message)
        return f"Message sent to {phone_number}: {message}"
    
    return send_text_to_user_wrapper
```

### Send Reaction Wrapper

```python
def _create_send_reaction_wrapper(self):
    """Create wrapper that auto-fills JID from Evolution context."""
    
    def send_reaction_wrapper(reaction: str) -> str:
        """Send reaction to WhatsApp message.
        
        Args:
            reaction: Emoji reaction to send
            
        Returns:
            Success confirmation
        """
        # Extract JID and message ID from Evolution context
        jid = self.context.get("evolution_jid")
        message_id = self.context.get("evolution_message_id")
        
        if not jid or not message_id:
            return "Error: Missing JID or message ID in context"
            
        # Send reaction using Evolution API
        result = send_reaction(jid, message_id, reaction)
        return f"Reaction {reaction} sent to message {message_id}"
    
    return send_reaction_wrapper
```

## User Information Persistence

### Automatic Context Extraction

Agents automatically extract and store user information:

```python
def _extract_user_info_from_evolution(self, evolution_payload):
    """Extract user information from Evolution payload."""
    
    # Extract phone number from JID
    jid = evolution_payload.get("key", {}).get("remoteJid", "")
    phone_number = jid.split("@")[0] if "@" in jid else ""
    
    # Extract user name
    user_name = evolution_payload.get("pushName", "")
    
    # Detect chat type
    is_group_chat = jid.endswith("@g.us")
    
    # Store in context for tool wrappers
    self.context.update({
        "user_phone_number": phone_number,
        "user_name": user_name,
        "evolution_jid": jid,
        "is_group_chat": is_group_chat,
        "evolution_message_id": evolution_payload.get("key", {}).get("id")
    })
    
    return {
        "phone_number": phone_number,
        "name": user_name,
        "is_group": is_group_chat
    }
```

### Memory Integration

User information is persisted to memory for future interactions:

```python
# Store user information in memory
user_info = {
    "phone_number": "5511999999999",
    "name": "John Doe",
    "last_interaction": "2024-01-01T12:00:00Z",
    "preferences": ["quick_responses", "emoji_reactions"]
}

await self.memory_handler.store_user_info(user_id, user_info)
```

## Group Chat Handling

### Group Context Detection

```python
def _handle_group_chat(self, evolution_payload):
    """Handle group chat specific logic."""
    
    jid = evolution_payload.get("key", {}).get("remoteJid", "")
    participant = evolution_payload.get("participant", "")
    
    if jid.endswith("@g.us"):
        # Group chat - extract participant info
        participant_phone = participant.split("@")[0]
        group_id = jid.split("@")[0]
        
        self.context.update({
            "group_id": group_id,
            "participant_phone": participant_phone,
            "is_group_chat": True
        })
        
        return True
    
    return False
```

### Group-Specific Features

- **Participant tracking**: Identify individual users in group chats
- **Group-wide announcements**: Send messages to entire group
- **Mention handling**: Process @mentions in group messages
- **Admin detection**: Identify group administrators

## Configuration

### Evolution API Settings

Configure Evolution API connection:

```python
# Environment variables
EVOLUTION_API_URL = "https://your-evolution-api.com"
EVOLUTION_API_KEY = "your-api-key"
EVOLUTION_INSTANCE_NAME = "your-instance"

# Agent configuration
config = {
    "model_name": "openai:gpt-4",
    "evolution_api_url": EVOLUTION_API_URL,
    "evolution_api_key": EVOLUTION_API_KEY,
    "evolution_instance": EVOLUTION_INSTANCE_NAME
}
```

### Tool Registration

Tools are automatically registered during agent initialization:

```python
class SimpleAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Register Evolution tools with context-aware wrappers
        self.tool_registry.register_tool(self._create_send_reaction_wrapper())
        self.tool_registry.register_tool(self._create_send_text_wrapper())
```

## Error Handling

### Common Errors

1. **Invalid Phone Number**
   ```json
   {
     "error": "Invalid phone number format",
     "details": "Phone number must include country code"
   }
   ```

2. **Evolution API Unavailable**
   ```json
   {
     "error": "Evolution API connection failed",
     "details": "Unable to connect to Evolution server"
   }
   ```

3. **Missing Context**
   ```json
   {
     "error": "Missing Evolution context",
     "details": "No phone number available for sending message"
   }
   ```

### Error Recovery

```python
try:
    result = await send_text_to_user(phone_number, message)
except EvolutionAPIError as e:
    logger.error(f"Evolution API error: {e}")
    return AgentResponse(
        text="Sorry, I couldn't send the message right now. Please try again later.",
        success=False,
        error_message=str(e)
    )
```

## Best Practices

### Message Formatting

1. **Keep messages concise** for mobile readability
2. **Use emojis appropriately** for engagement
3. **Format lists clearly** with line breaks
4. **Include call-to-action** when appropriate

### User Experience

1. **Respond quickly** to maintain conversation flow
2. **Personalize responses** using stored user information
3. **Handle context switches** gracefully
4. **Provide clear error messages** when issues occur

### Privacy & Security

1. **Validate phone numbers** before storing
2. **Encrypt sensitive data** in memory storage
3. **Respect user preferences** for communication
4. **Implement rate limiting** to prevent spam

## Examples

### Basic WhatsApp Response

```python
# User sends: "What's the weather like?"
evolution_payload = {
    "key": {"remoteJid": "5511999999999@s.whatsapp.net"},
    "message": {"conversation": "What's the weather like?"},
    "pushName": "John"
}

response = await agent.run(
    "What's the weather like?",
    channel_payload=evolution_payload
)

# Agent automatically has access to user's phone number for responses
```

### Group Chat Interaction

```python
# Group message with mention
evolution_payload = {
    "key": {"remoteJid": "120363123456789012@g.us"},
    "message": {"conversation": "@bot help me with my order"},
    "participant": "5511999999999@s.whatsapp.net",
    "pushName": "Customer"
}

response = await agent.run(
    "@bot help me with my order",
    channel_payload=evolution_payload
)
```

### Reaction to Message

```python
# Agent can react to user messages
await agent.run("React with a heart emoji to show appreciation")

# This will automatically use the message ID from Evolution context
```

## Troubleshooting

### Debug Logging

Enable debug logging for Evolution integration:

```python
import logging
logging.getLogger('src.tools.evolution').setLevel(logging.DEBUG)
logging.getLogger('src.agents.common.evolution').setLevel(logging.DEBUG)
```

### Common Issues

1. **Messages not sending**: Check Evolution API connectivity and credentials
2. **Context missing**: Verify Evolution payload is properly formatted
3. **Group chat issues**: Ensure participant information is included
4. **Rate limiting**: Implement delays between messages

### Testing

Test WhatsApp integration:

```bash
# Run Evolution integration tests
uv run pytest tests/agents/simple/test_simple_evolution.py -v

# Test specific WhatsApp functionality
uv run pytest tests/tools/evolution/ -v
```

## Future Enhancements

- **Media message support** (images, documents, audio)
- **WhatsApp Business API** integration
- **Advanced group management** (add/remove participants)
- **Message scheduling** and automation
- **WhatsApp Web** integration
- **Broadcast lists** support 