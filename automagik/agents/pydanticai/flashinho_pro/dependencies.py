"""
Dependencies for Flashinho Pro agent
"""
import os
from typing import Dict, Any, Optional

from automagik.agents.pydanticai.dependencies import PydanticAIDependencies
from automagik.agents.pydanticai.llm.google import GoogleLLMClient

from automagik.tools.flashed.provider import FlashedProvider


class FlashinhoProDependencies(PydanticAIDependencies):
    """Dependencies for Flashinho Pro agent."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize dependencies.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config or {})
        
        # Default model is the Pro model
        self.model_name = "google-gla:gemini-2.5-pro-preview-05-06"
        
        # Initialize LLM client
        self.llm_client = GoogleLLMClient(
            model=self.model_name,
            api_key=os.environ.get("GOOGLE_API_KEY"),
        )
        
        # Initialize Flashed provider
        self.flashed_provider = FlashedProvider() 