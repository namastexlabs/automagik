"""
Dependencies for Flashinho Pro agent
"""
import os
from typing import Dict, Any, Optional

from src.agents.pydanticai.dependencies import PydanticAIDependencies
from src.agents.pydanticai.llm.google import GoogleLLMClient

from src.tools.flashed.provider import FlashedProvider


class FlashinhoProDependencies(PydanticAIDependencies):
    """Dependencies for Flashinho Pro agent."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize dependencies.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config or {})
        
        # Default model is the Pro model
        self.model_name = "openai:gpt-4o"
        
        # Initialize LLM client (will be updated dynamically based on model)
        # For OpenAI models, the framework handles the client automatically
        self.llm_client = None  # Handled by framework based on model prefix
        
        # Initialize Flashed provider
        self.flashed_provider = FlashedProvider() 