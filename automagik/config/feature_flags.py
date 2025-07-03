"""
Feature Flag System for Automagik Agents

Provides environment-variable-driven feature flags for production configuration
and feature management.
"""

import os
import logging
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)




class MCPFeatureFlags:
    """
    Centralized feature flag management for Automagik Agents.
    
    Provides environment-variable-driven configuration with safe defaults.
    
    Environment Variables:
        MCP_HOT_RELOAD_ENABLED: Enable hot reload for MCP configs (default: true)
    """
    
    def __init__(self):
        """Initialize feature flags from environment variables."""
        self._flags: Dict[str, Any] = {}
        self._load_flags()
        
    def _load_flags(self) -> None:
        """Load all feature flags from environment variables with safe defaults."""
        # Hot reload flag (default enabled)
        self._flags["MCP_HOT_RELOAD_ENABLED"] = self._get_env_bool("MCP_HOT_RELOAD_ENABLED", True)
        
        
        # Log flag status on initialization
        enabled_flags = [flag for flag, value in self._flags.items() if value is True]
        disabled_flags = [flag for flag, value in self._flags.items() if value is False]
        
        logger.info(f"🚩 Feature flags initialized - Enabled: {len(enabled_flags)}, Disabled: {len(disabled_flags)}")
        logger.debug(f"Enabled flags: {enabled_flags}")
        logger.debug(f"Disabled flags: {disabled_flags}")
    
    def _get_env_bool(self, key: str, default: bool) -> bool:
        """
        Get boolean value from environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not set
            
        Returns:
            Boolean value
        """
        value = os.environ.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on", "enabled")
    
    
    def is_enabled(self, flag: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag: Flag name
            
        Returns:
            True if enabled, False otherwise
        """
        return bool(self._flags.get(flag, False))
    
    def get_value(self, flag: str) -> Any:
        """
        Get the raw value of a feature flag.
        
        Args:
            flag: Flag name
            
        Returns:
            Flag value (bool, enum, etc.)
        """
        return self._flags.get(flag)
    
    def enable_flag(self, flag: str) -> None:
        """
        Enable a feature flag programmatically.
        
        Args:
            flag: Flag name to enable
        """
        if flag in self._flags:
            self._flags[flag] = True
            os.environ[flag] = "true"
            logger.info(f"🚩 Enabled flag: {flag}")
        else:
            logger.warning(f"Unknown flag: {flag}")
    
    def disable_flag(self, flag: str) -> None:
        """
        Disable a feature flag programmatically.
        
        Args:
            flag: Flag name to disable
        """
        if flag in self._flags:
            self._flags[flag] = False
            os.environ[flag] = "false"
            logger.info(f"🚩 Disabled flag: {flag}")
        else:
            logger.warning(f"Unknown flag: {flag}")
    
    
    
    
    def get_all_flags(self) -> Dict[str, Any]:
        """
        Get all feature flags and their current values.
        
        Returns:
            Dictionary of all flags and values
        """
        return self._flags.copy()
    
    def get_flag_summary(self) -> Dict[str, Any]:
        """
        Get a summary of feature flag status for monitoring/debugging.
        
        Returns:
            Summary of flag status
        """
        return {
            "flags": self.get_all_flags(),
            "features": {
                "hot_reload": self.is_enabled("MCP_HOT_RELOAD_ENABLED")
            }
        }


# Global feature flags instance
_feature_flags: Optional[MCPFeatureFlags] = None


def get_feature_flags() -> MCPFeatureFlags:
    """
    Get the global feature flags instance.
    
    Returns:
        Global MCPFeatureFlags instance
    """
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = MCPFeatureFlags()
    return _feature_flags


def reload_feature_flags() -> MCPFeatureFlags:
    """
    Reload feature flags from environment variables.
    
    Returns:
        Reloaded MCPFeatureFlags instance
    """
    global _feature_flags
    _feature_flags = MCPFeatureFlags()
    return _feature_flags


# Convenience functions for common flag checks






def is_hot_reload_enabled() -> bool:
    """Check if hot reload is enabled."""
    return get_feature_flags().is_enabled("MCP_HOT_RELOAD_ENABLED")