"""Database connection management and query utilities."""

import logging
import os
import time
import urllib.parse
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

from datetime import datetime
import json
import traceback
import psycopg2
import psycopg2.extensions
from psycopg2.pool import ThreadedConnectionPool
from fastapi.concurrency import run_in_threadpool

from automagik.config import settings
from automagik.db.providers.factory import get_database_provider

# Configure logger
logger = logging.getLogger(__name__)

# Legacy support - these are now handled by providers
_pool: Optional[ThreadedConnectionPool] = None

# Register UUID adapter for psycopg2 (PostgreSQL compatibility)
psycopg2.extensions.register_adapter(uuid.UUID, lambda u: psycopg2.extensions.AsIs(f"'{u}'"))


def _is_shutdown_requested() -> bool:
    """Check if shutdown has been requested from main.py signal handler."""
    try:
        import automagik.main
        return getattr(automagik.main, '_shutdown_requested', False)
    except (ImportError, AttributeError):
        return False


def _interruptible_sleep(seconds: float) -> None:
    """Sleep that can be interrupted by shutdown signal or KeyboardInterrupt."""
    start_time = time.time()
    check_interval = 0.05
    
    while time.time() - start_time < seconds:
        if _is_shutdown_requested():
            logger.info("Sleep interrupted by shutdown signal - exiting immediately")
            raise KeyboardInterrupt("Shutdown requested")
        
        try:
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Sleep interrupted by KeyboardInterrupt - exiting immediately")
            raise
            
        if _is_shutdown_requested():
            logger.info("Sleep interrupted by shutdown signal after interval - exiting immediately")
            raise KeyboardInterrupt("Shutdown requested")


def generate_uuid() -> uuid.UUID:
    """Safely generate a new UUID."""
    provider = get_database_provider()
    return provider.generate_uuid()


def safe_uuid(value: Any) -> Any:
    """Convert UUID objects to strings for safe database use."""
    provider = get_database_provider()
    return provider.safe_uuid(value)


def check_migrations(connection) -> Tuple[bool, List[str]]:
    """Check if all migrations are applied."""
    provider = get_database_provider()
    return provider.check_migrations(connection)


def verify_database_health() -> bool:
    """Verify database health and migrations status."""
    provider = get_database_provider()
    return provider.verify_health()


def get_db_config() -> Dict[str, Any]:
    """Get database configuration - for backward compatibility."""
    provider = get_database_provider()
    if provider.get_database_type() != "postgresql":
        return {}
        
    # PostgreSQL configuration parsing
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
            logger.warning(f"Failed to parse AUTOMAGIK_DATABASE_URL: {str(e)}. Falling back to individual settings.")

    # Individual PostgreSQL settings have been removed - DATABASE_URL is now required
    raise ValueError("Database URL parsing failed and individual PostgreSQL settings are no longer supported")


def get_connection_pool(skip_health_check: bool = False):
    """Get or create a database connection pool."""
    provider = get_database_provider()
    return provider.get_connection_pool(skip_health_check=skip_health_check)


@contextmanager
def get_db_connection() -> Generator:
    """Get a database connection from the pool."""
    provider = get_database_provider()
    with provider.get_connection() as conn:
        yield conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Generator:
    """Get a database cursor with automatic commit/rollback."""
    provider = get_database_provider()
    with provider.get_cursor(commit=commit) as cursor:
        yield cursor


def execute_query(query: str, params: tuple = None, fetch: bool = True, commit: bool = True) -> List[Dict[str, Any]]:
    """Execute a database query and return the results."""
    provider = get_database_provider()
    return provider.execute_query(query, params, fetch, commit)


def execute_batch(query: str, params_list: List[Tuple], commit: bool = True) -> None:
    """Execute a batch query with multiple parameter sets."""
    provider = get_database_provider()
    return provider.execute_batch(query, params_list, commit)


def close_connection_pool() -> None:
    """Close the database connection pool."""
    provider = get_database_provider()
    provider.close_connection_pool()


def verify_db_read_write():
    """Performs a read/write test using a transaction rollback."""
    logger.info("🔍 Performing verification test of message storage without creating persistent sessions...")
    test_user_id = generate_uuid()
    
    # Create a test user and commit it to the database
    test_email = "test_verification@automagik.test"
    
    # Import user-related functions locally to avoid circular dependencies at module level
    from automagik.db.models import User
    from automagik.db import create_user, delete_user
    
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
        
        # Use provider-specific database connection
        from automagik.db.providers.factory import get_database_provider
        provider = get_database_provider()
        
        if provider.get_database_type() == "sqlite":
            # SQLite-specific transaction handling
            # Generate test UUIDs
            test_session_id = generate_uuid()
            test_message_id = generate_uuid()
            
            # Use provider execute_query for SQLite which handles parameter conversion
            try:
                # Insert test session
                provider.execute_query(
                    """
                    INSERT INTO sessions (id, user_id, platform, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (safe_uuid(test_session_id), safe_uuid(test_user_id), "verification_test", datetime.now(), datetime.now()),
                    fetch=False,
                    commit=False
                )
                
                # Insert test message
                provider.execute_query(
                    """
                    INSERT INTO messages (
                        id, session_id, user_id, role, text_content, raw_payload, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        safe_uuid(test_message_id),
                        safe_uuid(test_session_id),
                        safe_uuid(test_user_id),
                        "user",
                        "Test database connection",
                        json.dumps({"content": "Test database connection"}),
                        datetime.now(),
                        datetime.now()
                    ),
                    fetch=False,
                    commit=False
                )
                
                # Verify we can read the data back
                session_result = provider.execute_query(
                    "SELECT COUNT(*) FROM sessions WHERE id = %s", 
                    (safe_uuid(test_session_id),)
                )
                session_count = session_result[0]['COUNT(*)'] if session_result else 0
                
                message_result = provider.execute_query(
                    "SELECT COUNT(*) FROM messages WHERE id = %s", 
                    (safe_uuid(test_message_id),)
                )
                message_count = message_result[0]['COUNT(*)'] if message_result else 0
                
                if session_count > 0 and message_count > 0:
                    logger.info("✅ Database read/write test successful within transaction")
                else:
                    logger.error("❌ Failed to verify database read operations within transaction")
                    raise Exception("Database verification failed: Could not read back inserted test data")
                
                # Clean up test data manually for SQLite (since we're not using transactions)
                provider.execute_query("DELETE FROM messages WHERE id = %s", (safe_uuid(test_message_id),), fetch=False)
                provider.execute_query("DELETE FROM sessions WHERE id = %s", (safe_uuid(test_session_id),), fetch=False)
                logger.info("✅ Test data cleaned up successfully")
                
            except Exception as sqlite_error:
                logger.error(f"SQLite test failed: {sqlite_error}")
                # Try to clean up anyway
                try:
                    provider.execute_query("DELETE FROM messages WHERE id = %s", (safe_uuid(test_message_id),), fetch=False)
                    provider.execute_query("DELETE FROM sessions WHERE id = %s", (safe_uuid(test_session_id),), fetch=False)
                except Exception:
                    pass
                raise sqlite_error
                
        else:
            # PostgreSQL transaction handling (original logic)
            with get_db_connection() as conn:
                conn.autocommit = False  # PostgreSQL style
                
                # Generate test UUIDs
                test_session_id = generate_uuid()
                test_message_id = generate_uuid()
                
                with conn.cursor() as cur:
                    # Insert test session
                    cur.execute(
                        """
                        INSERT INTO sessions (id, user_id, platform, created_at, updated_at) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (safe_uuid(test_session_id), safe_uuid(test_user_id), "verification_test", datetime.now(), datetime.now())
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
                            safe_uuid(test_user_id),
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
                        conn.rollback()
                        raise Exception("Database verification failed: Could not read back inserted test data")
                    
                    # Roll back the transaction to avoid persisting test data
                    conn.rollback()
                    logger.info("✅ Test transaction rolled back - no test data persisted")
        
        logger.info("✅ Database verification completed successfully without creating persistent test data")

    except Exception as test_e:
        logger.error(f"❌ Database verification test failed: {str(test_e)}")
        logger.error(f"Detailed error: {traceback.format_exc()}")
        raise
    finally:
        # Clean up the test user regardless of transaction success/failure
        try:
            delete_user(test_user_id)
            logger.info(f"Cleaned up test user {test_user_id}")
        except Exception as cleanup_e:
            logger.warning(f"⚠️ Failed to clean up test user {test_user_id}: {str(cleanup_e)}")
            logger.warning(f"Cleanup error details: {traceback.format_exc()}")


# Async wrappers
async def async_execute_query(
    query: str,
    params: tuple | None = None,
    *,
    fetch: bool = True,
    commit: bool = True,
):
    """Async wrapper around execute_query that runs in a threadpool."""
    return await run_in_threadpool(execute_query, query, params, fetch, commit)


async def async_execute_batch(
    query: str,
    params_list: List[Tuple],
    *,
    commit: bool = True,
):
    """Async wrapper around execute_batch that runs in a threadpool."""
    return await run_in_threadpool(execute_batch, query, params_list, commit)


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database using provider-specific method."""
    try:
        provider = get_database_provider()
        return provider.table_exists(table_name)
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False


def get_table_columns(table_name: str) -> List[str]:
    """Get list of column names for a table using provider-specific method."""
    try:
        provider = get_database_provider()
        return provider.get_table_columns(table_name)
    except Exception as e:
        logger.error(f"Error getting columns for table {table_name}: {e}")
        return []