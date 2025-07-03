# CLAUDE.md

This file provides database development context for Claude Code working in this directory.

## Database Development Context

This directory contains the database layer for Automagik Agents. When working here, you're developing database operations, migrations, repository patterns, and data models.

## 🗄️ Database Architecture Overview

### Multi-Provider System
- **SQLite** (default) - Zero-config development
- **PostgreSQL** - Production-ready with advanced features
- **Provider abstraction** - Unified interface across database types

### Core Components
- **Models** (`models.py`) - Pydantic models for type safety
- **Repository** (`repository/`) - Data access layer with CRUD operations
- **Providers** (`providers/`) - Database-specific implementations
- **Migrations** (`migrations/`) - Schema evolution and data migrations
- **Connection** (`connection.py`) - Thread-safe connection pooling

## 🏗️ Database Development Patterns

### Repository Pattern Usage
```python
# ✅ CORRECT - Always import from centralized locations
from src.db import (
    create_user, get_user, list_users, update_user, delete_user,
    create_agent, get_agent, get_agent_by_name, list_agents,
    create_session, get_session, list_sessions,
    create_message, get_message, list_messages
)

# ❌ WRONG - Never import individual repository modules
from src.db.repository.user import create_user  # DON'T DO THIS
```

### Standard CRUD Naming Convention
```python
# Consistent patterns across all entities:
get_[entity](id)                    # Get by primary key
get_[entity]_by_[field](value)      # Get by specific field
list_[entity]s(filters, pagination) # List with filtering/pagination
create_[entity](model)              # Create or update (upsert behavior)
update_[entity](id, model)          # Update existing record
delete_[entity](id)                 # Delete by primary key
```

### Connection Management Patterns
```python
# Method 1: Context managers (recommended)
from src.db.connection import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

# Method 2: Helper functions for simple queries
from src.db.connection import execute_query
result = execute_query("SELECT * FROM agents WHERE name = %s", (agent_name,))

# Method 3: Batch operations
from src.db.connection import execute_batch
execute_batch(
    "INSERT INTO messages (id, text) VALUES %s",
    [(id1, text1), (id2, text2)]
)
```

## 📊 Data Model Patterns

### Core Entity Relationships
```python
# User (UUID primary key) -> Sessions -> Messages
# Agent (serial ID) -> Sessions -> Messages
# Agent -> Memory (global or user-specific)
# User -> Preferences (by category)
# Agent -> MCP Servers (many-to-many)
```

### JSONB Usage Patterns
```python
# Structured data with nested objects
preference = Preference(
    user_id=user_id,
    category="ui_settings",
    preferences={
        "theme": "dark",
        "language": "en",
        "notifications": {
            "email": True,
            "push": False
        }
    }
)

# Querying JSONB fields
dark_theme_users = execute_query(
    "SELECT * FROM preferences WHERE preferences->>'theme' = %s",
    ("dark",)
)

# Nested path queries
email_enabled = execute_query(
    "SELECT * FROM preferences WHERE preferences->'notifications'->>'email' = %s",
    ("true",)
)
```

### UUID Safety Pattern
```python
from src.db.repository import safe_uuid

# Always use safe_uuid for UUID parameters
user_uuid = safe_uuid(user_id_string)  # Handles both str and UUID inputs
```

## 🚀 Migration Development Patterns

### Migration File Structure
```bash
# Location: src/db/migrations/
# Naming: YYYYMMDD_HHMMSS_description.sql
# Example: 20250326_045944_add_channel_payload_to_messages.sql
```

### Idempotent Migration Patterns
```sql
-- Always use IF NOT EXISTS for safety
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS channel_payload JSONB DEFAULT '{}';

-- Safe index creation
CREATE INDEX IF NOT EXISTS idx_messages_channel_payload 
ON messages USING gin(channel_payload);

-- Safe constraint addition
ALTER TABLE messages 
ADD CONSTRAINT IF NOT EXISTS chk_channel_payload_valid 
CHECK (jsonb_typeof(channel_payload) = 'object');
```

### Migration Development Workflow
1. Create timestamped SQL file in `migrations/`
2. Update Pydantic models in `models.py`
3. Modify repository functions if needed
4. Update central imports in `__init__.py`
5. Test with `automagik agents db init --force`
6. Verify idempotency by running twice

## 🔧 Provider Development Patterns

### Adding New Database Provider
```python
# 1. Create provider class in providers/
class NewDatabaseProvider(DatabaseProvider):
    def connect(self):
        # Provider-specific connection logic
        pass
    
    def execute_query(self, query: str, params=None, fetch=False):
        # Provider-specific query execution
        pass

# 2. Register in providers/factory.py
def get_database_provider() -> DatabaseProvider:
    db_type = get_settings().database_type
    if db_type == "new_database":
        return NewDatabaseProvider()
    # ... existing providers
```

### Database Configuration Patterns
```python
# Environment variables for database selection
DATABASE_TYPE=sqlite|postgresql
DATABASE_URL=full_connection_string

# Or individual components
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=username
POSTGRES_PASSWORD=password
POSTGRES_DB=database_name

# Connection pool tuning
POSTGRES_POOL_MIN=10
POSTGRES_POOL_MAX=25
```

## 📝 Repository Development Patterns

### Creating New Repository Module
```python
# repository/new_entity.py
from typing import List, Optional, Tuple
from ..models import NewEntity
from ..connection import execute_query, get_db_connection
from . import safe_uuid

def create_new_entity(entity: NewEntity) -> str:
    """Create or update entity (upsert behavior)."""
    # Implementation with proper error handling
    pass

def get_new_entity(entity_id: str) -> Optional[NewEntity]:
    """Get entity by ID."""
    # Implementation
    pass

def list_new_entities(
    filters: Optional[Dict] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[NewEntity], int]:
    """List entities with pagination."""
    # Implementation with total count
    pass
```

### Updating Central Imports
```python
# Add to src/db/__init__.py
from .repository.new_entity import (
    create_new_entity,
    get_new_entity,
    list_new_entities
)

# Add to __all__ list
__all__ = [
    # ... existing exports
    "create_new_entity",
    "get_new_entity", 
    "list_new_entities"
]
```

## 🧪 Database Testing Patterns

### Repository Testing
```python
# Test with actual database (not mocked)
@pytest.fixture
def test_db():
    # Setup test database
    yield
    # Cleanup

def test_create_user(test_db):
    user = User(email="test@example.com", name="Test User")
    user_id = create_user(user)
    assert user_id is not None
    
    retrieved = get_user(user_id)
    assert retrieved.email == "test@example.com"
```

### Migration Testing
```python
def test_migration_idempotency():
    # Apply migration
    apply_migration("20250326_045944_add_column.sql")
    
    # Apply again - should not fail
    apply_migration("20250326_045944_add_column.sql")
    
    # Verify final state
    assert column_exists("table_name", "new_column")
```

## 🔍 Debugging Database Operations

```bash
# Enable SQL query logging
export AUTOMAGIK_LOG_SQL=true

# Check migration status
uv run python -c "
from src.db.connection import execute_query
result = execute_query('SELECT * FROM migrations ORDER BY applied_at DESC LIMIT 5')
for migration in result:
    print(f'{migration[1]}: {migration[2]} - {migration[4]}')
"

# Verify database health
uv run python -c "
from src.db.connection import verify_database_health
verify_database_health()
"

# Check connection pool status
uv run python -c "
from src.db.connection import get_connection_pool
pool = get_connection_pool()
print(f'Pool status: {pool.getconn().dsn}')
"
```

## ⚠️ Database Development Guidelines

### Performance Considerations
- Use pagination for large result sets
- Index frequently queried JSONB paths with GIN indexes
- Monitor slow queries with `AUTOMAGIK_LOG_SQL=true`
- Use connection pooling appropriately
- Implement proper connection cleanup

### Security Patterns
- Always use parameterized queries
- Validate input data with Pydantic models
- Use safe_uuid() for UUID handling
- Never concatenate user input into SQL strings

### Error Handling
```python
from src.db.exceptions import DatabaseError

try:
    user_id = create_user(user)
except DatabaseError as e:
    logger.error(f"Database operation failed: {e}")
    # Handle appropriately
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle appropriately
```

### Data Consistency
- Use transactions for multi-step operations
- Implement proper foreign key constraints
- Use CHECK constraints for data validation
- Handle concurrent access appropriately

This context focuses specifically on database development patterns and should be used alongside the global development rules in the root CLAUDE.md.