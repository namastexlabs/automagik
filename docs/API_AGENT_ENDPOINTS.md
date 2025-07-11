# Agent Management API Documentation

This documentation provides comprehensive examples for all agent-related API endpoints, including the new flexible identifier resolution system that supports both agent names and IDs.

## Base URL and Authentication

```
Base URL: http://localhost:18881/api/v1
Authentication: X-API-Key header required for all endpoints
```

**Headers for all requests:**
```json
{
  "X-API-Key": "your-api-key",
  "Content-Type": "application/json"
}
```

---

## 🎯 **Key Feature: Flexible Agent Identification**

All agent endpoints now support **both agent names and IDs** via the `{agent_identifier}` parameter:
- **By Name**: `/agent/simple/run`
- **By ID**: `/agent/6/run`

This provides maximum flexibility for UI developers!

---

## 📋 **Agent Endpoints**

### 1. List All Agents

**GET** `/agents`

**Response:**
```json
[
  {
    "id": 6,
    "name": "simple",
    "description": "Enhanced Simple Agent with multimodal capabilities"
  },
  {
    "id": 23,
    "name": "blackpearl_test", 
    "description": "blackpearl_test agent"
  }
]
```

### 2. Run Agent (Synchronous)

**POST** `/agent/{agent_identifier}/run`

**Request Body:**
```json
{
  "message_content": "Hello! Please help me with my task.",
  "session_name": "my_work_session",
  "user_id": "user123",
  "session_id": "optional-existing-session-id"
}
```

**Response:**
```json
{
  "message": "Hello! I'm here to help you with your task. What specific assistance do you need?",
  "session_id": "f4608ceb-78de-4675-90c3-39441ca6ed7b",
  "success": true,
  "tool_calls": [],
  "tool_outputs": [],
  "user_id": "062c749e-ec23-4a49-9ea5-77d2f08ffe7b",
  "usage": {
    "framework": "pydantic_ai",
    "model": "openai:gpt-4.1",
    "request_tokens": 230,
    "response_tokens": 44,
    "total_tokens": 274,
    "processing_time_ms": 2440.8,
    "content_types": ["text"]
  }
}
```

### 3. Run Agent (Asynchronous)

**POST** `/agent/{agent_identifier}/run/async`

**Request Body:**
```json
{
  "message_content": "This is a long-running task that might take time.",
  "session_name": "async_session"
}
```

**Response:**
```json
{
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Agent simple run started",
  "agent_name": "simple"
}
```

### 4. Check Async Run Status

**GET** `/run/{run_id}/status`

**Response:**
```json
{
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "agent_name": "simple",
  "created_at": "2025-07-10T16:52:14.860403",
  "started_at": "2025-07-10T16:52:15.100000",
  "completed_at": "2025-07-10T16:52:18.500000",
  "result": "Task completed successfully! Here are the results...",
  "error": null,
  "progress": {
    "phase": "completed",
    "execution_summary": {
      "duration_ms": 3400,
      "turns": 2,
      "cost_usd": 0.0234
    }
  }
}
```

### 5. Create Agent (via Copy)

**POST** `/agent/{source_agent_identifier}/copy`

**Request Body:**
```json
{
  "new_name": "my_custom_agent",
  "description": "My customized agent for specific tasks",
  "model": "anthropic:claude-3-sonnet-20240229",
  "system_prompt": "You are a specialized assistant for data analysis tasks. Always be precise and provide detailed explanations."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Agent 'simple' copied to 'my_custom_agent' successfully",
  "source_agent": "simple",
  "new_agent": "my_custom_agent",
  "agent_id": 80
}
```

### 6. Update Agent

**PUT** `/agent/{agent_identifier}`

**Request Body (all fields optional):**
```json
{
  "model": "openai:gpt-4-turbo",
  "description": "Updated agent with new model",
  "active": true,
  "config": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Agent 'my_custom_agent' updated successfully",
  "agent_name": "my_custom_agent"
}
```

### 7. Delete Agent

**DELETE** `/agent/{agent_identifier}`

**Response:**
```json
{
  "status": "success",
  "message": "Agent 'my_custom_agent' deleted successfully",
  "agent_name": "my_custom_agent"
}
```

---

## 📝 **Prompt Management Endpoints**

### 1. List Agent Prompts

**GET** `/agent/{agent_identifier}/prompt?status_key=active`

**Response:**
```json
{
  "prompts": [
    {
      "id": 15,
      "name": "Default System Prompt",
      "prompt_text": "You are a helpful AI assistant...",
      "description": "Default prompt for the agent",
      "status_key": "active",
      "is_default_from_code": true,
      "agent_id": 6,
      "created_at": "2025-07-10T10:30:00Z"
    }
  ],
  "total": 1
}
```

### 2. Get Specific Prompt

**GET** `/agent/{agent_identifier}/prompt/{prompt_id}`

**Response:**
```json
{
  "id": 15,
  "name": "Custom Analysis Prompt",
  "prompt_text": "You are a data analysis specialist. Always provide detailed insights and suggest next steps.",
  "description": "Specialized prompt for data analysis tasks",
  "status_key": "active",
  "is_default_from_code": false,
  "agent_id": 6,
  "created_at": "2025-07-10T10:30:00Z",
  "updated_at": "2025-07-10T12:15:00Z"
}
```

### 3. Create New Prompt

**POST** `/agent/{agent_identifier}/prompt`

**Request Body:**
```json
{
  "name": "Marketing Assistant Prompt",
  "prompt_text": "You are a marketing specialist. Focus on creative solutions, brand consistency, and measurable outcomes. Always ask clarifying questions about target audience and goals.",
  "description": "Specialized prompt for marketing tasks",
  "status_key": "active",
  "is_default_from_code": false
}
```

**Response:**
```json
{
  "id": 42,
  "name": "Marketing Assistant Prompt",
  "prompt_text": "You are a marketing specialist...",
  "description": "Specialized prompt for marketing tasks",
  "status_key": "active",
  "is_default_from_code": false,
  "agent_id": 6,
  "created_at": "2025-07-10T14:20:00Z"
}
```

### 4. Update Prompt

**PUT** `/agent/{agent_identifier}/prompt/{prompt_id}`

**Request Body:**
```json
{
  "name": "Updated Marketing Prompt",
  "prompt_text": "You are an expert marketing strategist with 10+ years experience...",
  "description": "Enhanced marketing prompt with more context"
}
```

**Response:**
```json
{
  "id": 42,
  "name": "Updated Marketing Prompt",
  "prompt_text": "You are an expert marketing strategist...",
  "description": "Enhanced marketing prompt with more context",
  "status_key": "active",
  "agent_id": 6,
  "updated_at": "2025-07-10T15:45:00Z"
}
```

### 5. Activate Prompt

**POST** `/agent/{agent_identifier}/prompt/{prompt_id}/activate`

**Response:**
```json
{
  "id": 42,
  "name": "Marketing Assistant Prompt",
  "status_key": "active",
  "message": "Prompt activated successfully"
}
```

### 6. Deactivate Prompt

**POST** `/agent/{agent_identifier}/prompt/{prompt_id}/deactivate`

**Response:**
```json
{
  "id": 42,
  "name": "Marketing Assistant Prompt", 
  "status_key": "inactive",
  "message": "Prompt deactivated successfully"
}
```

### 7. Delete Prompt

**DELETE** `/agent/{agent_identifier}/prompt/{prompt_id}`

**Response:**
```json
{
  "message": "Prompt deleted successfully",
  "deleted_prompt_id": 42
}
```

---

## 🔄 **Complete Workflow Examples**

### Example 1: Create and Configure New Agent

```javascript
// 1. Create agent from existing one
const createResponse = await fetch('/api/v1/agent/simple/copy', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    new_name: 'data_analyst',
    description: 'Specialized data analysis agent',
    model: 'anthropic:claude-3-sonnet-20240229'
  })
});

const agent = await createResponse.json();
// agent.agent_id = 81, agent.new_agent = 'data_analyst'

// 2. Create custom prompt
const promptResponse = await fetch(`/api/v1/agent/${agent.agent_id}/prompt`, {
  method: 'POST', 
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Data Analysis Specialist',
    prompt_text: 'You are a data analysis expert. Always provide statistical insights and visualize trends.',
    description: 'Specialized prompt for data analysis',
    status_key: 'active'
  })
});

const prompt = await promptResponse.json();
// prompt.id = 43

// 3. Update agent to use new prompt
const updateResponse = await fetch(`/api/v1/agent/data_analyst`, {
  method: 'PUT',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    active_default_prompt_id: prompt.id
  })
});
```

### Example 2: Run Agent with Different Identifiers

```javascript
// Using agent name
const runByName = await fetch('/api/v1/agent/data_analyst/run', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message_content: 'Analyze this dataset and provide insights.',
    session_name: 'analysis_session_1'
  })
});

// Using agent ID (same result)
const runById = await fetch('/api/v1/agent/81/run', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key', 
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message_content: 'Analyze this dataset and provide insights.',
    session_name: 'analysis_session_2'
  })
});
```

### Example 3: Model Provider Management

```javascript
// Change agent model provider
const modelUpdate = await fetch('/api/v1/agent/data_analyst', {
  method: 'PUT',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'openai:gpt-4-turbo',
    description: 'Updated to use GPT-4 Turbo for faster responses'
  })
});

// Test with new model
const testResponse = await fetch('/api/v1/agent/data_analyst/run', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message_content: 'Quick test with new model'
  })
});
```

---

## 🚨 **Error Responses**

### Agent Not Found
```json
{
  "detail": "Agent 'nonexistent_agent' not found"
}
// Status: 404
```

### Invalid API Key
```json
{
  "detail": "x-api-key is missing in headers or query parameters"
}
// Status: 401
```

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "message_content"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
// Status: 422
```

### Agent Run Failure
```json
{
  "error": "Agent not found: invalid_agent_name"
}
// Status: 500
```

---

## 🎛️ **Available Models**

The system supports multiple model providers. Common model strings include:

- **OpenAI**: `openai:gpt-4`, `openai:gpt-4-turbo`, `openai:gpt-3.5-turbo`
- **Anthropic**: `anthropic:claude-3-sonnet-20240229`, `anthropic:claude-3-haiku-20240307`
- **Google**: `gemini:gemini-pro`, `gemini:gemini-pro-vision`
- **Groq**: `groq:llama-3-70b`, `groq:mixtral-8x7b`

---

## 💡 **UI Development Tips**

1. **Flexible Identification**: Use IDs for internal operations, names for user-friendly displays
2. **Error Handling**: Always check for 404s when using agent identifiers
3. **Async Operations**: For long-running tasks, use async endpoints with status polling
4. **Model Updates**: Model changes take effect immediately for new runs
5. **Prompt Management**: Create specialized prompts for different use cases
6. **Session Management**: Use session names for persistent conversations

---

## 📊 **Status Codes Reference**

- **200**: Success
- **201**: Created (for POST operations)
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (missing/invalid API key)
- **404**: Not Found (agent/prompt not found)
- **422**: Unprocessable Entity (Pydantic validation errors)
- **500**: Internal Server Error

This comprehensive documentation should provide everything needed for UI integration with the agent management system!