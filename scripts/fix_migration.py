#!/usr/bin/env python
"""
Script to fix the migration issue by manually recording the migration as applied.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get database connection parameters from environment
    db_host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST", "localhost") 
    db_port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME", "automagik_agents")
    db_user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD", "postgres")
    
    # Try to parse from DATABASE_URL if available
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(database_url)
            db_host = parsed.hostname or db_host
            db_port = str(parsed.port) if parsed.port else db_port
            db_name = parsed.path.lstrip('/') or db_name
            db_user = parsed.username or db_user
            db_password = parsed.password or db_password
        except Exception as e:
            print(f"Error parsing DATABASE_URL: {str(e)}")
    
    print(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the migrations table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'migrations')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("Creating migrations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        
        # Check if the migration is already recorded
        cursor.execute("SELECT COUNT(*) FROM migrations WHERE name = %s", 
                      ("20250326_045944_add_channel_payload_to_messages.sql",))
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("Migration is already recorded in the migrations table.")
        else:
            # Record the migration as applied
            cursor.execute(
                "INSERT INTO migrations (name) VALUES (%s)",
                ("20250326_045944_add_channel_payload_to_messages.sql",)
            )
            print("✅ Successfully recorded the migration as applied.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Detailed error: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
