"""Base abstract class for AI framework integration.

This module defines the interface that all AI framework adapters must implement
to provide a consistent interface for AutomagikAgent.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Type
from dataclasses import dataclass

from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an AI agent."""
    model: str
    temperature: float = 0.7
    retries: int = 1
    tools: Optional[List[Any]] = None
    model_settings: Optional[Dict[str, Any]] = None
    usage_limits: Optional[Dict[str, Any]] = None


class AgentAIFramework(ABC):
    """Abstract base class for AI framework integration.
    
    This class defines the interface for integrating different AI frameworks
    (e.g., PydanticAI, LangChain, CrewAI) with AutomagikAgent.
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize the AI framework adapter.
        
        Args:
            config: Agent configuration including model, temperature, etc.
        """
        self.config = config
        self._agent_instance = None
        self.is_initialized = False
        
    @abstractmethod
    async def initialize(self, 
                        tools: List[Any], 
                        dependencies_type: Type[BaseDependencies],
                        mcp_servers: Optional[List[Any]] = None) -> None:
        """Initialize the underlying AI agent instance.
        
        This method should create and configure the agent instance with the
        provided tools and configuration.
        
        Args:
            tools: List of tools to register with the agent
            dependencies_type: Type of dependencies to use for the agent
            mcp_servers: Optional list of MCP servers to connect
        """
        pass
        
    @abstractmethod
    async def run(self,
                  user_input: Union[str, List[Any]],
                  dependencies: BaseDependencies,
                  message_history: Optional[List[Dict[str, Any]]] = None,
                  **kwargs) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            user_input: Text or multimodal input for the agent
            dependencies: Agent dependencies instance
            message_history: Optional conversation history
            **kwargs: Additional framework-specific parameters
            
        Returns:
            AgentResponse object with the agent's response
        """
        pass
        
    @abstractmethod
    def format_message_history(self, 
                              raw_messages: List[Dict[str, Any]]) -> List[Any]:
        """Convert raw message history to framework-specific format.
        
        Args:
            raw_messages: List of message dictionaries with role, content, etc.
            
        Returns:
            Messages in the format expected by the specific AI framework
        """
        pass
        
    @abstractmethod
    def extract_tool_calls(self, result: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from the framework's response.
        
        Args:
            result: The raw result from the AI framework
            
        Returns:
            List of tool call dictionaries
        """
        pass
        
    @abstractmethod
    def extract_tool_outputs(self, result: Any) -> List[Dict[str, Any]]:
        """Extract tool outputs from the framework's response.
        
        Args:
            result: The raw result from the AI framework
            
        Returns:
            List of tool output dictionaries
        """
        pass
        
    @abstractmethod
    def convert_tools(self, tools: List[Any]) -> List[Any]:
        """Convert tools to framework-specific format.
        
        Args:
            tools: List of tool functions/definitions
            
        Returns:
            Tools in the format expected by the specific AI framework
        """
        pass
        
    @property
    def is_ready(self) -> bool:
        """Check if the framework is initialized and ready to run.
        
        Returns:
            True if the agent is initialized and ready
        """
        return self.is_initialized and self._agent_instance is not None
        
    async def cleanup(self) -> None:
        """Clean up any resources used by the framework.
        
        Override this method if the framework needs cleanup logic.
        """
        pass
        
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update the agent configuration.
        
        Args:
            config_updates: Dictionary with configuration updates
        """
        for key, value in config_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Mark as needing re-initialization if config changes
        if self.is_initialized and config_updates:
            logger.info(f"Configuration updated, re-initialization required: {config_updates.keys()}")
            self.is_initialized = False