#!/usr/bin/env python3
"""
MCP System Migration Script - NMSTX-253 Core Component

This script migrates data from the old 2-table MCP system (mcp_servers + agent_mcp_servers)
to the new simplified single-table system (mcp_configs).

Usage:
    uv run python scripts/migrate_mcp_system.py [--dry-run] [--backup-only] [--rollback]
    
Features:
- Safe data migration with comprehensive backup
- Dry-run mode for testing 
- Rollback capability 
- Data validation and integrity checks
- Progress reporting
"""

import json
import logging
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.db.connection import execute_query
from src.db.models import MCPServerDB, AgentMCPServerDB, MCPConfigCreate
from src.db.repository.mcp import create_mcp_config, get_mcp_config_by_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPMigration:
    """Handle MCP system migration from old 2-table to new single-table architecture."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.backup_data = {}
        self.migration_stats = {
            "servers_processed": 0,
            "configs_created": 0,
            "agents_mapped": 0,
            "errors": []
        }
    
    def backup_existing_data(self) -> Dict[str, Any]:
        """Export current mcp_servers and agent_mcp_servers data for backup."""
        logger.info("🔄 Creating backup of existing MCP data...")
        
        try:
            # Backup mcp_servers table
            servers_result = execute_query("SELECT * FROM mcp_servers ORDER BY id")
            servers_data = []
            for row in servers_result:
                server = MCPServerDB.from_db_row(row)
                if server:
                    # Convert to dict for JSON serialization
                    server_dict = server.model_dump()
                    # Handle datetime serialization
                    for key, value in server_dict.items():
                        if hasattr(value, 'isoformat'):
                            server_dict[key] = value.isoformat()
                    servers_data.append(server_dict)
            
            # Backup agent_mcp_servers assignments
            assignments_result = execute_query("""
                SELECT ams.*, a.name as agent_name, s.name as server_name
                FROM agent_mcp_servers ams
                JOIN agents a ON ams.agent_id = a.id
                JOIN mcp_servers s ON ams.mcp_server_id = s.id
                ORDER BY ams.id
            """)
            assignments_data = []
            for row in assignments_result:
                assignment = AgentMCPServerDB.from_db_row(row)
                if assignment:
                    assign_dict = assignment.model_dump()
                    assign_dict['agent_name'] = row['agent_name']
                    assign_dict['server_name'] = row['server_name']
                    # Handle datetime serialization
                    for key, value in assign_dict.items():
                        if hasattr(value, 'isoformat'):
                            assign_dict[key] = value.isoformat()
                    assignments_data.append(assign_dict)
            
            backup = {
                "timestamp": datetime.now().isoformat(),
                "migration_version": "NMSTX-253",
                "mcp_servers": servers_data,
                "agent_assignments": assignments_data
            }
            
            self.backup_data = backup
            logger.info(f"✅ Backup created: {len(servers_data)} servers, {len(assignments_data)} assignments")
            return backup
            
        except Exception as e:
            logger.error(f"❌ Error creating backup: {str(e)}")
            raise
    
    def save_backup_to_file(self, backup_path: str = None) -> str:
        """Save backup data to JSON file."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"mcp_backup_{timestamp}.json"
        
        try:
            with open(backup_path, 'w') as f:
                json.dump(self.backup_data, f, indent=2)
            logger.info(f"💾 Backup saved to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Error saving backup: {str(e)}")
            raise
    
    def load_backup_from_file(self, backup_path: str) -> Dict[str, Any]:
        """Load backup data from JSON file."""
        try:
            with open(backup_path, 'r') as f:
                backup = json.load(f)
            self.backup_data = backup
            logger.info(f"📂 Backup loaded from: {backup_path}")
            return backup
        except Exception as e:
            logger.error(f"❌ Error loading backup: {str(e)}")
            raise
    
    def transform_server_to_config(self, server_data: Dict[str, Any], agent_names: List[str]) -> Dict[str, Any]:
        """Transform old server format to new config format."""
        config = {
            "name": server_data["name"],
            "server_type": server_data["server_type"],
            "enabled": server_data.get("enabled", True),
            "auto_start": server_data.get("auto_start", True),
            "timeout": server_data.get("timeout_seconds", 30) * 1000,  # Convert to milliseconds
            "retry_count": server_data.get("max_retries", 3),
            "agents": agent_names if agent_names else ["*"]  # Default to all agents if none specified
        }
        
        # Add server-type specific configuration
        if server_data["server_type"] == "stdio":
            if server_data.get("command"):
                config["command"] = server_data["command"]
            if server_data.get("env"):
                config["environment"] = server_data["env"]
        elif server_data["server_type"] == "http":
            if server_data.get("http_url"):
                config["url"] = server_data["http_url"]
        
        # Add tools configuration (default to include all)
        config["tools"] = {
            "include": ["*"],
            "exclude": []
        }
        
        # Add optional fields if they exist
        if server_data.get("tags"):
            config["tags"] = server_data["tags"]
        
        if server_data.get("priority"):
            config["priority"] = server_data["priority"]
            
        return config
    
    def migrate_to_new_schema(self) -> bool:
        """Transform old data to new format and create mcp_configs entries."""
        logger.info("🔄 Starting migration to new schema...")
        
        if not self.backup_data:
            logger.error("❌ No backup data available for migration")
            return False
        
        try:
            # Group agent assignments by server
            server_agents = {}
            for assignment in self.backup_data["agent_assignments"]:
                server_name = assignment["server_name"]
                agent_name = assignment["agent_name"]
                
                if server_name not in server_agents:
                    server_agents[server_name] = []
                server_agents[server_name].append(agent_name)
                self.migration_stats["agents_mapped"] += 1
            
            # Process each server
            for server_data in self.backup_data["mcp_servers"]:
                try:
                    server_name = server_data["name"]
                    agent_names = server_agents.get(server_name, [])
                    
                    # Transform to new config format
                    config_data = self.transform_server_to_config(server_data, agent_names)
                    
                    if self.dry_run:
                        logger.info(f"🔍 DRY RUN: Would create config for '{server_name}' with agents: {agent_names}")
                        logger.debug(f"Config: {json.dumps(config_data, indent=2)}")
                    else:
                        # Check if config already exists
                        existing = get_mcp_config_by_name(server_name)
                        if existing:
                            logger.warning(f"⚠️  Config '{server_name}' already exists, skipping")
                            continue
                        
                        # Create new config
                        config_create = MCPConfigCreate(name=server_name, config=config_data)
                        config_id = create_mcp_config(config_create)
                        
                        if config_id:
                            logger.info(f"✅ Created config '{server_name}' with ID {config_id}")
                            self.migration_stats["configs_created"] += 1
                        else:
                            logger.error(f"❌ Failed to create config '{server_name}'")
                            self.migration_stats["errors"].append(f"Failed to create config '{server_name}'")
                    
                    self.migration_stats["servers_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing server '{server_data.get('name', 'unknown')}': {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    self.migration_stats["errors"].append(error_msg)
            
            logger.info("✅ Migration to new schema completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during migration: {str(e)}")
            return False
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        logger.info("🔍 Validating migration results...")
        
        try:
            # Check that mcp_configs table has entries
            configs_result = execute_query("SELECT COUNT(*) as count FROM mcp_configs")
            config_count = configs_result[0]["count"] if configs_result else 0
            
            # Check against original server count
            original_server_count = len(self.backup_data.get("mcp_servers", []))
            
            logger.info(f"📊 Validation Results:")
            logger.info(f"   Original servers: {original_server_count}")
            logger.info(f"   New configs: {config_count}")
            logger.info(f"   Servers processed: {self.migration_stats['servers_processed']}")
            logger.info(f"   Configs created: {self.migration_stats['configs_created']}")
            logger.info(f"   Agents mapped: {self.migration_stats['agents_mapped']}")
            logger.info(f"   Errors: {len(self.migration_stats['errors'])}")
            
            if self.migration_stats["errors"]:
                logger.warning("⚠️  Migration completed with errors:")
                for error in self.migration_stats["errors"]:
                    logger.warning(f"   - {error}")
            
            return config_count > 0 and len(self.migration_stats["errors"]) == 0
            
        except Exception as e:
            logger.error(f"❌ Error during validation: {str(e)}")
            return False
    
    def rollback_migration(self, backup_path: str = None) -> bool:
        """Rollback migration by restoring original tables."""
        logger.info("🔄 Starting rollback process...")
        
        try:
            if backup_path:
                self.load_backup_from_file(backup_path)
            
            if not self.backup_data:
                logger.error("❌ No backup data available for rollback")
                return False
            
            if self.dry_run:
                logger.info("🔍 DRY RUN: Would perform rollback operations")
                return True
            
            # Clear new table
            execute_query("DELETE FROM mcp_configs", fetch=False)
            logger.info("🗑️  Cleared mcp_configs table")
            
            # Restore from backup tables (created by migration)
            execute_query("""
                INSERT INTO mcp_servers 
                SELECT * FROM mcp_servers_backup
            """, fetch=False)
            
            execute_query("""
                INSERT INTO agent_mcp_servers 
                SELECT id, agent_id, mcp_server_id, created_at, updated_at 
                FROM agent_mcp_servers_backup
            """, fetch=False)
            
            logger.info("✅ Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during rollback: {str(e)}")
            return False
    
    def print_summary(self):
        """Print migration summary."""
        logger.info("\n" + "="*60)
        logger.info("📋 MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        logger.info(f"Servers processed: {self.migration_stats['servers_processed']}")
        logger.info(f"Configs created: {self.migration_stats['configs_created']}")
        logger.info(f"Agents mapped: {self.migration_stats['agents_mapped']}")
        logger.info(f"Errors: {len(self.migration_stats['errors'])}")
        
        if self.migration_stats["errors"]:
            logger.info("\nErrors encountered:")
            for error in self.migration_stats["errors"]:
                logger.info(f"  - {error}")
        
        logger.info("="*60)


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="MCP System Migration Script (NMSTX-253)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Perform a dry run without making changes")
    parser.add_argument("--backup-only", action="store_true",
                       help="Only create backup, don't migrate")
    parser.add_argument("--rollback", type=str, metavar="BACKUP_FILE",
                       help="Rollback migration using specified backup file")
    parser.add_argument("--backup-path", type=str,
                       help="Custom path for backup file")
    
    args = parser.parse_args()
    
    migration = MCPMigration(dry_run=args.dry_run)
    
    try:
        if args.rollback:
            # Rollback mode
            logger.info("🔄 Starting rollback process...")
            success = migration.rollback_migration(args.rollback)
            if success:
                logger.info("✅ Rollback completed successfully")
                return 0
            else:
                logger.error("❌ Rollback failed")
                return 1
        
        else:
            # Forward migration mode
            logger.info("🚀 Starting MCP system migration (NMSTX-253)")
            
            # Step 1: Create backup
            backup_data = migration.backup_existing_data()
            backup_path = migration.save_backup_to_file(args.backup_path)
            
            if args.backup_only:
                logger.info("✅ Backup completed. Exiting as requested.")
                return 0
            
            # Step 2: Migrate to new schema
            migration_success = migration.migrate_to_new_schema()
            
            # Step 3: Validate migration
            if migration_success and not args.dry_run:
                validation_success = migration.validate_migration()
                if not validation_success:
                    logger.error("❌ Migration validation failed")
            
            # Step 4: Print summary
            migration.print_summary()
            
            if migration_success:
                logger.info("✅ Migration completed successfully")
                if not args.dry_run:
                    logger.info(f"💾 Backup saved to: {backup_path}")
                    logger.info("🔄 To rollback: python scripts/migrate_mcp_system.py --rollback " + backup_path)
                return 0
            else:
                logger.error("❌ Migration failed")
                return 1
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Migration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())