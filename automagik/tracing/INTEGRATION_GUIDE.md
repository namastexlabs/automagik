# Tracing Integration Guide

This guide shows how to integrate the tracing system into Automagik Agents.

## Current Status

### ✅ Implemented
- Core tracing infrastructure
- Telemetry collector with OTLP format
- LangWatch provider with basic integration
- Performance optimizations (circuit breaker, sampling, async)
- Privacy controls and opt-out mechanisms

### ❌ Not Yet Integrated
- AutomagikAgent doesn't use tracing yet
- CLI commands don't track usage
- API endpoints don't send telemetry
- No actual data being sent to https://telemetry.namastex.ai

## Integration Steps

### 1. Update AutomagikAgent Base Class

```python
# In automagik/agents/models/automagik_agent.py

from automagik.tracing import get_tracing_manager
from automagik.tracing.telemetry.cli_events import AgentExecutionEvent

class AutomagikAgent:
    def __init__(self, config: Dict[str, str]) -> None:
        # ... existing code ...
        
        # Initialize tracing
        self.tracing = get_tracing_manager()
        
    async def run(self, message_content: str, **kwargs) -> AgentResponse:
        """Run agent with tracing."""
        start_time = time.time()
        success = False
        
        try:
            # Determine sampling for observability
            if self.tracing.observability:
                sampling_decision = self.tracing.observability.sampler.should_sample(
                    trace_type=f"agent.{self.name}",
                    is_error=False
                )
                
                if sampling_decision.should_sample:
                    # Full observability tracing
                    with self.tracing.observability.providers["langwatch"].start_trace(
                        name=f"agent.{self.name}",
                        kind="agent_run",
                        attributes={
                            "agent.name": self.name,
                            "session.id": kwargs.get("session_id"),
                            "user.id": kwargs.get("user_id")
                        }
                    ):
                        result = await self._run_internal(message_content, **kwargs)
                else:
                    result = await self._run_internal(message_content, **kwargs)
            else:
                result = await self._run_internal(message_content, **kwargs)
            
            success = True
            return result
            
        except Exception as e:
            # Track error in telemetry
            if self.tracing.telemetry:
                self.tracing.telemetry.track_error(
                    error_type=type(e).__name__,
                    component=f"agent.{self.name}"
                )
            raise
            
        finally:
            # Always send telemetry (anonymous)
            duration_ms = (time.time() - start_time) * 1000
            
            if self.tracing.telemetry:
                event = AgentExecutionEvent(
                    agent_name=self.name,
                    framework=self.framework_type.value,
                    success=success,
                    duration_ms=duration_ms,
                    has_multimodal=bool(kwargs.get("multimodal_content")),
                    token_count=getattr(result, "total_tokens", None) if success else None,
                    anonymous_id=self.tracing.telemetry.anonymous_id,
                    session_id=self.tracing.telemetry.session_id
                )
                self.tracing.telemetry.track_event(event)
```

### 2. Add CLI Telemetry

```python
# In automagik/cli/agents.py

from automagik.tracing.integrations.cli import track_cli_command

@click.group()
def agents():
    """Manage AI agents"""
    pass

@agents.command()
@track_cli_command("agent list")
def list():
    """List all available agents"""
    # ... existing implementation ...

@agents.command()
@click.argument('agent_name')
@click.option('--message', '-m', required=True)
@track_cli_command("agent run")
def run(agent_name: str, message: str):
    """Run an agent"""
    # ... existing implementation ...
```

### 3. Add API Telemetry Middleware

```python
# In automagik/main.py

from automagik.tracing.integrations.api import TelemetryMiddleware

def create_app() -> FastAPI:
    # ... existing code ...
    
    # Add telemetry middleware
    app.add_middleware(TelemetryMiddleware)
    
    return app
```

### 4. Environment Configuration

```bash
# .env file

# Enable telemetry (opt-in)
AUTOMAGIK_TELEMETRY_ENABLED=true
AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces

# Enable observability providers
LANGWATCH_API_KEY=your-langwatch-key
LANGWATCH_ENDPOINT=https://app.langwatch.ai/api/v1/traces

# Optional: Disable in development
AUTOMAGIK_DISABLE_ALL_TRACING=false
```

## Data Flow

### Telemetry (Anonymous Usage)
1. User runs agent/CLI command/API request
2. Event is created with anonymous ID
3. Event is queued in AsyncTracer
4. Batch of events sent to https://telemetry.namastex.ai
5. Data used for:
   - Feature usage statistics
   - Performance monitoring
   - Error pattern detection
   - Framework preference tracking

### Observability (Detailed Traces)
1. User configures LangWatch API key
2. Agent execution is sampled (10% by default)
3. Full trace with LLM calls sent to LangWatch
4. Data includes:
   - Input/output messages
   - Token usage
   - Cost tracking
   - Tool executions

## Privacy Guarantees

### Telemetry
- No personal information
- No message content
- No file paths or secrets
- Only aggregate metrics

### Observability
- Requires explicit opt-in (API key)
- Only sent to configured providers
- User controls what's shared

## Testing Integration

```python
# Test telemetry is working
import os
os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"

from automagik.tracing import get_tracing_manager
tracing = get_tracing_manager()

# Check telemetry is active
assert tracing.telemetry is not None
assert tracing.config.telemetry_enabled is True

# Send test event
tracing.telemetry.track_feature_usage("test_feature")

# Check metrics
metrics = tracing.telemetry.get_metrics()
print(f"Events queued: {metrics['tracer']['queued']}")
print(f"Events sent: {metrics['tracer']['processed']}")
```

## Monitoring

```python
# Check tracing health
from automagik.tracing import get_tracing_manager

tracing = get_tracing_manager()
if tracing.telemetry:
    metrics = tracing.telemetry.get_metrics()
    print(f"Telemetry health: {metrics}")
    
if tracing.observability:
    providers = tracing.observability.get_active_providers()
    print(f"Active providers: {providers}")
```