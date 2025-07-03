"""Base database provider interface."""

import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Tuple, Union
from datetime import datetime

class DatabaseProvider(ABC):
    """Abstract base class for database providers."""
    
    @abstractmethod
    def get_connection_pool(self):
        """Get or create a database connection pool."""
        pass
    
    @abstractmethod
    @contextmanager
    def get_connection(self) -> Generator:
        """Get a database connection from the pool."""
        pass
    
    @abstractmethod
    @contextmanager
    def get_cursor(self, commit: bool = False) -> Generator:
        """Get a database cursor with automatic commit/rollback."""
        pass
    
    @abstractmethod
    def execute_query(
        self, 
        query: str, 
        params: Union[tuple, dict, None] = None, 
        fetch: bool = True, 
        commit: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute a database query and return the results."""
        pass
    
    @abstractmethod
    def execute_batch(
        self, 
        query: str, 
        params_list: List[Tuple], 
        commit: bool = True
    ) -> None:
        """Execute a batch query with multiple parameter sets."""
        pass
    
    @abstractmethod
    def close_connection_pool(self) -> None:
        """Close the database connection pool."""
        pass
    
    @abstractmethod
    def verify_health(self) -> bool:
        """Verify database health and connectivity."""
        pass
    
    @abstractmethod
    def check_migrations(self, connection) -> Tuple[bool, List[str]]:
        """Check if all migrations are applied."""
        pass
    
    @abstractmethod
    def apply_migrations(self, migrations_dir: str) -> bool:
        """Apply pending migrations."""
        pass
    
    @abstractmethod
    def generate_uuid(self) -> uuid.UUID:
        """Generate a new UUID."""
        pass
    
    @abstractmethod
    def safe_uuid(self, value: Any) -> Any:
        """Convert UUID objects to strings for safe database use."""
        pass
    
    @abstractmethod
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime for database storage."""
        pass
    
    @abstractmethod
    def parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime from database storage."""
        pass
    
    @abstractmethod
    def handle_jsonb(self, data: Dict[str, Any]) -> Any:
        """Handle JSONB data for storage/retrieval."""
        pass
    
    @abstractmethod
    def get_database_type(self) -> str:
        """Get the database type identifier."""
        pass
    
    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check if the provider supports a specific feature."""
        pass
    
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        pass
    
    @abstractmethod
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for a table."""
        pass
    
    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}({self.get_database_type()})"
    
    def __repr__(self) -> str:
        """String representation of the provider."""
        return self.__str__()