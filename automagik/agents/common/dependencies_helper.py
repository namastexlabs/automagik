"""Dependencies configuration utilities for agents.

This module provides functions for configuring agent dependencies,
including model settings, usage limits, and HTTP clients.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pydantic_ai.usage import UsageLimits
from pydantic_ai.settings import ModelSettings

from automagik.constants import (
    DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS
)

logger = logging.getLogger(__name__)

def parse_model_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse model settings from config dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with model settings
    """
    settings = {}
    
    # Extract settings with model_settings prefix
    for key, value in config.items():
        if key.startswith("model_settings."):
            setting_key = key.replace("model_settings.", "")
            settings[setting_key] = value
    
    # Set defaults if not provided
    if "temperature" not in settings and "model_settings.temperature" not in config:
        settings["temperature"] = DEFAULT_TEMPERATURE
    if "max_tokens" not in settings and "model_settings.max_tokens" not in config:
        settings["max_tokens"] = DEFAULT_MAX_TOKENS
    
    return settings

def create_model_settings(settings: Dict[str, Any], model_name: str = None) -> ModelSettings:
    """Create a ModelSettings object from a settings dictionary.
    
    Args:
        settings: Dictionary with model settings
        model_name: Optional model name to check for specific model compatibility
        
    Returns:
        ModelSettings object
    """
    if "temperature" not in settings:
        settings["temperature"] = DEFAULT_TEMPERATURE
    if "max_tokens" not in settings:
        settings["max_tokens"] = DEFAULT_MAX_TOKENS
    
    # Remove temperature parameter for o3-mini model as it's not supported
    if model_name and "o3-mini" in model_name and "temperature" in settings:
        logger.info(f"Removing unsupported temperature parameter for {model_name}")
        settings.pop("temperature")
    
    return ModelSettings(**settings)

def create_usage_limits(config: Dict[str, Any]) -> Optional[UsageLimits]:
    """Create usage limits from a config dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        UsageLimits object or None
    """
    response_tokens_limit = config.get("response_tokens_limit")
    request_limit = config.get("request_limit")
    total_tokens_limit = config.get("total_tokens_limit")
    
    if not any([response_tokens_limit, request_limit, total_tokens_limit]):
        return None
    
    if response_tokens_limit:
        response_tokens_limit = int(response_tokens_limit)
    if request_limit:
        request_limit = int(request_limit)
    if total_tokens_limit:
        total_tokens_limit = int(total_tokens_limit)
    
    return UsageLimits(
        response_tokens_limit=response_tokens_limit,
        request_limit=request_limit,
        total_tokens_limit=total_tokens_limit
    )

def get_model_name(config: Dict[str, Any]) -> str:
    """Get model name from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Model name
    """
    return config.get("model", os.environ.get("AUTOMAGIK_DEFAULT_MODEL", "gpt-4.1-mini"))

async def close_http_client(http_client) -> None:
    """Close an HTTP client safely.
    
    Args:
        http_client: HTTP client to close
    """
    if http_client:
        try:
            await http_client.aclose()
            logger.info("HTTP client closed successfully")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {str(e)}")

def message_history_to_pydantic_format(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert message history to PydanticAI format.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of messages in PydanticAI format
    """
    pydantic_messages = []
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            from pydantic_ai.messages import ModelRequest, SystemPromptPart
            pydantic_messages.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
        elif role == "user":
            from pydantic_ai.messages import ModelRequest, UserPromptPart
            pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            from pydantic_ai.messages import ModelResponse, TextPart
            pydantic_messages.append(ModelResponse(parts=[TextPart(content=content)]))
    
    return pydantic_messages

def add_system_message_to_history(message_history: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, Any]]:
    """Add system message to the beginning of message history.
    
    Args:
        message_history: List of message dictionaries
        system_prompt: System prompt string
        
    Returns:
        Updated message history
    """
    from pydantic_ai.messages import ModelRequest, SystemPromptPart
    
    system_message = ModelRequest(parts=[SystemPromptPart(content=system_prompt)])
    
    return [system_message] + message_history 