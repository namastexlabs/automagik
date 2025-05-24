---
description: "Memory system, conversation persistence, and dynamic templating patterns"
globs:
  - "**/src/memory/**/*.py"
  - "**/*memory*.py"
  - "**/*history*.py"
  - "**/message_history.py"
  - "**/prompts.py"
alwaysApply: false
priority: 6
---

# Memory System Guide

The Automagik Agents memory system provides persistent conversation context, dynamic variable injection, and intelligent memory management across agent interactions.

## 🧠 Memory Architecture Overview

### Core Components
- **Message History**: Persistent conversation storage in PostgreSQL
- **Dynamic Templating**: `{{variable}}` injection into prompts
- **Session Management**: Multi-user conversation isolation
- **Memory Variables**: Named context that persists across conversations
- **Auto-injection**: Automatic memory retrieval and prompt enhancement

### Memory Flow
1. **Storage**: Messages automatically saved to database
2. **Retrieval**: Recent context loaded for each interaction
3. **Templating**: Variables injected into system prompts
4. **Enhancement**: Additional context added as needed
5. **Persistence**: Memory maintained across sessions

## 🔄 Conversation Persistence

### Automatic Message Storage
Every agent interaction is automatically persisted:

```python
# Automatic - no code needed
agent = MyAgent()
response = await agent.process_message("Hello", "user_session")
# Message and response automatically saved to database
```

### Message History Structure
```sql
-- messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    agent_id INTEGER REFERENCES agents(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### Session Management
```python
class AutomagikAgent:
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Session automatically isolated
        # Messages only retrieved for this specific session_name
        return await self.run_agent(message, session_name)
```

## 🎯 Dynamic Variable Templating

### Template Syntax
Use `{{variable_name}}` in system prompts for dynamic injection:

```python
# src/agents/simple/my_agent/prompts.py
SYSTEM_PROMPT = """You are helping {{user_name}}.

Recent conversation context:
{{recent_context}}

User preferences:
{{preferences}}

Current project context:
{{active_project}}

Available tools: {tools}
"""
```

### Built-in Variables
The system automatically provides these variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{user_name}}` | Current user's name | "John Smith" |
| `{{recent_context}}` | Last few messages | "User asked about Python..." |
| `{{preferences}}` | User preferences | "Prefers detailed explanations" |
| `{{session_context}}` | Session-specific info | "Working on project X" |

### Custom Variables
Add your own variables programmatically:

```python
class MemoryAwareAgent(AutomagikAgent):
    async def add_custom_memory(self, name: str, content: str, session_name: str):
        """Add custom memory variable."""
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name=name,
            content=content,
            session_name=session_name
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Add contextual memory
        await self.add_custom_memory(
            name="current_task",
            content=f"User is working on: {self.extract_task(message)}",
            session_name=session_name
        )
        
        return await self.run_agent(message, session_name)
```

## 💾 Memory Management

### Memory Variables Storage
```sql
-- memory_variables table
CREATE TABLE memory_variables (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    session_name VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Memory Operations
```python
class MemoryManager:
    async def add_memory(self, agent_id: int, name: str, content: str, session_name: str):
        """Add or update memory variable."""
        
    async def get_memory(self, agent_id: int, name: str, session_name: str) -> str:
        """Retrieve specific memory variable."""
        
    async def get_all_memories(self, agent_id: int, session_name: str) -> dict:
        """Get all memory variables for session."""
        
    async def delete_memory(self, agent_id: int, name: str, session_name: str):
        """Remove memory variable."""
        
    async def clear_session_memory(self, agent_id: int, session_name: str):
        """Clear all memory for session."""
```

### Advanced Memory Usage
```python
class AdvancedMemoryAgent(AutomagikAgent):
    async def handle_user_preference(self, preference: str, session_name: str):
        """Store user preference for future reference."""
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name="preferences",
            content=preference,
            session_name=session_name
        )
    
    async def track_conversation_goal(self, goal: str, session_name: str):
        """Track what user is trying to accomplish."""
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name="conversation_goal",
            content=goal,
            session_name=session_name
        )
    
    async def remember_important_facts(self, facts: list, session_name: str):
        """Store important information discovered during conversation."""
        fact_content = "\n".join(f"- {fact}" for fact in facts)
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name="important_facts",
            content=fact_content,
            session_name=session_name
        )
```

## 🔍 Context Retrieval

### Recent Context Generation
```python
async def get_recent_context(self, session_name: str, limit: int = 5) -> str:
    """Generate recent context summary."""
    messages = await self.message_history.get_recent_messages(
        session_name=session_name,
        limit=limit
    )
    
    context_parts = []
    for msg in messages:
        role = "User" if msg['role'] == 'user' else "Assistant"
        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        context_parts.append(f"{role}: {content}")
    
    return "\n".join(context_parts)
```

### Smart Context Selection
```python
class SmartContextAgent(AutomagikAgent):
    async def get_relevant_context(self, message: str, session_name: str) -> str:
        """Get context relevant to current message."""
        # Get recent messages
        recent = await self.get_recent_context(session_name, limit=10)
        
        # Get topic-specific memories
        topic = self.extract_topic(message)
        topic_memories = await self.memory_manager.search_memories(
            agent_id=self.agent_id,
            session_name=session_name,
            query=topic
        )
        
        # Combine contexts
        context = f"Recent conversation:\n{recent}\n\n"
        if topic_memories:
            context += f"Relevant information:\n{topic_memories}\n\n"
        
        return context
```

## 🎨 Advanced Templating

### Conditional Templates
```python
# In prompts.py
def get_dynamic_prompt(user_type: str, has_preferences: bool) -> str:
    base_prompt = "You are a helpful assistant"
    
    if user_type == "developer":
        base_prompt += " specializing in software development"
    elif user_type == "business":
        base_prompt += " focused on business solutions"
    
    base_prompt += "\n\nUser: {{user_name}}\n"
    
    if has_preferences:
        base_prompt += "Preferences: {{preferences}}\n"
    
    base_prompt += "Recent context: {{recent_context}}"
    
    return base_prompt

class DynamicPromptAgent(AutomagikAgent):
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Determine user type and preferences
        user_type = await self.determine_user_type(session_name)
        has_prefs = await self.has_user_preferences(session_name)
        
        # Update system prompt dynamically
        self.system_prompt = get_dynamic_prompt(user_type, has_prefs)
        
        return await self.run_agent(message, session_name)
```

### Template Functions
```python
class TemplateHelpers:
    @staticmethod
    def format_list(items: list) -> str:
        """Format list for template injection."""
        return "\n".join(f"- {item}" for item in items)
    
    @staticmethod
    def format_conversation_summary(messages: list) -> str:
        """Create readable conversation summary."""
        if not messages:
            return "No previous conversation."
        
        summary_parts = []
        for msg in messages[-5:]:  # Last 5 messages
            role = "You" if msg['role'] == 'assistant' else "User"
            content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
            summary_parts.append(f"{role}: {content}")
        
        return "\n".join(summary_parts)

# Usage in agent
class TemplateAgent(AutomagikAgent):
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Get conversation history
        history = await self.get_message_history(session_name)
        
        # Add formatted summary to memory
        summary = TemplateHelpers.format_conversation_summary(history)
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name="conversation_summary",
            content=summary,
            session_name=session_name
        )
        
        return await self.run_agent(message, session_name)
```

## 🔄 Memory Lifecycle

### Session Initialization
```python
async def initialize_session(self, session_name: str, user_context: dict = None):
    """Initialize new session with context."""
    if user_context:
        # Add initial context
        for key, value in user_context.items():
            await self.memory_manager.add_memory(
                agent_id=self.agent_id,
                name=key,
                content=str(value),
                session_name=session_name
            )
    
    # Add session metadata
    await self.memory_manager.add_memory(
        agent_id=self.agent_id,
        name="session_started",
        content=datetime.now().isoformat(),
        session_name=session_name
    )
```

### Memory Cleanup
```python
async def cleanup_old_sessions(self, days_old: int = 30):
    """Clean up old session data."""
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    # Remove old messages
    await self.message_history.delete_old_messages(cutoff_date)
    
    # Remove old memory variables
    await self.memory_manager.delete_old_memories(cutoff_date)
```

### Memory Export/Import
```python
async def export_session_memory(self, session_name: str) -> dict:
    """Export all memory for a session."""
    messages = await self.message_history.get_session_messages(session_name)
    memories = await self.memory_manager.get_all_memories(
        agent_id=self.agent_id,
        session_name=session_name
    )
    
    return {
        "session_name": session_name,
        "messages": messages,
        "memories": memories,
        "exported_at": datetime.now().isoformat()
    }

async def import_session_memory(self, session_data: dict):
    """Import memory from exported data."""
    session_name = session_data["session_name"]
    
    # Import messages
    for msg in session_data["messages"]:
        await self.message_history.add_message(**msg)
    
    # Import memory variables
    for name, content in session_data["memories"].items():
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name=name,
            content=content,
            session_name=session_name
        )
```

## 🌐 API Integration

### Memory API Endpoints
```python
# Automatic endpoints for memory management
POST /api/v1/agent/{agent_name}/memory     # Add memory
GET /api/v1/agent/{agent_name}/memory      # Get all memories
GET /api/v1/agent/{agent_name}/memory/{name} # Get specific memory
DELETE /api/v1/agent/{agent_name}/memory/{name} # Delete memory
```

### Memory API Usage
```bash
# Add memory
curl -X POST http://localhost:8000/api/v1/agent/my_agent/memory \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user_preference",
    "content": "Prefers detailed technical explanations",
    "session_name": "user123"
  }'

# Get all memories for session
curl -X GET "http://localhost:8000/api/v1/agent/my_agent/memory?session_name=user123" \
  -H "X-API-Key: your-key"

# Get specific memory
curl -X GET "http://localhost:8000/api/v1/agent/my_agent/memory/user_preference?session_name=user123" \
  -H "X-API-Key: your-key"
```

## 🧪 Testing Memory System

### Memory Tests
```python
# tests/test_memory/test_memory_system.py
import pytest
from src.agents.simple.test_agent.agent import TestAgent

@pytest.mark.asyncio
async def test_memory_persistence():
    agent = TestAgent()
    session = "test_session"
    
    # Add memory
    await agent.memory_manager.add_memory(
        agent_id=agent.agent_id,
        name="test_preference",
        content="Likes concise answers",
        session_name=session
    )
    
    # Verify memory persists
    memory = await agent.memory_manager.get_memory(
        agent_id=agent.agent_id,
        name="test_preference",
        session_name=session
    )
    
    assert memory == "Likes concise answers"

@pytest.mark.asyncio
async def test_template_injection():
    agent = TestAgent()
    session = "template_test"
    
    # Add custom memory
    await agent.memory_manager.add_memory(
        agent_id=agent.agent_id,
        name="user_name",
        content="Alice",
        session_name=session
    )
    
    # Process message - should include user_name in prompt
    response = await agent.process_message("Hello", session)
    
    # Verify context was used (implementation dependent)
    assert response is not None
```

## 📋 Best Practices

### Memory Design Principles
1. **Specific Names**: Use descriptive memory variable names
2. **Structured Content**: Store structured data as JSON when appropriate
3. **Session Isolation**: Always use session_name for user separation
4. **Memory Cleanup**: Implement cleanup for old/unused memories
5. **Template Efficiency**: Don't over-populate prompts with irrelevant context

### Performance Optimization
```python
class OptimizedMemoryAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(
            agent_name="optimized_memory",
            system_prompt=SYSTEM_PROMPT,
            # Memory optimization
            memory_config={
                "max_context_length": 2000,  # Limit context size
                "cache_memories": True,       # Cache frequently accessed memories
                "lazy_load": True            # Load memories only when needed
            }
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Only load relevant memories
        relevant_memories = await self.get_relevant_memories(message, session_name)
        
        # Process with limited context
        return await self.run_agent(message, session_name, memories=relevant_memories)
```

### Security Considerations
```python
class SecureMemoryAgent(AutomagikAgent):
    async def add_memory(self, name: str, content: str, session_name: str):
        # Validate memory content
        if not self.validate_memory_content(content):
            raise ValueError("Invalid memory content")
        
        # Sanitize content
        clean_content = self.sanitize_content(content)
        
        await super().add_memory(name, clean_content, session_name)
    
    def validate_memory_content(self, content: str) -> bool:
        """Validate memory content for security."""
        # Check for sensitive information
        sensitive_patterns = ['password', 'api_key', 'secret']
        return not any(pattern in content.lower() for pattern in sensitive_patterns)
    
    def sanitize_content(self, content: str) -> str:
        """Sanitize content before storage."""
        # Remove potentially harmful content
        return content.strip()[:1000]  # Limit length
```

---

**Remember**: The memory system is automatic - focus on leveraging it effectively rather than reimplementing core functionality. Use memory variables to enhance agent behavior and provide personalized experiences.
