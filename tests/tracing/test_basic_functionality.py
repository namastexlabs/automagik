"""Basic tests for the tracing system."""

import os
import pytest
import time
from unittest.mock import patch, MagicMock

from automagik.tracing import get_tracing_manager
from automagik.tracing.config import TracingConfig
from automagik.tracing.performance import CircuitState
from automagik.tracing.telemetry import EventType, TelemetryEvent


class TestTracingConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TracingConfig()
        assert config.observability_enabled is True
        assert config.telemetry_enabled is True
        assert config.disable_all_tracing is False
        assert config.default_sampling_rate == 0.1
        assert config.max_queue_size == 10000
    
    def test_env_disable_all(self):
        """Test disabling all tracing via environment."""
        with patch.dict(os.environ, {"AUTOMAGIK_DISABLE_ALL_TRACING": "true"}):
            config = TracingConfig.from_env()
            assert config.disable_all_tracing is True
            assert config.observability_enabled is False
            assert config.telemetry_enabled is False
    
    def test_ci_environment_detection(self):
        """Test automatic disabling in CI environments."""
        with patch.dict(os.environ, {"CI": "true"}):
            config = TracingConfig.from_env()
            assert config.observability_enabled is False
            assert config.telemetry_enabled is False
        
        # Test explicit enabling in CI
        with patch.dict(os.environ, {
            "CI": "true",
            "AUTOMAGIK_ENABLE_TRACING_IN_CI": "true"
        }):
            config = TracingConfig.from_env()
            assert config.observability_enabled is True
            assert config.telemetry_enabled is True


class TestAsyncTracer:
    """Test async tracer functionality."""
    
    def test_basic_event_tracing(self):
        """Test basic event submission."""
        from automagik.tracing.performance import AsyncTracer
        
        events_processed = []
        
        def processor(batch):
            events_processed.extend(batch)
        
        tracer = AsyncTracer(
            max_workers=1,
            queue_size=100,
            batch_size=5,
            batch_timeout_ms=50,
            processor=processor
        )
        
        # Submit some events
        for i in range(10):
            assert tracer.trace_event({"id": i, "data": f"event_{i}"})
        
        # Wait for processing
        time.sleep(0.2)
        
        # Check events were processed
        assert len(events_processed) == 10
        assert events_processed[0]["id"] == 0
        assert events_processed[9]["id"] == 9
        
        # Check metrics
        metrics = tracer.get_metrics()
        assert metrics["queued"] == 10
        assert metrics["processed"] == 10
        assert metrics["dropped"] == 0
        
        tracer.shutdown()
    
    def test_queue_overflow_handling(self):
        """Test graceful handling of queue overflow."""
        from automagik.tracing.performance import AsyncTracer
        
        # Small queue that will overflow
        tracer = AsyncTracer(
            max_workers=1,
            queue_size=5,
            processor=lambda x: time.sleep(1)  # Slow processor
        )
        
        # Submit more events than queue can hold
        submitted = 0
        dropped = 0
        for i in range(20):
            if tracer.trace_event({"id": i}):
                submitted += 1
            else:
                dropped += 1
        
        # Should have dropped some events
        assert dropped > 0
        assert submitted <= 5  # Queue size
        
        metrics = tracer.get_metrics()
        assert metrics["dropped"] == dropped
        
        tracer.shutdown(timeout=0.1)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        from automagik.tracing.performance import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        def failing_func():
            raise Exception("Test failure")
        
        # First 3 failures should go through
        for i in range(3):
            result = breaker.call(failing_func)
            assert result is None
            assert breaker.state == CircuitState.CLOSED if i < 2 else CircuitState.OPEN
        
        # Circuit should now be open
        assert breaker.state == CircuitState.OPEN
        
        # Further calls should be rejected
        result = breaker.call(failing_func)
        assert result is None
        assert breaker.get_state()["metrics"]["rejected_calls"] == 1
    
    def test_circuit_recovery(self):
        """Test circuit breaker recovery after timeout."""
        from automagik.tracing.performance import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        def failing_func():
            raise Exception("Test failure")
        
        def working_func():
            return "success"
        
        # Open the circuit
        for _ in range(2):
            breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Circuit should attempt recovery
        result = breaker.call(working_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED


class TestAdaptiveSampling:
    """Test adaptive sampling strategies."""
    
    def test_error_always_sampled(self):
        """Test that errors are always sampled."""
        from automagik.tracing.performance import AdaptiveSampler
        
        sampler = AdaptiveSampler(base_rate=0.0)  # 0% base rate
        
        # Errors should still be sampled
        decision = sampler.should_sample(
            trace_type="test",
            is_error=True
        )
        assert decision.should_sample is True
        assert decision.reason == "error"
    
    def test_slow_operations_sampled(self):
        """Test that slow operations are always sampled."""
        from automagik.tracing.performance import AdaptiveSampler
        
        sampler = AdaptiveSampler(base_rate=0.0, slow_threshold_ms=100)
        
        # Slow operation should be sampled
        decision = sampler.should_sample(
            trace_type="test",
            duration_ms=150
        )
        assert decision.should_sample is True
        assert "slow_operation" in decision.reason
    
    def test_rate_limiting(self):
        """Test rate limiting per trace type."""
        from automagik.tracing.performance import AdaptiveSampler
        
        sampler = AdaptiveSampler(
            base_rate=1.0,  # 100% rate
            rate_limit_window_s=1.0,
            max_traces_per_window=2
        )
        
        # First 2 should be sampled
        for i in range(2):
            decision = sampler.should_sample(trace_type="test")
            assert decision.should_sample is True
        
        # 3rd should be rate limited
        decision = sampler.should_sample(trace_type="test")
        assert decision.should_sample is False
        assert decision.reason == "rate_limited"


class TestTelemetryPrivacy:
    """Test privacy features of telemetry."""
    
    def test_attribute_sanitization(self):
        """Test that sensitive attributes are removed."""
        event = TelemetryEvent(
            event_type=EventType.AGENT_RUN,
            attributes={
                "agent.type": "simple",  # Allowed
                "user_message": "My SSN is 123-45-6789",  # Not allowed
                "api_key": "sk-secret-key",  # Not allowed
                "duration_ms": 100,  # Allowed
                "/path/to/file": "data",  # Not allowed
            }
        )
        
        sanitized = event._sanitize_attributes(event.attributes)
        
        # Check allowed attributes are kept
        assert "agent.type" in sanitized
        assert sanitized["agent.type"] == "simple"
        assert "duration_ms" in sanitized
        assert sanitized["duration_ms"] == 100
        
        # Check sensitive attributes are removed
        assert "user_message" not in sanitized
        assert "api_key" not in sanitized
        assert "/path/to/file" not in sanitized
    
    def test_long_string_truncation(self):
        """Test that long strings are truncated."""
        event = TelemetryEvent(
            event_type=EventType.AGENT_RUN,
            attributes={
                "agent.type": "x" * 100  # Very long string
            }
        )
        
        sanitized = event._sanitize_attributes(event.attributes)
        
        assert len(sanitized["agent.type"]) == 53  # 50 + "..."
        assert sanitized["agent.type"].endswith("...")


class TestTracingManager:
    """Test the main tracing manager."""
    
    def test_lazy_initialization(self):
        """Test that components are lazy loaded."""
        from automagik.tracing.core import TracingManager
        
        manager = TracingManager()
        
        # Components should not be initialized yet
        assert manager._observability is None
        assert manager._telemetry is None
        
        # Access should trigger initialization
        with patch.dict(os.environ, {"AUTOMAGIK_TELEMETRY_ENABLED": "true"}):
            telemetry = manager.telemetry
            assert telemetry is not None
    
    def test_shutdown_handling(self):
        """Test graceful shutdown."""
        from automagik.tracing.core import TracingManager
        
        manager = TracingManager()
        
        # Force initialization
        _ = manager.telemetry
        
        # Shutdown should not raise errors
        manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])