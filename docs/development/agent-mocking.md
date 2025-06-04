# Agent Mocking Guide for Stress Testing

This guide demonstrates how to use Pydantic AI's mocking capabilities to test agents without expensive LLM provider calls.

## Overview

The enhanced stress testing framework now supports two modes:
- **API Mode**: Tests real API endpoints (original functionality)
- **Mock Mode**: Tests agents using mocked LLM responses (new feature)

## Benefits of Mocking

✅ **No Expensive API Calls**: Avoid charges from OpenAI, Anthropic, etc.  
✅ **Fast Execution**: Mock responses are instant  
✅ **Predictable Testing**: Consistent responses for CI/CD  
✅ **No Rate Limits**: Test at any concurrency level  
✅ **Offline Testing**: Works without internet connectivity  

## Setup Requirements

### Install Dependencies

```bash
# Install Pydantic AI for mocking
pip install pydantic-ai

# Install HTTP client for API testing  
pip install httpx

# Optional: Install psutil for performance monitoring
pip install psutil
```

### Verify Installation

```python
python scripts/benchmarks/test_agent_mocking.py
```

## Mock Types

### 1. TestModel (Simple & Fast)

TestModel generates valid structured responses based on agent schemas without any custom logic.

**Characteristics:**
- Fastest execution
- Generic responses
- Good for schema validation
- Minimal CPU/memory usage

**Example Usage:**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type test \
  --concurrency 100 \
  --requests 1000
```

### 2. FunctionModel (Customizable)

FunctionModel allows you to write custom response logic for more realistic testing.

**Characteristics:**
- Custom response logic
- Context-aware responses
- More realistic behavior
- Slightly higher overhead

**Example Usage:**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type function \
  --concurrency 50 \
  --requests 500
```

## Implementation Example

### Creating a Mocked Agent

```python
from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

# Safety: Prevent accidental real requests
models.ALLOW_MODEL_REQUESTS = False

# Simple TestModel
agent = Agent(TestModel(), system_prompt="You are a helpful assistant.")

# Custom FunctionModel
def smart_response(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    user_input = messages[-1].parts[-1].content.lower() if messages else ""
    
    if "weather" in user_input:
        response = "The weather is sunny and 72°F today."
    elif "joke" in user_input:
        response = "Why don't scientists trust atoms? Because they make up everything!"
    else:
        response = f"I understand you're asking about: {user_input}"
    
    return ModelResponse(parts=[TextPart(response)])

agent = Agent(FunctionModel(smart_response), system_prompt="Smart assistant.")

# Test the agent
result = await agent.run("What's the weather like?")
print(result.output)  # "The weather is sunny and 72°F today."
```

### Testing with Context Override

```python
# Override model for testing
with agent.override(model=TestModel()):
    result = await agent.run("Test message")
    
# Original agent remains unchanged after context
```

## Command Line Usage

### Mock Mode Examples

```bash
# Basic mocking test
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type test \
  --requests 100

# High concurrency mocking
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type function \
  --concurrency 200 \
  --requests 2000

# With verbose output and file export
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type test \
  --concurrency 100 \
  --requests 1000 \
  --verbose \
  --output mock_results.json
```

### API Mode Examples (Original)

```bash
# Real API testing (requires API key)
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type agent_run \
  --concurrency 50 \
  --requests 200

# Session queue testing
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type session_queue \
  --session-count 10 \
  --messages-per-session 5
```

## Performance Comparison

| Aspect | Mock Mode | API Mode |
|--------|-----------|----------|
| Cost | Free | $$ (provider charges) |
| Speed | ~1000+ req/sec | ~10-50 req/sec |
| Rate Limits | None | Provider dependent |
| Internet Required | No | Yes |
| Response Quality | Predictable | Variable |
| Use Case | Development/Testing | Production validation |

## Sample Output

```
============================================================
STRESS TEST RESULTS: Mocked Agent Test (test)
============================================================

📊 SUMMARY:
  Total Requests: 1000
  Successful: 1000
  Failed: 0
  Error Rate: 0.00%
  Duration: 2.45 seconds
  Throughput: 408.16 req/sec

⏱️  LATENCY STATISTICS:
  Mean: 2.12 ms
  Median: 1.98 ms
  95th percentile: 4.33 ms
  Max: 8.91 ms
  Min: 0.85 ms

🖥️  PERFORMANCE MONITORING:
  Peak Memory: 145.2 MB
  Memory Growth: 12.3 MB
  Avg CPU: 35.8%
  Max Connections: 0
  Max Open Files: 24
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Agent Performance Tests

on: [push, pull_request]

jobs:
  mock-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install pydantic-ai httpx
    
    - name: Run mock performance tests
      run: |
        python scripts/benchmarks/api_stress_test.py \
          --mode mock \
          --mock-type test \
          --concurrency 100 \
          --requests 500 \
          --output mock_results.json
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: mock-test-results
        path: mock_results.json
```

## Best Practices

### 1. Development Workflow
```bash
# Start with mocking for rapid development
python scripts/benchmarks/api_stress_test.py --mode mock --mock-type test

# Graduate to function mocking for realism  
python scripts/benchmarks/api_stress_test.py --mode mock --mock-type function

# Final validation with real API
python scripts/benchmarks/api_stress_test.py --mode api --api-key YOUR_KEY
```

### 2. Custom Mock Logic

```python
def realistic_mock(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # Extract user intent
    user_input = messages[-1].parts[-1].content if messages else ""
    
    # Simulate processing time occasionally
    if random.random() < 0.1:
        await asyncio.sleep(0.1)
    
    # Context-aware responses
    if "error" in user_input.lower():
        # Simulate occasional errors for testing
        raise ValueError("Simulated processing error")
    
    # Generate response based on patterns
    return generate_contextual_response(user_input)
```

### 3. Performance Baselines

Use mocking to establish performance baselines:
- Expected throughput under different loads
- Memory usage patterns
- Error handling behavior
- Concurrency limits

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'pydantic_ai'**
   ```bash
   pip install pydantic-ai
   ```

2. **ALLOW_MODEL_REQUESTS errors**
   ```python
   # Always set this when using mocks
   models.ALLOW_MODEL_REQUESTS = False
   ```

3. **Mock responses too generic**
   - Use FunctionModel instead of TestModel
   - Add custom response logic
   - Include context awareness

### Debug Mode

```bash
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type function \
  --verbose \
  --requests 10
```

## Advanced Usage

### Custom Agent Creation

```python
from pydantic_ai.tools import Tool

# Create agent with tools and mocking
@dataclasses.dataclass
class WeatherDeps:
    api_key: str

def mock_weather_tool(ctx, location: str) -> str:
    return f"Weather in {location}: 72°F and sunny"

agent = Agent(
    TestModel(),
    deps_type=WeatherDeps,
    system_prompt="You are a weather assistant."
)

agent.tool(mock_weather_tool)

# Test with dependencies
result = await agent.run(
    "What's the weather in NYC?",
    deps=WeatherDeps(api_key="mock_key")
)
```

## Conclusion

The mocking capabilities provide a powerful way to:
- Develop and test agents without costs
- Establish performance baselines
- Run comprehensive test suites in CI/CD
- Debug agent behavior in isolation

Use mocking for development and testing, then validate with real APIs before production deployment. 