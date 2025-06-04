#!/usr/bin/env python3
"""
Script to fix the migration tracking for partially applied migrations.
"""
import psycopg2
from src.config import settings
import urllib.parse

def main():
    # Get database connection parameters
    db_host = settings.POSTGRES_HOST
    db_port = str(settings.POSTGRES_PORT)
    db_name = settings.POSTGRES_DB
    db_user = settings.POSTGRES_USER
    db_password = settings.POSTGRES_PASSWORD
    
    # Try to parse from DATABASE_URL if available
    database_url = settings.DATABASE_URL
    if database_url:
        try:
            parsed = urllib.parse.urlparse(database_url)
            db_host = parsed.hostname or db_host
            db_port = str(parsed.port) if parsed.port else db_port
            db_name = parsed.path.lstrip('/') or db_name
            db_user = parsed.username or db_user
            db_password = parsed.password or db_password
        except Exception as e:
            print(f"Error parsing DATABASE_URL: {str(e)}")
    
    print(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    
    # Connect to database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )
    
    try:
        with conn.cursor() as cursor:
            # Check if the migrations are already recorded
            cursor.execute("""
                SELECT name FROM migrations 
                WHERE name IN ('20250524_085600_create_mcp_tables.sql', '20250601_082232_create_preferences_tables.sql')
            """)
            existing = [row[0] for row in cursor.fetchall()]
            
            # Insert missing migrations
            migrations_to_add = []
            
            if '20250524_085600_create_mcp_tables.sql' not in existing:
                # Check if MCP tables exist
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN ('mcp_servers', 'agent_mcp_servers')
                """)
                if cursor.fetchone()[0] == 2:
                    migrations_to_add.append('20250524_085600_create_mcp_tables.sql')
                    print("✅ MCP tables exist, will record migration as applied")
            
            if '20250601_082232_create_preferences_tables.sql' not in existing:
                # Check if preferences tables exist
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN ('preferences', 'preference_history')
                """)
                if cursor.fetchone()[0] == 2:
                    migrations_to_add.append('20250601_082232_create_preferences_tables.sql')
                    print("✅ Preferences tables exist, will record migration as applied")
            
            # Record the migrations
            for migration in migrations_to_add:
                cursor.execute(
                    "INSERT INTO migrations (name, status) VALUES (%s, 'applied')",
                    (migration,)
                )
                print(f"✅ Recorded migration: {migration}")
            
            conn.commit()
            print(f"✅ Successfully recorded {len(migrations_to_add)} migrations")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()