---
description: "Task Master system integration - mandatory for all substantial development work"
globs:
  - "**/tasks/**"
  - "**/tasks.json"
  - "**/*.task.md"
  - "**/scripts/**"
alwaysApply: true
priority: 1
---

# Task Master System Integration

**MANDATORY**: Use Task Master for ALL substantial development work in automagik-agents. This system ensures organized, trackable, and systematic development.

## 🚨 CRITICAL WORKFLOW

### Before Starting ANY Development

1. **Initialize Project**:
```bash
mcp_taskmaster-ai_initialize_project --projectRoot "/home/namastex/workspace/am-agents-labs"
```

2. **Parse Requirements** (if you have a PRD or feature description):
```bash
mcp_taskmaster-ai_parse_prd --projectRoot "/home/namastex/workspace/am-agents-labs" --numTasks 10
```

3. **Get Next Task**:
```bash
mcp_taskmaster-ai_next_task --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### During Development

4. **Mark Task In Progress**:
```bash
mcp_taskmaster-ai_set_task_status --id "1" --status "in-progress" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

5. **Add Subtasks** (for complex tasks):
```bash
mcp_taskmaster-ai_expand_task --id "1" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

6. **Update Progress**:
```bash
mcp_taskmaster-ai_update_subtask --id "1.1" --prompt "Implemented core logic, tested successfully" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### After Completion

7. **Mark Complete**:
```bash
mcp_taskmaster-ai_set_task_status --id "1" --status "done" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

## 📋 Task Creation Patterns

### Agent Development Tasks
```bash
# Create agent development task
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --prompt "Create new WhatsApp agent with Evolution API integration"

# Expand into subtasks
mcp_taskmaster-ai_expand_task --id "2" --num "5" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### API Development Tasks
```bash
# Create API task
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --prompt "Add new endpoint for agent memory management"

# Add dependencies
mcp_taskmaster-ai_add_dependency --id "3" --dependsOn "1" --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### Tool Integration Tasks
```bash
# Create tool task
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --prompt "Integrate Notion API for agent data storage"

# Use research mode for complex integrations
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --prompt "Research and implement Discord slash commands" --research true
```

## 🎯 Task Prioritization

### HIGH PRIORITY - Use Task Master For:
- **New agent development**
- **API endpoint creation**
- **Tool integrations**
- **Major feature additions**
- **Bug fixes affecting multiple components**
- **Documentation updates**

### MEDIUM PRIORITY - Optional Task Master:
- **Code formatting/cleanup**
- **Simple configuration changes**
- **Minor bug fixes**

### LOW PRIORITY - No Task Master Needed:
- **Single line fixes**
- **Comment updates**
- **Import reorganization**

## 📊 Task Management Commands

### Project Overview
```bash
# Get all tasks
mcp_taskmaster-ai_get_tasks --projectRoot "/home/namastex/workspace/am-agents-labs"

# Get specific task details
mcp_taskmaster-ai_get_task --id "1" --projectRoot "/home/namastex/workspace/am-agents-labs"

# Generate task files
mcp_taskmaster-ai_generate --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### Task Analysis
```bash
# Analyze project complexity
mcp_taskmaster-ai_analyze_project_complexity --projectRoot "/home/namastex/workspace/am-agents-labs"

# Expand all pending tasks
mcp_taskmaster-ai_expand_all --projectRoot "/home/namastex/workspace/am-agents-labs"
```

### Dependency Management
```bash
# Validate dependencies
mcp_taskmaster-ai_validate_dependencies --projectRoot "/home/namastex/workspace/am-agents-labs"

# Fix dependency issues
mcp_taskmaster-ai_fix_dependencies --projectRoot "/home/namastex/workspace/am-agents-labs"
```

## 🔄 Integration with Automagik Agents

### Agent Development Workflow
1. **Task**: "Create Discord agent with slash command support"
2. **Subtasks**: 
   - Setup Discord bot configuration
   - Implement AutomagikAgent subclass
   - Add slash command handlers
   - Integrate with memory system
   - Write tests and documentation

### Tool Development Workflow
1. **Task**: "Add Gmail integration for agent email capabilities"
2. **Subtasks**:
   - Research Gmail API patterns
   - Create tool schema definitions
   - Implement async business logic
   - Add error handling and validation
   - Register tool globally

### API Development Workflow
1. **Task**: "Extend agent API with bulk operations"
2. **Subtasks**:
   - Design bulk operation schemas
   - Implement route handlers
   - Add authentication middleware
   - Update API documentation
   - Write integration tests

## 📁 Task File Organization

Task Master creates this structure:
```
tasks/
├── tasks.json              # Main task database
├── 01-agent-development.md  # Individual task files
├── 02-api-endpoints.md
└── complexity-report.json   # Analysis results
```

## 🧠 Memory Integration

Always add insights to memory:
```bash
# Add project insights
mcp_memories_add_memories --text "Successfully implemented WhatsApp agent using Evolution API - key patterns: async message handling, webhook integration, session management"

# Search for related work
mcp_memories_search_memory --query "Discord agent implementation"
```

## 🚦 Quality Control

### Before Task Completion
- [ ] All subtasks marked as done
- [ ] Code follows automagik-agents patterns
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Memory updated with insights

### Task Review Criteria
- **Follows AutomagikAgent patterns**
- **Integrates with memory system**
- **Uses proper async/await**
- **Includes error handling**
- **Has comprehensive tests**

## 🎲 Quick Task Templates

### New Agent Template
```bash
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --title "Create [ServiceName] Agent" --description "Implement agent for [service] integration with [specific features]" --details "1. Extend AutomagikAgent\n2. Configure service tools\n3. Add memory templates\n4. Implement message processing\n5. Write tests"
```

### Tool Integration Template
```bash
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --title "Add [ServiceName] Tool Integration" --description "Create tool package for [service] API" --details "1. Create tool schema\n2. Implement async provider\n3. Add business logic\n4. Register globally\n5. Write tests"
```

### API Endpoint Template
```bash
mcp_taskmaster-ai_add_task --projectRoot "/home/namastex/workspace/am-agents-labs" --title "Add [FeatureName] API Endpoint" --description "Implement REST endpoint for [feature]" --details "1. Define Pydantic models\n2. Create route handlers\n3. Add authentication\n4. Update documentation\n5. Write tests"
```

---

**Remember**: Task Master is not optional for substantial work. It ensures systematic development, tracks progress, and maintains quality standards for the automagik-agents framework.
