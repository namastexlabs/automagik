"""Enhanced Discord Agent using API integration patterns."""
import logging
from typing import Dict

from src.agents.common.specialized_agents import APIIntegrationAgent
from src.agents.common.tool_wrapper_factory import ToolWrapperFactory
from .prompts.prompt import AGENT_PROMPT

# Discord API tools
from src.tools.discord import (
    list_guilds_and_channels,
    get_guild_info,
    fetch_messages,
    send_message
)

logger = logging.getLogger(__name__)


class DiscordAgent(APIIntegrationAgent):
    """Enhanced Discord Agent with API integration patterns.
    
    Leverages the ChannelHandler system for multimodal support and
    uses the API integration framework for Discord tools.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Discord Agent with API tools."""
        # Initialize with API integration framework
        super().__init__(config, AGENT_PROMPT, api_tools=['discord'])
        
        # Register Discord-specific tools using wrapper factory
        self._register_discord_tools()
        
        logger.info("Enhanced Discord Agent initialized with API integration framework")
    
    def _register_discord_tools(self) -> None:
        """Register Discord API tools using the wrapper factory."""
        discord_tools = {
            'list_guilds_and_channels': list_guilds_and_channels,
            'get_guild_info': get_guild_info,
            'fetch_messages': fetch_messages,
            'send_message': send_message
        }
        
        for tool_name, tool_func in discord_tools.items():
            wrapper = ToolWrapperFactory.create_api_tool_wrapper(
                tool_func, 
                self.context,
                response_formatter=self._format_discord_response
            )
            self.tool_registry.register_tool(wrapper)
        
        logger.debug("Registered Discord API tools")
    
    def _format_discord_response(self, response) -> Dict:
        """Format Discord API responses for consistency."""
        if isinstance(response, dict) and 'error' not in response:
            return {
                'success': True,
                'data': response,
                'source': 'discord_api'
            }
        return response


def create_agent(config: Dict[str, str]) -> DiscordAgent:
    """Factory function to create enhanced Discord agent."""
    try:
        return DiscordAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced Discord Agent: {str(e)}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)