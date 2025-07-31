# LangWatch Tracing Enhancements

## Overview

This document describes the enhancements made to the LangWatch integration to create beautiful, properly structured spans following LangWatch best practices and industry standards for observability.

## 🎯 Key Improvements

### 1. Enhanced Tool Call Tracing

**Before:**
- Basic tool calls logged as simple events
- No categorization or context
- Limited metadata

**After:**
- ✅ **Tool Categorization**: Tools are automatically categorized (Memory, DateTime, Communication, Multimodal, etc.)
- ✅ **Proper Span Structure**: Each tool call creates a dedicated span with proper parent-child relationships
- ✅ **Rich Context**: Includes duration, input/output, error handling
- ✅ **Security**: Input/output sanitization to prevent sensitive data leakage

### 2. Memory Operations as Dedicated Spans

**New Feature:**
- Memory operations (store, retrieve, list) are tracked as separate, specialized spans
- Enhanced context including operation type, key, content length
- Performance tracking with duration measurements
- Error handling for failed memory operations

### 3. Enhanced LLM Call Tracing

**Improvements:**
- ✅ **Vendor Detection**: Automatic detection of LLM vendor (OpenAI, Anthropic, Google, etc.)
- ✅ **Complete Conversation History**: Full message history including system prompts
- ✅ **Token Usage Tracking**: Detailed usage metrics for cost analysis
- ✅ **Model Parameters**: Temperature, max_tokens, and other configuration

### 4. Rich Metadata and Context

**New Fields:**
- `user_id`: User identification for analytics
- `thread_id`: Conversation grouping
- `customer_id`: Multi-tenancy support
- `session_id`: Session tracking
- `agent_id`: Agent instance identification
- `framework`: AI framework used (pydantic_ai, langchain, etc.)
- `multimodal`: Whether multimodal content was processed

### 5. Proper Span Relationships

- ✅ **Parent-Child Relationships**: Tool calls and memory operations properly linked to their parent spans
- ✅ **Hierarchical Structure**: Clear trace hierarchy for complex agent workflows
- ✅ **Span Naming**: Descriptive span names following LangWatch conventions

## 🛠️ Technical Implementation

### Enhanced LangWatch Provider

The `LangWatchProvider` class has been significantly enhanced with:

#### New Methods

1. **`log_memory_operation()`**
   ```python
   def log_memory_operation(
       self,
       operation: str,  # "store", "retrieve", "list"
       key: Optional[str] = None,
       content: Optional[str] = None,
       result: Any = None,
       duration_ms: Optional[float] = None,
       error: Optional[str] = None
   ) -> None:
   ```

2. **Enhanced `log_tool_call()`**
   ```python
   def log_tool_call(
       self,
       tool_name: str,
       args: Dict[str, Any],
       result: Any,
       duration_ms: Optional[float] = None,  # NEW
       error: Optional[str] = None           # NEW
   ) -> None:
   ```

#### Utility Methods

- `_categorize_tool()`: Automatic tool categorization
- `_detect_llm_vendor()`: LLM vendor detection
- `_sanitize_tool_args()`: Input sanitization for security
- `_sanitize_tool_result()`: Output sanitization

### LangWatch API Format

The provider now sends properly formatted spans to LangWatch:

#### Tool Call Span Example
```json
{
  "type": "span",
  "span_id": "tool-span-uuid",
  "parent_span_id": "parent-span-uuid",
  "name": "DateTime: get_current_time",
  "input": {
    "type": "json",
    "value": {"format": null}
  },
  "output": {
    "type": "json",
    "value": {
      "result": "14:30:25",
      "status": "success"
    }
  },
  "metrics": {
    "duration_ms": 50.19
  },
  "timestamps": {
    "started_at": 1751890811425,
    "finished_at": 1751890811475
  }
}
```

#### Memory Operation Span Example
```json
{
  "type": "span",
  "span_id": "memory-span-uuid",
  "parent_span_id": "parent-span-uuid",
  "name": "Memory: store",
  "input": {
    "type": "json",
    "value": {
      "operation": "store",
      "key": "user_preferences",
      "content_length": 47
    }
  },
  "output": {
    "type": "json",
    "value": {
      "result": "Memory stored successfully with ID: mem_456",
      "status": "success"
    }
  },
  "metrics": {
    "duration_ms": 80.19
  }
}
```

#### Enhanced LLM Span Example
```json
{
  "type": "llm",
  "span_id": "llm-span-uuid",
  "vendor": "openai",
  "model": "gpt-4-turbo",
  "input": {
    "type": "chat_messages",
    "value": [
      {"role": "system", "content": "You are a helpful assistant..."},
      {"role": "user", "content": "What time is it?"}
    ]
  },
  "output": {
    "type": "chat_messages",
    "value": [
      {"role": "assistant", "content": "The current time is 14:30:25"}
    ]
  },
  "params": {
    "temperature": 0.1,
    "max_tokens": 1000
  },
  "metrics": {
    "prompt_tokens": 145,
    "completion_tokens": 32,
    "total_tokens": 177
  }
}
```

#### Enhanced Trace Metadata
```json
{
  "trace_id": "trace-uuid",
  "user_id": "user-123",
  "thread_id": "thread-456",
  "customer_id": "customer-abc",
  "metadata": {
    "agent_name": "SimpleAgent",
    "agent_id": "simple-001",
    "framework": "pydantic_ai",
    "session_id": "session-789",
    "multimodal": false,
    "model": "gpt-4-turbo",
    "temperature": 0.1,
    "max_tokens": 1000,
    "tools_used": ["get_current_time", "store_memory"],
    "execution_duration_ms": 250,
    "success": true
  }
}
```

## 🔒 Security & Privacy Enhancements

### Input/Output Sanitization

- **Sensitive Data Redaction**: Automatic redaction of fields containing passwords, tokens, keys, secrets
- **Content Truncation**: Large inputs/outputs are truncated to prevent memory issues
- **Size Limits**: Enforced limits on trace payload sizes

### Privacy Controls

- All existing privacy controls maintained
- Enhanced opt-out mechanisms
- Sensitive data filtering at the provider level

## 📊 Dashboard Experience

With these enhancements, the LangWatch dashboard will show:

### Beautiful Span Visualization
- **Categorized Tool Calls**: Tool spans grouped by category (Memory, DateTime, Communication)
- **Hierarchical Structure**: Clear parent-child relationships
- **Rich Context**: Full input/output context with proper formatting

### Enhanced Filtering & Analysis
- **User Analytics**: Filter traces by user_id
- **Conversation Flows**: Group related traces by thread_id
- **Multi-tenancy**: Separate traces by customer_id
- **Performance Analysis**: Duration metrics for all operations

### Error Tracking
- **Failed Tool Calls**: Clearly marked error spans with error details
- **Memory Operation Failures**: Dedicated error tracking for memory operations
- **Communication Failures**: Network and service error tracking

### Usage Analytics
- **Token Usage**: Detailed LLM usage tracking for cost analysis
- **Tool Usage Patterns**: Understanding which tools are used most frequently
- **Performance Metrics**: Operation duration analysis

## 🧪 Testing

A comprehensive test suite has been created:

### Test Files

1. **`test_langwatch_integration_simple.py`**: Standalone demo of enhanced features
2. **`test_tracing_tool_calls.py`**: Full integration test with SimpleAgent

### Test Coverage

- ✅ Tool call tracing with categorization
- ✅ Memory operation tracing
- ✅ LLM call tracing with enhanced metadata
- ✅ Error handling and edge cases
- ✅ Input/output sanitization
- ✅ Performance measurement
- ✅ Metadata logging

### Running Tests

```bash
# Simple demonstration
python3 test_langwatch_integration_simple.py

# Full integration test (requires dependencies)
python3 test_tracing_tool_calls.py
```

## 🚀 Benefits

### For Developers
- **Better Debugging**: Clear trace hierarchy and rich context
- **Performance Insights**: Detailed timing information for optimization
- **Error Analysis**: Enhanced error tracking and diagnosis

### For Product Teams
- **User Behavior**: Understanding how users interact with agents
- **Feature Usage**: Which tools and capabilities are most valuable
- **Performance Monitoring**: System performance and reliability metrics

### For Business
- **Cost Analysis**: Detailed LLM usage and cost tracking
- **Customer Insights**: Multi-tenant analytics and usage patterns
- **Quality Metrics**: Success rates and error patterns

## 🔄 Migration Guide

### For Existing Code

The enhancements are backward compatible. Existing code will continue to work, but to take advantage of new features:

1. **Update Tool Calls**: Add duration and error parameters
   ```python
   # Before
   provider.log_tool_call("tool_name", args, result)
   
   # After (enhanced)
   provider.log_tool_call("tool_name", args, result, duration_ms=50, error=None)
   ```

2. **Add Memory Operation Tracking**:
   ```python
   provider.log_memory_operation(
       operation="store",
       key="user_pref",
       content="preference data",
       result="success",
       duration_ms=80
   )
   ```

3. **Enhanced Metadata**:
   ```python
   provider.log_metadata({
       "user_id": "user-123",
       "thread_id": "thread-456",
       "customer_id": "customer-abc",
       # ... other metadata
   })
   ```

### Configuration

No configuration changes required. All enhancements work with existing LangWatch API keys and endpoints.

## 📋 Future Enhancements

### Planned Features
- [ ] RAG operation spans for document retrieval
- [ ] Multimodal content spans for image/audio processing
- [ ] Workflow spans for complex agent orchestration
- [ ] Custom span types for domain-specific operations

### Integration Opportunities
- [ ] Integration with AutomagikAgent base class
- [ ] Automatic tool call interception
- [ ] CLI command tracing
- [ ] API endpoint tracing middleware

## 🎉 Conclusion

These enhancements transform the LangWatch integration from basic event logging to a comprehensive observability solution that provides deep insights into agent behavior, performance, and user interactions. The implementation follows LangWatch best practices and industry standards for observability, creating beautiful, actionable traces that enable better debugging, optimization, and business insights.

The enhanced spans are properly structured, categorized, and enriched with metadata that makes them valuable for developers, product teams, and business stakeholders alike.