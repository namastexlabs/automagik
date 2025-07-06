"""Circuit breaker pattern for preventing cascading failures."""

import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, skip calls  
    HALF_OPEN = "half_open" # Testing recovery


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures from tracing issues.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, calls go through
    - OPEN: Too many failures, calls are skipped
    - HALF_OPEN: Testing if the service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        name: str = "circuit_breaker"
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting reset
            expected_exception: Exception type to catch
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
        # Metrics
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.rejected_calls = 0
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if circuit is open
        """
        self.total_calls += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.debug(f"{self.name}: Attempting reset (half-open)")
            else:
                # Skip call entirely
                self.rejected_calls += 1
                return None
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            # Don't propagate tracing errors
            logger.debug(f"{self.name}: Caught expected error: {e}")
            return None
        except Exception as e:
            # Unexpected error - let it propagate
            logger.warning(f"{self.name}: Unexpected error: {e}")
            raise
    
    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if circuit is open
        """
        self.total_calls += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.debug(f"{self.name}: Attempting reset (half-open)")
            else:
                # Skip call entirely
                self.rejected_calls += 1
                return None
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            # Don't propagate tracing errors
            logger.debug(f"{self.name}: Caught expected error: {e}")
            return None
        except Exception as e:
            # Unexpected error - let it propagate
            logger.warning(f"{self.name}: Unexpected error: {e}")
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.successful_calls += 1
        self.failure_count = 0
        
        if self.state != CircuitState.CLOSED:
            logger.info(f"{self.name}: Circuit closed after successful call")
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    f"{self.name}: Circuit opened after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state and metrics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "metrics": {
                "total_calls": self.total_calls,
                "successful_calls": self.successful_calls,
                "failed_calls": self.failed_calls,
                "rejected_calls": self.rejected_calls,
                "success_rate": (
                    self.successful_calls / self.total_calls 
                    if self.total_calls > 0 else 0
                )
            }
        }
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info(f"{self.name}: Circuit manually reset")