# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Database Architecture & Usage

This codebase uses PostgreSQL with a sophisticated repository pattern, automated migrations, and type-safe Pydantic models.

## 🏗️ Database Architecture

### Core Models
- **User** (`users` table) - User accounts with UUID primary keys
- **Agent** (`agents` table) - AI agent configurations with serial IDs
- **Session** (`sessions` table) - Conversation sessions between users and agents
- **Message** (`messages` table) - Individual messages with channel payload support
- **Memory** (`memories` table) - Agent persistent memory storage
- **Prompt** (`prompts` table) - Versioned prompts for agents
- **Preference** (`preferences` table) - User preferences by category
- **MCPServerDB** (`mcp_servers` table) - MCP server configurations
- **AgentMCPServerDB** (`agent_mcp_servers` table) - Agent-to-MCP server links

### Key Features
- **UUID primary keys** for most entities (agents use serial IDs)
- **JSONB columns** for flexible data storage (config, metadata, preferences)
- **Automatic timestamps** (created_at, updated_at) via BaseDBModel
- **Foreign key constraints** with proper cascading
- **Type safety** through Pydantic models

## 🔄 Repository Pattern

### Import Structure
**ALWAYS** import from centralized locations:

```python
# ✅ CORRECT - Import from central db module
from src.db import (
    create_user, get_user, list_users, update_user, delete_user,
    create_agent, get_agent, get_agent_by_name, list_agents,
    create_session, get_session, list_sessions,
    create_message, get_message, list_messages,
    create_memory, get_memory, list_memories,
    create_prompt, get_prompt, list_prompts,
    create_preference, get_preference, list_preferences,
    create_mcp_server, get_mcp_server, list_mcp_servers
)

# ❌ WRONG - Never import individual repository modules
from src.db.repository.user import create_user  # DON'T DO THIS
```

### Standard CRUD Operations
Each entity follows consistent naming:
- `get_[entity](id)` - Get by primary key
- `get_[entity]_by_[field]()` - Get by specific field
- `list_[entity]s()` - List with pagination and filtering
- `create_[entity](model)` - Create or update if exists (upsert behavior)
- `update_[entity](id, model)` - Update existing record
- `delete_[entity](id)` - Delete by primary key

## 🔧 Connection Management

### Database Connections
Use thread-safe connection pooling with context managers:

```python
from src.db.connection import get_db_connection, get_db_cursor, execute_query

# Method 1: Context managers (recommended)
with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

# Method 2: Helper functions for simple queries
result = execute_query("SELECT * FROM agents WHERE name = %s", (agent_name,))

# Method 3: Batch operations
from src.db.connection import execute_batch
execute_batch(
    "INSERT INTO messages (id, text) VALUES %s",
    [(id1, text1), (id2, text2)]
)
```

### Connection Pool Configuration
```bash
# Environment variables for connection pooling
POSTGRES_POOL_MIN=10        # Minimum connections (default: 10)
POSTGRES_POOL_MAX=25        # Maximum connections (default: 25)
```

## 📁 Migration System

### Migration Structure
- **Location**: `src/db/migrations/`
- **Naming Convention**: `YYYYMMDD_HHMMSS_description.sql`
- **Automatic Application**: Runs during `automagik agents db init`
- **Tracking**: Applied migrations stored in `migrations` table with checksums

### Migration Features
- **Idempotency**: All migrations use `IF NOT EXISTS` patterns
- **Checksum Verification**: SHA256 hashes ensure integrity
- **Partial Application Detection**: Handles interrupted migrations
- **Rollback Support**: Uses savepoints for safe execution

### Writing Migrations
```sql
-- Example: 20250326_045944_add_channel_payload_to_messages.sql

-- Always use IF NOT EXISTS for idempotency
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS channel_payload JSONB DEFAULT '{}';

-- Create indexes safely
CREATE INDEX IF NOT EXISTS idx_messages_channel_payload 
ON messages USING gin(channel_payload);

-- Add constraints safely
ALTER TABLE messages 
ADD CONSTRAINT IF NOT EXISTS chk_channel_payload_valid 
CHECK (jsonb_typeof(channel_payload) = 'object');
```

## 🛠️ Common Database Operations

### Creating Records (Upsert Behavior)
```python
from src.db import create_user, create_agent
from src.db.models import User, Agent

# Users are upserted by email
user = User(
    email="test@example.com",
    name="Test User", 
    metadata={"role": "admin", "preferences": {"theme": "dark"}}
)
user_id = create_user(user)

# Agents are upserted by name
agent = Agent(
    name="helpful_assistant",
    type="simple",
    config={"model": "gpt-4", "temperature": 0.7},
    metadata={"version": "1.0", "capabilities": ["chat", "search"]}
)
agent_id = create_agent(agent)
```

### Querying with Pagination
```python
from src.db import list_sessions, list_messages

# Paginated session listing
sessions, total_count = list_sessions(
    user_id=user_id,
    agent_id=agent_id,  # Optional filter
    page=1,
    page_size=20
)

# Message listing with offset/limit
messages, total = list_messages(
    session_id=session_id,
    limit=50,
    offset=100  # For pagination
)
```

### Working with JSONB Data
```python
from src.db import create_preference, get_preference
from src.db.connection import execute_query

# Store nested JSON preferences
preference = Preference(
    user_id=user_id,
    category="ui_settings",
    preferences={
        "theme": "dark",
        "language": "en",
        "notifications": {
            "email": True,
            "push": False,
            "frequency": "daily"
        },
        "layout": {
            "sidebar": "collapsed",
            "density": "compact"
        }
    }
)
create_preference(preference)

# Query JSONB fields with operators
dark_theme_users = execute_query(
    "SELECT * FROM preferences WHERE preferences->>'theme' = %s",
    ("dark",)
)

# Query nested JSONB paths
email_enabled = execute_query(
    "SELECT * FROM preferences WHERE preferences->'notifications'->>'email' = %s",
    ("true",)
)
```

### Agent Memory Operations
```python
from src.db import create_memory, list_memories
from src.db.models import Memory

# Store global agent memory (user_id = None)
global_memory = Memory(
    agent_id=agent_id,
    user_id=None,  # Global memory
    name="system_context",
    content="I am a helpful assistant specializing in code analysis",
    metadata={"type": "system", "priority": "high"}
)
create_memory(global_memory)

# Store user-specific memory
user_memory = Memory(
    agent_id=agent_id,
    user_id=user_id,
    name="user_preferences",
    content="User prefers concise responses with code examples",
    metadata={"type": "preference", "confidence": 0.9, "last_updated": "2024-01-15"}
)
create_memory(user_memory)

# Retrieve memories with pattern matching
memories, count = list_memories(
    agent_id=agent_id,
    user_id=user_id,
    name_pattern="user_%"  # SQL LIKE pattern with %
)
```

## 🚀 Database Management Commands

### Initialization and Migrations
```bash
# Initialize database and apply all migrations
automagik agents db init

# Force reinitialize (WARNING: drops all tables)
automagik agents db init --force

# Clear all data but keep schema
automagik agents db clear --yes
```

### Development and Debugging
```bash
# Enable SQL query logging for debugging
export AM_LOG_SQL=true

# Check database health and migration status
uv run python -c "
from src.db.connection import verify_database_health
verify_database_health()
"

# Inspect recent migrations
uv run python -c "
from src.db.connection import execute_query
result = execute_query('SELECT * FROM migrations ORDER BY applied_at DESC LIMIT 5')
for migration in result:
    print(f'{migration[1]}: {migration[2]} - {migration[4]}')
"
```

## ⚙️ Database Configuration

### Environment Variables
```bash
# Option 1: Single connection string (preferred)
DATABASE_URL=postgresql://user:pass@localhost:5432/automagik

# Option 2: Individual components
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=automagik  
POSTGRES_PASSWORD=password
POSTGRES_DB=automagik

# Connection pool tuning
POSTGRES_POOL_MIN=10    # Minimum pool connections
POSTGRES_POOL_MAX=25    # Maximum pool connections

# Debugging
AM_LOG_SQL=true         # Log all SQL queries
```

## 📋 Best Practices

### 1. Repository Usage
- **Always use centralized imports** from `src.db`
- **Never import individual repository modules** directly
- **Leverage upsert behavior** - create_* functions handle existing records
- **Use appropriate get_* variants** for different lookup patterns

### 2. Connection Handling
- **Always use context managers** for connections and cursors
- **Use execute_query() helper** for simple operations
- **Use execute_batch()** for multiple similar operations
- **Monitor connection pool** usage in production

### 3. UUID Safety
```python
from src.db.repository import safe_uuid

# Always use safe_uuid for UUID parameters
user_uuid = safe_uuid(user_id_string)  # Handles both str and UUID inputs
```

### 4. JSONB Best Practices
- **Structure data consistently** across similar records
- **Use nested objects** for related settings
- **Index frequently queried paths** with GIN indexes
- **Validate JSON structure** in application code

### 5. Migration Guidelines
- **Use IF NOT EXISTS** for all DDL operations
- **Test locally first** before applying to production
- **Keep migrations focused** - one logical change per file
- **Document complex migrations** with comments

### 6. Error Handling
```python
try:
    user_id = create_user(user)
except Exception as e:
    logger.error(f"Failed to create user: {e}")
    # Handle appropriately
```

### 7. Performance Optimization
- **Use pagination** for large result sets
- **Index JSONB queries** that are used frequently
- **Monitor slow queries** with `AM_LOG_SQL=true`
- **Use connection pooling** appropriately

## 🔧 Schema Evolution Workflow

When modifying the database schema:

1. **Create migration file** in `src/db/migrations/` with proper timestamp
2. **Update Pydantic models** in `src/db/models.py`
3. **Modify repository functions** in `src/db/repository/[entity].py`
4. **Update central imports** in `src/db/__init__.py` and `src/db/repository.py`
5. **Test migration locally** with `automagik agents db init --force`
6. **Verify idempotency** by running migration twice
7. **Update tests** to reflect schema changes

## 🐛 Common Issues & Solutions

### Connection Pool Exhaustion
```bash
# Increase pool size if needed
export POSTGRES_POOL_MAX=50

# Monitor active connections
uv run python -c "
from src.db.connection import get_connection_pool
pool = get_connection_pool()
print(f'Active: {pool.getconn().dsn}')
"
```

### Migration Failures
```bash
# Check migration status
uv run python -c "
from src.db.connection import execute_query
result = execute_query('SELECT * FROM migrations WHERE status != %s', ('applied',))
print('Failed migrations:', result)
"

# Fix and reapply
automagik agents db init --force
```

### JSONB Query Performance
```sql
-- Add GIN indexes for frequently queried JSONB paths
CREATE INDEX idx_preferences_theme ON preferences USING gin((preferences->>'theme'));
CREATE INDEX idx_agent_config ON agents USING gin(config);
```

This database system provides a robust foundation for the automagik-agents framework with type safety, migration management, and flexible data storage through JSONB columns.