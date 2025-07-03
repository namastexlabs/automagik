"""PostgreSQL database provider implementation."""

import logging
import os
import time
import urllib.parse
import uuid
import json
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import ThreadedConnectionPool
from fastapi.concurrency import run_in_threadpool

from .base import DatabaseProvider
from automagik.config import settings

logger = logging.getLogger(__name__)

class PostgreSQLProvider(DatabaseProvider):
    """PostgreSQL database provider implementation."""
    
    def __init__(self):
        self._pool: Optional[ThreadedConnectionPool] = None
        # Register UUID adapter for psycopg2
        psycopg2.extensions.register_adapter(uuid.UUID, lambda u: psycopg2.extensions.AsIs(f"'{u}'"))
    
    def get_database_type(self) -> str:
        """Get the database type identifier."""
        return "postgresql"
    
    def supports_feature(self, feature: str) -> bool:
        """Check if the provider supports a specific feature."""
        supported_features = {
            "jsonb": True,
            "uuid": True,
            "foreign_keys": True,
            "transactions": True,
            "connection_pool": True,
            "async_operations": True,
            "concurrent_access": True,
            "full_text_search": True,
            "gin_indexes": True
        }
        return supported_features.get(feature, False)
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            result = self.execute_query(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table_name,),
                fetch=True
            )
            return result[0]['exists'] if result else False
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for a table."""
        try:
            result = self.execute_query(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                (table_name,),
                fetch=True
            )
            return [row['column_name'] for row in result]
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            return []
    
    def generate_uuid(self) -> uuid.UUID:
        """Generate a new UUID."""
        return uuid.uuid4()
    
    def safe_uuid(self, value: Any) -> Any:
        """Convert UUID objects to strings for safe database use."""
        if isinstance(value, uuid.UUID):
            return str(value)
        return value
    
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime for database storage."""
        return dt.isoformat()
    
    def parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime from database storage."""
        if isinstance(dt_str, datetime):
            return dt_str
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    
    def handle_jsonb(self, data: Dict[str, Any]) -> Any:
        """Handle JSONB data for storage/retrieval."""
        if data is None:
            return None
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return data
    
    def create_database_if_not_exists(self, database_name: str) -> bool:
        """Create database if it doesn't exist. Returns True if created or already exists."""
        try:
            config = self._get_db_config()
            
            # Connect to 'postgres' database to create the target database
            admin_config = config.copy()
            admin_config['database'] = 'postgres'  # Default admin database
            
            logger.info(f"Checking if database '{database_name}' exists...")
            
            # First check if database exists
            admin_conn = psycopg2.connect(**admin_config)
            admin_conn.autocommit = True
            
            with admin_conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    logger.info(f"✅ Database '{database_name}' already exists")
                    admin_conn.close()
                    return True
                
                # Create the database
                logger.info(f"Creating database '{database_name}'...")
                # Use identifier to safely quote the database name
                cursor.execute(f"CREATE DATABASE {psycopg2.extensions.quote_ident(database_name, cursor)}")
                logger.info(f"✅ Database '{database_name}' created successfully")
                
            admin_conn.close()
            return True
            
        except psycopg2.Error as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg:
                logger.info(f"✅ Database '{database_name}' already exists")
                return True
            elif "permission denied" in error_msg or "must be owner" in error_msg:
                logger.warning(f"⚠️ No permission to create database '{database_name}'. Please create it manually or use a user with CREATEDB privileges.")
                return False
            else:
                logger.error(f"❌ Failed to create database '{database_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating database '{database_name}': {e}")
            return False
    
    def _is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested from main.py signal handler."""
        try:
            import automagik.main
            return getattr(automagik.main, '_shutdown_requested', False)
        except (ImportError, AttributeError):
            return False
    
    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by shutdown signal or KeyboardInterrupt."""
        start_time = time.time()
        check_interval = 0.05  # 50ms intervals for responsive checking
        
        while time.time() - start_time < seconds:
            if self._is_shutdown_requested():
                logger.info("Sleep interrupted by shutdown signal - exiting immediately")
                raise KeyboardInterrupt("Shutdown requested")
            
            try:
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Sleep interrupted by KeyboardInterrupt - exiting immediately")
                raise
                
            if self._is_shutdown_requested():
                logger.info("Sleep interrupted by shutdown signal after interval - exiting immediately")
                raise KeyboardInterrupt("Shutdown requested")
    
    def _get_db_config(self) -> Dict[str, Any]:
        """Get database configuration from connection string or individual settings."""
        # Try to use AUTOMAGIK_DATABASE_URL first
        if settings.AUTOMAGIK_DATABASE_URL:
            try:
                env_db_url = os.environ.get("AUTOMAGIK_DATABASE_URL")
                actual_db_url = env_db_url if env_db_url else settings.AUTOMAGIK_DATABASE_URL
                parsed = urllib.parse.urlparse(actual_db_url)

                dbname = parsed.path.lstrip("/")

                return {
                    "host": parsed.hostname,
                    "port": parsed.port,
                    "user": parsed.username,
                    "password": parsed.password,
                    "database": dbname,
                    "client_encoding": "UTF8",
                }
            except Exception as e:
                logger.warning(
                    f"Failed to parse AUTOMAGIK_DATABASE_URL: {str(e)}. Falling back to individual settings."
                )

        # Fallback to individual settings - these variables have been removed
        # If DATABASE_URL parsing fails, there's no fallback anymore
        raise ValueError("Database URL parsing failed and individual PostgreSQL settings are no longer supported")
    
    def _try_connect_with_auto_create(self) -> ThreadedConnectionPool:
        """Try to connect to database, auto-creating if needed. Fail fast on permission errors."""
        config = self._get_db_config()
        database_name = config.get('database', 'automagik_agents')
        min_conn = getattr(settings, "AUTOMAGIK_POSTGRES_POOL_MIN", 1)
        max_conn = getattr(settings, "AUTOMAGIK_POSTGRES_POOL_MAX", 10)

        logger.info(f"Connecting to PostgreSQL at {config['host']}:{config['port']}/{database_name} with UTF8 encoding...")

        # First attempt: try to connect directly
        try:
            if settings.AUTOMAGIK_DATABASE_URL:
                dsn = settings.AUTOMAGIK_DATABASE_URL
                if "client_encoding" not in dsn.lower():
                    if "?" in dsn:
                        dsn += "&client_encoding=UTF8"
                    else:
                        dsn += "?client_encoding=UTF8"

                pool = ThreadedConnectionPool(minconn=min_conn, maxconn=max_conn, dsn=dsn)
                logger.info("✅ Successfully connected to PostgreSQL using DATABASE_URL with UTF8 encoding")
                return pool
            else:
                raise ValueError("AUTOMAGIK_DATABASE_URL is required for PostgreSQL connections")

        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()
            
            if "does not exist" in error_msg:
                logger.info(f"📝 Database '{database_name}' does not exist, attempting auto-creation...")
                
                # Try to create the database
                created = self.create_database_if_not_exists(database_name)
                
                if not created:
                    logger.error(f"❌ Failed to create database '{database_name}' and user lacks CREATEDB permissions")
                    logger.error("❌ Please create the database manually or use a user with CREATEDB privileges")
                    logger.error(f"❌ Manual command: CREATE DATABASE {database_name};")
                    raise Exception(f"Database '{database_name}' does not exist and cannot be auto-created due to insufficient permissions")
                
                # Database was created, now try to connect again
                logger.info(f"🔄 Attempting connection to newly created database '{database_name}'...")
                try:
                    if settings.AUTOMAGIK_DATABASE_URL:
                        dsn = settings.AUTOMAGIK_DATABASE_URL
                        if "client_encoding" not in dsn.lower():
                            if "?" in dsn:
                                dsn += "&client_encoding=UTF8"
                            else:
                                dsn += "?client_encoding=UTF8"

                        pool = ThreadedConnectionPool(minconn=min_conn, maxconn=max_conn, dsn=dsn)
                        logger.info("✅ Successfully connected to auto-created PostgreSQL database")
                        return pool
                    else:
                        raise ValueError("AUTOMAGIK_DATABASE_URL is required for PostgreSQL connections")
                
                except psycopg2.Error as retry_error:
                    logger.error(f"❌ Failed to connect even after creating database: {retry_error}")
                    raise Exception(f"Database '{database_name}' was created but connection still failed: {retry_error}")
            
            elif "permission denied" in error_msg or "authentication failed" in error_msg:
                logger.error(f"❌ Authentication failed for PostgreSQL: {e}")
                logger.error("❌ Please check username, password, and host configuration")
                raise Exception(f"PostgreSQL authentication failed: {e}")
            
            elif "could not connect" in error_msg or "connection refused" in error_msg:
                logger.error(f"❌ Cannot connect to PostgreSQL server: {e}")
                logger.error(f"❌ Please verify PostgreSQL is running on {config['host']}:{config['port']}")
                raise Exception(f"PostgreSQL server unreachable: {e}")
            
            else:
                logger.error(f"❌ Unexpected PostgreSQL connection error: {e}")
                raise Exception(f"PostgreSQL connection failed: {e}")

        except Exception as e:
            logger.error(f"❌ Unexpected error during PostgreSQL connection: {e}")
            raise

    def get_connection_pool(self, skip_health_check: bool = False) -> ThreadedConnectionPool:
        """Get or create a database connection pool with intelligent auto-creation."""
        if self._pool is None:
            if self._is_shutdown_requested():
                logger.info("Database connection pool initialization interrupted by shutdown signal")
                raise KeyboardInterrupt("Shutdown requested")
            
            # Try to connect with auto-creation - fail fast on errors
            self._pool = self._try_connect_with_auto_create()
            
            # Set encoding correctly for the pool
            with self._pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SET client_encoding = 'UTF8';")
                    conn.commit()
                self._pool.putconn(conn)
            
            # Only verify database health if explicitly requested (not during early message storage setup)
            if not skip_health_check:
                if not self.verify_health():
                    logger.error("❌ Database health check failed. Please run 'automagik agents db init' to apply pending migrations.")
                    raise Exception("Database migrations are not up to date")

        return self._pool
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Get a database connection from the pool."""
        pool = self.get_connection_pool()
        conn = None
        try:
            conn = pool.getconn()
            # Ensure UTF-8 encoding for this connection
            with conn.cursor() as cursor:
                cursor.execute("SET client_encoding = 'UTF8';")
                conn.commit()
            yield conn
        finally:
            if conn:
                pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit: bool = False) -> Generator:
        """Get a database cursor with automatic commit/rollback."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Union[tuple, dict, None] = None, 
        fetch: bool = True, 
        commit: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute a database query and return the results."""
        # Convert SQLite-style parameter placeholders to PostgreSQL style
        query = self._convert_query_to_postgresql(query)
        
        with self.get_cursor(commit=commit) as cursor:
            cursor.execute(query, params)
            
            if fetch and cursor.description:
                return [dict(record) for record in cursor.fetchall()]
            return []
    
    def execute_batch(
        self, 
        query: str, 
        params_list: List[Tuple], 
        commit: bool = True
    ) -> None:
        """Execute a batch query with multiple parameter sets."""
        # Convert SQLite-style parameter placeholders to PostgreSQL style
        query = self._convert_query_to_postgresql(query)
        
        with self.get_cursor(commit=commit) as cursor:
            execute_values(cursor, query, params_list)
    
    def _convert_query_to_postgresql(self, query: str) -> str:
        """Convert SQLite-style query syntax to PostgreSQL."""
        # Convert parameter placeholders from SQLite (?) to PostgreSQL (%s)
        converted_query = query.replace('?', '%s')
        
        # Additional conversions can be added here if needed for other SQLite->PostgreSQL conversions
        # For now, the main issue is just the parameter placeholders
        
        return converted_query
    
    def close_connection_pool(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Closed all PostgreSQL database connections")
    
    def check_migrations(self, connection) -> Tuple[bool, List[str]]:
        """Check if all migrations are applied."""
        try:
            from automagik.db.migration_manager import MigrationManager
            
            # Get the migrations directory path
            migrations_dir = Path("automagik/db/migrations")
            if not migrations_dir.exists():
                logger.warning("No migrations directory found")
                return True, []
            
            # Get all SQL files and sort them by name (which includes timestamp)
            migration_files = sorted(migrations_dir.glob("*.sql"))
            
            if not migration_files:
                return True, []
            
            # Create migration manager to check status
            migration_manager = MigrationManager(connection)
            
            # Check for pending migrations
            pending_migrations = []
            for migration_file in migration_files:
                migration_name = migration_file.name
                if migration_name not in migration_manager.applied_migrations:
                    # Also check if it was partially applied
                    partial_status = migration_manager._check_partial_migration(migration_name, "")
                    if partial_status != "fully_applied":
                        pending_migrations.append(migration_name)
            
            return len(pending_migrations) == 0, pending_migrations
            
        except Exception as e:
            logger.error(f"Error checking migrations: {e}")
            return False, []
    
    def apply_migrations(self, migrations_dir: str) -> bool:
        """Apply pending migrations."""
        try:
            from automagik.db.migration_manager import MigrationManager
            
            with self.get_connection() as conn:
                migration_manager = MigrationManager(conn)
                return migration_manager.apply_migrations(migrations_dir)
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def verify_health(self) -> bool:
        """Verify database health and migrations status."""
        try:
            with self.get_connection() as conn:
                is_healthy, pending_migrations = self.check_migrations(conn)
                
                if not is_healthy:
                    logger.warning("Database migrations are not up to date!")
                    logger.warning("Pending migrations:")
                    for migration in pending_migrations:
                        logger.warning(f"  - {migration}")
                    logger.warning("\\nPlease run 'automagik agents db init' to apply pending migrations.")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to verify database health: {e}")
            return False
    
    # Async wrappers
    async def async_execute_query(
        self,
        query: str,
        params: Union[tuple, dict, None] = None,
        *,
        fetch: bool = True,
        commit: bool = True,
    ):
        """Async wrapper around execute_query that runs in a threadpool."""
        return await run_in_threadpool(self.execute_query, query, params, fetch, commit)

    async def async_execute_batch(
        self,
        query: str,
        params_list: List[Tuple],
        *,
        commit: bool = True,
    ):
        """Async wrapper around execute_batch that runs in a threadpool."""
        return await run_in_threadpool(self.execute_batch, query, params_list, commit)
    
    def check_migrations(self, connection) -> Tuple[bool, List[str]]:
        """Check if all migrations are applied."""
        from ..migration_manager import MigrationManager
        
        try:
            manager = MigrationManager(connection)
            base_migrations_dir = Path("automagik/db/migrations")
            
            # Use database-specific directory if it exists
            postgres_migrations_dir = base_migrations_dir / "postgresql"
            if postgres_migrations_dir.exists():
                migrations_dir = postgres_migrations_dir
            else:
                migrations_dir = base_migrations_dir
            
            if not migrations_dir.exists():
                return True, []
            
            # Get all migration files
            migration_files = sorted(migrations_dir.glob("*.sql"))
            pending_migrations = []
            
            for migration_file in migration_files:
                migration_name = migration_file.name
                # Skip SQLite-specific migrations for PostgreSQL (only if in base directory)
                if migrations_dir == base_migrations_dir and migration_name == "00000000_000000_create_initial_schema.sql":
                    continue
                    
                if migration_name not in manager.applied_migrations:
                    pending_migrations.append(migration_name)
            
            return len(pending_migrations) == 0, pending_migrations
            
        except Exception as e:
            logger.error(f"Error checking migrations: {e}")
            return False, []
    
    def apply_migrations(self, migrations_dir: str) -> bool:
        """Apply pending migrations."""
        from ..migration_manager import MigrationManager
        
        try:
            with self.get_connection() as connection:
                manager = MigrationManager(connection)
                migrations_path = Path(migrations_dir)
                
                success_count, error_count, error_messages = manager.apply_all_migrations(migrations_path, "postgresql")
                
                if error_count > 0:
                    for error_msg in error_messages:
                        logger.error(error_msg)
                    return False
                
                logger.info(f"✅ Applied {success_count} migrations successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")
            return False