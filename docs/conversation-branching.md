# Conversation Branching - Messages API

## Overview

The Conversation Branching feature allows users to edit any message in a conversation and create alternative conversation paths. This enables exploring different conversation directions without losing the original thread, similar to version control for conversations.

## Key Features

- **Edit and Branch**: Edit any message and create a new conversation branch
- **Automatic Agent Execution**: Optionally re-run agents from the edited message point
- **Independent Development**: Each branch evolves independently
- **Complete History**: Original conversations remain unchanged
- **API Management**: Full REST API for managing branches and trees

## Visual Overview

### Basic Conversation Flow

```
Original Conversation:
┌─────────────────────────────────────────────────┐
│ Session: main-conversation                      │
├─────────────────────────────────────────────────┤
│ [1] User: "Hello, I need help with my project" │
│ [2] Agent: "I'd be happy to help! What kind   │
│           of project are you working on?"      │
│ [3] User: "It's a web application"             │
│ [4] Agent: "Great! What framework are you      │
│           using?"                              │
└─────────────────────────────────────────────────┘
```

### Branching Example

```
After editing message [3] and creating a branch:

Original Session: main-conversation
┌─────────────────────────────────────────────────┐
│ [1] User: "Hello, I need help with my project" │
│ [2] Agent: "I'd be happy to help! What kind   │
│           of project are you working on?"      │
│ [3] User: "It's a web application"             │ ◄─── Branch Point
│ [4] Agent: "Great! What framework are you      │
│           using?"                              │
└─────────────────────────────────────────────────┘
                    │
                    └─── branches to
                    
New Branch Session: mobile-app-branch
┌─────────────────────────────────────────────────┐
│ [1] User: "Hello, I need help with my project" │ ◄─── Copied
│ [2] Agent: "I'd be happy to help! What kind   │ ◄─── Copied  
│           of project are you working on?"      │
│ [3] User: "It's a mobile application"          │ ◄─── Edited Content
│ [4] Agent: "Excellent! Are you developing for │ ◄─── New Agent Response
│           iOS, Android, or cross-platform?"    │
└─────────────────────────────────────────────────┘
```

### Hierarchical Branch Structure

```
Session Tree Visualization:

main-conversation (root)
├── web-framework-branch
│   ├── react-specialization-branch  
│   └── vue-specialization-branch
├── mobile-app-branch
│   ├── ios-native-branch
│   └── flutter-branch
└── desktop-app-branch
    └── electron-branch
```

## API Endpoints

### 1. Direct Branching

**Create a conversation branch from any message:**

```http
POST /api/v1/messages/{message_id}/branch
```

**Request Body:**
```json
{
  "edited_message_content": "It's a mobile application",
  "branch_name": "Mobile App Discussion",
  "run_agent": true
}
```

**Response:**
```json
{
  "status": "success",
  "branch_session_id": "uuid-of-new-branch",
  "original_session_id": "uuid-of-original-session",
  "branch_point_message_id": "uuid-of-branched-message",
  "detail": "Branch created successfully"
}
```

### 2. Inline Branching

**Update a message with branching option:**

```http
PUT /api/v1/messages/{message_id}
```

**Request Body:**
```json
{
  "text_content": "Actually, it's a mobile application",
  "create_branch": true,
  "branch_name": "Mobile App Path",
  "run_agent": true
}
```

### 3. Session Branch Management

**List all branches for a session:**

```http
GET /api/v1/sessions/{session_id}/branches
```

**Response:**
```json
{
  "main_session": {
    "session_id": "main-session-uuid",
    "session_name": "Original Conversation",
    "is_main_branch": true,
    "created_at": "2025-06-24T10:00:00Z"
  },
  "branches": [
    {
      "session_id": "branch-1-uuid",
      "session_name": "Mobile App Discussion",
      "branch_type": "edit_branch",
      "branch_point_message_id": "message-uuid",
      "is_main_branch": false,
      "created_at": "2025-06-24T11:00:00Z"
    }
  ],
  "total_branches": 1
}
```

**Get hierarchical branch tree:**

```http
GET /api/v1/sessions/{session_id}/branch-tree
```

## Agent Execution Flow

### Automatic Agent Re-execution

When `run_agent: true` is specified, the system:

1. **Identifies the Agent**: Retrieves agent information from the parent session
2. **Creates Agent Context**: Builds conversation context up to the branch point
3. **Executes Agent**: Runs the agent with the edited message content
4. **Stores Response**: Saves the agent's response in the new branch session

### Flow Diagram

```
User Edits Message → Create Branch → Copy History → Execute Agent → Save Response
       │                 │              │             │            │
       │                 │              │             │            │
   ┌───▼───┐        ┌────▼────┐    ┌────▼────┐   ┌────▼────┐  ┌───▼────┐
   │ Edit  │        │ New     │    │ Copy    │   │ Agent   │  │ Agent  │
   │Message│        │ Branch  │    │ Message │   │ Execution│  │Response│
   │Content│        │ Session │    │ History │   │ Trigger │  │ Stored │
   └───────┘        └─────────┘    └─────────┘   └─────────┘  └────────┘
```

## Use Cases

### 1. Exploring Different Solutions

**Scenario**: User asks about building an app, then wants to explore both web and mobile options.

```
Original: "I want to build an app" → "What type of app?"
├── Branch 1: "A web application" → Web-specific guidance
└── Branch 2: "A mobile app" → Mobile-specific guidance
```

### 2. Correcting Misunderstandings

**Scenario**: User realizes they provided incorrect information and wants to correct it.

```
Original: "I'm using React" → React-specific advice
└── Branch: "Actually, I'm using Vue" → Vue-specific advice (new branch)
```

### 3. Testing Different Approaches

**Scenario**: Trying different conversation strategies with an AI agent.

```
Original: "I'm feeling stressed" → General advice
├── Branch 1: "I'm stressed about work" → Work-specific guidance  
└── Branch 2: "I'm stressed about relationships" → Relationship guidance
```

## Database Schema

### Session Branching Fields

```sql
ALTER TABLE sessions ADD COLUMN parent_session_id UUID;
ALTER TABLE sessions ADD COLUMN branch_point_message_id UUID;
ALTER TABLE sessions ADD COLUMN branch_type session_branch_type;
ALTER TABLE sessions ADD COLUMN is_main_branch BOOLEAN DEFAULT true;

-- Foreign key constraints
ALTER TABLE sessions ADD CONSTRAINT sessions_parent_session_id_fkey
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id) ON DELETE CASCADE;

ALTER TABLE sessions ADD CONSTRAINT sessions_branch_point_message_id_fkey
    FOREIGN KEY (branch_point_message_id) REFERENCES messages(id) ON DELETE SET NULL;
```

### Branch Types

```sql
CREATE TYPE session_branch_type AS ENUM ('edit_branch', 'manual_branch');
```

- **edit_branch**: Created by editing an existing message
- **manual_branch**: Created programmatically or through other means

## Implementation Details

### Message History Copying

When a branch is created:

1. **Identify Branch Point**: Find the message being edited
2. **Copy Previous Messages**: Copy all messages created before the branch point
3. **Create Edited Message**: Insert the new edited message content
4. **Maintain Timestamps**: Preserve original message creation times for copied messages

### Session Relationships

```sql
-- Find all branches of a session
WITH RECURSIVE session_branches AS (
    SELECT s.*, 0 as depth
    FROM sessions s 
    WHERE s.id = $root_session_id
    
    UNION ALL
    
    SELECT s.*, sb.depth + 1
    FROM sessions s
    INNER JOIN session_branches sb ON s.parent_session_id = sb.id
)
SELECT * FROM session_branches WHERE depth > 0;
```

## Error Handling

### Robust Branch Creation

- **Agent Execution Failures**: Branch creation succeeds even if agent execution fails
- **Database Constraints**: Foreign key constraints ensure data integrity
- **Session Validation**: Parent sessions must exist before creating branches
- **Message Validation**: Branch point messages must exist in the parent session

### Error Responses

```json
{
  "detail": "Message with ID {message_id} not found."
}
```

```json
{
  "detail": "Parent session not found."
}
```

```json
{
  "detail": "Failed to create conversation branch due to an internal error."
}
```

## Performance Considerations

### Indexes

```sql
-- Optimized queries for branch operations
CREATE INDEX idx_sessions_parent_session_id ON sessions(parent_session_id);
CREATE INDEX idx_sessions_branch_point_message_id ON sessions(branch_point_message_id);
CREATE INDEX idx_sessions_is_main_branch ON sessions(is_main_branch);
```

### Query Optimization

- **Recursive CTEs**: Use depth limits to prevent infinite recursion
- **Pagination**: Support for paginated branch listings
- **Selective Loading**: Load only necessary branch metadata for tree views

## Best Practices

### 1. Branch Naming

```json
{
  "branch_name": "Mobile App Discussion - iOS Focus",
  "branch_name": "Project Requirements - Alternative Approach",
  "branch_name": "Debugging Session - Memory Issue Path"
}
```

### 2. Agent Execution Strategy

- Set `run_agent: true` when you want the AI to continue the conversation
- Set `run_agent: false` when you only want to edit without AI response
- Consider the context and conversation flow before triggering agents

### 3. Branch Management

- Use descriptive branch names for easy identification
- Regularly clean up unused branches in long-running conversations
- Monitor branch depth to avoid overly complex conversation trees

## Security Considerations

### Access Control

- All branching endpoints require API authentication
- Users can only branch their own conversations (when user authentication is implemented)
- Branch operations respect existing session permissions

### Data Integrity

- Foreign key constraints prevent orphaned branches
- Message copying preserves original content integrity
- Branch metadata is immutable after creation

## Monitoring and Analytics

### Metrics to Track

- **Branch Creation Rate**: How often users create branches
- **Agent Execution Success**: Success rate of agent runs in branches
- **Branch Depth**: Average and maximum depth of conversation trees
- **Branch Adoption**: Which branches users continue developing

### Logging

The system logs all branch operations:

```
INFO: Created branch session {branch_id} from parent {parent_id}
INFO: Copied messages to branch session {branch_id}
INFO: Triggering agent execution for branch session {branch_id}
INFO: Agent execution completed successfully for branch {branch_id}
```

## Future Enhancements

### Planned Features

1. **Branch Merging**: Ability to merge insights from different branches
2. **Branch Visualization**: Web UI for visualizing conversation trees
3. **Branch Templates**: Pre-defined branching patterns for common scenarios
4. **Branch Analytics**: Detailed analytics on branch usage and effectiveness
5. **Collaborative Branching**: Multiple users working on different branches
6. **Branch Notifications**: Alerts when branches are created or updated

### API Versioning

The branching API is designed with extensibility in mind:

```http
GET /api/v1/sessions/{id}/branches
GET /api/v2/sessions/{id}/branches  # Future enhanced version
```

## Troubleshooting

### Common Issues

**Q: Branch creation succeeds but agent doesn't respond**
A: Check that the parent session has an associated agent_id. Review logs for agent execution errors.

**Q: "Session not found" error when accessing branches**  
A: Ensure you're using the correct session UUID and that the session exists in the database.

**Q: Branch tree shows incomplete hierarchy**
A: This may indicate database constraint violations. Check foreign key relationships.

### Debug Commands

```bash
# Check recent branch operations
make logs | grep -i "branch\|agent execution"

# Verify session relationships
curl -X GET "/api/v1/sessions/{session_id}/branches" -H "X-API-Key: your-key"

# Test agent execution
curl -X POST "/api/v1/messages/{message_id}/branch" \
  -H "X-API-Key: your-key" \
  -d '{"edited_message_content": "test", "run_agent": true}'
```

## Conclusion

The Conversation Branching feature provides a powerful way to explore multiple conversation paths while maintaining conversation history and enabling automatic agent participation. This feature is essential for complex conversations where users need to explore different directions or correct misunderstandings without losing valuable context.

The implementation is production-ready with comprehensive error handling, proper database constraints, and full API coverage for managing conversation branches and trees.