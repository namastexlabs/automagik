# API Stress Testing Guide

This guide covers the stress testing tools available for the Automagik Agents API.

## Available Tools

### 1. Basic Agent Benchmark (`agent_run_bench.py`)
Simple benchmark focused on the agent run endpoint.

```bash
python scripts/benchmarks/agent_run_bench.py \
    --base-url http://localhost:8000 \
    --agent-name simple_agent \
    --concurrency 200 \
    --requests 1000
```

### 2. Comprehensive API Stress Test (`api_stress_test.py`)
Advanced stress testing with multiple test types and performance monitoring.

## Test Types

### Agent Run Test
Tests the primary agent execution endpoint with realistic payloads.

```bash
python scripts/benchmarks/api_stress_test.py \
    --base-url http://localhost:8000 \
    --api-key your-api-key \
    --test-type agent_run \
    --agent-name simple_agent \
    --concurrency 100 \
    --requests 500
```

### Session Queue Merging Test
**Validates the session queue fix** - tests rapid messages to the same session to verify merging behavior.

```bash
python scripts/benchmarks/api_stress_test.py \
    --base-url http://localhost:8000 \
    --api-key your-api-key \
    --test-type session_queue \
    --session-count 10 \
    --messages-per-session 20 \
    --concurrency 50
```

This test specifically validates:
- Multiple rapid messages to the same session are properly merged
- Session queue cancellation works under load
- No duplicate processing occurs
- Proper error handling under concurrent load

### Full API Test
Tests multiple endpoints with weighted distribution.

```bash
python scripts/benchmarks/api_stress_test.py \
    --base-url http://localhost:8000 \
    --api-key your-api-key \
    --test-type full_api \
    --concurrency 200 \
    --requests 1000
```

**Endpoint Distribution:**
- 60% - Agent run requests
- 10% - Agent list requests
- 10% - Session list requests  
- 10% - User creation requests
- 10% - Memory creation requests

## Performance Monitoring

The stress test tool monitors:

- **Latency Statistics**: Mean, median, 95th percentile, min/max
- **Throughput**: Requests per second
- **Error Rates**: Success/failure ratios with sample errors
- **Memory Usage**: Peak memory and growth during test
- **System Resources**: CPU usage, open files, connections

## Example Output

```
================================================================================
STRESS TEST RESULTS: Session Queue Merging Test
================================================================================

📊 SUMMARY:
  Total Requests: 200
  Successful: 195
  Failed: 5
  Error Rate: 2.50%
  Duration: 12.34 seconds
  Throughput: 16.21 req/sec

⏱️  LATENCY STATISTICS:
  Mean: 1,234.56 ms
  Median: 987.65 ms
  95th percentile: 2,345.67 ms
  Max: 3,456.78 ms
  Min: 123.45 ms

🖥️  PERFORMANCE MONITORING:
  Peak Memory: 245.3 MB
  Memory Growth: 12.7 MB
  Avg CPU: 45.2%
  Max Connections: 150
  Max Open Files: 85
```

## Configuration Options

### Common Parameters
- `--base-url`: API server URL (default: http://localhost:8000)
- `--api-key`: Required API key for authentication
- `--concurrency`: Number of concurrent requests (default: 100)
- `--requests`: Total number of requests (default: 500)
- `--timeout`: Request timeout in seconds (default: 30.0)
- `--verbose`: Enable verbose logging
- `--output`: Save results to JSON file

### Session Queue Specific
- `--session-count`: Number of unique sessions (default: 10)
- `--messages-per-session`: Messages per session (default: 20)

### Agent Specific
- `--agent-name`: Agent to test (default: simple_agent)

## Interpreting Results

### Key Metrics to Monitor

1. **Error Rate**: Should be < 1% under normal load
2. **95th Percentile Latency**: Important for user experience
3. **Memory Growth**: Should not grow continuously (memory leaks)
4. **Throughput**: Requests per second capacity

### Session Queue Validation

For session queue tests, look for:
- Low error rates despite rapid concurrent messages
- Consistent latency even with message merging
- No memory leaks from cancelled futures
- Proper cancellation behavior (check logs)

### Performance Baselines

Typical expectations for a well-configured system:
- **Throughput**: 50-200 req/sec (depends on agent complexity)
- **Latency**: < 2000ms for 95th percentile
- **Error Rate**: < 1%
- **Memory Growth**: < 50MB over 1000+ requests

## Troubleshooting

### High Error Rates
- Check API key authentication
- Verify database connectivity
- Monitor server logs for errors
- Check resource limits (connections, memory)

### High Latency
- Monitor database query performance
- Check session queue merging behavior
- Verify no blocking operations in event loop
- Review agent processing complexity

### Memory Growth
- Look for connection leaks
- Check session queue cleanup
- Monitor unclosed resources
- Review agent state management

## Integration with CI/CD

Example GitHub Actions step:

```yaml
- name: Run API Stress Test
  run: |
    python scripts/benchmarks/api_stress_test.py \
      --base-url http://localhost:8000 \
      --api-key ${{ secrets.API_KEY }} \
      --test-type session_queue \
      --concurrency 50 \
      --requests 200 \
      --output stress_test_results.json
      
- name: Check Performance Thresholds
  run: |
    python scripts/check_performance_thresholds.py \
      --results stress_test_results.json \
      --max-error-rate 0.01 \
      --max-p95-latency 2000
```

## Advanced Usage

### Custom Payload Testing
Modify `PayloadGenerator` class to test specific scenarios:

```python
# Test large payloads
def large_payload_test():
    return {
        "input_text": "x" * 10000,  # 10KB message
        "message_type": "text"
    }

# Test specific agent parameters
def custom_agent_payload():
    return {
        "input_text": "test message",
        "message_limit": 100,
        "preserve_system_prompt": True,
        "custom_param": "value"
    }
```

### Environment-Specific Testing

```bash
# Production-like load test
python scripts/benchmarks/api_stress_test.py \
    --base-url https://api.production.com \
    --api-key $PROD_API_KEY \
    --test-type full_api \
    --concurrency 500 \
    --requests 5000 \
    --timeout 60

# Session queue edge case testing
python scripts/benchmarks/api_stress_test.py \
    --base-url http://localhost:8000 \
    --api-key test-key \
    --test-type session_queue \
    --session-count 1 \
    --messages-per-session 100 \
    --concurrency 200
``` 