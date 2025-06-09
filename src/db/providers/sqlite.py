"""SQLite database provider implementation."""

import logging
import os
import sqlite3
import uuid
import json
import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from fastapi.concurrency import run_in_threadpool

from .base import DatabaseProvider

logger = logging.getLogger(__name__)

class SQLiteConnectionPool:
    """Simple connection pool for SQLite to handle concurrent access."""
    
    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool = Queue(maxsize=max_connections)
        self._all_connections = []
        self._lock = threading.Lock()
        
        # Initialize the pool
        for _ in range(max_connections):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper configuration."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.database_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None  # Enable autocommit mode
        )
        
        # Enable foreign keys and WAL mode for better concurrent access
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 134217728")  # 128MB
        
        # Configure row factory for dict-like results
        conn.row_factory = self._dict_factory
        
        with self._lock:
            self._all_connections.append(conn)
        
        return conn
    
    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary."""
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        try:
            conn = self._pool.get(timeout=10)
            return conn
        except Empty:
            # If pool is empty, create a new connection
            logger.warning("Connection pool exhausted, creating new connection")
            return self._create_connection()
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except:
            # Pool is full, close the connection
            conn.close()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            # Close all connections in the pool
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break
            
            # Close any remaining connections
            for conn in self._all_connections:
                try:
                    conn.close()
                except:
                    pass
            
            self._all_connections.clear()

class SQLiteProvider(DatabaseProvider):
    """SQLite database provider implementation."""
    
    def __init__(self, database_path: str = None):
        self.database_path = database_path or self._get_default_database_path()
        self._pool: Optional[SQLiteConnectionPool] = None
        self._migrations_applied = set()
    
    def _get_default_database_path(self) -> str:
        """Get the default SQLite database path."""
        # Use environment variable if set, otherwise default to data directory
        db_path = os.environ.get("SQLITE_DATABASE_PATH")
        if db_path:
            return db_path
        
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        return str(data_dir / "automagik.db")
    
    def get_database_type(self) -> str:
        """Get the database type identifier."""
        return "sqlite"
    
    def supports_feature(self, feature: str) -> bool:
        """Check if the provider supports a specific feature."""
        supported_features = {
            "jsonb": False,  # SQLite doesn't have native JSONB, but we can simulate it
            "json": True,    # SQLite supports JSON functions
            "uuid": True,    # We handle UUIDs as strings
            "foreign_keys": True,
            "transactions": True,
            "connection_pool": True,
            "async_operations": True,
            "concurrent_access": True,  # Limited compared to PostgreSQL
            "full_text_search": True,   # SQLite FTS
            "gin_indexes": False        # PostgreSQL specific
        }
        return supported_features.get(feature, False)
    
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
        """Handle JSONB data for storage/retrieval - SQLite uses JSON text."""
        if data is None:
            return None
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return data
    
    def get_connection_pool(self) -> SQLiteConnectionPool:
        """Get or create a database connection pool."""
        if self._pool is None:
            logger.info(f"Creating SQLite connection pool for database: {self.database_path}")
            self._pool = SQLiteConnectionPool(self.database_path, max_connections=10)
        
        return self._pool
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Get a database connection from the pool."""
        pool = self.get_connection_pool()
        conn = None
        try:
            conn = pool.get_connection()
            yield conn
        finally:
            if conn:
                pool.return_connection(conn)
    
    @contextmanager
    def get_cursor(self, commit: bool = False) -> Generator:
        """Get a database cursor with automatic commit/rollback."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
        # Convert PostgreSQL-style queries to SQLite compatible format
        query = self._convert_query_to_sqlite(query)
        
        with self.get_cursor(commit=commit) as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                # SQLite with dict factory returns rows as dicts
                return cursor.fetchall()
            return []
    
    def execute_batch(
        self, 
        query: str, 
        params_list: List[Tuple], 
        commit: bool = True
    ) -> None:
        """Execute a batch query with multiple parameter sets."""
        query = self._convert_query_to_sqlite(query)
        
        with self.get_cursor(commit=commit) as cursor:
            cursor.executemany(query, params_list)
    
    def _convert_query_to_sqlite(self, query: str) -> str:
        """Convert PostgreSQL-specific query syntax to SQLite."""
        # Convert RETURNING clauses (SQLite supports them in newer versions)
        # Convert JSONB operators to JSON functions
        # Convert UUID-specific operations
        # Convert timestamp operations
        
        # Basic conversions for common patterns
        conversions = [
            # PostgreSQL CURRENT_TIMESTAMP to SQLite
            ("CURRENT_TIMESTAMP", "datetime('now')"),
            # PostgreSQL boolean literals
            ("TRUE", "1"),
            ("FALSE", "0"),
            # PostgreSQL string concatenation
            ("||", "||"),  # SQLite supports this
            # PostgreSQL ILIKE to SQLite (case-insensitive)
            (" ILIKE ", " LIKE "),
        ]
        
        converted_query = query
        for pg_syntax, sqlite_syntax in conversions:
            converted_query = converted_query.replace(pg_syntax, sqlite_syntax)
        
        return converted_query
    
    def close_connection_pool(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            self._pool.close_all()
            self._pool = None
            logger.info("Closed all SQLite database connections")
    
    def check_migrations(self, connection) -> Tuple[bool, List[str]]:
        """Check if all migrations are applied."""
        try:
            # Create migrations table if it doesn't exist
            connection.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
                    status TEXT NOT NULL DEFAULT 'applied'
                )
            """)
            connection.commit()
            
            # Get applied migrations
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM migrations WHERE status = 'applied'")
            applied_migrations = {row['name'] for row in cursor.fetchall()}
            
            # Get the migrations directory path
            migrations_dir = Path("src/db/migrations")
            if not migrations_dir.exists():
                logger.warning("No migrations directory found")
                return True, []
            
            # Get all SQL files and sort them by name (which includes timestamp)
            migration_files = sorted(migrations_dir.glob("*.sql"))
            
            if not migration_files:
                return True, []
            
            # Check for pending migrations
            pending_migrations = []
            for migration_file in migration_files:
                migration_name = migration_file.name
                if migration_name not in applied_migrations:
                    pending_migrations.append(migration_name)
            
            return len(pending_migrations) == 0, pending_migrations
            
        except Exception as e:
            logger.error(f"Error checking migrations: {e}")
            return False, []
    
    def apply_migrations(self, migrations_dir: str) -> bool:
        """Apply pending migrations."""
        try:
            migrations_path = Path(migrations_dir)
            if not migrations_path.exists():
                logger.warning(f"Migrations directory {migrations_dir} does not exist")
                return True
            
            with self.get_connection() as conn:
                # Create migrations table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        checksum TEXT NOT NULL,
                        applied_at TEXT NOT NULL DEFAULT (datetime('now')),
                        status TEXT NOT NULL DEFAULT 'applied'
                    )
                """)
                conn.commit()
                
                # Get applied migrations
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM migrations WHERE status = 'applied'")
                applied_migrations = {row['name'] for row in cursor.fetchall()}
                
                # Get all migration files
                migration_files = sorted(migrations_path.glob("*.sql"))
                
                for migration_file in migration_files:
                    migration_name = migration_file.name
                    
                    if migration_name in applied_migrations:
                        continue
                    
                    logger.info(f"Applying migration: {migration_name}")
                    
                    # Read and convert migration SQL
                    migration_sql = migration_file.read_text()
                    migration_sql = self._convert_migration_to_sqlite(migration_sql)
                    
                    # Calculate checksum
                    import hashlib
                    checksum = hashlib.sha256(migration_sql.encode()).hexdigest()
                    
                    try:
                        # Execute migration in a transaction
                        conn.execute("BEGIN")
                        
                        # Execute migration SQL
                        for statement in migration_sql.split(';'):
                            statement = statement.strip()
                            if statement and not statement.startswith('--'):
                                try:
                                    conn.execute(statement)
                                except Exception as stmt_error:
                                    # Log but continue for some SQLite-specific errors
                                    if "duplicate column name" in str(stmt_error).lower():
                                        logger.info(f"Column already exists, skipping: {stmt_error}")
                                        continue
                                    elif "no such table" in str(stmt_error).lower() and "ALTER TABLE" in statement.upper():
                                        logger.info(f"Table doesn't exist for ALTER, skipping: {stmt_error}")
                                        continue
                                    else:
                                        raise stmt_error
                        
                        # Record migration as applied
                        conn.execute(
                            "INSERT INTO migrations (name, checksum, status) VALUES (?, ?, 'applied')",
                            (migration_name, checksum)
                        )
                        
                        conn.commit()
                        logger.info(f"Successfully applied migration: {migration_name}")
                        
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to apply migration {migration_name}: {e}")
                        return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def _convert_migration_to_sqlite(self, migration_sql: str) -> str:
        """Convert PostgreSQL migration SQL to SQLite compatible format."""
        import re
        
        # Handle PostgreSQL DO blocks
        converted_sql = self._handle_do_blocks(migration_sql)
        
        # Remove PostgreSQL specific statements that SQLite doesn't support
        # Remove RAISE NOTICE statements
        converted_sql = re.sub(r'RAISE\s+NOTICE\s+[^;]+;', '', converted_sql, flags=re.IGNORECASE)
        
        # Remove COMMENT ON statements (SQLite doesn't support them)
        converted_sql = re.sub(r'COMMENT\s+ON\s+[^;]+;', '', converted_sql, flags=re.IGNORECASE)
        
        # Convert common PostgreSQL syntax to SQLite
        conversions = [
            # UUID type to TEXT
            ("UUID", "TEXT"),
            # JSONB to TEXT (we'll store JSON as text)
            ("JSONB", "TEXT"),
            # SERIAL to INTEGER PRIMARY KEY AUTOINCREMENT
            ("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            ("SERIAL", "INTEGER"),
            # TIMESTAMP to TEXT (SQLite doesn't have native timestamp)
            ("TIMESTAMP", "TEXT"),
            ("TIMESTAMPTZ", "TEXT"),
            # Boolean type (SQLite uses INTEGER for boolean)
            ("BOOLEAN", "INTEGER"),
            # Default values
            ("DEFAULT NOW()", "DEFAULT (datetime('now'))"),
            ("DEFAULT CURRENT_TIMESTAMP", "DEFAULT (datetime('now'))"),
            ("DEFAULT TRUE", "DEFAULT 1"),
            ("DEFAULT FALSE", "DEFAULT 0"),
            # Remove PostgreSQL-specific extensions and functions
            ("CREATE EXTENSION IF NOT EXISTS", "-- CREATE EXTENSION IF NOT EXISTS"),
            # Convert GIN indexes to regular indexes (SQLite doesn't support GIN)
            ("USING gin", ""),
            ("USING GIN", ""),
            # Convert PostgreSQL operators
            ("->", "->"),  # SQLite supports JSON operators in newer versions
            ("->>", "->>"),
        ]
        
        for pg_syntax, sqlite_syntax in conversions:
            converted_sql = converted_sql.replace(pg_syntax, sqlite_syntax)
        
        # Remove IF NOT EXISTS from ALTER TABLE (SQLite doesn't support it well)
        converted_sql = converted_sql.replace("ADD COLUMN IF NOT EXISTS", "ADD COLUMN")
        
        return converted_sql
    
    def _handle_do_blocks(self, migration_sql: str) -> str:
        """Convert PostgreSQL DO blocks to SQLite equivalent."""
        import re
        
        # Remove DO blocks entirely and extract the SQL inside
        # Pattern: DO $$ ... END $$;
        do_pattern = r'DO\s+\$\$\s*(.*?)\s*END\s+\$\$;'
        
        def extract_sql_from_do_block(match):
            block_content = match.group(1)
            
            # Extract actual SQL statements from IF blocks
            # Look for ALTER TABLE, UPDATE, INSERT, etc. statements
            sql_statements = []
            
            # Pattern for IF NOT EXISTS blocks with ALTER TABLE
            if_not_exists_pattern = r'IF\s+NOT\s+EXISTS\s*\(.*?\)\s*THEN\s*(.*?)\s*(?:ELSE|END\s+IF)'
            for if_match in re.finditer(if_not_exists_pattern, block_content, re.DOTALL | re.IGNORECASE):
                sql_content = if_match.group(1).strip()
                if sql_content:
                    sql_statements.append(sql_content)
            
            # Pattern for IF EXISTS blocks
            if_exists_pattern = r'IF\s+EXISTS\s*\(.*?\)\s*THEN\s*(.*?)\s*(?:ELSE|END\s+IF)'
            for if_match in re.finditer(if_exists_pattern, block_content, re.DOTALL | re.IGNORECASE):
                sql_content = if_match.group(1).strip()
                if sql_content:
                    sql_statements.append(sql_content)
            
            # If no specific patterns found, try to extract any SQL statements
            if not sql_statements:
                # Look for common SQL statements
                statement_patterns = [
                    r'(ALTER\s+TABLE\s+[^;]+;)',
                    r'(UPDATE\s+[^;]+;)',
                    r'(INSERT\s+[^;]+;)',
                    r'(CREATE\s+[^;]+;)',
                    r'(COMMENT\s+ON\s+[^;]+;)'
                ]
                
                for pattern in statement_patterns:
                    for stmt_match in re.finditer(pattern, block_content, re.DOTALL | re.IGNORECASE):
                        sql_statements.append(stmt_match.group(1).strip())
            
            # Return the extracted SQL statements
            if sql_statements:
                return '\\n'.join(sql_statements)
            else:
                # If we can't extract anything useful, comment out the block
                return f'-- Converted DO block: {block_content[:100]}...'
        
        # Replace all DO blocks
        converted = re.sub(do_pattern, extract_sql_from_do_block, migration_sql, flags=re.DOTALL | re.IGNORECASE)
        
        return converted
    
    def verify_health(self) -> bool:
        """Verify database health and migrations status."""
        try:
            with self.get_connection() as conn:
                # Test basic connectivity
                conn.execute("SELECT 1")
                
                # Check migrations
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