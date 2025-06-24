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
from src.config import settings

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
    
    def _is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested from main.py signal handler."""
        try:
            import src.main
            return getattr(src.main, '_shutdown_requested', False)
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
        # Try to use DATABASE_URL first
        if settings.DATABASE_URL:
            try:
                env_db_url = os.environ.get("DATABASE_URL")
                actual_db_url = env_db_url if env_db_url else settings.DATABASE_URL
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
                    f"Failed to parse DATABASE_URL: {str(e)}. Falling back to individual settings."
                )

        # Fallback to individual settings
        return {
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "user": settings.POSTGRES_USER,
            "password": settings.POSTGRES_PASSWORD,
            "database": settings.POSTGRES_DB,
            "client_encoding": "UTF8",
        }
    
    def get_connection_pool(self) -> ThreadedConnectionPool:
        """Get or create a database connection pool."""
        if self._pool is None:
            config = self._get_db_config()
            max_retries = 5
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                if self._is_shutdown_requested():
                    logger.info("Database connection pool initialization interrupted by shutdown signal")
                    raise KeyboardInterrupt("Shutdown requested")
                    
                try:
                    min_conn = getattr(settings, "POSTGRES_POOL_MIN", 1)
                    max_conn = getattr(settings, "POSTGRES_POOL_MAX", 10)

                    logger.info(
                        f"Connecting to PostgreSQL at {config['host']}:{config['port']}/{config['database']} with UTF8 encoding..."
                    )

                    if self._is_shutdown_requested():
                        logger.info("Database connection attempt aborted due to shutdown signal")
                        raise KeyboardInterrupt("Shutdown requested during connection attempt")

                    # Try with DATABASE_URL first
                    if settings.DATABASE_URL and attempt == 0:
                        try:
                            dsn = settings.DATABASE_URL
                            if "client_encoding" not in dsn.lower():
                                if "?" in dsn:
                                    dsn += "&client_encoding=UTF8"
                                else:
                                    dsn += "?client_encoding=UTF8"

                            self._pool = ThreadedConnectionPool(
                                minconn=min_conn, maxconn=max_conn, dsn=dsn
                            )
                            logger.info("Successfully connected to PostgreSQL using DATABASE_URL with UTF8 encoding")
                            
                            # Set encoding correctly
                            with self._pool.getconn() as conn:
                                with conn.cursor() as cursor:
                                    cursor.execute("SET client_encoding = 'UTF8';")
                                    conn.commit()
                                self._pool.putconn(conn)
                            break
                        except Exception as e:
                            logger.warning(f"Failed to connect using DATABASE_URL: {str(e)}. Will try with individual params.")

                    # Try with individual params
                    self._pool = ThreadedConnectionPool(
                        minconn=min_conn,
                        maxconn=max_conn,
                        host=config["host"],
                        port=config["port"],
                        user=config["user"],
                        password=config["password"],
                        database=config["database"],
                        client_encoding="UTF8",
                    )
                    
                    # Set encoding correctly
                    with self._pool.getconn() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("SET client_encoding = 'UTF8';")
                            conn.commit()
                        self._pool.putconn(conn)
                    
                    logger.info("Successfully connected to PostgreSQL database with UTF8 encoding")
                    
                    # Verify database health after successful connection
                    if not self.verify_health():
                        logger.error("Database health check failed. Please run 'automagik agents db init' to apply pending migrations.")
                        raise Exception("Database migrations are not up to date")
                    
                    break
                    
                except KeyboardInterrupt:
                    logger.info("Database connection attempt interrupted by user - exiting immediately")
                    raise
                    
                except psycopg2.Error as e:
                    if self._is_shutdown_requested():
                        logger.info("Shutdown requested during database error handling - exiting immediately")
                        raise KeyboardInterrupt("Shutdown requested during error handling")
                        
                    if attempt < max_retries - 1:
                        logger.warning(f"Failed to connect to database (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        
                        if self._is_shutdown_requested():
                            logger.info("Shutdown requested before retry delay - exiting immediately")
                            raise KeyboardInterrupt("Shutdown requested before retry")
                        
                        try:
                            self._interruptible_sleep(retry_delay)
                        except KeyboardInterrupt:
                            logger.info("Database connection retry interrupted by user - exiting immediately")
                            raise
                            
                        if self._is_shutdown_requested():
                            logger.info("Shutdown requested after retry delay - exiting immediately")
                            raise KeyboardInterrupt("Shutdown requested after retry delay")
                    else:
                        logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                        raise

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
        with self.get_cursor(commit=commit) as cursor:
            execute_values(cursor, query, params_list)
    
    def close_connection_pool(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Closed all PostgreSQL database connections")
    
    def check_migrations(self, connection) -> Tuple[bool, List[str]]:
        """Check if all migrations are applied."""
        try:
            from src.db.migration_manager import MigrationManager
            
            # Get the migrations directory path
            migrations_dir = Path("src/db/migrations")
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
            from src.db.migration_manager import MigrationManager
            
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
            migrations_dir = Path("src/db/migrations")
            
            if not migrations_dir.exists():
                return True, []
            
            # Get all migration files
            migration_files = sorted(migrations_dir.glob("*.sql"))
            pending_migrations = []
            
            for migration_file in migration_files:
                migration_name = migration_file.name
                # Skip SQLite-specific migrations for PostgreSQL
                if migration_name == "00000000_000000_create_initial_schema.sql":
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
                
                success_count, error_count, error_messages = manager.apply_all_migrations(migrations_path)
                
                if error_count > 0:
                    for error_msg in error_messages:
                        logger.error(error_msg)
                    return False
                
                logger.info(f"✅ Applied {success_count} migrations successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")
            return False