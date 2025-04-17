"""Database connection management and query utilities."""

import logging
import os
import time
import urllib.parse
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from pathlib import Path

import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import ThreadedConnectionPool, SimpleConnectionPool

from src.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Connection pool for database connections
_pool: Optional[ThreadedConnectionPool] = None

# Register UUID adapter for psycopg2
psycopg2.extensions.register_adapter(uuid.UUID, lambda u: psycopg2.extensions.AsIs(f"'{u}'"))


def generate_uuid() -> uuid.UUID:
    """Safely generate a new UUID.
    
    This function ensures that the uuid module is properly accessed
    and not shadowed by local variables.
    
    Returns:
        A new UUID4 object
    """
    return uuid.uuid4()


def safe_uuid(value: Any) -> Any:
    """Convert UUID objects to strings for safe database use.
    
    This is a utility function for cases where direct SQL queries are used
    instead of repository functions. It ensures UUID objects are properly
    converted to strings to prevent adaptation errors.
    
    Args:
        value: The value to convert if it's a UUID
        
    Returns:
        String representation of UUID or the original value
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def check_migrations(cursor) -> Tuple[bool, List[str]]:
    """Check if all migrations are applied.
    
    Returns:
        Tuple of (is_healthy, list_of_pending_migrations)
    """
    try:
        # Get the migrations directory path
        migrations_dir = Path("src/db/migrations")
        if not migrations_dir.exists():
            logger.warning("No migrations directory found")
            return True, []
        
        # Get all SQL files and sort them by name (which includes timestamp)
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        if not migration_files:
            return True, []
        
        # Create migrations table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Get list of already applied migrations
        cursor.execute("SELECT name FROM migrations")
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
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


def verify_database_health() -> bool:
    """Verify database health and migrations status.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        with get_db_cursor(commit=False) as cursor:
            is_healthy, pending_migrations = check_migrations(cursor)
            
            if not is_healthy:
                logger.warning("Database migrations are not up to date!")
                logger.warning("Pending migrations:")
                for migration in pending_migrations:
                    logger.warning(f"  - {migration}")
                logger.warning("\nPlease run 'automagik-agents db init' to apply pending migrations.")
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to verify database health: {e}")
        return False


def get_db_config() -> Dict[str, Any]:
    """Get database configuration from connection string or individual settings."""
    # Try to use DATABASE_URL first
    if settings.DATABASE_URL:
        try:
            # Parse the database URL
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
                "client_encoding": "UTF8",  # Explicitly set client encoding to UTF8
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
        "client_encoding": "UTF8",  # Explicitly set client encoding to UTF8
    }


def get_connection_pool() -> ThreadedConnectionPool:
    """Get or create a database connection pool."""
    global _pool

    if _pool is None:
        config = get_db_config()
        max_retries = 5
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                min_conn = getattr(settings, "POSTGRES_POOL_MIN", 1)
                max_conn = getattr(settings, "POSTGRES_POOL_MAX", 10)

                logger.info(
                    f"Connecting to PostgreSQL at {config['host']}:{config['port']}/{config['database']} with UTF8 encoding..."
                )

                # Can either connect with individual params or with a connection string
                if settings.DATABASE_URL and attempt == 0:
                    try:
                        # Add client_encoding to the connection string if not already present
                        dsn = settings.DATABASE_URL
                        if "client_encoding" not in dsn.lower():
                            if "?" in dsn:
                                dsn += "&client_encoding=UTF8"
                            else:
                                dsn += "?client_encoding=UTF8"

                        _pool = ThreadedConnectionPool(
                            minconn=min_conn, maxconn=max_conn, dsn=dsn
                        )
                        logger.info(
                            "Successfully connected to PostgreSQL using DATABASE_URL with UTF8 encoding"
                        )
                        # Make sure we set the encoding correctly
                        with _pool.getconn() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute("SET client_encoding = 'UTF8';")
                                conn.commit()
                            _pool.putconn(conn)
                        break
                    except Exception as e:
                        logger.warning(
                            f"Failed to connect using DATABASE_URL: {str(e)}. Will try with individual params."
                        )

                # Try with individual params
                _pool = ThreadedConnectionPool(
                    minconn=min_conn,
                    maxconn=max_conn,
                    host=config["host"],
                    port=config["port"],
                    user=config["user"],
                    password=config["password"],
                    database=config["database"],
                    client_encoding="UTF8",  # Explicitly set client encoding
                )
                # Make sure we set the encoding correctly
                with _pool.getconn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SET client_encoding = 'UTF8';")
                        conn.commit()
                    _pool.putconn(conn)
                logger.info(
                    "Successfully connected to PostgreSQL database with UTF8 encoding"
                )
                
                # Verify database health after successful connection
                if not verify_database_health():
                    logger.error("Database health check failed. Please run 'automagik-agents db init' to apply pending migrations.")
                    raise Exception("Database migrations are not up to date")
                
                break
            except psycopg2.Error as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to connect to database (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Failed to connect to database after {max_retries} attempts: {str(e)}"
                    )
                    raise

    return _pool


@contextmanager
def get_db_connection() -> Generator:
    """Get a database connection from the pool."""
    pool = get_connection_pool()
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
def get_db_cursor(commit: bool = False) -> Generator:
    """Get a database cursor with automatic commit/rollback."""
    with get_db_connection() as conn:
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


def execute_query(query: str, params: tuple = None, fetch: bool = True, commit: bool = True) -> List[Dict[str, Any]]:
    """Execute a database query and return the results.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch and return results
        commit: Whether to commit the transaction
        
    Returns:
        List of records as dictionaries if fetch=True, otherwise empty list
    """
    with get_db_cursor(commit=commit) as cursor:
        cursor.execute(query, params)
        
        if fetch and cursor.description:
            return [dict(record) for record in cursor.fetchall()]
        return []


def execute_batch(query: str, params_list: List[Tuple], commit: bool = True) -> None:
    """Execute a batch query with multiple parameter sets.
    
    Args:
        query: SQL query template
        params_list: List of parameter tuples
        commit: Whether to commit the transaction
    """
    with get_db_cursor(commit=commit) as cursor:
        execute_values(cursor, query, params_list)


def close_connection_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Closed all database connections")


def verify_db_read_write():
    """Performs a read/write test using a transaction rollback.
    
    Creates a temporary user, starts a transaction, inserts a session and message,
    verifies they can be read, rolls back the transaction, and deletes the user.
    Raises an exception if any part of the verification fails.
    """
    logger.info("🔍 Performing verification test of message storage without creating persistent sessions...")
    pool = get_connection_pool()
    test_user_id = generate_uuid()
    conn = None  # Initialize conn to None
    
    # Create a test user and commit it to the database
    test_email = "test_verification@automagik.test"
    
    # Import user-related functions locally to avoid circular dependencies at module level
    from src.db.models import User
    from src.db import create_user, delete_user
    
    test_user = User(
        id=test_user_id,
        email=test_email,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    try:
        create_user(test_user)  # This will be committed
        logger.info(f"Created test user with ID {test_user_id} for verification")

        # Now use a separate transaction for test session/message that will be rolled back
        logger.info("Testing database message storage functionality with transaction rollback...")
        conn = pool.getconn()
        conn.autocommit = False  # Start a transaction
        
        # Generate test UUIDs
        test_session_id = generate_uuid()
        test_message_id = generate_uuid()
        
        # Create the session and message within the transaction
        with conn.cursor() as cur:
            # Insert test session
            cur.execute(
                """
                INSERT INTO sessions (id, user_id, platform, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (safe_uuid(test_session_id), test_user_id, "verification_test", datetime.now(), datetime.now())
            )
            
            # Insert test message
            cur.execute(
                """
                INSERT INTO messages (
                    id, session_id, user_id, role, text_content, raw_payload, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    safe_uuid(test_message_id),
                    safe_uuid(test_session_id),
                    test_user_id,
                    "user",
                    "Test database connection",
                    json.dumps({"content": "Test database connection"}),
                    datetime.now(),
                    datetime.now()
                )
            )
            
            # Verify we can read the data back
            cur.execute("SELECT COUNT(*) FROM sessions WHERE id = %s", (safe_uuid(test_session_id),))
            session_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE id = %s", (safe_uuid(test_message_id),))
            message_count = cur.fetchone()[0]
            
            if session_count > 0 and message_count > 0:
                logger.info("✅ Database read/write test successful within transaction")
            else:
                logger.error("❌ Failed to verify database read operations within transaction")
                # Attempt to rollback before raising
                try: conn.rollback() 
                except: pass
                raise Exception("Database verification failed: Could not read back inserted test data")
            
            # Roll back the transaction to avoid persisting test data
            conn.rollback()
            logger.info("✅ Test transaction rolled back - no test data persisted")
        
        # Return connection to pool
        pool.putconn(conn)
        conn = None # Reset conn after putting it back
        logger.info("✅ Database verification completed successfully without creating persistent test data")

    except Exception as test_e:
        logger.error(f"❌ Database verification test failed: {str(test_e)}")
        # Ensure any open transaction is rolled back
        if conn:
            try: conn.rollback() 
            except: pass
            try: pool.putconn(conn) # Try to return connection even on error
            except: pass 
        # Log detailed error before raising
        logger.error(f"Detailed error: {traceback.format_exc()}")
        raise # Re-raise the original exception after cleanup attempts
    finally:
        # Clean up the test user regardless of transaction success/failure
        try:
            delete_user(test_user_id)
            logger.info(f"Cleaned up test user {test_user_id}")
        except Exception as cleanup_e:
            # Log as warning because the primary error (if any) is more important
            logger.warning(f"⚠️ Failed to clean up test user {test_user_id}: {str(cleanup_e)}")
            logger.warning(f"Cleanup error details: {traceback.format_exc()}") 