"""Example integration of tracing with AutomagikAgent.

This file shows how the tracing system would integrate with agents.
The actual integration would be added to the AutomagikAgent base class.
"""

import time
from typing import Dict, Any, Optional

from automagik.tracing import get_tracing_manager
from automagik.tracing.performance import SamplingDecision


class TracingMixin:
    """Mixin to add tracing capabilities to agents.
    
    This would be added to the AutomagikAgent base class.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get global tracing manager
        self.tracing = get_tracing_manager()
        
        # Agent-specific sampler for fine control
        if self.tracing.observability:
            self.sampler = self.tracing.observability.sampler
    
    async def run_with_tracing(self, message_content: str, **kwargs) -> Any:
        """Run agent with integrated tracing.
        
        This method shows how tracing would wrap the agent's run method.
        """
        start_time = time.time()
        success = False
        error_type = None
        
        # Determine if we should trace this run
        sampling_decision = self._should_sample(kwargs)
        
        try:
            # Observability tracing (detailed, sampled)
            if sampling_decision.should_sample and self.tracing.observability:
                with self.tracing.observability.trace_agent_run(
                    agent_name=self.name,
                    session_id=kwargs.get("session_id", "unknown"),
                    message_preview=message_content[:100]  # Limited preview
                ) as trace_ctx:
                    # Log the sampling decision
                    trace_ctx.attributes["sampling.reason"] = sampling_decision.reason
                    trace_ctx.attributes["sampling.rate"] = sampling_decision.sample_rate
                    
                    # Run the actual agent
                    result = await self._run_internal(message_content, **kwargs)
                    
                    # Log usage if available
                    if hasattr(result, 'usage') and result.usage:
                        self._log_usage_to_observability(result.usage)
            else:
                # No detailed tracing, just run
                result = await self._run_internal(message_content, **kwargs)
            
            success = True
            return result
            
        except Exception as e:
            error_type = type(e).__name__
            
            # Log error to observability if sampled
            if sampling_decision.should_sample and self.tracing.observability:
                for provider in self.tracing.observability.providers.values():
                    provider.log_error(e, {
                        "agent": self.name,
                        "session_id": kwargs.get("session_id")
                    })
            
            # Always track errors in telemetry (anonymous)
            if self.tracing.telemetry:
                self.tracing.telemetry.track_error(
                    error_type=error_type,
                    component=f"agent.{self.name}"
                )
            
            raise
            
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Always send anonymous telemetry (not sampled)
            if self.tracing.telemetry:
                self.tracing.telemetry.track_agent_run(
                    agent_type=self.name,
                    framework=self.framework_type.value,
                    success=success,
                    duration_ms=duration_ms
                )
            
            # Track feature usage
            if self.tracing.telemetry:
                # Track framework selection
                self.tracing.telemetry.track_feature_usage(
                    f"framework.{self.framework_type.value}",
                    category="agent_framework"
                )
                
                # Track multimodal usage if applicable
                if kwargs.get("multimodal_content"):
                    self.tracing.telemetry.track_feature_usage(
                        "multimodal_content",
                        category="agent_capability"
                    )
    
    def _should_sample(self, kwargs: Dict[str, Any]) -> SamplingDecision:
        """Determine if this run should be sampled for detailed tracing.
        
        Args:
            kwargs: Run kwargs that might influence sampling
            
        Returns:
            SamplingDecision with result and reason
        """
        if not self.tracing.observability or not hasattr(self, 'sampler'):
            return SamplingDecision(should_sample=False, reason="no_observability")
        
        # Check if this is the first run for this agent type
        is_first = kwargs.get("is_first_run", False)
        
        return self.sampler.should_sample(
            trace_type=f"agent.{self.name}",
            duration_ms=None,  # Not known yet
            is_error=False,
            attributes={
                "is_first_occurrence": is_first,
                "session_id": kwargs.get("session_id"),
                "has_multimodal": bool(kwargs.get("multimodal_content"))
            }
        )
    
    def _log_usage_to_observability(self, usage: Dict[str, Any]):
        """Log token usage to observability providers.
        
        Args:
            usage: Usage dictionary with token counts and costs
        """
        if not self.tracing.observability:
            return
        
        # Log to each active provider
        for provider in self.tracing.observability.providers.values():
            provider.log_llm_call(
                model=self.config.model,
                messages=[],  # Would include actual messages in production
                response="",  # Would include response in production
                usage=usage
            )


# Example of how it would be integrated into AutomagikAgent
"""
class AutomagikAgent(TracingMixin, BaseAgent):
    # ... existing code ...
    
    async def run(self, message_content: str, **kwargs) -> AgentResponse:
        # Use the tracing-wrapped version
        return await self.run_with_tracing(message_content, **kwargs)
"""