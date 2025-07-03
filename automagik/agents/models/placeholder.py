"""Placeholder agent implementation.

This module provides a basic placeholder agent to use when an agent fails to initialize.
"""

import logging
from typing import Dict, Any, Optional, Union

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory

logger = logging.getLogger(__name__)

class PlaceholderAgent(AutomagikAgent):
    """A minimal placeholder agent for error cases."""
    
    def __init__(self, config: Dict[str, str]):
        """Initialize the placeholder agent.
        
        Args:
            config: Configuration dictionary
        """
        error_msg = config.get("error", "Unknown error")
        name = config.get("name", "placeholder_agent")
        
        # Initialize the base agent first
        super().__init__(config)
        
        # Set up prompt text to be registered later
        self._code_prompt_text = f"You are a placeholder agent named {name}. " \
                        f"The original agent failed to initialize with error: {error_msg}"
        self._prompt_registered = False
        
        self.error = error_msg
        self.name = name
        logger.warning(f"Created placeholder agent '{name}' with error: {error_msg}")
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj=None, channel_payload=None, message_limit=None) -> AgentResponse:
        """Run the placeholder agent.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message
            message_history_obj: Optional MessageHistory instance
            channel_payload: Optional channel-specific payload
            message_limit: Optional message limit
            
        Returns:
            AgentResponse with error message
        """
        # Try to register and load the prompt
        if self.db_id:
            await self._check_and_register_prompt()
            await self.load_active_prompt_template(status_key="default")
        
        message = f"I'm sorry, but the agent failed to initialize with error: {self.error}"
        
        return AgentResponse(
            text=message,
            success=False,
            error_message=self.error
        )
        
    async def process_message(self, user_message: Union[str, Dict[str, Any]], 
                              session_id: Optional[str] = None, 
                              agent_id: Optional[Union[int, str]] = None, 
                              user_id: int = 1, 
                              context: Optional[Dict] = None, 
                              message_history: Optional[MessageHistory] = None) -> AgentResponse:
        """Process a user message.
        
        Args:
            user_message: User message text or dictionary
            session_id: Optional session ID
            agent_id: Optional agent ID
            user_id: User ID (default 1)
            context: Optional context dictionary
            message_history: Optional MessageHistory instance
            
        Returns:
            AgentResponse with error message
        """
        if isinstance(user_message, dict):
            content = user_message.get("content", "")
        else:
            content = user_message
            
        return await self.run(content) 