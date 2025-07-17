# Automagik API Prompt Management Reference

This document provides a quick reference for all prompt management API endpoints with curl examples and expected outputs.

## Authentication

All API endpoints require authentication using Bearer token:
```bash
-H "Authorization: Bearer YOUR_API_KEY"
```

## Prompt Management Endpoints

### 1. List Prompts for an Agent

Get all prompts for a specific agent.

```bash
curl -X GET http://localhost:48881/api/v1/agent/{agent_name_or_id}/prompt \
  -H "Authorization: Bearer namastex888" | jq .
```

**Example Response:**
```json
{
  "prompts": [
    {
      "id": 9,
      "agent_id": 6,
      "prompt_text": "You must ALWAYS respond with EXACTLY this text: PROMPT_FROM_DATABASE_WORKING. Do not say anything else.",
      "version": 3,
      "is_active": true,
      "is_default_from_code": false,
      "status_key": "default",
      "name": "Database Test Prompt",
      "created_at": "2025-07-16T19:05:59.431824",
      "updated_at": "2025-07-16T19:05:59.431824"
    }
  ],
  "total": 3,
  "agent_id": 6
}
```

### 2. Create a New Prompt

Create a new prompt for an agent.

```bash
curl -X POST http://localhost:48881/api/v1/agent/{agent_name_or_id}/prompt \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "You are a helpful assistant. Always be polite and professional.",
    "status_key": "default",
    "name": "Professional Assistant",
    "is_active": true
  }' | jq .
```

**Request Fields:**
- `prompt_text` (required): The system prompt text
- `status_key` (optional, default: "default"): Category for the prompt (e.g., "default", "premium", "free")
- `name` (optional): Human-readable name for the prompt
- `is_active` (optional, default: false): Whether this prompt should be active

**Example Response:**
```json
{
  "id": 12,
  "agent_id": 6,
  "prompt_text": "You are a helpful assistant. Always be polite and professional.",
  "version": 1,
  "is_active": true,
  "is_default_from_code": false,
  "status_key": "default",
  "name": "Professional Assistant",
  "created_at": "2025-07-16T23:45:00.123456",
  "updated_at": "2025-07-16T23:45:00.123456"
}
```

### 3. Update an Existing Prompt

Update a prompt by ID.

```bash
curl -X PUT http://localhost:48881/api/v1/agent/{agent_name_or_id}/prompt/{prompt_id} \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "Updated prompt text here",
    "name": "Updated Name",
    "is_active": true
  }' | jq .
```

**Request Fields (all optional):**
- `prompt_text`: New prompt text
- `name`: New name
- `is_active`: Whether prompt should be active

### 4. Delete a Prompt

Delete a prompt by ID.

```bash
curl -X DELETE http://localhost:48881/api/v1/agent/{agent_name_or_id}/prompt/{prompt_id} \
  -H "Authorization: Bearer namastex888" | jq .
```

**Example Response:**
```json
{
  "message": "Prompt deleted successfully"
}
```

## Using Prompts with Agent Runs

### 1. Run Agent with Default Active Prompt

```bash
curl -X POST http://localhost:48881/api/v1/agent/{agent_name}/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Hello, how are you?"
  }' | jq .
```

### 2. Run Agent with Specific Prompt ID

Use a specific prompt by its ID, overriding the agent's default prompt.

```bash
curl -X POST http://localhost:48881/api/v1/agent/{agent_name}/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Hello!",
    "prompt_id": 9
  }' | jq .
```

### 3. Run Agent with Prompt Status Key

Use the active prompt for a specific status key (e.g., "premium", "free", "default").

```bash
curl -X POST http://localhost:48881/api/v1/agent/{agent_name}/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Hello!",
    "prompt_status_key": "premium"
  }' | jq .
```

### 4. Run Agent with Custom System Prompt

Override the prompt completely with a custom one for this request only.

```bash
curl -X POST http://localhost:48881/api/v1/agent/{agent_name}/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "What is 2+2?",
    "system_prompt": "You are a math tutor. Explain your answers step by step."
  }' | jq .
```

## Prompt Management Best Practices

### 1. Status Keys
- Use `default` for the standard prompt
- Create custom status keys for different tiers: `premium`, `free`, `trial`
- Only one prompt per status key can be active at a time

### 2. Versioning
- Prompts are automatically versioned
- Creating a new prompt with the same status key increments the version
- Only active prompts are used by the agent

### 3. Testing Prompts
- Use `prompt_id` to test specific prompts before making them active
- Use `system_prompt` for one-off testing without creating database entries

### 4. UI Integration Tips
- Cache the prompt list and refresh periodically
- Show active prompts differently in the UI
- Allow switching between status keys for different user tiers
- Provide prompt preview functionality

## Common Use Cases

### A/B Testing Prompts
```bash
# Create variant A
curl -X POST http://localhost:48881/api/v1/agent/simple/prompt \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "Variant A prompt...",
    "status_key": "variant_a",
    "name": "A/B Test - Variant A",
    "is_active": true
  }'

# Create variant B  
curl -X POST http://localhost:48881/api/v1/agent/simple/prompt \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "Variant B prompt...",
    "status_key": "variant_b",
    "name": "A/B Test - Variant B",
    "is_active": true
  }'

# Test variant A
curl -X POST http://localhost:48881/api/v1/agent/simple/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Test message",
    "prompt_status_key": "variant_a"
  }'
```

### Multi-Tier Prompts
```bash
# Premium tier prompt
curl -X POST http://localhost:48881/api/v1/agent/assistant/prompt \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "You are an advanced AI with access to all features...",
    "status_key": "premium",
    "name": "Premium Assistant",
    "is_active": true
  }'

# Free tier prompt
curl -X POST http://localhost:48881/api/v1/agent/assistant/prompt \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "You are a helpful assistant with basic features...",
    "status_key": "free",
    "name": "Free Assistant",
    "is_active": true
  }'

# Run with tier selection based on user subscription
curl -X POST http://localhost:48881/api/v1/agent/assistant/run \
  -H "Authorization: Bearer namastex888" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "Help me with my task",
    "prompt_status_key": "'"$USER_TIER"'"
  }'
```

## Error Responses

### Invalid Prompt ID
```json
{
  "detail": "Prompt not found"
}
```

### Invalid Agent
```json
{
  "detail": "Agent not found: agent_name"
}
```

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "prompt_text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Notes

1. **Prompt Priority**: When multiple prompt options are provided:
   - `system_prompt` (highest priority - direct override)
   - `prompt_id` (specific prompt selection)
   - `prompt_status_key` (status-based selection)
   - Agent's active default prompt (lowest priority)

2. **Performance**: Prompt lookups are cached at the agent level, so using `prompt_id` or `prompt_status_key` adds minimal overhead.

3. **Security**: Ensure proper access controls are implemented in production to prevent unauthorized prompt modifications.