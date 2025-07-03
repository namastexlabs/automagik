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

class SQLiteCursorWrapper:
    """Wrapper to provide context manager support for SQLite cursors."""
    
    def __init__(self, cursor):
        self.cursor = cursor
    
    def __enter__(self):
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
    
    def __getattr__(self, name):
        return getattr(self.cursor, name)

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
        
        # SQLite cursors don't support context managers by default
        # We'll handle this in the get_cursor method instead
        
        with self._lock:
            self._all_connections.append(conn)
        
        return conn
    
    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary with JSON field parsing."""
        columns = [column[0] for column in cursor.description]
        result = dict(zip(columns, row))
        
        # Parse JSON fields that are stored as text
        json_fields = {
            'config', 'metadata', 'raw_payload', 'tool_calls', 'tool_outputs', 
            'context', 'user_data', 'channel_payload', 'preferences', 
            'old_preferences', 'new_preferences', 'args', 'env', 'command',
            'tags', 'tools_discovered', 'resources_discovered'
        }
        
        for field_name, value in result.items():
            if field_name in json_fields and value is not None and isinstance(value, str):
                try:
                    # Only parse if it looks like JSON (starts with { or [)
                    if value.strip().startswith(('{', '[')):
                        result[field_name] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, keep as string
                    pass
        
        return result
    
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
        except Exception:
            # Pool is full, close the connection
            conn.close()
    
    def getconn(self) -> sqlite3.Connection:
        """Get a connection from the pool (PostgreSQL-style interface compatibility)."""
        return self.get_connection()
    
    def putconn(self, conn: sqlite3.Connection):
        """Return a connection to the pool (PostgreSQL-style interface compatibility)."""
        self.return_connection(conn)
    
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
                except Exception:
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
        db_path = os.environ.get("AUTOMAGIK_SQLITE_DATABASE_PATH")
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
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            result = self.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
                fetch=True
            )
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for a table."""
        try:
            result = self.execute_query(
                f"PRAGMA table_info({table_name})",
                fetch=True
            )
            return [row['name'] for row in result]
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
        """Handle JSONB data for storage/retrieval - SQLite uses JSON text."""
        if data is None:
            return None
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return data
    
    def get_connection_pool(self, skip_health_check: bool = False) -> SQLiteConnectionPool:
        """Get or create a database connection pool."""
        if self._pool is None:
            logger.info(f"Creating SQLite connection pool for database: {self.database_path}")
            self._pool = SQLiteConnectionPool(self.database_path, max_connections=10)
            # Initialize schema if needed
            self._initialize_schema()
        
        return self._pool
    
    def _initialize_schema(self):
        """Initialize SQLite database schema if not already created."""
        try:
            with self.get_connection() as conn:
                # Check if core tables exist to determine if full schema initialization is needed
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
                if cursor.fetchone() is None:
                    logger.info("Initializing SQLite database schema...")
                    self._create_schema(conn)
                    logger.info("✅ SQLite database schema initialized successfully")
                else:
                    # Database already initialized – check for tables added by newer migrations
                    # This is a lightweight forward-compatibility safeguard so old databases
                    # created before the MCP + Tools refactor keep working without a manual
                    # migration step.
                    missing_table_statements = {
                        "mcp_configs": """
                        CREATE TABLE IF NOT EXISTS mcp_configs (
                            id TEXT PRIMARY KEY,
                            name TEXT UNIQUE NOT NULL,
                            config TEXT NOT NULL,
                            created_at TEXT NOT NULL DEFAULT (datetime('now')),
                            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                        );
                        CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);
                        """,
                        "tools": """
                        CREATE TABLE IF NOT EXISTS tools (
                            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
                            name TEXT NOT NULL UNIQUE,
                            type TEXT NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
                            description TEXT,
                            module_path TEXT,
                            function_name TEXT,
                            mcp_server_name TEXT,
                            mcp_tool_name TEXT,
                            parameters_schema TEXT,
                            capabilities TEXT DEFAULT '[]',
                            categories TEXT DEFAULT '[]',
                            enabled INTEGER DEFAULT 1,
                            agent_restrictions TEXT DEFAULT '[]',
                            execution_count INTEGER DEFAULT 0,
                            last_executed_at TEXT,
                            average_execution_time_ms INTEGER DEFAULT 0,
                            created_at TEXT NOT NULL DEFAULT (datetime('now')),
                            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                        );
                        CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
                        CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
                        CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
                        CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name) WHERE mcp_server_name IS NOT NULL;
                        """,
                        # tool_executions table is handled by migrations, not schema initialization
                        "workflow_processes": """
                        CREATE TABLE IF NOT EXISTS workflow_processes (
                            run_id TEXT PRIMARY KEY,
                            pid INTEGER,
                            status TEXT NOT NULL DEFAULT 'running',
                            workflow_name TEXT,
                            session_id TEXT,
                            user_id TEXT,
                            started_at TEXT DEFAULT (datetime('now')),
                            workspace_path TEXT,
                            last_heartbeat TEXT DEFAULT (datetime('now')),
                            process_info TEXT DEFAULT '{}',
                            created_at TEXT DEFAULT (datetime('now')),
                            updated_at TEXT DEFAULT (datetime('now'))
                        );
                        CREATE INDEX IF NOT EXISTS idx_workflow_processes_status ON workflow_processes(status);
                        CREATE INDEX IF NOT EXISTS idx_workflow_processes_started_at ON workflow_processes(started_at);
                        CREATE INDEX IF NOT EXISTS idx_workflow_processes_last_heartbeat ON workflow_processes(last_heartbeat);
                        CREATE INDEX IF NOT EXISTS idx_workflow_processes_session_id ON workflow_processes(session_id);
                        """
                    }

                    for table_name, ddl in missing_table_statements.items():
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if cursor.fetchone() is None:
                            logger.info(f"Adding missing table '{table_name}' to existing SQLite database…")
                            conn.executescript(ddl)
                            conn.commit()
                            logger.info(f"✅ Created table '{table_name}' and related indexes")
        except Exception as e:
            logger.error(f"Failed to initialize or upgrade SQLite schema: {e}")
            raise
    
    def _create_schema(self, conn: sqlite3.Connection):
        """Create the complete database schema for SQLite."""
        schema_sql = """
        -- Create users table
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            phone_number TEXT,
            user_data TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Create agents table
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            model TEXT NOT NULL,
            description TEXT,
            version TEXT,
            config TEXT DEFAULT '{}',
            active INTEGER DEFAULT 1,
            run_id INTEGER DEFAULT 0,
            system_prompt TEXT,
            active_default_prompt_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Create sessions table
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            agent_id INTEGER,
            agent_name TEXT,
            name TEXT,
            platform TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            run_finished_at TEXT,
            message_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );

        -- Create messages table
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            user_id TEXT,
            agent_id INTEGER,
            role TEXT NOT NULL,
            text_content TEXT,
            media_url TEXT,
            mime_type TEXT,
            message_type TEXT,
            raw_payload TEXT DEFAULT '{}',
            tool_calls TEXT DEFAULT '{}',
            tool_outputs TEXT DEFAULT '{}',
            system_prompt TEXT,
            user_feedback TEXT,
            flagged TEXT,
            context TEXT DEFAULT '{}',
            channel_payload TEXT DEFAULT '{}',
            usage TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );

        -- Create memories table
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            content TEXT,
            session_id TEXT,
            user_id TEXT,
            agent_id INTEGER,
            read_mode TEXT,
            access TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );

        -- Create prompts table
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            prompt_text TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 0,
            is_default_from_code INTEGER NOT NULL DEFAULT 0,
            status_key TEXT NOT NULL DEFAULT 'default',
            name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
            UNIQUE(agent_id, status_key, version)
        );

        -- Create mcp_servers table (comprehensive version matching PostgreSQL)
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            server_type TEXT NOT NULL CHECK (server_type IN ('stdio', 'http')),
            description TEXT,
            
            -- Server connection configuration
            command TEXT, -- JSON array of command parts for stdio servers
            env TEXT DEFAULT '{}', -- Environment variables as key-value pairs
            http_url TEXT, -- URL for HTTP servers
            
            -- Server behavior configuration
            auto_start INTEGER NOT NULL DEFAULT 1,
            max_retries INTEGER NOT NULL DEFAULT 3,
            timeout_seconds INTEGER NOT NULL DEFAULT 30,
            tags TEXT DEFAULT '[]', -- JSON array of tags for categorization
            priority INTEGER NOT NULL DEFAULT 0,
            
            -- Server state tracking
            status TEXT NOT NULL DEFAULT 'stopped' CHECK (status IN ('stopped', 'starting', 'running', 'error', 'stopping')),
            enabled INTEGER NOT NULL DEFAULT 1,
            started_at TEXT,
            last_error TEXT,
            error_count INTEGER NOT NULL DEFAULT 0,
            connection_attempts INTEGER NOT NULL DEFAULT 0,
            last_ping TEXT,
            
            -- Discovery results
            tools_discovered TEXT DEFAULT '[]', -- JSON array of discovered tool names
            resources_discovered TEXT DEFAULT '[]', -- JSON array of discovered resource URIs
            
            -- Audit trail
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_started TEXT,
            last_stopped TEXT
        );

        -- Create agent_mcp_servers table
        CREATE TABLE IF NOT EXISTS agent_mcp_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            mcp_server_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
            FOREIGN KEY (mcp_server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
            UNIQUE(agent_id, mcp_server_id)
        );

        -- Create preferences table
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            preferences TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, category)
        );

        -- Create preference_history table
        CREATE TABLE IF NOT EXISTS preference_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference_id INTEGER NOT NULL,
            old_preferences TEXT,
            new_preferences TEXT,
            changed_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (preference_id) REFERENCES preferences(id) ON DELETE CASCADE
        );

        -- Create new simplified mcp_configs table (NMSTX-253 Refactor)
        CREATE TABLE IF NOT EXISTS mcp_configs (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            config TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Create tools table for unified tool management
        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
            description TEXT,
            
            -- For code tools
            module_path TEXT,
            function_name TEXT,
            
            -- For MCP tools  
            mcp_server_name TEXT,
            mcp_tool_name TEXT,
            
            -- Tool metadata
            parameters_schema TEXT,
            capabilities TEXT DEFAULT '[]',
            categories TEXT DEFAULT '[]',
            
            -- Tool configuration
            enabled INTEGER DEFAULT 1,
            agent_restrictions TEXT DEFAULT '[]',
            
            -- Execution metadata
            execution_count INTEGER DEFAULT 0,
            last_executed_at TEXT,
            average_execution_time_ms INTEGER DEFAULT 0,
            
            -- Audit fields
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_agent_id ON messages(agent_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);
        CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
        CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
        CREATE INDEX IF NOT EXISTS idx_prompts_agent_id_status_key ON prompts(agent_id, status_key);
        CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(agent_id, status_key, is_active);
        
        -- MCP server indexes
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_name ON mcp_servers(name);
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_status ON mcp_servers(status);
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_enabled ON mcp_servers(enabled);
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_type ON mcp_servers(server_type);
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_auto_start ON mcp_servers(auto_start, enabled);
        
        -- Agent MCP server assignment indexes
        CREATE INDEX IF NOT EXISTS idx_agent_mcp_servers_agent_id ON agent_mcp_servers(agent_id);
        CREATE INDEX IF NOT EXISTS idx_agent_mcp_servers_server_id ON agent_mcp_servers(mcp_server_id);
        CREATE INDEX IF NOT EXISTS idx_mcp_servers_agent_status ON agent_mcp_servers(agent_id, mcp_server_id);
        
        -- New MCP configs indexes (NMSTX-253 Refactor)
        CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);
        
        -- Tools table indexes
        CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
        CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
        CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
        CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name) WHERE mcp_server_name IS NOT NULL;

        -- ---------------------------------------------
        -- Workflow execution process tracking (NMSTX-317)
        -- ---------------------------------------------

        -- The workflow_processes table keeps a lightweight heartbeat of all
        -- workflow runs that are currently executing (or have executed
        -- recently) inside the Automagik worker pool.  The data is used for
        -- real-time monitoring in the UI and to implement the emergency kill
        -- endpoint.  It purposely lives outside of the Jobs / Sessions
        -- hierarchy so that a stuck workflow can always be cleaned up even if
        -- higher-level records are corrupted.

        CREATE TABLE IF NOT EXISTS workflow_processes (
            run_id TEXT PRIMARY KEY,
            pid INTEGER,
            status TEXT NOT NULL DEFAULT 'running',
            workflow_name TEXT,
            session_id TEXT,
            user_id TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            workspace_path TEXT,
            last_heartbeat TEXT DEFAULT (datetime('now')),
            process_info TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_workflow_processes_status ON workflow_processes(status);
        CREATE INDEX IF NOT EXISTS idx_workflow_processes_started_at ON workflow_processes(started_at);
        CREATE INDEX IF NOT EXISTS idx_workflow_processes_last_heartbeat ON workflow_processes(last_heartbeat);
        CREATE INDEX IF NOT EXISTS idx_workflow_processes_session_id ON workflow_processes(session_id);

        -- Enable foreign key constraints
        PRAGMA foreign_keys = ON;
        """
        
        # Execute schema creation
        conn.executescript(schema_sql)
        conn.commit()
    
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
    
    def _convert_params_to_sqlite(self, params: Union[tuple, list, dict, None]) -> Union[tuple, list, dict, None]:
        """Convert parameters to SQLite-compatible types."""
        if params is None:
            return None
        
        def convert_value(value):
            # Convert UUID objects to strings
            if hasattr(value, '__class__') and value.__class__.__name__ == 'UUID':
                return str(value)
            # Convert datetime objects to ISO format strings
            elif hasattr(value, 'isoformat'):
                return value.isoformat()
            # Convert boolean values to integers for SQLite (do this before checking int since bool is subclass of int)
            elif isinstance(value, bool):
                return 1 if value else 0
            # Convert other non-basic types to strings
            elif value is not None and not isinstance(value, (str, int, float, bytes, type(None))):
                return str(value)
            return value
        
        if isinstance(params, (tuple, list)):
            converted = [convert_value(param) for param in params]
            return tuple(converted) if isinstance(params, tuple) else converted
        elif isinstance(params, dict):
            return {key: convert_value(value) for key, value in params.items()}
        else:
            return params

    def execute_query(
        self, 
        query: str, 
        params: Union[tuple, list, dict, None] = None, 
        fetch: bool = True, 
        commit: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute a database query and return the results."""
        # Convert PostgreSQL-style queries to SQLite compatible format
        query = self._convert_query_to_sqlite(query)
        # Convert parameters to SQLite-compatible types
        converted_params = self._convert_params_to_sqlite(params)
        
        with self.get_cursor(commit=commit) as cursor:
            if converted_params:
                cursor.execute(query, converted_params)
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
        # Convert all parameter sets to SQLite-compatible types
        converted_params_list = [self._convert_params_to_sqlite(params) for params in params_list]
        
        with self.get_cursor(commit=commit) as cursor:
            cursor.executemany(query, converted_params_list)
    
    def _convert_query_to_sqlite(self, query: str) -> str:
        """Convert PostgreSQL-specific query syntax to SQLite."""
        import re
        
        # Convert parameter placeholders from PostgreSQL (%s) to SQLite (?)
        converted_query = query.replace('%s', '?')
        
        # Basic conversions for common patterns
        conversions = [
            # PostgreSQL CURRENT_TIMESTAMP to SQLite
            ("CURRENT_TIMESTAMP", "datetime('now')"),
            ("NOW()", "datetime('now')"),
            # PostgreSQL boolean literals
            ("TRUE", "1"),
            ("FALSE", "0"),
            # PostgreSQL SERIAL to INTEGER PRIMARY KEY AUTOINCREMENT
            ("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            # PostgreSQL UUID default to TEXT
            ("UUID PRIMARY KEY DEFAULT gen_random_uuid()", "TEXT PRIMARY KEY"),
            # PostgreSQL TIMESTAMPTZ to TEXT
            ("TIMESTAMPTZ", "TEXT"),
            ("TIMESTAMP WITH TIME ZONE", "TEXT"),
            # PostgreSQL JSONB to TEXT
            ("JSONB", "TEXT"),
            # PostgreSQL string concatenation
            ("||", "||"),  # SQLite supports this
            # PostgreSQL ILIKE to SQLite (case-insensitive)
            (" ILIKE ", " LIKE "),
            # PostgreSQL LIMIT/OFFSET syntax (SQLite supports this)
            # PostgreSQL ON CONFLICT clauses
            ("ON CONFLICT DO NOTHING", "OR IGNORE"),
        ]
        
        for pg_syntax, sqlite_syntax in conversions:
            converted_query = converted_query.replace(pg_syntax, sqlite_syntax)
        
        # Handle PostgreSQL-specific type casting first
        # PostgreSQL: '[]'::json -> SQLite: '[]'
        converted_query = re.sub(r"'([^']+)'::json", r"'\1'", converted_query, flags=re.IGNORECASE)
        
        # Handle complex COALESCE with JSON_AGG and FILTER
        # PostgreSQL: COALESCE(JSON_AGG(...) FILTER (...), '[]')
        # SQLite: Use simpler GROUP_CONCAT approach
        complex_coalesce_pattern = r"COALESCE\(\s*JSON_AGG\(([^)]+)\s+ORDER\s+BY\s+[^)]+\)\s+FILTER\s+\([^)]+\),\s*'(\[\])'\s*\)"
        match = re.search(complex_coalesce_pattern, converted_query, re.IGNORECASE)
        if match:
            column_expr = match.group(1).strip()
            match.group(2)
            # Simple SQLite replacement that creates a JSON-like array
            replacement = f"'[' || COALESCE(GROUP_CONCAT('\"' || {column_expr} || '\"'), '') || ']'"
            converted_query = re.sub(complex_coalesce_pattern, replacement, converted_query, flags=re.IGNORECASE)
        
        # Handle standalone JSON_AGG with FILTER
        json_agg_filter_pattern = r'JSON_AGG\(([^)]+)\s+ORDER\s+BY\s+[^)]+\)\s+FILTER\s+\([^)]+\)'
        if re.search(json_agg_filter_pattern, converted_query, re.IGNORECASE):
            converted_query = re.sub(
                json_agg_filter_pattern,
                r"'[' || COALESCE(GROUP_CONCAT('\"' || \1 || '\"'), '') || ']'",
                converted_query,
                flags=re.IGNORECASE
            )
        
        # Handle simple JSON_AGG without FILTER
        simple_json_agg_pattern = r'JSON_AGG\(([^)]+)\)'
        converted_query = re.sub(
            simple_json_agg_pattern,
            r"'[' || COALESCE(GROUP_CONCAT('\"' || \1 || '\"'), '') || ']'",
            converted_query,
            flags=re.IGNORECASE
        )
        
        # Handle remaining COALESCE patterns with JSON casting
        coalesce_json_pattern = r"COALESCE\(([^,]+),\s*'(\[\])'\)"
        converted_query = re.sub(
            coalesce_json_pattern,
            r"COALESCE(\1, '\2')",
            converted_query,
            flags=re.IGNORECASE
        )
        
        # Handle PostgreSQL boolean literals in WHERE clauses
        converted_query = re.sub(r'\bTRUE\b', '1', converted_query, flags=re.IGNORECASE)
        converted_query = re.sub(r'\bFALSE\b', '0', converted_query, flags=re.IGNORECASE)
        
        # Handle PostgreSQL JSON containment operator @> for SQLite
        # PostgreSQL: config->'agents' @> '[{"agent_name"}]'
        # SQLite: JSON_SEARCH(config, 'one', 'agent_name', NULL, '$.agents[*]') IS NOT NULL
        json_contains_pattern = r"([a-zA-Z_]+)->'([^']+)'\s+@>\s+(%s|\?)"
        if re.search(json_contains_pattern, converted_query):
            # For now, replace with a simpler LIKE pattern for SQLite
            # This is a simplified approach - full JSON path queries would be more complex
            converted_query = re.sub(
                r"([a-zA-Z_]+)->'([^']+)'\s+@>\s+(%s|\?)",
                r"json_extract(\1, '$.\2') LIKE '%'||replace(replace(\3, '[', ''), ']', '')||'%'",
                converted_query
            )
        
        # Handle ORDER BY with NULLS LAST/FIRST (PostgreSQL) to SQLite equivalent
        # PostgreSQL: ORDER BY column NULLS LAST
        # SQLite: ORDER BY column IS NULL, column
        nulls_last_pattern = r'ORDER BY\s+([^,\s]+)\s+NULLS\s+LAST'
        converted_query = re.sub(
            nulls_last_pattern, 
            r'ORDER BY \1 IS NULL, \1',
            converted_query,
            flags=re.IGNORECASE
        )
        
        # PostgreSQL: ORDER BY column NULLS FIRST  
        # SQLite: ORDER BY column IS NULL DESC, column
        nulls_first_pattern = r'ORDER BY\s+([^,\s]+)\s+NULLS\s+FIRST'
        converted_query = re.sub(
            nulls_first_pattern,
            r'ORDER BY \1 IS NULL DESC, \1', 
            converted_query,
            flags=re.IGNORECASE
        )
        
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
            
            # Get the migrations directory path - check SQLite-specific first
            base_migrations_dir = Path("automagik/db/migrations")
            if not base_migrations_dir.exists():
                logger.warning("No migrations directory found")
                return True, []
            
            # Check if we're already in a SQLite-specific directory
            migrations_dir = base_migrations_dir
            if base_migrations_dir.name == "sqlite":
                # Already in SQLite-specific directory
                logger.info(f"Using SQLite-specific migrations directory: {migrations_dir}")
                base_migrations_dir = base_migrations_dir.parent  # Update base_migrations_dir to actual base
            else:
                # Check if SQLite-specific directory exists within the provided path
                sqlite_migrations_dir = base_migrations_dir / "sqlite"
                if sqlite_migrations_dir.exists():
                    migrations_dir = sqlite_migrations_dir
                    logger.info(f"Using SQLite-specific migrations directory: {migrations_dir}")
                else:
                    logger.info(f"Using base migrations directory: {migrations_dir}")
            
            # Get all SQL files and sort them by name (which includes timestamp)
            migration_files = sorted(migrations_dir.glob("*.sql"))
            
            if not migration_files:
                return True, []
            
            # Check for pending migrations
            pending_migrations = []
            for migration_file in migration_files:
                migration_name = migration_file.name
                # Skip PostgreSQL-specific migrations for SQLite (only if in base directory)
                # If we're using SQLite-specific directory, don't skip any migrations
                if (migrations_dir == base_migrations_dir and 
                    migration_name == "00000000_000000_create_initial_schema.sql"):
                    # Skip PostgreSQL-specific initial schema
                    logger.info(f"Skipping PostgreSQL-specific migration: {migration_name}")
                    continue
                    
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
                # Create a basic migration manager for SQLite
                # Note: We use a simple approach since MigrationManager is designed for PostgreSQL
                
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
                
                # Check if we're already in a SQLite-specific directory
                actual_migrations_dir = migrations_path
                if migrations_path.name == "sqlite":
                    # Already in SQLite-specific directory
                    logger.info(f"Using SQLite-specific migrations directory: {actual_migrations_dir}")
                    base_migrations_dir = migrations_path.parent  # This is the actual base directory
                else:
                    # Check if SQLite-specific directory exists within the provided path
                    sqlite_migrations_dir = migrations_path / "sqlite"
                    if sqlite_migrations_dir.exists():
                        actual_migrations_dir = sqlite_migrations_dir
                        logger.info(f"Using SQLite-specific migrations directory: {actual_migrations_dir}")
                        base_migrations_dir = migrations_path  # This is the base directory
                    else:
                        # Use the provided directory as-is
                        logger.info(f"Using base migrations directory: {actual_migrations_dir}")
                        base_migrations_dir = migrations_path
                
                # Get all migration files
                migration_files = sorted(actual_migrations_dir.glob("*.sql"))
                
                for migration_file in migration_files:
                    migration_name = migration_file.name
                    
                    # Skip PostgreSQL-specific migrations for SQLite (only if in base directory)
                    # If we're using SQLite-specific directory, don't skip any migrations
                    logger.debug(f"Checking migration {migration_name}: actual_dir={actual_migrations_dir}, base_dir={base_migrations_dir}, equal={actual_migrations_dir == base_migrations_dir}")
                    if (actual_migrations_dir == base_migrations_dir and 
                        migration_name == "00000000_000000_create_initial_schema.sql"):
                        logger.info(f"Migration '{migration_name}' is PostgreSQL-specific, skipping for SQLite.")
                        continue
                    
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
                        # Execute migration using executescript for better transaction handling
                        # This ensures all statements are executed within a single transaction
                        conn.executescript(migration_sql)
                        
                        # Record migration as applied in a separate transaction
                        conn.execute(
                            "INSERT INTO migrations (name, checksum, status) VALUES (?, ?, 'applied')",
                            (migration_name, checksum)
                        )
                        
                        conn.commit()
                        logger.info(f"Successfully applied migration: {migration_name}")
                        
                    except Exception as e:
                        conn.rollback()
                        error_msg = str(e).lower()
                        
                        # Handle idempotent migration errors - these are safe to ignore
                        if any(phrase in error_msg for phrase in [
                            "duplicate column name", 
                            "already exists", 
                            "table already exists",
                            "index already exists"
                        ]):
                            logger.info(f"Migration {migration_name} changes already exist, marking as applied")
                            # Record as applied since the changes already exist
                            conn.execute(
                                "INSERT INTO migrations (name, checksum, status) VALUES (?, ?, 'applied')",
                                (migration_name, checksum)
                            )
                            conn.commit()
                        else:
                            logger.error(f"Failed to apply migration {migration_name}: {e}")
                            return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def _convert_migration_to_sqlite(self, migration_sql: str) -> str:
        """Convert PostgreSQL migration SQL to SQLite compatible format."""
        import re
        
        # First, handle PostgreSQL DO blocks and functions - convert them to SQLite equivalents
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
            ("NOW()", "(datetime('now'))"),
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
        """Convert PostgreSQL blocks, functions, and complex syntax to SQLite equivalents."""
        import re
        
        # Handle DO blocks by removing them entirely for SQLite
        # SQLite doesn't support procedural code, so we strip them out
        do_pattern = r'DO\s+\$\$.*?\$\$;'
        migration_sql = re.sub(do_pattern, '-- PostgreSQL DO block removed for SQLite compatibility', migration_sql, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove PostgreSQL functions (CREATE OR REPLACE FUNCTION ... $$ LANGUAGE plpgsql;)
        function_pattern = r'CREATE\s+OR\s+REPLACE\s+FUNCTION.*?\$\$\s+LANGUAGE.*?;'
        migration_sql = re.sub(function_pattern, '-- PostgreSQL function removed for SQLite compatibility', migration_sql, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove PostgreSQL triggers that use functions
        trigger_pattern = r'CREATE\s+TRIGGER\s+\w+.*?EXECUTE\s+FUNCTION.*?;'
        migration_sql = re.sub(trigger_pattern, '-- PostgreSQL trigger removed for SQLite compatibility', migration_sql, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove DROP TRIGGER statements since we're not creating them
        drop_trigger_pattern = r'DROP\s+TRIGGER\s+IF\s+EXISTS.*?;'
        migration_sql = re.sub(drop_trigger_pattern, '-- DROP TRIGGER removed for SQLite compatibility', migration_sql, flags=re.IGNORECASE)
        
        # Remove PostgreSQL-specific constraint syntax
        constraint_patterns = [
            r'ADD\s+CONSTRAINT\s+\w+\s+CHECK\s*\([^)]*\?\s*[^)]*\);?',  # JSON ? operator constraints
            r'WHERE\s+\([^)]*\)\s*::\s*boolean\s*=\s*true',  # PostgreSQL boolean casting in WHERE
            r'jsonb_typeof\([^)]*\)\s*=\s*[\'"][^\'"]*[\'"]',  # jsonb_typeof function
        ]
        
        for pattern in constraint_patterns:
            migration_sql = re.sub(pattern, '-- PostgreSQL constraint removed for SQLite compatibility', migration_sql, flags=re.IGNORECASE)
        
        # Remove CREATE TABLE ... AS SELECT (backup tables)
        backup_table_pattern = r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+\w+_backup\s+AS\s+SELECT.*?;'
        migration_sql = re.sub(backup_table_pattern, '-- Backup table creation removed for SQLite compatibility', migration_sql, flags=re.DOTALL | re.IGNORECASE)
        
        return migration_sql
    
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