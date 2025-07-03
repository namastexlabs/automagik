"""
Comprehensive migration validation system.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from .models import Migration, MigrationExecutionContext
from .exceptions import ValidationError, DependencyError, ConflictError

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Comprehensive migration validator with schema and content validation."""
    
    def __init__(self, context: MigrationExecutionContext):
        self.context = context
        self.database_type = context.database_type.lower()
        
        # SQL pattern definitions
        self.destructive_patterns = [
            r'\bDROP\s+TABLE\b',
            r'\bTRUNCATE\b',
            r'\bDELETE\s+FROM\b',
            r'\bDROP\s+COLUMN\b',
            r'\bDROP\s+INDEX\b',
            r'\bDROP\s+CONSTRAINT\b'
        ]
        
        self.data_modification_patterns = [
            r'\bINSERT\s+INTO\b',
            r'\bUPDATE\b',
            r'\bDELETE\s+FROM\b',
            r'\bMERGE\b'
        ]
        
        self.idempotent_patterns = [
            r'\bIF\s+NOT\s+EXISTS\b',
            r'\bCREATE\s+OR\s+REPLACE\b',
            r'\bDO\s+\$\$\b',
            r'\bDROP\s+.*\s+IF\s+EXISTS\b'
        ]
    
    def validate_migration(self, migration: Migration) -> Tuple[bool, List[str]]:
        """
        Comprehensive migration validation.
        Returns (is_valid, error_messages).
        """
        errors = []
        
        try:
            # Basic validation
            errors.extend(self._validate_basic_structure(migration))
            
            # SQL syntax validation
            errors.extend(self._validate_sql_syntax(migration))
            
            # Content analysis
            errors.extend(self._validate_sql_content(migration))
            
            # Security validation
            errors.extend(self._validate_security(migration))
            
            # Database-specific validation
            errors.extend(self._validate_database_specific(migration))
            
            # Performance considerations
            errors.extend(self._validate_performance(migration))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Validation error for migration {migration.id}: {e}")
            return False, [f"Validation exception: {str(e)}"]
    
    def validate_batch(self, migrations: List[Migration]) -> Tuple[bool, List[str]]:
        """
        Validate a batch of migrations for dependencies and conflicts.
        """
        errors = []
        
        try:
            # Check individual migrations
            for migration in migrations:
                is_valid, migration_errors = self.validate_migration(migration)
                if not is_valid:
                    errors.extend([f"{migration.id}: {err}" for err in migration_errors])
            
            # Check dependencies
            errors.extend(self._validate_dependencies(migrations))
            
            # Check for conflicts
            errors.extend(self._validate_conflicts(migrations))
            
            # Check execution order
            errors.extend(self._validate_execution_order(migrations))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Batch validation error: {e}")
            return False, [f"Batch validation exception: {str(e)}"]
    
    def _validate_basic_structure(self, migration: Migration) -> List[str]:
        """Validate basic migration structure."""
        errors = []
        
        if not migration.id:
            errors.append("Migration ID is required")
        
        if not migration.name:
            errors.append("Migration name is required")
        
        if not migration.version:
            errors.append("Migration version is required")
        
        if not migration.sql_content or not migration.sql_content.strip():
            errors.append("Migration SQL content is required")
        
        # Validate version format
        if not re.match(r'^\d{8}_\d{6}$', migration.version):
            errors.append("Version must follow format YYYYMMDD_HHMMSS")
        
        return errors
    
    def _validate_sql_syntax(self, migration: Migration) -> List[str]:
        """Basic SQL syntax validation."""
        errors = []
        sql = migration.sql_content.strip()
        
        # Check for common syntax issues
        if sql.count('(') != sql.count(')'):
            errors.append("Unmatched parentheses in SQL")
        
        if sql.count("'") % 2 != 0:
            errors.append("Unmatched single quotes in SQL")
        
        # Check for incomplete statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        for i, stmt in enumerate(statements):
            if not stmt:
                continue
            
            # Basic statement validation
            if not self._is_valid_sql_statement(stmt):
                errors.append(f"Invalid SQL statement at position {i + 1}")
        
        return errors
    
    def _validate_sql_content(self, migration: Migration) -> List[str]:
        """Validate SQL content for patterns and best practices."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # Check for destructive operations
        destructive_ops = []
        for pattern in self.destructive_patterns:
            if re.search(pattern, sql_upper):
                destructive_ops.append(pattern)
        
        if destructive_ops and not migration.is_destructive:
            errors.append(f"Destructive operations detected but not marked: {destructive_ops}")
        
        # Check for data modifications
        data_mods = []
        for pattern in self.data_modification_patterns:
            if re.search(pattern, sql_upper):
                data_mods.append(pattern)
        
        if data_mods and not migration.has_data_migration:
            errors.append(f"Data modifications detected but not marked: {data_mods}")
        
        # Check idempotency
        idempotent_indicators = any(
            re.search(pattern, sql_upper) for pattern in self.idempotent_patterns
        )
        
        if not idempotent_indicators and not migration.is_idempotent:
            errors.append("Migration may not be idempotent - consider adding IF NOT EXISTS clauses")
        
        return errors
    
    def _validate_security(self, migration: Migration) -> List[str]:
        """Validate migration for security issues."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'\bGRANT\s+ALL\b',
            r'\bCREATE\s+USER\b',
            r'\bALTER\s+USER\b',
            r'\bDROP\s+USER\b',
            r'--\s*EXEC',  # Potential SQL injection via comments
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_upper):
                errors.append(f"Potentially dangerous operation detected: {pattern}")
        
        # Check for hardcoded credentials
        credential_patterns = [
            r'PASSWORD\s*=\s*[\'"][^\'"]+[\'"]',
            r'PWD\s*=\s*[\'"][^\'"]+[\'"]',
        ]
        
        for pattern in credential_patterns:
            if re.search(pattern, migration.sql_content, re.IGNORECASE):
                errors.append("Hardcoded credentials detected in migration")
        
        return errors
    
    def _validate_database_specific(self, migration: Migration) -> List[str]:
        """Database-specific validation."""
        errors = []
        
        if self.database_type == 'postgresql':
            errors.extend(self._validate_postgresql(migration))
        elif self.database_type == 'sqlite':
            errors.extend(self._validate_sqlite(migration))
        elif self.database_type == 'mysql':
            errors.extend(self._validate_mysql(migration))
        
        return errors
    
    def _validate_postgresql(self, migration: Migration) -> List[str]:
        """PostgreSQL-specific validation."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # Check for unsupported operations
        if 'ENUM' in sql_upper and 'ALTER TYPE' in sql_upper:
            errors.append("Altering ENUM types can be problematic in PostgreSQL")
        
        # Check for proper DO block usage
        if 'DO $$' in migration.sql_content and 'END $$' not in migration.sql_content:
            errors.append("DO blocks must be properly closed with END $$")
        
        return errors
    
    def _validate_sqlite(self, migration: Migration) -> List[str]:
        """SQLite-specific validation."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # SQLite limitations
        if 'ALTER TABLE' in sql_upper and 'DROP COLUMN' in sql_upper:
            errors.append("SQLite does not support DROP COLUMN in older versions")
        
        if 'FOREIGN KEY' in sql_upper:
            errors.append("Ensure foreign key constraints are enabled in SQLite")
        
        return errors
    
    def _validate_mysql(self, migration: Migration) -> List[str]:
        """MySQL-specific validation."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # MySQL considerations
        if 'FULLTEXT' in sql_upper:
            errors.append("FULLTEXT indexes require MyISAM or InnoDB engine")
        
        return errors
    
    def _validate_performance(self, migration: Migration) -> List[str]:
        """Validate migration for performance considerations."""
        errors = []
        sql_upper = migration.sql_content.upper()
        
        # Check for potentially slow operations
        if 'ALTER TABLE' in sql_upper and 'ADD COLUMN' in sql_upper:
            if 'DEFAULT' not in sql_upper:
                errors.append("Adding non-nullable columns without defaults can be slow")
        
        # Check for missing indexes on foreign keys
        if 'FOREIGN KEY' in sql_upper:
            errors.append("Consider adding indexes on foreign key columns for performance")
        
        # Large data operations
        if re.search(r'\bINSERT\s+INTO\b.*\bSELECT\b', sql_upper):
            errors.append("Large INSERT...SELECT operations should be batched")
        
        return errors
    
    def _validate_dependencies(self, migrations: List[Migration]) -> List[str]:
        """Validate migration dependencies."""
        errors = []
        migration_ids = {m.id for m in migrations}
        
        for migration in migrations:
            for dep_id in migration.dependencies:
                if dep_id not in migration_ids:
                    errors.append(f"Migration {migration.id} depends on missing migration {dep_id}")
        
        return errors
    
    def _validate_conflicts(self, migrations: List[Migration]) -> List[str]:
        """Validate migration conflicts."""
        errors = []
        
        for migration in migrations:
            for conflict_id in migration.conflicts_with:
                if any(m.id == conflict_id for m in migrations):
                    errors.append(f"Migration {migration.id} conflicts with {conflict_id}")
        
        return errors
    
    def _validate_execution_order(self, migrations: List[Migration]) -> List[str]:
        """Validate migration execution order."""
        errors = []
        
        # Check version ordering
        versions = [m.version for m in migrations]
        if versions != sorted(versions):
            errors.append("Migrations must be ordered by version")
        
        # Check dependency ordering
        applied_ids = set()
        for migration in migrations:
            for dep_id in migration.dependencies:
                if dep_id not in applied_ids:
                    errors.append(f"Migration {migration.id} dependency {dep_id} not applied first")
            applied_ids.add(migration.id)
        
        return errors
    
    def _is_valid_sql_statement(self, statement: str) -> bool:
        """Basic SQL statement validation."""
        statement = statement.strip().upper()
        
        # Must start with a valid SQL keyword
        valid_starts = [
            'CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE',
            'SELECT', 'WITH', 'DO', 'GRANT', 'REVOKE', 'COMMENT'
        ]
        
        return any(statement.startswith(keyword) for keyword in valid_starts)
    
    def get_migration_risk_assessment(self, migration: Migration) -> Dict[str, Any]:
        """Assess migration risk level and provide recommendations."""
        risk_factors = {
            'destructive_operations': migration.is_destructive,
            'data_modifications': migration.has_data_migration,
            'not_idempotent': not migration.is_idempotent,
            'no_rollback': migration.rollback_sql is None,
            'high_priority': migration.priority == 'critical'
        }
        
        risk_score = sum(risk_factors.values())
        
        if risk_score >= 4:
            risk_level = "HIGH"
        elif risk_score >= 2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        recommendations = []
        if not migration.is_idempotent:
            recommendations.append("Make migration idempotent")
        if migration.rollback_sql is None:
            recommendations.append("Provide rollback SQL")
        if migration.is_destructive:
            recommendations.append("Create backup before execution")
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': recommendations
        }