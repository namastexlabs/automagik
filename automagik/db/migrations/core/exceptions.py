"""
Migration-specific exceptions with detailed error context.
"""

from typing import Optional, Dict, Any, List


class MigrationError(Exception):
    """Base exception for all migration-related errors."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.migration_name = migration_name
        self.context = context or {}
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.migration_name:
            base_msg = f"Migration '{self.migration_name}': {base_msg}"
        if self.context:
            base_msg += f" (Context: {self.context})"
        return base_msg


class ValidationError(MigrationError):
    """Raised when migration validation fails."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None,
                 validation_errors: Optional[List[str]] = None):
        super().__init__(message, migration_name)
        self.validation_errors = validation_errors or []
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.validation_errors:
            errors_str = "; ".join(self.validation_errors)
            base_msg += f" (Validation errors: {errors_str})"
        return base_msg


class RollbackError(MigrationError):
    """Raised when migration rollback fails."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None,
                 rollback_sql: Optional[str] = None):
        super().__init__(message, migration_name)
        self.rollback_sql = rollback_sql


class ConflictError(MigrationError):
    """Raised when migration conflicts with existing schema or data."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None,
                 conflicting_objects: Optional[List[str]] = None):
        super().__init__(message, migration_name)
        self.conflicting_objects = conflicting_objects or []


class IntegrityError(MigrationError):
    """Raised when migration would violate data integrity constraints."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None,
                 constraint_violations: Optional[List[str]] = None):
        super().__init__(message, migration_name)
        self.constraint_violations = constraint_violations or []


class DependencyError(MigrationError):
    """Raised when migration dependencies are not satisfied."""
    
    def __init__(self, message: str, migration_name: Optional[str] = None,
                 missing_dependencies: Optional[List[str]] = None):
        super().__init__(message, migration_name)
        self.missing_dependencies = missing_dependencies or []


class LockError(MigrationError):
    """Raised when unable to acquire migration lock."""
    
    def __init__(self, message: str, lock_holder: Optional[str] = None,
                 lock_acquired_at: Optional[str] = None):
        super().__init__(message)
        self.lock_holder = lock_holder
        self.lock_acquired_at = lock_acquired_at