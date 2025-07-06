# Automagik Tracing System

A high-performance, privacy-first tracing system that provides both detailed observability and anonymous usage telemetry for Automagik Agents.

## Overview

The tracing system has two distinct layers:

1. **Observability Layer**: Detailed execution traces sent to providers like LangWatch, Langfuse
2. **Telemetry Layer**: Privacy-first anonymous usage analytics

## Quick Start

### Basic Usage

```python
from automagik.tracing import get_tracing_manager

# Get the global tracing manager
tracing = get_tracing_manager()

# Track agent execution (telemetry - anonymous)
if tracing.telemetry:
    tracing.telemetry.track_agent_run(
        agent_type="simple",
        framework="pydantic_ai",
        success=True,
        duration_ms=1234.5
    )

# Track feature usage
if tracing.telemetry:
    tracing.telemetry.track_feature_usage("multimodal_content")

# Track errors (no details, just type)
if tracing.telemetry:
    tracing.telemetry.track_error(
        error_type="TimeoutError",
        component="agent.simple"
    )
```

### Configuration

Configure via environment variables:

```bash
# Observability Providers (detailed traces)
export LANGWATCH_API_KEY=your-api-key
export LANGFUSE_PUBLIC_KEY=your-public-key
export LANGFUSE_SECRET_KEY=your-secret-key

# Privacy Controls
export AUTOMAGIK_DISABLE_ALL_TRACING=false  # Nuclear option
export AUTOMAGIK_OBSERVABILITY_ENABLED=true # Detailed traces
export AUTOMAGIK_TELEMETRY_ENABLED=true     # Anonymous analytics

# Performance Tuning
export AUTOMAGIK_TRACE_QUEUE_SIZE=10000
export AUTOMAGIK_TRACE_BATCH_SIZE=50
export AUTOMAGIK_SAMPLING_RATE=0.1  # 10% sampling
```

### Privacy Controls

Multiple ways to opt out:

```bash
# Environment variable
export AUTOMAGIK_DISABLE_ALL_TRACING=true

# Opt-out file
touch ~/.automagik-no-tracing

# CI environments are auto-disabled unless:
export AUTOMAGIK_ENABLE_TRACING_IN_CI=true
```

## Architecture

### Performance Features

- **Async Processing**: Non-blocking trace submission with background workers
- **Batch Processing**: Events are batched for efficient transmission
- **Circuit Breaker**: Auto-disables on failures to prevent cascading issues
- **Adaptive Sampling**: Intelligent sampling based on error/slow operations
- **Bounded Queues**: Memory-safe with automatic overflow handling

### Key Metrics

- **Latency Impact**: <1ms added latency (p99)
- **Memory Usage**: <50MB for trace buffers
- **CPU Overhead**: <0.5% usage
- **Throughput**: >10,000 events/second

## Integration Example

### With AutomagikAgent

```python
class MyAgent(AutomagikAgent):
    async def run(self, message_content: str, **kwargs):
        # Tracing is automatic via the base class
        # Just call the parent run method
        return await super().run(message_content, **kwargs)
```

### Manual Integration

```python
from automagik.tracing import get_tracing_manager
import time

async def my_function():
    tracing = get_tracing_manager()
    start_time = time.time()
    
    try:
        # Your code here
        result = await do_something()
        
        # Track success
        if tracing.telemetry:
            tracing.telemetry.track_feature_usage("my_feature")
        
        return result
        
    except Exception as e:
        # Track error (no details)
        if tracing.telemetry:
            tracing.telemetry.track_error(
                error_type=type(e).__name__,
                component="my_component"
            )
        raise
    
    finally:
        # Track timing
        duration_ms = (time.time() - start_time) * 1000
        # Log metrics...
```

## Telemetry Data

### What We Collect (Anonymous)

- Feature usage counts
- Error types (not messages)
- Performance metrics (duration, success rate)
- System info (OS, Python version)
- Anonymous session IDs

### What We DON'T Collect

- Personal information
- Actual message content
- File paths or secrets
- IP addresses or hostnames
- Error details or stack traces

## Observability Providers

### LangWatch

Full execution traces including:
- LLM interactions
- Tool executions
- Token usage
- Cost tracking

### Adding New Providers

Create a new provider by implementing the `ObservabilityProvider` interface:

```python
from automagik.tracing.observability.base import ObservabilityProvider

class MyProvider(ObservabilityProvider):
    def initialize(self, config):
        # Setup
        pass
    
    def log_llm_call(self, model, messages, response, usage):
        # Send to your service
        pass
```

## Development

### Running Tests

```bash
pytest tests/tracing/ -v
```

### Performance Testing

```python
# Monitor tracing overhead
metrics = tracing.telemetry.get_metrics()
print(f"Events processed: {metrics['tracer']['processed']}")
print(f"Events dropped: {metrics['tracer']['dropped']}")
print(f"Circuit breaker: {metrics['circuit_breaker']['state']}")
```

## Troubleshooting

### Tracing Not Working?

1. Check configuration:
   ```python
   tracing = get_tracing_manager()
   print(f"Telemetry enabled: {tracing.config.telemetry_enabled}")
   print(f"Observability enabled: {tracing.config.observability_enabled}")
   ```

2. Check for opt-out:
   ```bash
   ls ~/.automagik-no-tracing
   echo $AUTOMAGIK_DISABLE_ALL_TRACING
   ```

3. Check circuit breaker:
   ```python
   if tracing.telemetry:
       metrics = tracing.telemetry.get_metrics()
       print(metrics['circuit_breaker'])
   ```

### High Memory Usage?

Adjust queue sizes:
```bash
export AUTOMAGIK_TRACE_QUEUE_SIZE=1000  # Smaller queue
export AUTOMAGIK_TRACE_BATCH_SIZE=10    # Smaller batches
```

### Too Many Traces?

Adjust sampling rate:
```bash
export AUTOMAGIK_SAMPLING_RATE=0.01  # 1% sampling
```