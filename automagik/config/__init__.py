"""
Configuration module for Automagik Agents.

This module provides centralized configuration management including
feature flags, environment settings, and application configuration.
"""

# Import main configuration classes and functions from sibling config.py module
# We need to access the config.py file at the src level
import importlib.util
import os

# Get the path to the config.py file in the parent directory  
_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
_spec = importlib.util.spec_from_file_location("src_config", _config_path)
_config_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_module)

# Import the needed items
LogLevel = _config_module.LogLevel
Environment = _config_module.Environment
Settings = _config_module.Settings
settings = _config_module.settings
load_settings = _config_module.load_settings
get_settings = _config_module.load_settings  # Alias for compatibility
mask_connection_string = _config_module.mask_connection_string
get_model_settings = _config_module.get_model_settings

from .feature_flags import (
    MCPFeatureFlags,
    get_feature_flags,
    reload_feature_flags,
    is_hot_reload_enabled
)

__all__ = [
    # Main configuration classes and functions
    "LogLevel",
    "Environment",
    "Settings",
    "settings",
    "load_settings",
    "get_settings",
    "mask_connection_string",
    "get_model_settings",
    # Feature flags
    "MCPFeatureFlags",
    "get_feature_flags",
    "reload_feature_flags",
    "is_hot_reload_enabled"
]