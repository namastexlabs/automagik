"""Configuration management for the tracing system."""

import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class TracingConfig:
    """Configuration for tracing systems."""
    
    # Observability settings
    observability_enabled: bool = True
    observability_providers: List[str] = field(default_factory=list)
    
    # Telemetry settings  
    telemetry_enabled: bool = True
    telemetry_endpoint: str = "https://telemetry.namastex.ai/v1/traces"
    telemetry_anonymous_id: Optional[str] = None
    
    # Privacy settings
    disable_all_tracing: bool = False
    disable_in_ci: bool = True
    
    # Performance settings
    max_queue_size: int = 10000
    batch_size: int = 50
    batch_timeout_ms: int = 5000  # 5 seconds
    max_workers: int = 2
    
    # Sampling settings
    default_sampling_rate: float = 0.1  # 10%
    error_sampling_rate: float = 1.0    # 100%
    slow_threshold_ms: float = 1000     # 1 second
    
    @classmethod
    def from_env(cls) -> 'TracingConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Global disable
        if os.getenv("AUTOMAGIK_DISABLE_ALL_TRACING", "false").lower() == "true":
            config.disable_all_tracing = True
            config.observability_enabled = False
            config.telemetry_enabled = False
            return config
        
        # Check for opt-out file
        opt_out_file = os.path.expanduser("~/.automagik-no-tracing")
        if os.path.exists(opt_out_file):
            config.disable_all_tracing = True
            config.observability_enabled = False
            config.telemetry_enabled = False
            return config
            
        # Observability configuration
        config.observability_enabled = os.getenv(
            "AUTOMAGIK_OBSERVABILITY_ENABLED", "true"
        ).lower() == "true"
        
        # Detect available providers based on API keys
        if config.observability_enabled:
            providers = []
            langwatch_key = os.getenv("LANGWATCH_API_KEY")
            if langwatch_key:
                providers.append("langwatch")
                print(f"🔑 LangWatch API key detected: {langwatch_key[:10]}...")
            if os.getenv("LANGFUSE_PUBLIC_KEY"):
                providers.append("langfuse")
            if os.getenv("LANGSMITH_API_KEY"):
                providers.append("langsmith")
            config.observability_providers = providers
            print(f"📊 Observability providers configured: {providers}")
        
        # Telemetry configuration
        config.telemetry_enabled = os.getenv(
            "AUTOMAGIK_TELEMETRY_ENABLED", "true"
        ).lower() == "true"
        
        if os.getenv("AUTOMAGIK_TELEMETRY_ENDPOINT"):
            config.telemetry_endpoint = os.getenv("AUTOMAGIK_TELEMETRY_ENDPOINT")
        
        # Auto-disable in CI unless explicitly enabled
        if any(os.getenv(var) for var in ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS"]):
            if os.getenv("AUTOMAGIK_ENABLE_TRACING_IN_CI", "false").lower() != "true":
                config.disable_in_ci = True
                config.observability_enabled = False
                config.telemetry_enabled = False
        
        # Performance settings from env
        if os.getenv("AUTOMAGIK_TRACE_QUEUE_SIZE"):
            config.max_queue_size = int(os.getenv("AUTOMAGIK_TRACE_QUEUE_SIZE"))
        if os.getenv("AUTOMAGIK_TRACE_BATCH_SIZE"):
            config.batch_size = int(os.getenv("AUTOMAGIK_TRACE_BATCH_SIZE"))
        if os.getenv("AUTOMAGIK_TRACE_WORKERS"):
            config.max_workers = int(os.getenv("AUTOMAGIK_TRACE_WORKERS"))
            
        # Sampling settings from env
        if os.getenv("AUTOMAGIK_SAMPLING_RATE"):
            config.default_sampling_rate = float(os.getenv("AUTOMAGIK_SAMPLING_RATE"))
        if os.getenv("AUTOMAGIK_ERROR_SAMPLING_RATE"):
            config.error_sampling_rate = float(os.getenv("AUTOMAGIK_ERROR_SAMPLING_RATE"))
        
        return config

    def is_tracing_enabled(self) -> bool:
        """Check if any tracing is enabled."""
        return not self.disable_all_tracing and (
            self.observability_enabled or self.telemetry_enabled
        )