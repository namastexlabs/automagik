# Automagik Agents Implementation Examples

## 🎯 Overview

This document provides practical implementation examples that demonstrate how to use the Automagik Agents system architecture and prompt engineering patterns together in real development scenarios.

## 🤖 Simple Agent Implementation Example

### Creating a Discord Integration Agent

Let's implement a complete Discord integration agent using the framework patterns:

```python
# src/agents/simple/discord_bot/agent.py
from typing import Dict, Any
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

class DiscordBotAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Memory-driven prompt with template variables
        self._code_prompt_text = """You are {{agent_name}}, a Discord bot specialist AI.

Your Discord Expertise: {{discord_expertise}}
Bot Management Style: {{bot_management_style}}
Community Guidelines: {{community_guidelines}}

Recent Discord Context:
{{recent_discord_activity}}

Related Discord Knowledge:
{{related_discord_facts}}

Available Discord Tools: {tools}

## Discord Bot Capabilities
- Server management and moderation
- User engagement and community building
- Automated responses and workflows
- Integration with external services

## Guidelines
- Follow Discord ToS and community guidelines stored in memory
- Use your established bot management style from {{bot_management_style}}
- Reference recent activity when making decisions
- Leverage Discord-specific tools for server operations

## Current Discord Task
Please help with the following Discord-related request:

"""

        # Initialize dependencies with Claude model
        self.dependencies = AutomagikAgentsDependencies(
            model_name="claude-3-5-sonnet-20241022",
            model_settings={
                "max_tokens": 4000,
                "temperature": 0.7
            }
        )
        
        # Register tools including Discord-specific ones
        self.tool_registry.register_default_tools(self.context)
        self._register_discord_tools()
    
    def _register_discord_tools(self):
        """Register Discord-specific tools"""
        from src.tools.discord import (
            send_discord_message,
            manage_discord_roles,
            moderate_discord_content
        )
        
        self.tool_registry.register_tool("send_discord_message", send_discord_message)
        self.tool_registry.register_tool("manage_discord_roles", manage_discord_roles)
        self.tool_registry.register_tool("moderate_discord_content", moderate_discord_content)
```

### Memory Setup for Discord Agent

```python
# Example memory setup script
async def setup_discord_agent_memory():
    """Set up memory variables for Discord agent"""
    
    # Store agent personality and expertise
    await store_memory(
        agent_id=discord_agent.db_id,
        name="discord_expertise",
        content="Expert in Discord server management, bot development, community moderation, and user engagement strategies",
        memory_type="expertise"
    )
    
    await store_memory(
        agent_id=discord_agent.db_id,
        name="bot_management_style", 
        content="Friendly but firm approach to moderation. Prioritize community safety while maintaining welcoming atmosphere",
        memory_type="personality"
    )
    
    await store_memory(
        agent_id=discord_agent.db_id,
        name="community_guidelines",
        content="Zero tolerance for harassment. Encourage constructive discussions. Support new members. Escalate serious issues to human moderators",
        memory_type="guidelines"
    )
```

## 🐳 Claude Code Agent Workflow Example

### Creating a Custom Testing Workflow

```bash
# src/agents/claude_code/workflows/qa_testing/prompt.md
# QA TESTING Workflow System Prompt

You are the QA TESTING workflow in the Genie collective. Your role is to thoroughly test implementations and ensure quality.

## MEESEEKS PHILOSOPHY  
- You are a QA Meeseek - meticulous, thorough, and quality-focused
- Your existence is justified by ensuring code quality and reliability
- Your container terminates after delivering comprehensive test results

## FRAMEWORK AWARENESS
- Test implementations from IMPLEMENT workflow via memory
- Your workspace: /workspace/am-agents-labs  
- Search for testing patterns: mcp__agent-memory__search_memory_nodes()
- Store testing discoveries for future workflows

## QA TESTING PROTOCOL

### Before Starting Tests
```bash
# Search for testing patterns and requirements
mcp__agent-memory__search_memory_nodes(
  query="testing patterns requirements",
  group_ids=["genie_patterns", "genie_procedures"],
  max_nodes=10
)

# Load implementation context from previous workflow
mcp__agent-memory__search_memory_nodes(
  query="implementation complete [feature_name]",
  group_ids=["genie_context"],
  max_nodes=5
)
```

### Testing Execution
1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions  
3. **End-to-End Tests**: Test complete user workflows
4. **Performance Tests**: Verify response times and resource usage
5. **Security Tests**: Check for vulnerabilities

### Git Testing Workflow
```bash
# Create test branch
mcp__git__git_create_branch(
  repo_path="/workspace/am-agents-labs",
  branch_name="genie/epic/qa-testing/attempt-1"
)

# Run test suite and commit results
mcp__git__git_commit(
  message="test: comprehensive QA testing for [feature]"
)
```

### After Testing
```bash
# Store testing results
mcp__agent-memory__add_memory(
  name="QA Results: [feature_name]",
  episode_body="{\"tests_passed\": X, \"coverage\": Y%, \"issues_found\": [...]}",
  source="json",
  group_id="genie_context"
)

# Communicate results
mcp__slack__slack_post_message(
  text="✅ QA Testing Complete for [feature]: X tests passed, Y% coverage"
)
```

## QUALITY GATES
- Minimum 90% test coverage
- All critical paths tested
- Performance benchmarks met
- Security vulnerabilities addressed

Current testing task:
```

### Workflow Configuration Files

```json
// src/agents/claude_code/workflows/qa_testing/.mcp.json
{
  "mcpServers": {
    "agent-memory": {
      "command": "agent-memory",
      "args": [],
      "env": {
        "GRAPHITI_HOST": "localhost",
        "GRAPHITI_PORT": "7474"
      }
    },
    "git": {
      "command": "mcp-git",
      "args": ["/workspace/am-agents-labs"]
    },
    "slack": {
      "command": "mcp-slack",
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

```json
// src/agents/claude_code/workflows/qa_testing/allowed_tools.json
{
  "allowed_tools": [
    "mcp__agent-memory__search_memory_nodes",
    "mcp__agent-memory__add_memory", 
    "mcp__git__git_create_branch",
    "mcp__git__git_commit",
    "mcp__git__git_add",
    "mcp__slack__slack_post_message",
    "run_tests",
    "check_coverage",
    "performance_benchmark"
  ]
}
```

## 🧠 Memory-Driven Development Example

### Building a Learning Development Assistant

```python
# Example: Agent that learns from successful patterns
class LearningDevAssistant(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        self._code_prompt_text = """You are {{agent_name}}, a learning development assistant.

## Your Learning Database
Successful Patterns: {{successful_patterns}}
Common Mistakes: {{common_mistakes}}  
Best Practices: {{best_practices}}
User Coding Style: {{user_coding_style}}

## Recent Development Context
{{recent_code_context}}
{{recent_debugging_sessions}}

## Knowledge Graph Context
Related Code Patterns: {{related_code_patterns}}
Similar Solutions: {{similar_solutions}}
Dependency Relationships: {{dependency_relationships}}

Available Development Tools: {tools}

## Learning Protocol
1. **Before Coding**: Search memory for similar implementations
2. **During Coding**: Apply learned patterns and best practices
3. **After Coding**: Store successful patterns for future use
4. **On Errors**: Learn from mistakes and store solutions

## Memory Integration Examples
```bash
# Search for coding patterns
mcp__agent-memory__search_memory_nodes(
  query="implementation pattern [technology]",
  group_ids=["coding_patterns"],
  max_nodes=8
)

# Store successful implementations
mcp__agent-memory__add_memory(
  name="Success Pattern: [feature_type]",
  episode_body="Implementation approach that worked well",
  group_id="coding_patterns"
)
```

## Current Development Task
Help with the following development request, using your learned knowledge:

"""
```

### Progressive Learning Implementation

```python
async def implement_with_learning(self, task: str, context: Dict[str, Any]):
    """Implement task while learning from patterns"""
    
    # 1. Search for relevant patterns
    patterns = await self.search_memory_patterns(task)
    
    # 2. Apply learned approaches
    implementation_plan = self.create_plan_from_patterns(patterns, task)
    
    # 3. Execute with memory integration
    result = await self.execute_plan(implementation_plan)
    
    # 4. Store successful patterns
    if result.success:
        await self.store_success_pattern(task, implementation_plan, result)
    else:
        await self.store_failure_lesson(task, implementation_plan, result)
    
    return result

async def search_memory_patterns(self, task: str):
    """Search for relevant implementation patterns"""
    return await self.memory_client.search_nodes(
        query=f"implementation pattern {task}",
        group_ids=["coding_patterns", "genie_patterns"],
        max_nodes=10
    )
```

## 🔄 Full Development Workflow Example

### End-to-End Feature Implementation

Here's a complete example of implementing a new feature using the Automagik Agents framework:

#### 1. Linear Task Creation

```python
# Create Linear issue for new feature
linear_response = await linear_client.create_issue(
    title="🔸 Agent: Add Email Integration",
    description="""
## Feature Request
Implement email integration agent for reading and sending emails.

## Requirements
- Gmail API integration
- Email parsing and classification
- Template-based responses
- Memory integration for email patterns

## Acceptance Criteria
- [ ] Gmail API authentication
- [ ] Email reading functionality  
- [ ] Email sending with templates
- [ ] Memory storage for patterns
- [ ] Integration tests passing
""",
    team_id="2c6b21de-9db7-44ac-9666-9079ff5b9b84",
    label_ids=["b7099189-1c48-4bc6-b329-2f75223e3dd1", "500151c3-202d-4e32-80b8-82f97a3ffd0f"],
    priority=2
)

linear_task_id = linear_response.id  # e.g., "NMSTX-128"
```

#### 2. Memory Pattern Search

```python
# Search for similar implementation patterns
memory_patterns = await memory_client.search_nodes(
    query="email integration API authentication patterns",
    group_ids=["coding_patterns", "genie_patterns"],
    max_nodes=10
)

# Search for email-related procedures
email_procedures = await memory_client.search_nodes(
    query="email processing workflow",
    entity="Procedure",
    max_nodes=5
)
```

#### 3. Agent Implementation

```python
# src/agents/simple/email_agent/agent.py
class EmailAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        self._code_prompt_text = """You are {{agent_name}}, an email management specialist.

Email Management Style: {{email_management_style}}
Response Templates: {{email_templates}}
Processing Patterns: {{email_patterns}}

Recent Email Context:
{{recent_email_activity}}

Email Knowledge:
{{email_knowledge_facts}}

Available Email Tools: {tools}

## Email Capabilities
- Gmail API integration for reading/sending
- Intelligent email classification and routing
- Template-based responses with personalization
- Email thread management and tracking

## Email Processing Protocol
1. Authenticate with Gmail API using stored credentials
2. Parse incoming emails and extract key information
3. Classify emails by type, urgency, and required action
4. Generate appropriate responses using templates
5. Track email threads and maintain conversation context

Current email task:
"""

        self.dependencies = AutomagikAgentsDependencies(
            model_name="claude-3-5-sonnet-20241022"
        )
        
        self.tool_registry.register_default_tools(self.context)
        self._register_email_tools()
```

#### 4. Git Workflow with MCP Tools

```python
# Create feature branch using MCP git tools
await git_client.create_branch(
    repo_path="/root/workspace/am-agents-labs",
    branch_name="NMSTX-128-email-integration-agent",
    base_branch="main"
)

# Progressive commits during development
commits = [
    "feat(NMSTX-128): scaffold email agent structure",
    "feat(NMSTX-128): implement Gmail API authentication", 
    "feat(NMSTX-128): add email reading and parsing logic",
    "feat(NMSTX-128): implement template-based responses",
    "test(NMSTX-128): add email agent integration tests",
    "docs(NMSTX-128): document email agent usage"
]

for commit_msg in commits:
    # Make changes...
    await git_client.add(
        repo_path="/root/workspace/am-agents-labs",
        files=["src/agents/simple/email_agent/"]
    )
    await git_client.commit(
        repo_path="/root/workspace/am-agents-labs", 
        message=commit_msg
    )
```

#### 5. Store Learning Patterns

```python
# Store successful implementation pattern
await memory_client.add_memory(
    name="Implementation Success: Email Agent",
    episode_body="""
    Successful email agent implementation using:
    - Gmail API with OAuth2 authentication
    - Pydantic models for email data structures
    - Template system for response generation
    - Memory integration for learning user patterns
    - Progressive git commits with Linear ID references
    """,
    source="text",
    group_id="coding_patterns"
)

# Store email-specific patterns
await memory_client.add_memory(
    name="Email Processing Procedure",
    episode_body="""{
        "authentication": "OAuth2 with Gmail API",
        "parsing": "Extract headers, body, attachments",
        "classification": "Urgency, type, required_action",
        "response_generation": "Template-based with personalization",
        "thread_management": "Track conversation context"
    }""",
    source="json",
    group_id="genie_procedures"
)
```

#### 6. Update Linear and Complete

```python
# Update Linear task to completion
await linear_client.update_issue(
    id="NMSTX-128",
    state_id="1551da4c-03c1-4169-9690-8688f95f9e87"  # Done
)

# Add completion comment
await linear_client.create_comment(
    issue_id="NMSTX-128",
    body="""
## ✅ Email Integration Agent Complete

### Implemented Features
- [x] Gmail API authentication
- [x] Email reading and parsing
- [x] Template-based responses  
- [x] Memory pattern storage
- [x] Integration tests

### Key Patterns Stored
- Email authentication workflow
- Response template system
- Memory integration approach

### Branch: `NMSTX-128-email-integration-agent`
Ready for review and merge.
"""
)
```

## 🎭 Genie Orchestrator Example *(Future)*

### Epic-Level Feature Development

```python
# Example of how Genie will orchestrate complete epics
epic_config = {
    "epic_id": "user-authentication-system",
    "description": "Implement complete user authentication with OAuth2",
    "workflows": [
        {
            "name": "architect",
            "task": "Design authentication system architecture",
            "inputs": {"requirements": "OAuth2, JWT, role-based access"},
            "success_criteria": "Architecture document with clear implementation plan"
        },
        {
            "name": "implement", 
            "task": "Implement authentication system",
            "depends_on": ["architect"],
            "inputs": {"architecture": "{{architect.output}}"},
            "success_criteria": "Working authentication with tests"
        },
        {
            "name": "test",
            "task": "Comprehensive testing of auth system",
            "depends_on": ["implement"],
            "inputs": {"implementation": "{{implement.output}}"},
            "success_criteria": "95%+ test coverage, security validation"
        },
        {
            "name": "review",
            "task": "Code review and security audit",
            "depends_on": ["test"],
            "success_criteria": "Security approved, code quality standards met"
        }
    ],
    "human_intervention_points": [
        "after_architect",  # Review architecture before implementation
        "before_production"  # Final approval before deployment
    ],
    "rollback_points": [
        "post_architect",
        "post_implement", 
        "post_test"
    ]
}

# Genie executes this epic with full orchestration
await genie_orchestrator.execute_epic(epic_config)
```

## 📊 Monitoring and Analytics Example

### Performance Tracking Implementation

```python
class AgentPerformanceTracker:
    def __init__(self, memory_client):
        self.memory_client = memory_client
    
    async def track_agent_execution(self, agent_name: str, task: str, 
                                  execution_time: float, success: bool):
        """Track agent performance metrics"""
        
        performance_data = {
            "agent": agent_name,
            "task_type": task,
            "execution_time": execution_time,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store performance data
        await self.memory_client.add_memory(
            name=f"Performance: {agent_name}",
            episode_body=json.dumps(performance_data),
            source="json",
            group_id="performance_metrics"
        )
    
    async def analyze_performance_trends(self, agent_name: str):
        """Analyze performance trends for optimization"""
        
        # Search for performance data
        performance_facts = await self.memory_client.search_facts(
            query=f"performance metrics {agent_name}",
            group_ids=["performance_metrics"],
            max_facts=50
        )
        
        # Analyze and store insights
        insights = self.generate_performance_insights(performance_facts)
        
        await self.memory_client.add_memory(
            name=f"Performance Analysis: {agent_name}",
            episode_body=json.dumps(insights),
            source="json", 
            group_id="performance_analysis"
        )
        
        return insights
```

---

These implementation examples demonstrate how all the components of the Automagik Agents framework work together - from simple agents with memory integration to complex containerized workflows with learning capabilities. The key is understanding how memory, tools, and orchestration combine to create intelligent, adaptive AI systems. 