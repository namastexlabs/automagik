#!/usr/bin/env python3
"""
Debug Session Data

Check what's actually stored in the database for our test sessions to understand
why multimodal sessions show 0 tokens.
"""

import sys
import os
import sqlite3
import json

def find_database():
    """Find the SQLite database file."""
    possible_paths = [
        "data/automagik_agents.db",
        "automagik.db",
        "src/automagik.db", 
        "/tmp/automagik.db",
        "data/automagik.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def debug_session_data(session_ids):
    """Debug the actual data stored for our test sessions."""
    
    db_path = find_database()
    if not db_path:
        print("❌ Could not find SQLite database")
        return
    
    print(f"📁 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Available tables: {[t[0] for t in tables]}")
        
        # Check recent sessions
        cursor.execute("SELECT id, created_at, agent_id FROM sessions ORDER BY created_at DESC LIMIT 10")
        recent_sessions = cursor.fetchall()
        print(f"\n📅 Recent sessions:")
        for session in recent_sessions:
            print(f"  {session[0]} (agent: {session[2]}, created: {session[1]})")
        
        for session_id in session_ids:
            print(f"\n🔍 Debugging session: {session_id}")
            
            # Check if session exists
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            
            if session:
                print("  ✅ Session found in database")
                # Get column names
                cursor.execute("PRAGMA table_info(sessions)")
                session_columns = [col[1] for col in cursor.fetchall()]
                session_data = dict(zip(session_columns, session))
                print(f"  📝 Session data: {session_data}")
            else:
                print("  ❌ Session not found in database")
                continue
            
            # Check messages for this session
            cursor.execute("SELECT * FROM messages WHERE session_id = ?", (session_id,))
            messages = cursor.fetchall()
            
            print(f"  📨 Found {len(messages)} messages")
            
            if messages:
                # Get message column names
                cursor.execute("PRAGMA table_info(messages)")
                message_columns = [col[1] for col in cursor.fetchall()]
                
                for i, message in enumerate(messages, 1):
                    message_data = dict(zip(message_columns, message))
                    print(f"\n  Message {i}:")
                    print(f"    ID: {message_data.get('id')}")
                    print(f"    Role: {message_data.get('role')}")
                    print(f"    Content length: {len(message_data.get('content', ''))}")
                    
                    # Check usage data
                    usage = message_data.get('usage')
                    if usage:
                        print(f"    ✅ Has usage data")
                        try:
                            if isinstance(usage, str):
                                usage_parsed = json.loads(usage)
                                print(f"    📊 Usage: {json.dumps(usage_parsed, indent=6)}")
                            else:
                                print(f"    📊 Usage: {usage}")
                        except:
                            print(f"    ❌ Could not parse usage: {usage}")
                    else:
                        print(f"    ❌ No usage data")
                    
                    # Check other fields
                    for field in ['multimodal_content', 'media_contents', 'message_type']:
                        if field in message_data and message_data[field]:
                            print(f"    📎 {field}: {message_data[field]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Debug our test sessions."""
    
    # Session IDs from our tests + the one we found in the database
    session_ids = [
        "88bd1861-d4d3-45c8-8ee4-09d022e301e8",  # Text session
        "0e768185-3e4f-47bb-96ed-7dba722569dc",  # Multimodal session  
        "6a182890-0eb7-445d-a766-ec40a205a3a5"   # Found in database
    ]
    
    print("🔬 SESSION DATA DEBUGGING")
    print("=" * 50)
    
    debug_session_data(session_ids)
    
    print("\n🎯 SUMMARY:")
    print("- Check if usage data is being saved")
    print("- Check if multimodal content is being processed")
    print("- Check if usage tracking is working for different frameworks")

if __name__ == "__main__":
    main()