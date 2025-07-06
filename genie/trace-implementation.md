# Trace Implementation Plan for Automagik Agents

## Overview

This document outlines the implementation plan for adding comprehensive tracing to Automagik Agents. We need to support two distinct types of tracing:

1. **Observability Tracing** (LangWatch, Langfuse, etc.) - Detailed execution traces with actual data
2. **Usage Telemetry** (Privacy-first analytics) - Anonymous feature usage for open-source insights

## Architecture Separation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Automagik Agents                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐    │
│  │   Observability Layer        │    │    Usage Telemetry Layer        │    │
│  │   (Detailed Traces)          │    │    (Anonymous Analytics)        │    │
│  │                              │    │                                 │    │
│  │  • LangWatch                 │    │  • Feature usage counts         │    │
│  │  • Langfuse                  │    │  • Command execution stats      │    │
│  │  • LangSmith                 │    │  • Framework selection metrics  │    │
│  │  • Honeycomb                 │    │  • Error patterns (no details)  │    │
│  │  • Custom OTLP               │    │  • Performance aggregates       │    │
│  │                              │    │                                 │    │
│  │  [Contains actual data]      │    │  [No PII or actual content]     │    │
│  └─────────────────────────────┘    └─────────────────────────────────┘    │
│                     │                                 │                      │
│  ┌──────────────────┴─────────────────────────────────┴──────────────────┐  │
│  │                    OpenTelemetry SDK (Shared Core)                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Create Base Tracing Module Structure
```
automagik/tracing/
├── __init__.py
├── core.py                 # Core tracing manager
├── observability/          # Detailed tracing providers
│   ├── __init__.py
│   ├── base.py            # Base provider interface
│   ├── langwatch.py       # LangWatch integration
│   ├── langfuse.py        # Langfuse integration
│   └── adapters/          # Framework-specific adapters
│       ├── pydantic_ai.py # PydanticAI to OTLP adapter
│       └── agno.py        # Agno to OTLP adapter
├── telemetry/             # Usage telemetry
│   ├── __init__.py
│   ├── collector.py       # Anonymous usage collector
│   ├── events.py          # Event definitions
│   └── privacy.py         # Privacy filters
└── config.py              # Configuration management
```

#### 1.2 Core Tracing Manager
```python
# automagik/tracing/core.py
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import os

@dataclass
class TracingConfig:
    """Configuration for tracing systems"""
    # Observability settings
    observability_enabled: bool = True
    observability_providers: List[str] = None
    
    # Telemetry settings  
    telemetry_enabled: bool = True
    telemetry_endpoint: str = "https://telemetry.namastex.ai/v1/traces"
    telemetry_anonymous_id: Optional[str] = None
    
    # Privacy settings
    disable_all_tracing: bool = False
    disable_in_ci: bool = True
    
    @classmethod
    def from_env(cls) -> 'TracingConfig':
        """Load configuration from environment"""
        config = cls()
        
        # Global disable
        if os.getenv("AUTOMAGIK_DISABLE_ALL_TRACING", "false").lower() == "true":
            config.disable_all_tracing = True
            return config
            
        # Observability configuration
        config.observability_enabled = os.getenv(
            "AUTOMAGIK_OBSERVABILITY_ENABLED", "true"
        ).lower() == "true"
        
        # Telemetry configuration
        config.telemetry_enabled = os.getenv(
            "AUTOMAGIK_TELEMETRY_ENABLED", "true"
        ).lower() == "true"
        
        # Auto-disable in CI unless explicitly enabled
        if any(os.getenv(var) for var in ["CI", "GITHUB_ACTIONS"]):
            if os.getenv("AUTOMAGIK_ENABLE_TRACING_IN_CI", "false").lower() != "true":
                config.disable_in_ci = True
                config.observability_enabled = False
                config.telemetry_enabled = False
        
        return config

class TracingManager:
    """Central manager for all tracing systems"""
    
    def __init__(self):
        self.config = TracingConfig.from_env()
        self.observability = None
        self.telemetry = None
        
        if not self.config.disable_all_tracing:
            self._initialize_systems()
    
    def _initialize_systems(self):
        """Initialize tracing systems based on configuration"""
        if self.config.observability_enabled:
            from .observability import ObservabilityManager
            self.observability = ObservabilityManager(self.config)
            
        if self.config.telemetry_enabled:
            from .telemetry import TelemetryCollector
            self.telemetry = TelemetryCollector(self.config)
```

### Phase 2: Observability Layer (Week 2)

#### 2.1 Base Provider Interface
```python
# automagik/tracing/observability/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, ContextManager
from dataclasses import dataclass

@dataclass
class TraceContext:
    """Context for a trace span"""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any]

class ObservabilityProvider(ABC):
    """Base class for observability providers"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the provider with configuration"""
        pass
    
    @abstractmethod
    def start_trace(self, name: str, kind: str, attributes: Dict[str, Any]) -> ContextManager[TraceContext]:
        """Start a new trace span"""
        pass
    
    @abstractmethod
    def log_llm_call(self, model: str, messages: List[Dict], response: Any, usage: Dict[str, Any]) -> None:
        """Log LLM interaction with full details"""
        pass
    
    @abstractmethod
    def log_tool_call(self, tool_name: str, args: Dict, result: Any) -> None:
        """Log tool/function execution"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Cleanup provider resources"""
        pass
```

#### 2.2 LangWatch Provider Implementation
```python
# automagik/tracing/observability/langwatch.py
import os
from typing import Any, Dict, List, ContextManager
from contextlib import contextmanager
from langwatch import LangWatch
from .base import ObservabilityProvider, TraceContext

class LangWatchProvider(ObservabilityProvider):
    """LangWatch observability provider"""
    
    def __init__(self):
        self.client = None
        self.enabled = False
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize LangWatch client"""
        api_key = os.getenv("LANGWATCH_API_KEY")
        if not api_key:
            return
            
        self.client = LangWatch(api_key=api_key)
        self.enabled = True
        
    @contextmanager
    def start_trace(self, name: str, kind: str, attributes: Dict[str, Any]) -> ContextManager[TraceContext]:
        """Start a LangWatch trace"""
        if not self.enabled:
            yield TraceContext(trace_id="disabled", span_id="disabled", attributes={})
            return
            
        trace = self.client.trace()
        trace.update(
            name=name,
            type=kind,
            metadata=attributes
        )
        
        try:
            yield TraceContext(
                trace_id=trace.trace_id,
                span_id=trace.span_id,
                attributes=attributes
            )
        finally:
            trace.end()
    
    def log_llm_call(self, model: str, messages: List[Dict], response: Any, usage: Dict[str, Any]) -> None:
        """Log LLM interaction to LangWatch"""
        if not self.enabled:
            return
            
        self.client.log_llm_call(
            model=model,
            input_messages=messages,
            output=response,
            metrics={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cost": usage.get("cost_usd", 0)
            }
        )
    
    def log_tool_call(self, tool_name: str, args: Dict, result: Any) -> None:
        """Log tool execution to LangWatch"""
        if not self.enabled:
            return
            
        self.client.log_tool_call(
            name=tool_name,
            input=args,
            output=result
        )
    
    def shutdown(self) -> None:
        """Cleanup LangWatch resources"""
        if self.client:
            self.client.flush()
```

#### 2.3 Framework Adapters
```python
# automagik/tracing/observability/adapters/pydantic_ai.py
from typing import Any, Dict
from pydantic_ai import Agent
from pydantic_ai.result import RunResult
from ..base import ObservabilityProvider

class PydanticAIAdapter:
    """Adapter to bridge PydanticAI with observability providers"""
    
    def __init__(self, provider: ObservabilityProvider):
        self.provider = provider
        
    def wrap_agent_run(self, agent: Agent, original_run):
        """Wrap PydanticAI agent run method with tracing"""
        async def traced_run(*args, **kwargs):
            # Start trace
            with self.provider.start_trace(
                name=f"pydantic_ai.{agent.name}",
                kind="agent_run",
                attributes={
                    "agent.name": agent.name,
                    "agent.model": str(agent.model),
                    "framework": "pydantic_ai"
                }
            ) as trace_context:
                # Run original method
                result: RunResult = await original_run(*args, **kwargs)
                
                # Log LLM interactions from result
                if hasattr(result, 'all_messages'):
                    messages = result.all_messages()
                    # Extract and log each LLM call
                    for message in messages:
                        if hasattr(message, 'usage'):
                            self.provider.log_llm_call(
                                model=str(agent.model),
                                messages=[{"role": "user", "content": args[0]}],
                                response=result.data,
                                usage={
                                    "input_tokens": message.usage.request_tokens,
                                    "output_tokens": message.usage.response_tokens,
                                    "total_tokens": message.usage.total_tokens
                                }
                            )
                
                return result
                
        return traced_run
```

### Phase 3: Usage Telemetry Layer (Week 3)

#### 3.1 Event Definitions
```python
# automagik/tracing/telemetry/events.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class EventType(Enum):
    """Telemetry event types"""
    # Agent events
    AGENT_RUN = "agent.run"
    AGENT_ERROR = "agent.error"
    
    # Framework events
    FRAMEWORK_SELECTED = "framework.selected"
    
    # Tool events
    TOOL_EXECUTED = "tool.executed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    
    # System events
    STARTUP = "system.startup"
    FEATURE_USED = "feature.used"

@dataclass
class TelemetryEvent:
    """Base telemetry event"""
    event_type: EventType
    timestamp: float
    anonymous_id: str
    session_id: str
    
    # High-level attributes only (no actual content)
    attributes: Dict[str, Any]
    
    def to_otlp_span(self) -> Dict[str, Any]:
        """Convert to OTLP span format"""
        return {
            "name": self.event_type.value,
            "attributes": {
                "event.type": self.event_type.value,
                "user.anonymous_id": self.anonymous_id,
                "session.id": self.session_id,
                **self._sanitize_attributes(self.attributes)
            }
        }
    
    def _sanitize_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any potentially sensitive data"""
        sanitized = {}
        
        # Whitelist of allowed attribute patterns
        allowed_prefixes = [
            "agent.type", "agent.framework", "framework.name",
            "tool.type", "workflow.type", "error.type",
            "feature.name", "duration_ms", "success"
        ]
        
        for key, value in attrs.items():
            if any(key.startswith(prefix) for prefix in allowed_prefixes):
                # Further sanitize values
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                sanitized[key] = value
                
        return sanitized
```

#### 3.2 Privacy-First Collector
```python
# automagik/tracing/telemetry/collector.py
import hashlib
import time
from typing import Optional, Dict, Any
from collections import defaultdict
from pathlib import Path
import json

class TelemetryCollector:
    """Collects anonymous usage telemetry"""
    
    def __init__(self, config):
        self.config = config
        self.anonymous_id = self._get_anonymous_id()
        self.session_id = self._generate_session_id()
        self.event_buffer = []
        self.feature_counters = defaultdict(int)
        
    def _get_anonymous_id(self) -> str:
        """Get or create persistent anonymous ID"""
        id_file = Path.home() / ".automagik" / "anonymous_id"
        
        if id_file.exists():
            return id_file.read_text().strip()
            
        # Generate new anonymous ID
        # Use machine characteristics but hash them for privacy
        import platform
        machine_data = f"{platform.system()}-{platform.machine()}"
        anonymous_id = hashlib.sha256(machine_data.encode()).hexdigest()[:16]
        
        # Save for consistency
        id_file.parent.mkdir(exist_ok=True, parents=True)
        id_file.write_text(anonymous_id)
        
        return anonymous_id
    
    def track_agent_run(self, agent_type: str, framework: str, success: bool, duration_ms: float):
        """Track agent execution (no content)"""
        self.track_event(EventType.AGENT_RUN, {
            "agent.type": agent_type,  # e.g., "simple", "claude_code"
            "agent.framework": framework,  # e.g., "pydantic_ai", "agno"
            "success": success,
            "duration_ms": int(duration_ms)
        })
        
    def track_feature_usage(self, feature_name: str):
        """Track feature usage"""
        self.feature_counters[feature_name] += 1
        self.track_event(EventType.FEATURE_USED, {
            "feature.name": feature_name
        })
    
    def track_error(self, error_type: str, component: str):
        """Track error occurrence (no details)"""
        # Only track error type, not the actual error message
        self.track_event(EventType.AGENT_ERROR, {
            "error.type": error_type,  # e.g., "timeout", "api_error"
            "component": component
        })
```

### Phase 4: Integration Points (Week 4)

#### 4.1 Agent Integration
```python
# Update automagik/agents/models/automagik_agent.py

from automagik.tracing import get_tracing_manager

class AutomagikAgent:
    def __init__(self, config: Dict[str, str]) -> None:
        # ... existing code ...
        
        # Initialize tracing
        self.tracing = get_tracing_manager()
        
    async def run(self, message_content: str, **kwargs) -> AgentResponse:
        """Run agent with integrated tracing"""
        start_time = time.time()
        success = False
        
        try:
            # Observability tracing (if enabled)
            if self.tracing.observability:
                # Wrap the actual run with observability
                with self.tracing.observability.trace_agent_run(
                    agent_name=self.name,
                    session_id=kwargs.get("session_id"),
                    message_preview=message_content[:100]  # Limited preview
                ):
                    response = await self._run_with_framework(message_content, **kwargs)
            else:
                response = await self._run_with_framework(message_content, **kwargs)
            
            success = True
            return response
            
        except Exception as e:
            # Track error in telemetry (no details)
            if self.tracing.telemetry:
                self.tracing.telemetry.track_error(
                    error_type=type(e).__name__,
                    component=f"agent.{self.name}"
                )
            raise
            
        finally:
            # Usage telemetry (always anonymous)
            duration_ms = (time.time() - start_time) * 1000
            if self.tracing.telemetry:
                self.tracing.telemetry.track_agent_run(
                    agent_type=self.name,
                    framework=self.framework_type.value,
                    success=success,
                    duration_ms=duration_ms
                )
```

#### 4.2 Workflow Integration
```python
# Update automagik/agents/claude_code/agent.py

from automagik.tracing import get_tracing_manager

class ClaudeCodeAgent:
    async def run_workflow(self, workflow_name: str, *args, **kwargs):
        """Run workflow with tracing"""
        tracing = get_tracing_manager()
        
        # Start observability trace
        if tracing.observability:
            trace_context = tracing.observability.start_workflow_trace(
                workflow_name=workflow_name,
                run_id=kwargs.get("run_id")
            )
        
        # Track workflow start in telemetry
        if tracing.telemetry:
            tracing.telemetry.track_event(EventType.WORKFLOW_STARTED, {
                "workflow.type": workflow_name
            })
        
        try:
            result = await self._execute_workflow(workflow_name, *args, **kwargs)
            
            # Track completion
            if tracing.telemetry:
                tracing.telemetry.track_event(EventType.WORKFLOW_COMPLETED, {
                    "workflow.type": workflow_name,
                    "success": True
                })
                
            return result
            
        except Exception as e:
            if tracing.telemetry:
                tracing.telemetry.track_error(
                    error_type=type(e).__name__,
                    component=f"workflow.{workflow_name}"
                )
            raise
```

### Phase 5: Configuration & CLI (Week 5)

#### 5.1 Environment Configuration
```bash
# .env.example

# === OBSERVABILITY PROVIDERS ===
# These send detailed traces with actual data
# Choose which providers to enable

# LangWatch - https://langwatch.ai
LANGWATCH_API_KEY=your-api-key-here
LANGWATCH_ENDPOINT=https://app.langwatch.ai/api/v1/traces

# Langfuse - https://langfuse.com  
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com

# LangSmith - https://smith.langchain.com
LANGSMITH_API_KEY=your-api-key
LANGSMITH_PROJECT=automagik-agents

# === USAGE TELEMETRY ===
# Anonymous usage analytics for open source insights
AUTOMAGIK_TELEMETRY_ENABLED=true  # Set to false to disable
AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces

# === PRIVACY CONTROLS ===
AUTOMAGIK_DISABLE_ALL_TRACING=false  # Nuclear option - disables everything
AUTOMAGIK_OBSERVABILITY_ENABLED=true  # Control detailed tracing
AUTOMAGIK_ENABLE_TRACING_IN_CI=false  # Enable in CI environments
```

#### 5.2 CLI Commands
```python
# automagik/cli/commands/tracing.py

@click.group()
def tracing():
    """Manage tracing and observability"""
    pass

@tracing.command()
def status():
    """Show current tracing configuration"""
    manager = get_tracing_manager()
    config = manager.config
    
    click.echo("🔭 Tracing Configuration\n")
    
    # Observability status
    click.echo("📊 Observability (Detailed Tracing):")
    click.echo(f"   Status: {'Enabled' if config.observability_enabled else 'Disabled'}")
    
    if config.observability_enabled:
        providers = manager.observability.get_active_providers()
        click.echo(f"   Active Providers: {', '.join(providers) or 'None'}")
        click.echo("   Data Sent: Full execution traces, LLM calls, tool usage")
    
    # Telemetry status
    click.echo("\n📈 Usage Telemetry (Anonymous Analytics):")
    click.echo(f"   Status: {'Enabled' if config.telemetry_enabled else 'Disabled'}")
    
    if config.telemetry_enabled:
        click.echo(f"   Anonymous ID: {manager.telemetry.anonymous_id}")
        click.echo("   Data Sent: Feature usage, error types, performance metrics")
        click.echo("   No Personal Data: ✓")

@tracing.command()
@click.option('--observability/--no-observability', help='Enable/disable detailed tracing')
@click.option('--telemetry/--no-telemetry', help='Enable/disable usage analytics')
def configure(observability, telemetry):
    """Configure tracing settings"""
    # Implementation to update .env or config file
    pass
```

## Migration Strategy

### From Logfire to Unified Tracing

1. **Keep Logfire Running** (Month 1)
   - Add new tracing alongside Logfire
   - No disruption to existing monitoring

2. **Dual Running** (Month 2)
   - Run both systems in parallel
   - Compare data quality and completeness
   - Fix any gaps in new system

3. **Gradual Migration** (Month 3)
   - Move PydanticAI agents to new system
   - Deprecate Logfire usage
   - Full cutover

## Privacy & Security Considerations

### Observability Layer
- Contains actual user data and LLM interactions
- Requires explicit opt-in via API keys
- Data sent to third-party services
- Follow each provider's security guidelines

### Telemetry Layer  
- NO personal data or content
- Anonymous IDs only
- Aggregated metrics
- Self-hosted endpoint option
- GDPR compliant by design

## Testing Strategy

### Unit Tests
```python
# tests/tracing/test_telemetry_privacy.py
def test_telemetry_sanitization():
    """Ensure no PII leaks in telemetry"""
    event = TelemetryEvent(
        event_type=EventType.AGENT_RUN,
        attributes={
            "agent.type": "simple",
            "user_message": "My SSN is 123-45-6789",  # Should be filtered
            "api_key": "sk-secret",  # Should be filtered
        }
    )
    
    sanitized = event.to_otlp_span()
    assert "user_message" not in sanitized["attributes"]
    assert "api_key" not in sanitized["attributes"]
    assert "agent.type" in sanitized["attributes"]
```

### Integration Tests
- Test each observability provider
- Verify telemetry data format
- Check privacy filters work
- Validate opt-out mechanisms

## Performance Optimization Strategies

### 1. Asynchronous Non-Blocking Design
```python
# automagik/tracing/performance/async_tracer.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional
import queue
import threading

class AsyncTracer:
    """High-performance async tracer with minimal overhead"""
    
    def __init__(self, max_workers: int = 2, queue_size: int = 10000):
        # Use bounded queue to prevent memory issues
        self.event_queue = queue.Queue(maxsize=queue_size)
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tracer")
        self.running = True
        self._start_background_workers()
        
    def _start_background_workers(self):
        """Start background threads for trace processing"""
        for _ in range(2):  # 2 worker threads
            self.executor.submit(self._process_events)
    
    def _process_events(self):
        """Process events in background thread"""
        while self.running:
            try:
                # Batch processing for efficiency
                batch = []
                # Wait up to 100ms for first event
                batch.append(self.event_queue.get(timeout=0.1))
                
                # Collect up to 50 more events without waiting
                for _ in range(49):
                    try:
                        batch.append(self.event_queue.get_nowait())
                    except queue.Empty:
                        break
                
                # Process batch
                if batch:
                    self._send_batch(batch)
                    
            except queue.Empty:
                continue
            except Exception as e:
                # Never crash - log and continue
                logger.debug(f"Tracer error: {e}")
    
    def trace_event(self, event: Dict[str, Any]) -> None:
        """Add event to queue - returns immediately"""
        try:
            # Non-blocking put with timeout
            self.event_queue.put_nowait(event)
        except queue.Full:
            # Drop event rather than block
            logger.debug("Trace queue full, dropping event")
```

### 2. Lazy Initialization
```python
# automagik/tracing/core.py
class TracingManager:
    """Lazy-loading tracing manager"""
    
    def __init__(self):
        self._observability = None
        self._telemetry = None
        self._initialized = False
        
    @property
    def observability(self):
        """Lazy load observability only when needed"""
        if self._observability is None and not self._initialized:
            self._initialize_observability()
        return self._observability
        
    @property  
    def telemetry(self):
        """Lazy load telemetry only when needed"""
        if self._telemetry is None and not self._initialized:
            self._initialize_telemetry()
        return self._telemetry
        
    def _initialize_observability(self):
        """Initialize only if API keys are present"""
        if any([
            os.getenv("LANGWATCH_API_KEY"),
            os.getenv("LANGFUSE_PUBLIC_KEY"),
            os.getenv("LANGSMITH_API_KEY")
        ]):
            from .observability import ObservabilityManager
            self._observability = ObservabilityManager()
```

### 3. Sampling Strategies
```python
# automagik/tracing/performance/sampling.py
import random
import time
from typing import Dict, Any

class AdaptiveSampler:
    """Adaptive sampling to reduce trace volume"""
    
    def __init__(self, base_rate: float = 0.1):
        self.base_rate = base_rate  # 10% default sampling
        self.error_rate = 1.0  # Always sample errors
        self.slow_threshold_ms = 1000  # Always sample slow requests
        self.rate_limits = {}  # Per-endpoint rate limiting
        
    def should_sample(self, 
                      trace_type: str, 
                      duration_ms: Optional[float] = None,
                      is_error: bool = False) -> bool:
        """Decide if trace should be sampled"""
        
        # Always sample errors
        if is_error:
            return random.random() < self.error_rate
            
        # Always sample slow operations
        if duration_ms and duration_ms > self.slow_threshold_ms:
            return True
            
        # Rate limit per trace type
        now = time.time()
        last_sampled = self.rate_limits.get(trace_type, 0)
        
        # At most 1 trace per type per second
        if now - last_sampled < 1.0:
            return False
            
        # Random sampling
        if random.random() < self.base_rate:
            self.rate_limits[trace_type] = now
            return True
            
        return False

# Usage in agent
class AutomagikAgent:
    def __init__(self):
        self.sampler = AdaptiveSampler(base_rate=0.1)
        
    async def run(self, message_content: str, **kwargs):
        start_time = time.time()
        should_trace = self.sampler.should_sample(f"agent.{self.name}")
        
        if should_trace and self.tracing.observability:
            # Full tracing
            with self.tracing.observability.trace_agent_run(...):
                result = await self._run_internal(...)
        else:
            # No tracing overhead
            result = await self._run_internal(...)
            
        # Always collect lightweight telemetry
        duration_ms = (time.time() - start_time) * 1000
        if self.tracing.telemetry:
            # This is async and non-blocking
            self.tracing.telemetry.track_metrics(duration_ms)
```

### 4. Circuit Breaker Pattern
```python
# automagik/tracing/performance/circuit_breaker.py
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, skip calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Prevent cascading failures from tracing issues"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                # Skip call entirely
                return None
                
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            # Don't propagate tracing errors
            return None
            
    def _on_success(self):
        """Reset on success"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        
    def _on_failure(self):
        """Track failures"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            
    def _should_attempt_reset(self) -> bool:
        """Check if we should try again"""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
```

### 5. Memory-Efficient Buffering
```python
# automagik/tracing/performance/buffer.py
from collections import deque
import sys

class RingBuffer:
    """Fixed-size ring buffer for traces"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 50):
        self.buffer = deque(maxlen=max_size)
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_size_bytes = 0
        
    def add(self, item: Dict[str, Any]) -> bool:
        """Add item if within memory limits"""
        item_size = sys.getsizeof(item)
        
        # Check memory limit
        if self.current_size_bytes + item_size > self.max_memory_bytes:
            # Remove oldest items until we have space
            while self.buffer and self.current_size_bytes + item_size > self.max_memory_bytes:
                removed = self.buffer.popleft()
                self.current_size_bytes -= sys.getsizeof(removed)
        
        self.buffer.append(item)
        self.current_size_bytes += item_size
        return True
        
    def flush(self) -> List[Dict[str, Any]]:
        """Get all items and clear buffer"""
        items = list(self.buffer)
        self.buffer.clear()
        self.current_size_bytes = 0
        return items
```

### 6. Connection Pooling & Reuse
```python
# automagik/tracing/performance/connection_pool.py
import httpx
from typing import Dict

class TracingConnectionPool:
    """Reusable connection pool for trace endpoints"""
    
    def __init__(self):
        self.clients: Dict[str, httpx.AsyncClient] = {}
        
    def get_client(self, endpoint: str) -> httpx.AsyncClient:
        """Get or create client for endpoint"""
        if endpoint not in self.clients:
            self.clients[endpoint] = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,  # 5s connect timeout
                    read=10.0,    # 10s read timeout
                    write=5.0,    # 5s write timeout
                    pool=30.0     # 30s pool timeout
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30.0
                ),
                http2=True  # Use HTTP/2 for better performance
            )
        return self.clients[endpoint]
        
    async def close_all(self):
        """Close all clients"""
        for client in self.clients.values():
            await client.aclose()
```

### 7. Performance Monitoring
```python
# automagik/tracing/performance/metrics.py
import time
from dataclasses import dataclass
from typing import Dict

@dataclass
class TracingMetrics:
    """Metrics for tracing system performance"""
    events_queued: int = 0
    events_sent: int = 0
    events_dropped: int = 0
    avg_latency_ms: float = 0.0
    errors: int = 0
    
class PerformanceMonitor:
    """Monitor tracing system performance"""
    
    def __init__(self):
        self.metrics = TracingMetrics()
        self.latencies = deque(maxlen=1000)  # Last 1000 latencies
        
    def record_event_queued(self):
        self.metrics.events_queued += 1
        
    def record_event_sent(self, latency_ms: float):
        self.metrics.events_sent += 1
        self.latencies.append(latency_ms)
        self.metrics.avg_latency_ms = sum(self.latencies) / len(self.latencies)
        
    def record_event_dropped(self):
        self.metrics.events_dropped += 1
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get tracing system health"""
        drop_rate = self.metrics.events_dropped / max(self.metrics.events_queued, 1)
        
        return {
            "healthy": drop_rate < 0.01 and self.metrics.avg_latency_ms < 100,
            "metrics": {
                "queued": self.metrics.events_queued,
                "sent": self.metrics.events_sent,
                "dropped": self.metrics.events_dropped,
                "drop_rate": drop_rate,
                "avg_latency_ms": self.metrics.avg_latency_ms
            }
        }
```

### 8. Zero-Copy Context Propagation
```python
# automagik/tracing/performance/context.py
from contextvars import ContextVar
from typing import Optional, Dict, Any

# Use contextvars for zero-copy context propagation
trace_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('trace_context', default=None)

class TraceContext:
    """Lightweight trace context"""
    
    @staticmethod
    def set(trace_id: str, span_id: str, sampling_decision: bool):
        """Set trace context - no copying"""
        trace_context.set({
            'trace_id': trace_id,
            'span_id': span_id,
            'sampled': sampling_decision
        })
    
    @staticmethod
    def get() -> Optional[Dict[str, Any]]:
        """Get current trace context"""
        return trace_context.get()
    
    @staticmethod
    def is_sampled() -> bool:
        """Check if current trace is sampled"""
        ctx = trace_context.get()
        return ctx.get('sampled', False) if ctx else False
```

## Success Metrics

### Performance Metrics
- **Latency Impact**: <1ms added latency (p99)
- **CPU Overhead**: <0.5% CPU usage
- **Memory Usage**: <50MB for tracing buffers
- **Drop Rate**: <0.1% events dropped
- **Throughput**: >10,000 events/second per instance

### Reliability Metrics
- **Circuit Breaker**: Auto-disable after 5 failures
- **Recovery Time**: <60 seconds after failures
- **Queue Overflow**: Graceful degradation
- **No Blocking**: Zero blocking operations in hot path

### Business Metrics  
- Understand feature adoption rates
- Identify common error patterns
- Track framework preferences
- Monitor performance trends

## Timeline

- **Week 1**: Core infrastructure
- **Week 2**: Observability providers
- **Week 3**: Telemetry system
- **Week 4**: Integration points
- **Week 5**: CLI and configuration
- **Week 6**: Testing and documentation
- **Week 7**: Gradual rollout
- **Week 8**: Full deployment

This implementation plan provides a clear path to add comprehensive tracing while maintaining strict separation between detailed observability and privacy-preserving telemetry.