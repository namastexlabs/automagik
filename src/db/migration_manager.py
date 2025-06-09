"""
Enhanced migration manager with better error handling and idempotency.
"""
import logging
import psycopg2
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations with proper error handling and partial migration detection."""
    
    def __init__(self, connection):
        self.connection = connection
        self.applied_migrations = set()
        self._ensure_migrations_table()
        self._load_applied_migrations()
    
    def _ensure_migrations_table(self):
        """Ensure the migrations tracking table exists."""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    checksum VARCHAR(64),
                    applied_at TIMESTAMPTZ DEFAULT NOW(),
                    execution_time_ms INTEGER,
                    status VARCHAR(20) DEFAULT 'applied' CHECK (status IN ('applied', 'partially_applied', 'failed'))
                )
            """)
            # Add checksum column if it doesn't exist (for existing installations)
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'migrations' AND column_name = 'checksum'
                    ) THEN
                        ALTER TABLE migrations ADD COLUMN checksum VARCHAR(64);
                        ALTER TABLE migrations ADD COLUMN execution_time_ms INTEGER;
                        ALTER TABLE migrations ADD COLUMN status VARCHAR(20) DEFAULT 'applied';
                    END IF;
                END
                $$;
            """)
            self.connection.commit()
    
    def _load_applied_migrations(self):
        """Load the list of successfully applied migrations."""
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT name FROM migrations WHERE status = 'applied'")
            self.applied_migrations = {row[0] for row in cursor.fetchall()}
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of migration content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _check_partial_migration(self, migration_name: str, migration_content: str) -> Optional[str]:
        """
        Check if a migration was partially applied by examining database state.
        Returns the status of the partial migration check.
        """
        # Special handling for known problematic migrations
        if migration_name == "20250524_085600_create_mcp_tables.sql":
            with self.connection.cursor() as cursor:
                # Check if tables exist
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN ('mcp_servers', 'agent_mcp_servers')
                """)
                table_count = cursor.fetchone()[0]
                
                if table_count == 2:
                    # Tables exist, check for constraints
                    cursor.execute("""
                        SELECT COUNT(*) FROM pg_constraint 
                        WHERE conname IN ('chk_stdio_has_command', 'chk_http_has_url')
                    """)
                    constraint_count = cursor.fetchone()[0]
                    
                    if constraint_count == 2:
                        return "fully_applied"
                    else:
                        return "partially_applied"
                elif table_count > 0:
                    return "partially_applied"
        
        elif migration_name == "20250601_082232_create_preferences_tables.sql":
            with self.connection.cursor() as cursor:
                # Check if tables exist
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN ('preferences', 'preference_history')
                """)
                table_count = cursor.fetchone()[0]
                
                if table_count == 2:
                    # Tables exist, check for trigger
                    cursor.execute("""
                        SELECT COUNT(*) FROM pg_trigger 
                        WHERE tgname = 'preferences_updated_at_trigger'
                    """)
                    trigger_count = cursor.fetchone()[0]
                    
                    if trigger_count == 1:
                        return "fully_applied"
                    else:
                        return "partially_applied"
                elif table_count > 0:
                    return "partially_applied"
        
        return None
    
    def _make_migration_idempotent(self, migration_name: str, content: str) -> str:
        """
        Transform migration SQL to be idempotent where possible.
        """
        # Skip transformation if already idempotent (check for DO $$ blocks)
        if "DO $$" in content and "IF NOT EXISTS" in content:
            return content
        
        # For MCP tables migration
        if migration_name == "20250524_085600_create_mcp_tables.sql":
            # Only transform if not already transformed
            if "ALTER TABLE mcp_servers ADD CONSTRAINT chk_stdio_has_command" in content and "DO $$" not in content:
                # Replace constraint creation with idempotent version
                content = content.replace(
                    "ALTER TABLE mcp_servers ADD CONSTRAINT chk_stdio_has_command",
                    "DO $$\nBEGIN\n    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_stdio_has_command') THEN\n        ALTER TABLE mcp_servers ADD CONSTRAINT chk_stdio_has_command"
                )
                content = content.replace(
                    "CHECK (server_type != 'stdio' OR command IS NOT NULL);",
                    "CHECK (server_type != 'stdio' OR command IS NOT NULL);\n    END IF;\nEND\n$$;"
                )
                
                content = content.replace(
                    "ALTER TABLE mcp_servers ADD CONSTRAINT chk_http_has_url",
                    "DO $$\nBEGIN\n    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_http_has_url') THEN\n        ALTER TABLE mcp_servers ADD CONSTRAINT chk_http_has_url"
                )
                content = content.replace(
                    "CHECK (server_type != 'http' OR http_url IS NOT NULL);",
                    "CHECK (server_type != 'http' OR http_url IS NOT NULL);\n    END IF;\nEND\n$$;"
                )
            
            # Make triggers idempotent if not already
            if "DROP TRIGGER IF EXISTS update_mcp_servers_updated_at" not in content:
                content = content.replace(
                    "CREATE TRIGGER update_mcp_servers_updated_at",
                    "DROP TRIGGER IF EXISTS update_mcp_servers_updated_at ON mcp_servers;\nCREATE TRIGGER update_mcp_servers_updated_at"
                )
                content = content.replace(
                    "CREATE TRIGGER update_agent_mcp_servers_updated_at",
                    "DROP TRIGGER IF EXISTS update_agent_mcp_servers_updated_at ON agent_mcp_servers;\nCREATE TRIGGER update_agent_mcp_servers_updated_at"
                )
        
        # For preferences tables migration
        elif migration_name == "20250601_082232_create_preferences_tables.sql":
            # Make trigger idempotent if not already
            if "DROP TRIGGER IF EXISTS preferences_updated_at_trigger" not in content:
                content = content.replace(
                    "CREATE TRIGGER preferences_updated_at_trigger",
                    "DROP TRIGGER IF EXISTS preferences_updated_at_trigger ON preferences;\nCREATE TRIGGER preferences_updated_at_trigger"
            )
        
        return content
    
    def apply_migration(self, migration_path: Path) -> Tuple[bool, str]:
        """
        Apply a single migration file.
        Returns (success, message).
        """
        migration_name = migration_path.name
        
        # Skip SQLite-specific migrations when using PostgreSQL
        if migration_name == "00000000_000000_create_initial_schema.sql":
            return True, f"Migration '{migration_name}' is SQLite-specific, skipping for PostgreSQL."
        
        # Check if already applied
        if migration_name in self.applied_migrations:
            return True, f"Migration '{migration_name}' already applied, skipping."
        
        try:
            # Read migration content
            with open(migration_path, 'r') as f:
                original_content = f.read()
            
            checksum = self._calculate_checksum(original_content)
            
            # Check for partial application
            partial_status = self._check_partial_migration(migration_name, original_content)
            
            if partial_status == "fully_applied":
                # Migration was fully applied but not recorded
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO migrations (name, checksum, status) VALUES (%s, %s, 'applied')",
                        (migration_name, checksum)
                    )
                self.connection.commit()
                return True, f"Migration '{migration_name}' was already fully applied. Recorded in migrations table."
            
            # Make migration idempotent
            migration_content = self._make_migration_idempotent(migration_name, original_content)
            
            # Apply migration
            start_time = datetime.now()
            
            # Use a savepoint for this specific migration
            with self.connection.cursor() as cursor:
                cursor.execute("SAVEPOINT migration_savepoint")
                
                try:
                    cursor.execute(migration_content)
                    
                    # Record successful migration
                    execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    cursor.execute(
                        "INSERT INTO migrations (name, checksum, execution_time_ms, status) VALUES (%s, %s, %s, 'applied')",
                        (migration_name, checksum, execution_time_ms)
                    )
                    
                    cursor.execute("RELEASE SAVEPOINT migration_savepoint")
                    self.connection.commit()
                    
                    self.applied_migrations.add(migration_name)
                    return True, f"✅ Migration '{migration_name}' applied successfully in {execution_time_ms}ms"
                    
                except Exception as e:
                    cursor.execute("ROLLBACK TO SAVEPOINT migration_savepoint")
                    
                    # Check if it's a "already exists" error that we can safely ignore
                    error_msg = str(e).lower()
                    if any(phrase in error_msg for phrase in ["already exists", "duplicate key", "already added"]):
                        # Record as applied since the objects already exist
                        cursor.execute(
                            "INSERT INTO migrations (name, checksum, status) VALUES (%s, %s, 'applied') ON CONFLICT (name) DO NOTHING",
                            (migration_name, checksum)
                        )
                        self.connection.commit()
                        return True, f"⚠️ Migration '{migration_name}' objects already exist. Marked as applied."
                    
                    raise e
                    
        except Exception as e:
            return False, f"❌ Failed to apply migration '{migration_name}': {e}"
    
    def apply_all_migrations(self, migrations_dir: Path) -> Tuple[int, int, List[str]]:
        """
        Apply all pending migrations from a directory.
        Returns (success_count, error_count, error_messages).
        """
        if not migrations_dir.exists():
            return 0, 0, ["Migrations directory not found"]
        
        migration_files = sorted(migrations_dir.glob("*.sql"))
        success_count = 0
        error_count = 0
        error_messages = []
        
        for migration_file in migration_files:
            success, message = self.apply_migration(migration_file)
            
            if success:
                success_count += 1
                logger.info(message)
            else:
                error_count += 1
                error_messages.append(message)
                logger.error(message)
        
        return success_count, error_count, error_messages