"""Database provider factory for selecting between PostgreSQL and SQLite."""

import logging
import os
from typing import Optional

from .base import DatabaseProvider
from .postgresql import PostgreSQLProvider
from .sqlite import SQLiteProvider

logger = logging.getLogger(__name__)

# Global provider instance
_provider: Optional[DatabaseProvider] = None

def get_database_provider() -> DatabaseProvider:
    """Get the configured database provider singleton."""
    global _provider
    
    if _provider is None:
        _provider = create_database_provider()
    
    return _provider

def create_database_provider() -> DatabaseProvider:
    """Create a new database provider based on configuration."""
    # Get database type from environment variable
    db_type = os.environ.get("AUTOMAGIK_DATABASE_TYPE", "sqlite").lower()
    
    # Only auto-detect PostgreSQL if AUTOMAGIK_DATABASE_TYPE is not explicitly set
    if "AUTOMAGIK_DATABASE_TYPE" not in os.environ:
        # Check for PostgreSQL connection string to auto-detect
        database_url = os.environ.get("AUTOMAGIK_DATABASE_URL", "")
        if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
            logger.info("PostgreSQL AUTOMAGIK_DATABASE_URL detected, auto-setting AUTOMAGIK_DATABASE_TYPE to postgresql")
            db_type = "postgresql"
    
    # Create appropriate provider
    if db_type == "postgresql":
        logger.info("Using PostgreSQL database provider")
        return PostgreSQLProvider()
    elif db_type == "sqlite":
        # Get SQLite database path
        sqlite_path = os.environ.get("AUTOMAGIK_SQLITE_DATABASE_PATH")
        logger.info(f"Using SQLite database provider (path: {sqlite_path or 'default'})")
        return SQLiteProvider(database_path=sqlite_path)
    else:
        raise ValueError(f"Unsupported database type: {db_type}. Supported types: postgresql, sqlite")

def reset_database_provider():
    """Reset the global provider instance. Useful for testing."""
    global _provider
    if _provider:
        try:
            _provider.close_connection_pool()
        except Exception as e:
            logger.warning(f"Error closing database provider: {e}")
    _provider = None

def get_supported_database_types() -> list[str]:
    """Get list of supported database types."""
    return ["postgresql", "sqlite"]

def is_database_type_supported(db_type: str) -> bool:
    """Check if a database type is supported."""
    return db_type.lower() in get_supported_database_types()

def get_database_type() -> str:
    """Get the currently configured database type."""
    provider = get_database_provider()
    return provider.get_database_type()

def supports_feature(feature: str) -> bool:
    """Check if the current database provider supports a specific feature."""
    provider = get_database_provider()
    return provider.supports_feature(feature)