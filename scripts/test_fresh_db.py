#!/usr/bin/env python3
"""
Test script to verify migrations work on a fresh database.
"""
import psycopg2
from src.config import settings
import urllib.parse

def main():
    # Get database connection parameters
    db_host = settings.POSTGRES_HOST
    db_port = str(settings.POSTGRES_PORT)
    db_name = "test_automagik_fresh"  # Test database name
    db_user = settings.POSTGRES_USER
    db_password = settings.POSTGRES_PASSWORD
    
    # Try to parse from DATABASE_URL if available
    database_url = settings.DATABASE_URL
    if database_url:
        try:
            parsed = urllib.parse.urlparse(database_url)
            db_host = parsed.hostname or db_host
            db_port = str(parsed.port) if parsed.port else db_port
            db_user = parsed.username or db_user
            db_password = parsed.password or db_password
        except Exception as e:
            print(f"Error parsing DATABASE_URL: {str(e)}")
    
    print(f"Testing fresh database installation: {db_host}:{db_port}/{db_name}")
    
    # Connect to postgres database to create/drop test database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname="postgres",
        user=db_user,
        password=db_password
    )
    conn.autocommit = True
    
    try:
        with conn.cursor() as cursor:
            # Drop test database if exists
            print("Dropping test database if exists...")
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            
            # Create fresh test database
            print("Creating fresh test database...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            
        conn.close()
        
        # Connect to the new test database
        test_conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Import and run the migration manager
        from src.db.migration_manager import MigrationManager
        from pathlib import Path
        
        # Create all tables first
        with test_conn.cursor() as cursor:
            # Create basic tables that migrations depend on
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    type VARCHAR(50),
                    model VARCHAR(255),
                    description TEXT,
                    version VARCHAR(50),
                    config JSONB,
                    active BOOLEAN DEFAULT TRUE,
                    run_id INTEGER DEFAULT 0,
                    system_prompt TEXT,
                    active_default_prompt_id INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT,
                    phone_number VARCHAR(50),
                    user_data JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    agent_id INTEGER REFERENCES agents(id),
                    name VARCHAR(255),
                    platform VARCHAR(50),
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    run_finished_at TIMESTAMPTZ
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID REFERENCES sessions(id),
                    user_id UUID REFERENCES users(id),
                    agent_id INTEGER REFERENCES agents(id),
                    role VARCHAR(20) NOT NULL,
                    text_content TEXT,
                    media_url TEXT,
                    mime_type TEXT,
                    message_type TEXT,
                    raw_payload JSONB,
                    tool_calls JSONB,
                    tool_outputs JSONB,
                    system_prompt TEXT,
                    user_feedback TEXT,
                    flagged TEXT,
                    context JSONB,
                    channel_payload JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    content TEXT,
                    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
                    read_mode VARCHAR(50),
                    access VARCHAR(20),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id SERIAL PRIMARY KEY,
                    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
                    prompt_text TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    is_default_from_code BOOLEAN NOT NULL DEFAULT FALSE,
                    status_key VARCHAR(255) NOT NULL DEFAULT 'default',
                    name VARCHAR(255),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(agent_id, status_key, version)
                )
            """)
            
        test_conn.commit()
        
        print("\nRunning migrations on fresh database...")
        migration_manager = MigrationManager(test_conn)
        
        migrations_dir = Path("src/db/migrations")
        success_count, error_count, error_messages = migration_manager.apply_all_migrations(migrations_dir)
        
        print(f"\n✅ Migrations completed: {success_count} successful, {error_count} errors")
        
        if error_count > 0:
            print("\n❌ Errors encountered:")
            for msg in error_messages:
                print(f"  - {msg}")
        
        # Verify all tables were created
        with test_conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"\n📋 Tables created: {', '.join(tables)}")
            
            # Check for expected tables
            expected_tables = [
                'agent_mcp_servers', 'agents', 'mcp_servers', 'memories', 
                'messages', 'migrations', 'preference_history', 'preferences',
                'prompts', 'sessions', 'users'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                print(f"\n⚠️ Missing expected tables: {', '.join(missing_tables)}")
            else:
                print("\n✅ All expected tables created successfully!")
        
        test_conn.close()
        
        # Clean up - drop test database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname="postgres",
            user=db_user,
            password=db_password
        )
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            print(f"\nCleaning up - dropping test database {db_name}...")
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        conn.close()
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname="postgres", 
                user=db_user,
                password=db_password
            )
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()