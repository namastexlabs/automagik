# Token Usage Tracking System

## Overview

The Token Usage Tracking System provides comprehensive monitoring and analytics for AI model token consumption across all agent interactions. This system tracks token usage at the message level and provides session, user, and agent-level analytics.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PydanticAI    │───▶│  AgentResponse   │───▶│ MessageHistory  │
│   Framework     │    │  (with usage)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Analytics     │◀───│ TokenAnalytics   │◀───│   Database      │
│   API Routes    │    │    Service       │    │ (messages.usage)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components

### 1. Database Layer

#### Migration
- **File**: `src/db/migrations/20250618_151523_add_usage_tracking_to_messages.sql`
- **Purpose**: Adds `usage` column to messages table
- **Features**:
  - SQLite/PostgreSQL compatible
  - JSON field for flexible usage data
  - Performance indexes on model and token fields

```sql
ALTER TABLE messages ADD COLUMN IF NOT EXISTS usage TEXT;
CREATE INDEX IF NOT EXISTS idx_messages_usage_model 
ON messages ((usage->>'model')) WHERE usage IS NOT NULL;
```

#### Models
- **File**: `src/db/models.py`
- **Updates**: Added `usage` field to Message model
- **Features**: JSON field with automatic serialization/deserialization

### 2. Agent Framework Integration

#### PydanticAI Framework
- **File**: `src/agents/models/ai_frameworks/pydantic_ai.py`
- **Method**: `extract_usage_info(result)`
- **Purpose**: Extracts token usage from PydanticAI results

**Usage Information Structure**:
```python
{
    "framework": "pydantic_ai",
    "model": "gpt-4",
    "total_requests": 1,
    "request_tokens": 100,
    "response_tokens": 200,
    "total_tokens": 300,
    "cache_creation_tokens": 25,
    "cache_read_tokens": 10,
    "per_message_usage": [...]
}
```

#### AgentResponse Enhancement
- **File**: `src/agents/models/response.py`
- **Addition**: `usage` field for carrying token information through pipeline

### 3. Message Pipeline Integration

#### Message Formatting
- **File**: `src/agents/common/message_parser.py`
- **Function**: `format_message_for_db()`
- **Enhancement**: Added `usage` parameter

#### AutomagikAgent Integration
- **File**: `src/agents/models/automagik_agent.py`
- **Integration**: Passes `response.usage` to message formatting

#### MessageHistory Storage
- **File**: `src/memory/message_history.py`
- **Method**: `add_response()`
- **Enhancement**: Accepts and stores usage information

### 4. Analytics Service

#### TokenAnalyticsService
- **File**: `src/services/token_analytics.py`
- **Purpose**: Provides comprehensive usage analytics

**Key Methods**:
- `get_session_usage_summary(session_id)` - Session-level analytics
- `get_user_usage_summary(user_id, days=30)` - User analytics
- `get_agent_usage_summary(agent_id, days=30)` - Agent analytics
- `get_top_usage_sessions(limit=10, days=7)` - High usage sessions

### 5. API Endpoints

#### Analytics Routes
- **File**: `src/api/routes/analytics_routes.py`
- **Prefix**: `/api/v1/analytics`

**Endpoints**:
- `GET /sessions/{session_id}/usage` - Session usage details
- `GET /users/{user_id}/usage?days=30` - User usage summary
- `GET /agents/{agent_id}/usage?days=30` - Agent usage summary
- `GET /sessions/top-usage?limit=10&days=7` - Top usage sessions

#### Session Enhancement
- **File**: `src/api/controllers/session_controller.py`
- **Enhancement**: Session details now include `token_analytics`

## Usage Data Flow

1. **Agent Execution**: PydanticAI framework extracts usage from API response
2. **Response Creation**: Usage data added to AgentResponse object
3. **Message Formatting**: Usage included in database message format
4. **Database Storage**: Usage stored as JSON in messages.usage column
5. **Analytics Retrieval**: TokenAnalyticsService queries and aggregates usage data
6. **API Exposure**: Analytics endpoints provide usage insights

## Configuration

### Environment Variables
No additional configuration required - system uses existing database settings.

### Database Compatibility
- **SQLite**: Uses JSON functions (JSON_EXTRACT)
- **PostgreSQL**: Uses JSONB operators (->>, ->>)

## API Usage Examples

### Session Usage Analytics
```bash
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8000/api/v1/analytics/sessions/{session_id}/usage"
```

**Response**:
```json
{
  "session_id": "uuid",
  "total_tokens": 750,
  "total_requests": 5,
  "models": [
    {
      "model": "gpt-4",
      "framework": "pydantic_ai",
      "message_count": 3,
      "total_tokens": 450,
      "request_tokens": 150,
      "response_tokens": 300
    }
  ],
  "summary": {
    "message_count": 5,
    "unique_models": 1,
    "total_request_tokens": 250,
    "total_response_tokens": 500
  }
}
```

### User Usage Analytics
```bash
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8000/api/v1/analytics/users/{user_id}/usage?days=30"
```

### Session with Analytics
Session details now automatically include token analytics:
```bash
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8000/api/v1/sessions/{session_id}"
```

## Testing

### Test Coverage
- **Service Tests**: `tests/services/test_token_analytics.py` (11 tests)
- **API Tests**: `tests/api/test_analytics_routes.py` (13 tests)  
- **Integration Tests**: `tests/agents/test_usage_tracking_integration.py` (9 tests)
- **Database Tests**: `tests/db/test_usage_tracking_db.py` (11 tests)

### Running Tests
```bash
# All token analytics tests
uv run pytest tests/services/test_token_analytics.py tests/api/test_analytics_routes.py -v

# Specific test categories
uv run pytest -m token_analytics
uv run pytest -m analytics_service
uv run pytest -m analytics_api
```

## Performance Considerations

### Database Indexes
- Index on `usage->>'model'` for model-based queries
- Index on `usage->>'total_tokens'` for usage-based sorting
- Index on `usage->>'framework'` for framework filtering

### Query Optimization
- Analytics queries use aggregation to minimize data transfer
- Date filtering reduces dataset size for recent analytics
- Pagination available for large result sets

## Future Enhancements

### Cost Calculation
The system is designed to support cost calculation without hardcoding pricing:
```python
# Future implementation
def calculate_costs(usage_data, pricing_config):
    cost = (
        usage_data["request_tokens"] * pricing_config["input_price"] +
        usage_data["response_tokens"] * pricing_config["output_price"]
    )
    return cost
```

### Additional AI Frameworks
The architecture supports adding other AI frameworks:
1. Implement framework-specific usage extraction
2. Update AgentResponse to include framework usage
3. Analytics service automatically handles all frameworks

### Real-time Monitoring
- WebSocket endpoints for real-time usage monitoring
- Usage alerts and thresholds
- Dashboard integration

## Troubleshooting

### Common Issues

#### Missing Usage Data
- **Cause**: Agent framework not extracting usage
- **Solution**: Check framework implementation of `extract_usage_info()`

#### Analytics Query Performance
- **Cause**: Large dataset, missing indexes
- **Solution**: Verify database indexes are created, use date filtering

#### Incorrect Token Counts
- **Cause**: Framework usage extraction errors
- **Solution**: Check logs for extraction errors, verify result format

### Debugging

Enable debug logging for detailed usage tracking:
```python
import logging
logging.getLogger("src.services.token_analytics").setLevel(logging.DEBUG)
logging.getLogger("src.agents.models.ai_frameworks").setLevel(logging.DEBUG)
```

## Integration with Existing Code

The token usage tracking system is designed to be non-intrusive:
- **Backward Compatible**: Existing code continues to work without modification
- **Optional Data**: Usage data is optional - missing usage doesn't break functionality
- **Graceful Degradation**: Analytics return empty results if no usage data available

## Security Considerations

- **API Authentication**: All analytics endpoints require API key authentication
- **Data Privacy**: Usage data doesn't contain message content, only metadata
- **Access Control**: Future enhancement could add user-specific access controls