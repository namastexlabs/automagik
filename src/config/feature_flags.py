"""
Feature Flag System for MCP Migration Safety - NMSTX-257

Provides environment-variable-driven feature flags for safe production rollout
of the NMSTX-253 MCP System Refactor with immediate rollback capability.

This module replaces the embedded FeatureFlags class in migrate_mcp_system.py
with a centralized, production-ready feature flag system.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MigrationMode(Enum):
    """Migration execution modes for safety control."""
    SAFE = "safe"          # Default: Full safety checks enabled
    FULL = "full"          # Complete migration with monitoring  
    ROLLBACK = "rollback"  # Immediate rollback mode
    VALIDATE = "validate"  # Validation-only mode


class MCPFeatureFlags:
    """
    Centralized feature flag management for MCP system migration and operation.
    
    Provides environment-variable-driven configuration with safe defaults and
    immediate rollback capabilities for production deployment.
    
    Environment Variables:
        MCP_USE_NEW_SYSTEM: Enable/disable new MCP system (default: false)
        MCP_MIGRATION_MODE: Migration execution mode (default: safe)
        MCP_BACKUP_VALIDATION: Enable backup validation (default: true)
        MCP_ENABLE_AUTO_ROLLBACK: Enable automatic rollback (default: true)
        MCP_SAFETY_CHECKS: Enable safety checks (default: true)
        MCP_MONITORING_ENABLED: Enable monitoring (default: true)
        MCP_HOT_RELOAD_ENABLED: Enable hot reload (default: true)
        MCP_PERFORMANCE_MONITORING: Enable performance tracking (default: true)
    """
    
    def __init__(self):
        """Initialize feature flags from environment variables."""
        self._flags: Dict[str, Any] = {}
        self._load_flags()
        
    def _load_flags(self) -> None:
        """Load all feature flags from environment variables with safe defaults."""
        # Core system flags
        self._flags["MCP_USE_NEW_SYSTEM"] = self._get_env_bool("MCP_USE_NEW_SYSTEM", False)
        self._flags["MCP_MIGRATION_MODE"] = self._get_env_enum("MCP_MIGRATION_MODE", MigrationMode, MigrationMode.SAFE)
        
        # Safety and validation flags (default enabled for safety)
        self._flags["MCP_BACKUP_VALIDATION"] = self._get_env_bool("MCP_BACKUP_VALIDATION", True)
        self._flags["MCP_ENABLE_AUTO_ROLLBACK"] = self._get_env_bool("MCP_ENABLE_AUTO_ROLLBACK", True)
        self._flags["MCP_SAFETY_CHECKS"] = self._get_env_bool("MCP_SAFETY_CHECKS", True)
        
        # Monitoring and performance flags (default enabled)
        self._flags["MCP_MONITORING_ENABLED"] = self._get_env_bool("MCP_MONITORING_ENABLED", True)
        self._flags["MCP_HOT_RELOAD_ENABLED"] = self._get_env_bool("MCP_HOT_RELOAD_ENABLED", True)
        self._flags["MCP_PERFORMANCE_MONITORING"] = self._get_env_bool("MCP_PERFORMANCE_MONITORING", True)
        
        # Legacy migration flags (for backward compatibility)
        self._flags["MCP_MIGRATION_ENABLED"] = self._get_env_bool("MCP_MIGRATION_ENABLED", False)
        
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
    
    def _get_env_enum(self, key: str, enum_class: type, default: Enum) -> Enum:
        """
        Get enum value from environment variable.
        
        Args:
            key: Environment variable name
            enum_class: Enum class to parse
            default: Default enum value
            
        Returns:
            Enum value
        """
        value = os.environ.get(key, default.value).lower()
        try:
            return enum_class(value)
        except ValueError:
            logger.warning(f"Invalid {key} value '{value}', using default '{default.value}'")
            return default
    
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
    
    def set_migration_mode(self, mode: MigrationMode) -> None:
        """
        Set the migration mode.
        
        Args:
            mode: Migration mode to set
        """
        self._flags["MCP_MIGRATION_MODE"] = mode
        os.environ["MCP_MIGRATION_MODE"] = mode.value
        logger.info(f"🚩 Migration mode set to: {mode.value}")
    
    def get_migration_mode(self) -> MigrationMode:
        """
        Get the current migration mode.
        
        Returns:
            Current migration mode
        """
        return self._flags.get("MCP_MIGRATION_MODE", MigrationMode.SAFE)
    
    def is_production_ready(self) -> bool:
        """
        Check if the system is configured for production deployment.
        
        Returns:
            True if all safety flags are properly configured
        """
        required_safety_flags = [
            "MCP_BACKUP_VALIDATION",
            "MCP_ENABLE_AUTO_ROLLBACK", 
            "MCP_SAFETY_CHECKS",
            "MCP_MONITORING_ENABLED"
        ]
        
        for flag in required_safety_flags:
            if not self.is_enabled(flag):
                logger.warning(f"Production safety flag disabled: {flag}")
                return False
        
        return True
    
    def emergency_rollback_mode(self) -> None:
        """
        Enable emergency rollback mode - disables new system and enables safety.
        
        This is for immediate production rollback situations.
        """
        logger.critical("🚨 EMERGENCY ROLLBACK MODE ACTIVATED")
        
        # Disable new system immediately
        self.disable_flag("MCP_USE_NEW_SYSTEM")
        
        # Enable all safety mechanisms
        self.enable_flag("MCP_BACKUP_VALIDATION")
        self.enable_flag("MCP_ENABLE_AUTO_ROLLBACK")
        self.enable_flag("MCP_SAFETY_CHECKS")
        self.enable_flag("MCP_MONITORING_ENABLED")
        
        # Set rollback migration mode
        self.set_migration_mode(MigrationMode.ROLLBACK)
        
        logger.critical("🚨 Emergency rollback flags set - system will use legacy MCP implementation")
    
    def enable_production_mode(self) -> None:
        """
        Enable production mode with new system and all safety features.
        
        This is for enabling the new MCP system in production.
        """
        logger.info("🚀 Enabling production mode")
        
        # Enable new system
        self.enable_flag("MCP_USE_NEW_SYSTEM")
        
        # Ensure all safety features are enabled
        self.enable_flag("MCP_BACKUP_VALIDATION")
        self.enable_flag("MCP_ENABLE_AUTO_ROLLBACK")
        self.enable_flag("MCP_SAFETY_CHECKS")
        self.enable_flag("MCP_MONITORING_ENABLED")
        self.enable_flag("MCP_PERFORMANCE_MONITORING")
        
        # Set safe migration mode
        self.set_migration_mode(MigrationMode.SAFE)
        
        logger.info("🚀 Production mode enabled with full safety features")
    
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
            Summary of flag status and recommendations
        """
        summary = {
            "flags": self.get_all_flags(),
            "production_ready": self.is_production_ready(),
            "migration_mode": self.get_migration_mode().value,
            "new_system_enabled": self.is_enabled("MCP_USE_NEW_SYSTEM"),
            "safety_features": {
                "backup_validation": self.is_enabled("MCP_BACKUP_VALIDATION"),
                "auto_rollback": self.is_enabled("MCP_ENABLE_AUTO_ROLLBACK"),
                "safety_checks": self.is_enabled("MCP_SAFETY_CHECKS"),
                "monitoring": self.is_enabled("MCP_MONITORING_ENABLED")
            },
            "performance_features": {
                "hot_reload": self.is_enabled("MCP_HOT_RELOAD_ENABLED"),
                "performance_monitoring": self.is_enabled("MCP_PERFORMANCE_MONITORING")
            }
        }
        
        # Add recommendations
        recommendations = []
        if not self.is_production_ready():
            recommendations.append("Enable all safety flags for production deployment")
        if self.is_enabled("MCP_USE_NEW_SYSTEM") and not self.is_enabled("MCP_MONITORING_ENABLED"):
            recommendations.append("Enable monitoring when using new system")
        if self.get_migration_mode() != MigrationMode.SAFE and self.is_enabled("MCP_USE_NEW_SYSTEM"):
            recommendations.append("Use SAFE migration mode for production")
        
        summary["recommendations"] = recommendations
        return summary


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
def use_new_mcp_system() -> bool:
    """Check if new MCP system should be used."""
    return get_feature_flags().is_enabled("MCP_USE_NEW_SYSTEM")


def is_migration_enabled() -> bool:
    """Check if migration is enabled."""
    return get_feature_flags().is_enabled("MCP_MIGRATION_ENABLED")


def is_auto_rollback_enabled() -> bool:
    """Check if automatic rollback is enabled."""
    return get_feature_flags().is_enabled("MCP_ENABLE_AUTO_ROLLBACK")


def is_monitoring_enabled() -> bool:
    """Check if monitoring is enabled."""
    return get_feature_flags().is_enabled("MCP_MONITORING_ENABLED")


def get_migration_mode() -> MigrationMode:
    """Get current migration mode."""
    return get_feature_flags().get_migration_mode()


def is_hot_reload_enabled() -> bool:
    """Check if hot reload is enabled."""
    return get_feature_flags().is_enabled("MCP_HOT_RELOAD_ENABLED")