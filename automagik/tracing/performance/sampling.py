"""Adaptive sampling strategies to reduce trace volume while maintaining visibility."""

import random
import time
from typing import Dict, Optional, Any

from dataclasses import dataclass, field


@dataclass
class SamplingDecision:
    """Result of a sampling decision."""
    should_sample: bool
    reason: str = ""
    sample_rate: float = 1.0


class AdaptiveSampler:
    """Adaptive sampling to reduce trace volume intelligently.
    
    Features:
    - Always samples errors
    - Always samples slow operations
    - Rate limiting per trace type
    - Configurable base sampling rate
    - Dynamic rate adjustment based on volume
    """
    
    def __init__(
        self, 
        base_rate: float = 0.1,
        error_rate: float = 1.0,
        slow_threshold_ms: float = 1000,
        rate_limit_window_s: float = 1.0,
        max_traces_per_window: int = 10
    ):
        """Initialize adaptive sampler.
        
        Args:
            base_rate: Default sampling rate (0.0 to 1.0)
            error_rate: Sampling rate for errors (usually 1.0)
            slow_threshold_ms: Threshold for slow operations in ms
            rate_limit_window_s: Window size for rate limiting
            max_traces_per_window: Max traces per type per window
        """
        self.base_rate = base_rate
        self.error_rate = error_rate
        self.slow_threshold_ms = slow_threshold_ms
        self.rate_limit_window_s = rate_limit_window_s
        self.max_traces_per_window = max_traces_per_window
        
        # Rate limiting state
        self.trace_counts: Dict[str, list] = {}  # trace_type -> [timestamps]
        
        # Metrics
        self.total_decisions = 0
        self.sampled_count = 0
        self.reasons: Dict[str, int] = {
            "error": 0,
            "slow": 0,
            "rate_limited": 0,
            "random": 0,
            "always": 0
        }
    
    def should_sample(
        self,
        trace_type: str,
        duration_ms: Optional[float] = None,
        is_error: bool = False,
        attributes: Optional[Dict[str, any]] = None
    ) -> SamplingDecision:
        """Decide if a trace should be sampled.
        
        Args:
            trace_type: Type of trace (e.g., "agent.simple", "workflow.test")
            duration_ms: Operation duration in milliseconds
            is_error: Whether this is an error trace
            attributes: Additional attributes for decision
            
        Returns:
            SamplingDecision with result and reason
        """
        self.total_decisions += 1
        
        # Always sample errors
        if is_error:
            self.sampled_count += 1
            self.reasons["error"] += 1
            return SamplingDecision(
                should_sample=True,
                reason="error",
                sample_rate=self.error_rate
            )
        
        # Always sample slow operations
        if duration_ms and duration_ms > self.slow_threshold_ms:
            self.sampled_count += 1
            self.reasons["slow"] += 1
            return SamplingDecision(
                should_sample=True,
                reason=f"slow_operation_{duration_ms}ms",
                sample_rate=1.0
            )
        
        # Check for special attributes that force sampling
        if attributes:
            # Always sample first occurrence of a trace type
            if attributes.get("is_first_occurrence"):
                self.sampled_count += 1
                self.reasons["always"] += 1
                return SamplingDecision(
                    should_sample=True,
                    reason="first_occurrence",
                    sample_rate=1.0
                )
        
        # Apply rate limiting
        if not self._check_rate_limit(trace_type):
            self.reasons["rate_limited"] += 1
            return SamplingDecision(
                should_sample=False,
                reason="rate_limited",
                sample_rate=0.0
            )
        
        # Random sampling based on configured rate
        if random.random() < self.base_rate:
            self.sampled_count += 1
            self.reasons["random"] += 1
            self._record_trace(trace_type)
            return SamplingDecision(
                should_sample=True,
                reason="random_sample",
                sample_rate=self.base_rate
            )
        
        return SamplingDecision(
            should_sample=False,
            reason="not_sampled",
            sample_rate=self.base_rate
        )
    
    def _check_rate_limit(self, trace_type: str) -> bool:
        """Check if trace type is within rate limit.
        
        Args:
            trace_type: Type of trace to check
            
        Returns:
            True if within rate limit, False otherwise
        """
        now = time.time()
        
        # Get or create trace history
        if trace_type not in self.trace_counts:
            self.trace_counts[trace_type] = []
        
        trace_history = self.trace_counts[trace_type]
        
        # Remove old timestamps outside the window
        cutoff_time = now - self.rate_limit_window_s
        trace_history[:] = [ts for ts in trace_history if ts > cutoff_time]
        
        # Check if we're at the limit
        return len(trace_history) < self.max_traces_per_window
    
    def _record_trace(self, trace_type: str):
        """Record that a trace was sampled for rate limiting.
        
        Args:
            trace_type: Type of trace that was sampled
        """
        now = time.time()
        
        if trace_type not in self.trace_counts:
            self.trace_counts[trace_type] = []
        
        self.trace_counts[trace_type].append(now)
    
    def get_metrics(self) -> Dict[str, any]:
        """Get sampling metrics."""
        sampling_rate = (
            self.sampled_count / self.total_decisions 
            if self.total_decisions > 0 else 0
        )
        
        return {
            "total_decisions": self.total_decisions,
            "sampled_count": self.sampled_count,
            "effective_rate": sampling_rate,
            "configured_rate": self.base_rate,
            "reasons": self.reasons.copy(),
            "active_trace_types": len(self.trace_counts)
        }
    
    def adjust_rate(self, target_rate: float):
        """Dynamically adjust the base sampling rate.
        
        Args:
            target_rate: New sampling rate (0.0 to 1.0)
        """
        old_rate = self.base_rate
        self.base_rate = max(0.0, min(1.0, target_rate))
        
        if old_rate != self.base_rate:
            # Could log or emit metric about rate change
            pass


class CompositeSampler:
    """Composite sampler that combines multiple sampling strategies."""
    
    def __init__(self, samplers: list[AdaptiveSampler]):
        """Initialize with a list of samplers.
        
        Args:
            samplers: List of samplers to combine
        """
        self.samplers = samplers
    
    def should_sample(self, **kwargs) -> SamplingDecision:
        """Check all samplers and return combined decision.
        
        Uses OR logic - if any sampler says yes, we sample.
        """
        for sampler in self.samplers:
            decision = sampler.should_sample(**kwargs)
            if decision.should_sample:
                return decision
        
        # No sampler said yes
        return SamplingDecision(
            should_sample=False,
            reason="all_samplers_rejected"
        )