"""Virtual agent configuration validator."""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class VirtualAgentConfigValidator:
    """Validator for virtual agent configurations."""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """Validate virtual agent configuration and return list of errors.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Check if this is marked as a virtual agent
            agent_source = config.get("agent_source")
            if agent_source != "virtual":
                return []  # Not a virtual agent, skip validation
            
            # Validate required fields
            if not config.get("default_model"):
                errors.append("Virtual agents must specify a default_model")
            
            # Validate tool configuration if present
            tool_config = config.get("tool_config", {})
            if tool_config:
                tool_errors = VirtualAgentConfigValidator._validate_tool_config(tool_config)
                errors.extend(tool_errors)
                
        except Exception as e:
            logger.error(f"Error validating virtual agent config: {e}")
            errors.append(f"Configuration validation failed: {str(e)}")
        
        return errors
    
    @staticmethod
    def _validate_tool_config(tool_config: Dict[str, Any]) -> List[str]:
        """Validate tool configuration section.
        
        Args:
            tool_config: Tool configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate enabled_tools is a list
        enabled_tools = tool_config.get("enabled_tools", [])
        if not isinstance(enabled_tools, list):
            errors.append("tool_config.enabled_tools must be a list")
        
        # Validate disabled_tools is a list if present
        disabled_tools = tool_config.get("disabled_tools", [])
        if disabled_tools and not isinstance(disabled_tools, list):
            errors.append("tool_config.disabled_tools must be a list")
        
        # Validate tool_permissions is a dict if present
        tool_permissions = tool_config.get("tool_permissions", {})
        if tool_permissions and not isinstance(tool_permissions, dict):
            errors.append("tool_config.tool_permissions must be a dictionary")
        
        # Validate individual tool permissions
        for tool_name, permissions in tool_permissions.items():
            if not isinstance(permissions, dict):
                errors.append(f"tool_config.tool_permissions.{tool_name} must be a dictionary")
                continue
                
            # Validate specific permission types
            max_results = permissions.get("max_results")
            if max_results is not None and not isinstance(max_results, int):
                errors.append(f"tool_config.tool_permissions.{tool_name}.max_results must be an integer")
                
            rate_limit = permissions.get("rate_limit_per_minute")
            if rate_limit is not None and not isinstance(rate_limit, int):
                errors.append(f"tool_config.tool_permissions.{tool_name}.rate_limit_per_minute must be an integer")
        
        return errors
    
    @staticmethod
    def is_virtual_agent(config: Dict[str, Any]) -> bool:
        """Check if a configuration represents a virtual agent.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            True if this is a virtual agent configuration
        """
        return config.get("agent_source") == "virtual"
    
    @staticmethod
    def get_allowed_tools() -> List[str]:
        """Get list of allowed tool names for virtual agents.
        
        Returns:
            List of allowed tool names
        """
        # These are the known safe tools that virtual agents can use
        return [
            "memory",
            "datetime", 
            "evolution_send_message",
            "search",
            "file_operations",  # Basic file operations
        ]
    
    @staticmethod
    def validate_tool_names(enabled_tools: List[str]) -> List[str]:
        """Validate that tool names are allowed for virtual agents.
        
        Args:
            enabled_tools: List of enabled tool names
            
        Returns:
            List of validation error messages
        """
        errors = []
        allowed_tools = VirtualAgentConfigValidator.get_allowed_tools()
        
        for tool_name in enabled_tools:
            if tool_name not in allowed_tools:
                errors.append(f"Tool '{tool_name}' is not allowed for virtual agents. Allowed tools: {', '.join(allowed_tools)}")
        
        return errors