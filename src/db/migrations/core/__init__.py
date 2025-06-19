"""
Comprehensive Database Migration Package

This package provides a robust, enterprise-grade migration system with:
- Full CRUD operations with validation
- Comprehensive error handling and recovery
- Migration versioning and rollback support
- Schema validation and integrity checks
- Batch operations with transaction safety
- Detailed logging and monitoring
"""

from .engine import MigrationEngine
from .validator import MigrationValidator
from .operations import MigrationOperations
from .models import Migration, MigrationStatus, MigrationBatch
from .exceptions import (
    MigrationError,
    ValidationError,
    RollbackError,
    ConflictError,
    IntegrityError
)

__version__ = "1.0.0"
__all__ = [
    "MigrationEngine",
    "MigrationValidator", 
    "MigrationOperations",
    "Migration",
    "MigrationStatus",
    "MigrationBatch",
    "MigrationError",
    "ValidationError",
    "RollbackError",
    "ConflictError",
    "IntegrityError"
]