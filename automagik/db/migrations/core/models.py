"""
Pydantic models for migration system.
"""

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from pydantic import BaseModel, Field, validator, root_validator


class MigrationStatus(str, Enum):
    """Migration execution status."""
    PENDING = "pending"
    RUNNING = "running"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIALLY_APPLIED = "partially_applied"


class MigrationPriority(str, Enum):
    """Migration priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Migration(BaseModel):
    """Comprehensive migration model with validation and metadata."""
    
    # Core identification
    id: str = Field(..., description="Unique migration identifier")
    name: str = Field(..., description="Human-readable migration name")
    version: str = Field(..., description="Migration version (timestamp-based)")
    
    # Content and validation
    sql_content: str = Field(..., description="Migration SQL content")
    rollback_sql: Optional[str] = Field(None, description="Rollback SQL content")
    checksum: str = Field(..., description="SHA256 checksum of SQL content")
    
    # Metadata
    description: Optional[str] = Field(None, description="Migration description")
    author: Optional[str] = Field(None, description="Migration author")
    priority: MigrationPriority = Field(MigrationPriority.MEDIUM, description="Migration priority")
    tags: List[str] = Field(default_factory=list, description="Migration tags")
    
    # Dependencies and relationships
    dependencies: List[str] = Field(default_factory=list, description="Required migration IDs")
    conflicts_with: List[str] = Field(default_factory=list, description="Conflicting migration IDs")
    
    # Execution context
    database_type: Optional[str] = Field(None, description="Target database type")
    min_version: Optional[str] = Field(None, description="Minimum database version")
    max_version: Optional[str] = Field(None, description="Maximum database version")
    
    # Runtime information
    status: MigrationStatus = Field(MigrationStatus.PENDING, description="Current status")
    applied_at: Optional[datetime] = Field(None, description="Application timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Validation flags
    is_idempotent: bool = Field(False, description="Whether migration is idempotent")
    has_data_migration: bool = Field(False, description="Whether migration modifies data")
    is_destructive: bool = Field(False, description="Whether migration drops/truncates")
    
    @validator('checksum', pre=True, always=True)
    def generate_checksum(cls, v, values):
        """Generate checksum from SQL content if not provided."""
        if v is None and 'sql_content' in values:
            content = values['sql_content']
            return hashlib.sha256(content.encode('utf-8')).hexdigest()
        return v
    
    @validator('version', pre=True, always=True)
    def validate_version_format(cls, v):
        """Validate version follows timestamp format."""
        if v and not v.replace('_', '').replace('-', '').isdigit():
            raise ValueError("Version must be timestamp-based (YYYYMMDD_HHMMSS)")
        return v
    
    @root_validator
    def validate_destructive_operations(cls, values):
        """Warn about destructive operations."""
        sql_content = values.get('sql_content', '').upper()
        destructive_keywords = ['DROP TABLE', 'TRUNCATE', 'DELETE FROM', 'DROP COLUMN']
        
        if any(keyword in sql_content for keyword in destructive_keywords):
            values['is_destructive'] = True
            
        return values
    
    @classmethod
    def from_file(cls, file_path: Path, **kwargs) -> 'Migration':
        """Create migration from SQL file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Migration file not found: {file_path}")
            
        content = file_path.read_text(encoding='utf-8')
        
        # Extract metadata from comments
        metadata = cls._extract_metadata_from_sql(content)
        
        # Generate ID from filename
        migration_id = file_path.stem
        
        return cls(
            id=migration_id,
            name=metadata.get('name', migration_id),
            version=cls._extract_version_from_filename(file_path.name),
            sql_content=content,
            description=metadata.get('description'),
            author=metadata.get('author'),
            **kwargs
        )
    
    @staticmethod
    def _extract_metadata_from_sql(content: str) -> Dict[str, str]:
        """Extract metadata from SQL comments."""
        metadata = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-- @'):
                # Format: -- @key: value
                parts = line[4:].split(':', 1)
                if len(parts) == 2:
                    key, value = parts
                    metadata[key.strip()] = value.strip()
                    
        return metadata
    
    @staticmethod
    def _extract_version_from_filename(filename: str) -> str:
        """Extract version from filename."""
        # Assumes format: YYYYMMDD_HHMMSS_description.sql
        parts = filename.split('_')
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return filename.split('.')[0]


class MigrationBatch(BaseModel):
    """Represents a batch of migrations to be executed together."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Batch ID")
    name: str = Field(..., description="Batch name")
    migrations: List[Migration] = Field(..., description="Migrations in batch")
    
    # Execution settings
    fail_fast: bool = Field(True, description="Stop on first failure")
    use_transaction: bool = Field(True, description="Execute in single transaction")
    parallel_execution: bool = Field(False, description="Execute migrations in parallel")
    
    # Status tracking
    status: MigrationStatus = Field(MigrationStatus.PENDING, description="Batch status")
    started_at: Optional[datetime] = Field(None, description="Batch start time")
    completed_at: Optional[datetime] = Field(None, description="Batch completion time")
    success_count: int = Field(0, description="Number of successful migrations")
    failure_count: int = Field(0, description="Number of failed migrations")
    
    @validator('migrations')
    def validate_migration_order(cls, v):
        """Ensure migrations are in correct dependency order."""
        # Simple validation - check versions are ascending
        versions = [m.version for m in v]
        if versions != sorted(versions):
            raise ValueError("Migrations must be ordered by version")
        return v
    
    def get_total_migrations(self) -> int:
        """Get total number of migrations in batch."""
        return len(self.migrations)
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get migrations that haven't been applied yet."""
        return [m for m in self.migrations if m.status == MigrationStatus.PENDING]
    
    def get_failed_migrations(self) -> List[Migration]:
        """Get migrations that failed."""
        return [m for m in self.migrations if m.status == MigrationStatus.FAILED]


class MigrationExecutionContext(BaseModel):
    """Context information for migration execution."""
    
    # Database connection info
    connection_string: str = Field(..., description="Database connection string")
    database_type: str = Field(..., description="Database type (postgresql, sqlite, etc.)")
    database_version: Optional[str] = Field(None, description="Database version")
    
    # Execution environment
    dry_run: bool = Field(False, description="Whether this is a dry run")
    auto_rollback: bool = Field(True, description="Auto-rollback on failure")
    backup_before_migration: bool = Field(False, description="Create backup before migration")
    
    # Monitoring and logging
    enable_monitoring: bool = Field(True, description="Enable performance monitoring")
    log_level: str = Field("INFO", description="Logging level")
    
    # Constraints and limits
    max_execution_time_seconds: int = Field(3600, description="Maximum execution time")
    lock_timeout_seconds: int = Field(30, description="Lock acquisition timeout")
    
    class Config:
        validate_assignment = True