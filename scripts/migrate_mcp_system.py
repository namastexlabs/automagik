#!/usr/bin/env python3
"""
MCP System Migration Script - NMSTX-253

This script migrates from the complex 2-table MCP system to the simplified 
single-table architecture with JSON configuration storage.

IMPORTANT: This script includes backup and rollback functionality.
FEATURE FLAGS: Supports safe production rollout with automatic safety triggers.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import (
    # Legacy functions
    list_mcp_servers, get_agent_server_assignments,
    # New functions
    create_mcp_config, list_mcp_configs
)
from src.db.models import MCPConfigCreate
from src.db.connection import execute_query, get_db_connection
from src.config import settings

# Import new centralized safety systems
from src.config.feature_flags import get_feature_flags, MCPFeatureFlags
from src.mcp.migration_monitor import MigrationMonitor, MonitoringLevel
from src.mcp.safety_triggers import SafetyTriggerSystem

logger = logging.getLogger(__name__)


# Legacy FeatureFlags class - replaced by centralized MCPFeatureFlags
class FeatureFlags:
    """Feature flag management for safe migration rollout."""
    
    def __init__(self):
        self.flags = {
            "MCP_USE_NEW_SYSTEM": self._get_env_bool("MCP_USE_NEW_SYSTEM", False),
            "MCP_MIGRATION_ENABLED": self._get_env_bool("MCP_MIGRATION_ENABLED", False),
            "MCP_SAFETY_CHECKS": self._get_env_bool("MCP_SAFETY_CHECKS", True),
            "MCP_AUTO_ROLLBACK": self._get_env_bool("MCP_AUTO_ROLLBACK", True),
            "MCP_MONITORING_ENABLED": self._get_env_bool("MCP_MONITORING_ENABLED", True),
        }
    
    def _get_env_bool(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable."""
        value = os.environ.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def is_enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled."""
        return self.flags.get(flag, False)
    
    def enable(self, flag: str):
        """Enable a feature flag."""
        self.flags[flag] = True
        os.environ[flag] = "true"
    
    def disable(self, flag: str):
        """Disable a feature flag."""
        self.flags[flag] = False
        os.environ[flag] = "false"


class MigrationMonitor:
    """Monitors migration progress and triggers safety measures."""
    
    def __init__(self):
        self.start_time = None
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}
        self.safety_thresholds = {
            "max_errors": 5,
            "max_duration_minutes": 30,
            "min_success_rate": 0.8,
            "max_response_time_ms": 5000,
        }
    
    def start_monitoring(self):
        """Start monitoring the migration process."""
        self.start_time = time.time()
        logger.info("🔍 Migration monitoring started")
    
    def record_error(self, error: str, context: str = ""):
        """Record an error during migration."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "context": context
        }
        self.errors.append(error_entry)
        logger.error(f"❌ Migration error: {error} (Context: {context})")
        
        # Check if we've hit the error threshold
        if len(self.errors) >= self.safety_thresholds["max_errors"]:
            raise SafetyThresholdExceeded(f"Too many errors: {len(self.errors)}")
    
    def record_warning(self, warning: str, context: str = ""):
        """Record a warning during migration."""
        warning_entry = {
            "timestamp": datetime.now().isoformat(),
            "warning": warning,
            "context": context
        }
        self.warnings.append(warning_entry)
        logger.warning(f"⚠️ Migration warning: {warning} (Context: {context})")
    
    def check_duration_threshold(self):
        """Check if migration is taking too long."""
        if self.start_time:
            duration_minutes = (time.time() - self.start_time) / 60
            if duration_minutes > self.safety_thresholds["max_duration_minutes"]:
                raise SafetyThresholdExceeded(f"Migration exceeded time limit: {duration_minutes:.1f} minutes")
    
    def test_response_time(self) -> float:
        """Test system response time after migration changes."""
        start = time.time()
        try:
            # Simple database query to test response time
            execute_query("SELECT 1", fetch=True)
            response_time_ms = (time.time() - start) * 1000
            
            if response_time_ms > self.safety_thresholds["max_response_time_ms"]:
                self.record_warning(
                    f"High response time: {response_time_ms:.1f}ms",
                    "post_migration_test"
                )
            
            return response_time_ms
        except Exception as e:
            self.record_error(f"Response time test failed: {e}", "post_migration_test")
            return float('inf')
    
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        duration = (time.time() - self.start_time) if self.start_time else 0
        return {
            "duration_minutes": duration / 60,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "performance_metrics": self.performance_metrics
        }


class SafetyThresholdExceeded(Exception):
    """Raised when safety thresholds are exceeded during migration."""
    pass


class MCPMigration:
    """Handles migration from legacy MCP system to simplified config system."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.backup_data = {}
        
        # Use centralized feature flags system
        self.feature_flags = get_feature_flags()
        
        # Use centralized monitoring system with intensive monitoring for migration
        self.monitor = MigrationMonitor(monitoring_level=MonitoringLevel.INTENSIVE)
        
        # Initialize safety trigger system
        self.safety_triggers = SafetyTriggerSystem()
        self.safety_triggers.add_rollback_handler(self._handle_auto_rollback)
        
        self.auto_rollback_enabled = self.feature_flags.is_enabled("MCP_ENABLE_AUTO_ROLLBACK")
    
    def _handle_auto_rollback(self, trigger_event) -> None:
        """Handle automatic rollback triggered by safety system."""
        logger.critical(f"🚨 Auto-rollback triggered: {trigger_event.message}")
        try:
            # Clear the partially migrated data
            if not self.dry_run:
                execute_query("DELETE FROM mcp_configs", fetch=False)
                logger.info("✅ Automatic rollback completed - cleared mcp_configs")
        except Exception as e:
            logger.error(f"❌ Automatic rollback failed: {e}")
        
    def backup_existing_data(self) -> Dict[str, Any]:
        """Export current mcp_servers and agent_mcp_servers data.
        
        Returns:
            Dictionary containing backup data
        """
        logger.info("📦 Backing up existing MCP data...")
        
        backup = {
            "timestamp": datetime.now().isoformat(),
            "version": "legacy_to_simplified",
            "mcp_servers": [],
            "agent_assignments": []
        }
        
        try:
            # Backup MCP servers
            servers = list_mcp_servers(enabled_only=False)
            for server in servers:
                server_data = {
                    "id": server.id,
                    "name": server.name,
                    "server_type": server.server_type,
                    "description": server.description,
                    "command": server.command,
                    "env": server.env,
                    "http_url": server.http_url,
                    "auto_start": server.auto_start,
                    "max_retries": server.max_retries,
                    "timeout_seconds": server.timeout_seconds,
                    "tags": server.tags,
                    "priority": server.priority,
                    "status": server.status,
                    "enabled": server.enabled,
                    "tools_discovered": server.tools_discovered,
                    "resources_discovered": server.resources_discovered,
                    "created_at": server.created_at.isoformat() if server.created_at else None,
                    "updated_at": server.updated_at.isoformat() if server.updated_at else None
                }
                backup["mcp_servers"].append(server_data)
            
            # Backup agent assignments
            assignments = get_agent_server_assignments()
            for assignment in assignments:
                assignment_data = {
                    "id": assignment.id,
                    "agent_id": assignment.agent_id,
                    "mcp_server_id": assignment.mcp_server_id,
                    "created_at": assignment.created_at.isoformat() if assignment.created_at else None
                }
                backup["agent_assignments"].append(assignment_data)
            
            logger.info(f"✅ Backed up {len(backup['mcp_servers'])} servers and {len(backup['agent_assignments'])} assignments")
            self.backup_data = backup
            return backup
            
        except Exception as e:
            logger.error(f"❌ Error backing up data: {e}")
            raise
    
    def transform_server_config(self, server_data: Dict[str, Any], agent_names: List[str]) -> Dict[str, Any]:
        """Transform legacy server data to new config format.
        
        Args:
            server_data: Legacy server data
            agent_names: List of agent names assigned to this server
            
        Returns:
            New configuration dictionary
        """
        config = {
            "name": server_data["name"],
            "server_type": server_data["server_type"],
            "enabled": server_data.get("enabled", True),
            "auto_start": server_data.get("auto_start", True),
            "timeout": (server_data.get("timeout_seconds", 30) * 1000),  # Convert to ms
            "retry_count": server_data.get("max_retries", 3),
            "agents": agent_names if agent_names else ["*"]  # Default to wildcard if no assignments
        }
        
        # Add optional fields
        if server_data.get("description"):
            config["description"] = server_data["description"]
        
        if server_data.get("tags"):
            config["tags"] = server_data["tags"]
        
        if server_data.get("priority"):
            config["priority"] = server_data["priority"]
        
        # Add type-specific configuration
        if server_data["server_type"] == "stdio":
            if server_data.get("command"):
                config["command"] = server_data["command"]
            if server_data.get("env"):
                config["environment"] = server_data["env"]
        elif server_data["server_type"] == "http":
            if server_data.get("http_url"):
                config["url"] = server_data["http_url"]
        
        # Add tools configuration (default to include all)
        config["tools"] = {"include": ["*"], "exclude": []}
        
        return config
    
    def get_agent_names_for_server(self, server_id: int) -> List[str]:
        """Get agent names assigned to a server from backup data.
        
        Args:
            server_id: Legacy server ID
            
        Returns:
            List of agent names
        """
        agent_ids = [
            assignment["agent_id"] 
            for assignment in self.backup_data["agent_assignments"]
            if assignment["mcp_server_id"] == server_id
        ]
        
        if not agent_ids:
            return []
        
        # Get agent names from database
        try:
            placeholders = ",".join(["%s"] * len(agent_ids))
            query = f"SELECT name FROM agents WHERE id IN ({placeholders})"
            result = execute_query(query, agent_ids)
            return [row["name"] for row in result]
        except Exception as e:
            logger.warning(f"⚠️  Could not get agent names for server {server_id}: {e}")
            return []
    
    def pre_migration_checks(self) -> bool:
        """Perform safety checks before starting migration."""
        logger.info("🔍 Running pre-migration safety checks...")
        
        try:
            # Check feature flags
            if not self.feature_flags.is_enabled("MCP_MIGRATION_ENABLED"):
                logger.error("❌ Migration is disabled by feature flag MCP_MIGRATION_ENABLED")
                return False
            
            # Test database connectivity
            execute_query("SELECT 1", fetch=True)
            logger.info("✅ Database connectivity test passed")
            
            # Check if new table exists
            try:
                execute_query("SELECT COUNT(*) FROM mcp_configs", fetch=True)
                logger.info("✅ New mcp_configs table exists")
            except Exception as e:
                self.monitor.record_error(f"mcp_configs table not found: {e}", "pre_migration_check")
                return False
            
            # Check system performance baseline
            response_time = self.monitor.test_response_time()
            if response_time == float('inf'):
                return False
            
            logger.info(f"✅ Baseline response time: {response_time:.1f}ms")
            
            return True
            
        except Exception as e:
            self.monitor.record_error(f"Pre-migration check failed: {e}", "pre_migration_check")
            return False
    
    def migrate_to_new_schema(self) -> bool:
        """Transform old data to new format and create mcp_configs entries.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔄 Migrating to new MCP config schema...")
        
        # Start monitoring
        if self.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
            self.monitor.start_monitoring()
        
        # Pre-migration safety checks
        if self.feature_flags.is_enabled("MCP_SAFETY_CHECKS"):
            if not self.pre_migration_checks():
                logger.error("❌ Pre-migration safety checks failed")
                return False
        
        if not self.backup_data:
            self.monitor.record_error("No backup data available for migration", "migration_start")
            return False
        
        success_count = 0
        error_count = 0
        
        try:
            for server_data in self.backup_data["mcp_servers"]:
                try:
                    # Check monitoring thresholds periodically
                    if self.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
                        self.monitor.check_duration_threshold()
                    
                    # Get agent names for this server
                    agent_names = self.get_agent_names_for_server(server_data["id"])
                    
                    # Transform to new config format
                    config = self.transform_server_config(server_data, agent_names)
                    
                    # Create new config entry
                    if not self.dry_run:
                        config_create = MCPConfigCreate(
                            name=config["name"],
                            config=config
                        )
                        
                        config_id = create_mcp_config(config_create)
                        if config_id:
                            logger.info(f"✅ Migrated server '{config['name']}' to config ID {config_id}")
                            success_count += 1
                            
                            # Test system performance after each migration
                            if self.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
                                response_time = self.monitor.test_response_time()
                                self.monitor.performance_metrics[config['name']] = response_time
                        else:
                            error_msg = f"Failed to create config for server '{config['name']}'"
                            self.monitor.record_error(error_msg, f"server_{config['name']}")
                            error_count += 1
                    else:
                        logger.info(f"🔍 [DRY RUN] Would migrate server '{config['name']}' with config: {json.dumps(config, indent=2)}")
                        success_count += 1
                        
                except Exception as e:
                    error_msg = f"Error migrating server '{server_data.get('name', 'unknown')}': {e}"
                    self.monitor.record_error(error_msg, f"server_{server_data.get('name', 'unknown')}")
                    error_count += 1
            
            logger.info(f"📊 Migration summary: {success_count} successful, {error_count} errors")
            
            # Final safety check
            if self.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
                final_response_time = self.monitor.test_response_time()
                logger.info(f"📊 Final response time: {final_response_time:.1f}ms")
            
            return error_count == 0
            
        except SafetyThresholdExceeded as e:
            logger.error(f"🚨 Safety threshold exceeded: {e}")
            
            # Automatic rollback if enabled
            if self.auto_rollback_enabled and not self.dry_run:
                logger.warning("🔙 Triggering automatic rollback due to safety threshold")
                try:
                    # Clear the partially migrated data
                    execute_query("DELETE FROM mcp_configs", fetch=False)
                    logger.info("✅ Automatic rollback completed")
                except Exception as rollback_error:
                    logger.error(f"❌ Automatic rollback failed: {rollback_error}")
            
            return False
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("🔍 Validating migration...")
        
        try:
            # Check that all servers were migrated
            original_count = len(self.backup_data["mcp_servers"])
            migrated_configs = list_mcp_configs(enabled_only=False)
            migrated_count = len(migrated_configs)
            
            if migrated_count != original_count:
                logger.error(f"❌ Count mismatch: {original_count} original servers, {migrated_count} migrated configs")
                return False
            
            # Check that all server names exist
            original_names = {server["name"] for server in self.backup_data["mcp_servers"]}
            migrated_names = {config.name for config in migrated_configs}
            
            missing_names = original_names - migrated_names
            if missing_names:
                logger.error(f"❌ Missing server names after migration: {missing_names}")
                return False
            
            logger.info("✅ Migration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during validation: {e}")
            return False
    
    def save_backup_to_file(self, backup_path: str) -> bool:
        """Save backup data to file.
        
        Args:
            backup_path: Path to save backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_file, 'w') as f:
                json.dump(self.backup_data, f, indent=2)
            
            logger.info(f"💾 Backup saved to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving backup to {backup_path}: {e}")
            return False
    
    def rollback_migration(self, backup_path: str) -> bool:
        """Rollback migration using backup data.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔙 Rolling back migration...")
        
        try:
            # Load backup data
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Clear new mcp_configs table
            if not self.dry_run:
                execute_query("DELETE FROM mcp_configs", fetch=False)
                logger.info("🗑️  Cleared mcp_configs table")
            else:
                logger.info("🔍 [DRY RUN] Would clear mcp_configs table")
            
            logger.info("✅ Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during rollback: {e}")
            return False


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate MCP system from legacy to simplified architecture")
    parser.add_argument("--dry-run", action="store_true", help="Run migration without making changes")
    parser.add_argument("--backup-file", default="./data/mcp_backup.json", help="Path to save/load backup file")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration using backup file")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing migration")
    parser.add_argument("--enable-migration", action="store_true", help="Enable migration feature flag")
    parser.add_argument("--disable-safety", action="store_true", help="Disable safety checks (dangerous!)")
    parser.add_argument("--disable-monitoring", action="store_true", help="Disable performance monitoring")
    parser.add_argument("--disable-auto-rollback", action="store_true", help="Disable automatic rollback")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    migration = MCPMigration(dry_run=args.dry_run)
    
    # Apply command line flag overrides
    if args.enable_migration:
        migration.feature_flags.enable("MCP_MIGRATION_ENABLED")
        logger.info("🚩 Migration enabled via command line flag")
    
    if args.disable_safety:
        migration.feature_flags.disable("MCP_SAFETY_CHECKS")
        logger.warning("⚠️ Safety checks disabled via command line flag")
    
    if args.disable_monitoring:
        migration.feature_flags.disable("MCP_MONITORING_ENABLED")
        logger.warning("⚠️ Monitoring disabled via command line flag")
    
    if args.disable_auto_rollback:
        migration.feature_flags.disable("MCP_AUTO_ROLLBACK")
        logger.warning("⚠️ Auto-rollback disabled via command line flag")
    
    # Display current feature flag status
    logger.info("🚩 Feature flags status:")
    for flag, enabled in migration.feature_flags.flags.items():
        status = "ENABLED" if enabled else "DISABLED"
        logger.info(f"   {flag}: {status}")
    
    try:
        if args.rollback:
            logger.info("🔙 Starting migration rollback...")
            success = migration.rollback_migration(args.backup_file)
        elif args.validate_only:
            logger.info("🔍 Validating existing migration...")
            # Load existing backup for validation
            with open(args.backup_file, 'r') as f:
                migration.backup_data = json.load(f)
            success = migration.validate_migration()
        else:
            logger.info("🚀 Starting MCP system migration...")
            
            # Step 1: Backup existing data
            backup_data = migration.backup_existing_data()
            migration.save_backup_to_file(args.backup_file)
            
            # Step 2: Migrate to new schema
            success = migration.migrate_to_new_schema()
            
            # Step 3: Validate migration
            if success and not args.dry_run:
                success = migration.validate_migration()
        
        # Display monitoring summary
        if migration.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
            summary = migration.monitor.get_summary()
            logger.info("📊 Migration monitoring summary:")
            logger.info(f"   Duration: {summary['duration_minutes']:.1f} minutes")
            logger.info(f"   Errors: {summary['total_errors']}")
            logger.info(f"   Warnings: {summary['total_warnings']}")
            if summary['performance_metrics']:
                avg_response_time = sum(summary['performance_metrics'].values()) / len(summary['performance_metrics'])
                logger.info(f"   Average response time: {avg_response_time:.1f}ms")
        
        if success:
            if args.dry_run:
                logger.info("✅ Dry run completed successfully - no changes made")
            else:
                logger.info("✅ Migration completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Migration failed")
            # Save monitoring data for analysis
            if migration.feature_flags.is_enabled("MCP_MONITORING_ENABLED"):
                summary_file = args.backup_file.replace('.json', '_monitoring.json')
                try:
                    with open(summary_file, 'w') as f:
                        json.dump(migration.monitor.get_summary(), f, indent=2)
                    logger.info(f"📊 Monitoring data saved to {summary_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not save monitoring data: {e}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()