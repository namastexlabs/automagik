# Conversation Branching - API Examples

## Complete Usage Examples

### Example 1: Customer Support Scenario

#### Initial Conversation

```bash
# Create initial message
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "customer-support-session-uuid",
    "user_id": "customer-uuid",
    "agent_id": 17,
    "role": "user",
    "text_content": "My order arrived damaged"
  }'

# Agent responds (automatically via agent execution)
# Response: "I'm sorry to hear that! Let me help you with this issue..."

# Customer provides more details
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "customer-support-session-uuid",
    "user_id": "customer-uuid", 
    "role": "user",
    "text_content": "The box was completely crushed"
  }'
```

#### Creating Different Resolution Branches

```bash
# Branch 1: Refund Path
curl -X POST "http://localhost:18881/api/v1/messages/{last-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "The box was crushed and I want a refund",
    "branch_name": "Refund Process",
    "run_agent": true
  }'

# Response:
{
  "status": "success",
  "branch_session_id": "refund-branch-uuid",
  "original_session_id": "customer-support-session-uuid",
  "branch_point_message_id": "crushed-box-message-uuid",
  "detail": "Branch created successfully"
}

# Branch 2: Replacement Path  
curl -X POST "http://localhost:18881/api/v1/messages/{last-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "The box was crushed, can I get a replacement?",
    "branch_name": "Replacement Process",
    "run_agent": true
  }'

# Branch 3: Discount Path
curl -X POST "http://localhost:18881/api/v1/messages/{last-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "The box was crushed, what compensation can you offer?",
    "branch_name": "Compensation Discussion", 
    "run_agent": true
  }'
```

#### Viewing All Branches

```bash
# Get all branches for the session
curl -X GET "http://localhost:18881/api/v1/sessions/customer-support-session-uuid/branches" \
  -H "X-API-Key: your-api-key"

# Response:
{
  "main_session": {
    "session_id": "customer-support-session-uuid",
    "session_name": "Customer Support Chat",
    "is_main_branch": true,
    "created_at": "2025-06-24T10:00:00Z"
  },
  "branches": [
    {
      "session_id": "refund-branch-uuid",
      "session_name": "Refund Process",
      "branch_type": "edit_branch",
      "branch_point_message_id": "crushed-box-message-uuid",
      "is_main_branch": false,
      "created_at": "2025-06-24T10:15:00Z"
    },
    {
      "session_id": "replacement-branch-uuid", 
      "session_name": "Replacement Process",
      "branch_type": "edit_branch",
      "branch_point_message_id": "crushed-box-message-uuid",
      "is_main_branch": false,
      "created_at": "2025-06-24T10:16:00Z"
    },
    {
      "session_id": "compensation-branch-uuid",
      "session_name": "Compensation Discussion",
      "branch_type": "edit_branch", 
      "branch_point_message_id": "crushed-box-message-uuid",
      "is_main_branch": false,
      "created_at": "2025-06-24T10:17:00Z"
    }
  ],
  "total_branches": 3
}
```

### Example 2: Technical Support with Progressive Branching

#### Initial Troubleshooting

```bash
# User reports issue
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "tech-support-uuid",
    "user_id": "user-uuid",
    "agent_id": 25,
    "role": "user", 
    "text_content": "My app keeps crashing when I try to upload files"
  }'

# Agent asks for details (automatic response)
# Agent: "What device and operating system are you using?"

# User provides initial answer
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "tech-support-uuid",
    "user_id": "user-uuid",
    "role": "user",
    "text_content": "iPhone"
  }'
```

#### Device-Specific Branches

```bash
# Create iPhone-specific branch (original path continues)
# Agent responds with iOS-specific troubleshooting...

# Create Android branch to explore alternative scenario
curl -X PUT "http://localhost:18881/api/v1/messages/{iphone-message-id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Android phone",
    "create_branch": true,
    "branch_name": "Android Troubleshooting",
    "run_agent": true
  }'

# Create desktop branch for comprehensive coverage
curl -X PUT "http://localhost:18881/api/v1/messages/{iphone-message-id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Windows desktop computer",
    "create_branch": true,
    "branch_name": "Desktop Troubleshooting", 
    "run_agent": true
  }'
```

#### Sub-branching for Specific Issues

```bash
# In the iPhone branch, create sub-branches for specific iOS versions
curl -X POST "http://localhost:18881/api/v1/messages/{ios-response-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "I'm using iOS 17.2 and the crash happens immediately",
    "branch_name": "iOS 17.2 Specific Issue",
    "run_agent": true
  }'

curl -X POST "http://localhost:18881/api/v1/messages/{ios-response-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "I'm using iOS 16.5 and it crashes after selecting the file",
    "branch_name": "iOS 16.5 Different Behavior",
    "run_agent": true
  }'
```

### Example 3: Educational Tutoring Session

#### Learning Path Exploration

```bash
# Student asks about learning programming
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "tutoring-session-uuid",
    "user_id": "student-uuid",
    "agent_id": 30,
    "role": "user",
    "text_content": "I want to learn programming but don't know where to start"
  }'

# Tutor agent responds with general guidance
# Agent: "Great! What type of projects interest you most?"

# Student gives initial answer
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "tutoring-session-uuid",
    "user_id": "student-uuid",
    "role": "user",
    "text_content": "I think web development sounds interesting"
  }'
```

#### Exploring Different Programming Paths

```bash
# Web Development Path (continues from original)
# Agent provides web development roadmap...

# Mobile Development Alternative
curl -X POST "http://localhost:18881/api/v1/messages/{web-interest-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Actually, mobile app development sounds more exciting",
    "branch_name": "Mobile Development Path", 
    "run_agent": true
  }'

# Data Science Alternative
curl -X POST "http://localhost:18881/api/v1/messages/{web-interest-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "I'm more interested in data science and AI",
    "branch_name": "Data Science Learning Path",
    "run_agent": true
  }'

# Game Development Alternative
curl -X POST "http://localhost:18881/api/v1/messages/{web-interest-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Game development would be amazing to learn",
    "branch_name": "Game Development Journey",
    "run_agent": true
  }'
```

### Example 4: Project Planning with Multiple Approaches

#### Initial Project Discussion

```bash
# Client describes project requirements
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "project-planning-uuid",
    "user_id": "client-uuid",
    "agent_id": 35,
    "role": "user",
    "text_content": "We need to build a system for managing customer orders"
  }'

# Consultant agent asks clarifying questions
# Agent: "What's your current order volume and expected growth?"

curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "project-planning-uuid", 
    "user_id": "client-uuid",
    "role": "user",
    "text_content": "We process about 1000 orders per month"
  }'
```

#### Architecture Exploration Branches

```bash
# Microservices Architecture Branch
curl -X POST "http://localhost:18881/api/v1/messages/{order-volume-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "1000 orders/month, expecting 10x growth, need scalable microservices",
    "branch_name": "Microservices Architecture Approach",
    "run_agent": true
  }'

# Monolithic Architecture Branch  
curl -X POST "http://localhost:18881/api/v1/messages/{order-volume-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "1000 orders/month, stable volume, prefer simple architecture",
    "branch_name": "Monolithic Architecture Approach",
    "run_agent": true
  }'

# SaaS Integration Branch
curl -X POST "http://localhost:18881/api/v1/messages/{order-volume-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "1000 orders/month, prefer using existing SaaS solutions",
    "branch_name": "SaaS Integration Approach",
    "run_agent": true
  }'
```

### Example 5: Debugging Session with Multiple Hypotheses

#### Initial Error Report

```bash
# Developer reports bug
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "debugging-session-uuid",
    "user_id": "developer-uuid", 
    "agent_id": 40,
    "role": "user",
    "text_content": "Getting intermittent 500 errors in production API"
  }'

# AI assistant starts investigation
# Agent: "Can you share the error logs and when this started?"

curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "debugging-session-uuid",
    "user_id": "developer-uuid",
    "role": "user", 
    "text_content": "Started after deployment yesterday, happens randomly"
  }'
```

#### Hypothesis Testing Branches

```bash
# Database Connection Hypothesis
curl -X POST "http://localhost:18881/api/v1/messages/{deployment-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Started after deployment, database queries timing out occasionally",
    "branch_name": "Database Connection Issue Investigation", 
    "run_agent": true
  }'

# Memory Leak Hypothesis
curl -X POST "http://localhost:18881/api/v1/messages/{deployment-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Started after deployment, server memory usage keeps climbing",
    "branch_name": "Memory Leak Investigation",
    "run_agent": true
  }'

# Third-party API Hypothesis
curl -X POST "http://localhost:18881/api/v1/messages/{deployment-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Started after deployment, external API calls failing sometimes",
    "branch_name": "Third-party API Issue Investigation",
    "run_agent": true
  }'
```

## Advanced Branch Management

### Viewing Conversation Evolution

```bash
# Get hierarchical view of all branches
curl -X GET "http://localhost:18881/api/v1/sessions/debugging-session-uuid/branch-tree" \
  -H "X-API-Key: your-api-key"

# Response shows complete tree structure:
{
  "root": {
    "session_id": "debugging-session-uuid",
    "session_name": "Production API Debugging",
    "is_main_branch": true,
    "created_at": "2025-06-24T14:00:00Z",
    "children": [
      {
        "session_id": "db-investigation-uuid",
        "session_name": "Database Connection Issue Investigation",
        "branch_type": "edit_branch",
        "is_main_branch": false
      },
      {
        "session_id": "memory-investigation-uuid", 
        "session_name": "Memory Leak Investigation",
        "branch_type": "edit_branch",
        "is_main_branch": false
      },
      {
        "session_id": "api-investigation-uuid",
        "session_name": "Third-party API Issue Investigation", 
        "branch_type": "edit_branch",
        "is_main_branch": false
      }
    ]
  },
  "total_sessions": 4
}
```

### Accessing Specific Branch Conversations

```bash
# View messages in a specific branch
curl -X GET "http://localhost:18881/api/v1/messages?session_id=db-investigation-uuid" \
  -H "X-API-Key: your-api-key"

# Continue conversation in specific branch
curl -X POST "http://localhost:18881/api/v1/messages" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "db-investigation-uuid",
    "user_id": "developer-uuid",
    "role": "user",
    "text_content": "Found the issue - connection pool was exhausted"
  }'
```

## Error Handling Examples

### Handling Invalid Branch Attempts

```bash
# Attempt to branch from non-existent message
curl -X POST "http://localhost:18881/api/v1/messages/invalid-uuid/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "This will fail",
    "branch_name": "Failed Branch",
    "run_agent": true
  }'

# Response:
{
  "detail": "Message with ID invalid-uuid not found."
}
```

### Handling Agent Execution Failures

```bash
# Branch creation with agent that doesn't exist
curl -X POST "http://localhost:18881/api/v1/messages/{valid-message-id}/branch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_message_content": "Test message",
    "branch_name": "Test Branch",
    "run_agent": true
  }'

# Branch creates successfully even if agent execution fails
# Check logs for agent execution issues:
# "No agent found for parent session {session_id}, skipping agent execution"
```

## Performance Testing Examples

### Load Testing Branch Creation

```bash
# Create multiple branches rapidly to test performance
for i in {1..10}; do
  curl -X POST "http://localhost:18881/api/v1/messages/{message-id}/branch" \
    -H "X-API-Key: your-api-key" \
    -H "Content-Type: application/json" \
    -d "{
      \"edited_message_content\": \"Test branch $i\",
      \"branch_name\": \"Performance Test Branch $i\",
      \"run_agent\": false
    }" &
done
wait

# Monitor response times and database performance
```

### Bulk Branch Operations

```bash
# Test retrieving large branch trees
curl -X GET "http://localhost:18881/api/v1/sessions/{session-with-many-branches}/branches" \
  -H "X-API-Key: your-api-key" \
  -w "Time: %{time_total}s\n"

# Test paginated message retrieval from branches
curl -X GET "http://localhost:18881/api/v1/messages?session_id={branch-session}&page_size=100" \
  -H "X-API-Key: your-api-key" \
  -w "Time: %{time_total}s\n"
```

These examples demonstrate comprehensive usage patterns for the conversation branching feature, covering real-world scenarios and edge cases that developers and users might encounter.