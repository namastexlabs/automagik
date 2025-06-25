#!/usr/bin/env python
"""Test script for validating Flashinho authentication flow."""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_URL = "http://localhost:18881/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "flashinho_pro"

# Test conversation code
CONVERSATION_CODE = "1bl1UKm0JC"

# Test messages
TEST_MESSAGES = [
    {
        "message_content": "[Cezar Vasconcelos]: Opa aí sim",
        "message_limit": 100,
        "user": {
            "phone_number": "+555197285829",
            "email": "",
            "user_data": {
                "name": "Cezar Vasconcelos",
                "whatsapp_id": "555197285829@s.whatsapp.net",
                "source": "whatsapp"
            }
        },
        "message_type": "text",
        "session_name": "555197285829",
        "preserve_system_prompt": False
    },
    {
        "message_content": f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
        "message_limit": 100,
        "user": {
            "phone_number": "+555197285829",
            "email": "",
            "user_data": {
                "name": "Cezar Vasconcelos",
                "whatsapp_id": "555197285829@s.whatsapp.net",
                "source": "whatsapp"
            }
        },
        "message_type": "text",
        "session_name": "555197285829",
        "preserve_system_prompt": False
    },
    {
        "message_content": "[Cezar Vasconcelos]: Agora sim, estou autenticado?",
        "message_limit": 100,
        "user": {
            "phone_number": "+555197285829",
            "email": "",
            "user_data": {
                "name": "Cezar Vasconcelos",
                "whatsapp_id": "555197285829@s.whatsapp.net",
                "source": "whatsapp"
            }
        },
        "message_type": "text",
        "session_name": "555197285829",
        "preserve_system_prompt": False
    }
]


async def send_message(client: httpx.AsyncClient, message_data: Dict[str, Any], message_num: int) -> Dict[str, Any]:
    """Send a message to the API and return the response."""
    print(f"\n{'='*60}")
    print(f"MESSAGE {message_num}: Sending message...")
    print(f"Content: {message_data['message_content']}")
    
    try:
        response = await client.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=message_data,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✅ Response received:")
        print(f"Status: {result.get('status')}")
        print(f"Session ID: {result.get('session_id')}")
        
        if result.get('message'):
            print(f"\nAgent Response: {result['message']}")
            
        # Check for user identification in the response
        if result.get('data'):
            data = result['data']
            if 'user_id' in data:
                print(f"\n🔍 User ID detected: {data['user_id']}")
            if 'flashed_user_id' in data:
                print(f"🔍 Flashed User ID: {data['flashed_user_id']}")
                
        return result
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error {e.response.status_code}: {e.response.text}")
        return {"error": str(e)}
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return {"error": str(e)}


async def check_database_state():
    """Check the current state of the database for our test user."""
    print("\n" + "="*60)
    print("DATABASE STATE CHECK")
    print("="*60)
    
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Check user with phone number
        cur.execute("""
            SELECT id, phone_number, email, user_data
            FROM users
            WHERE phone_number = '+555197285829'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        user = cur.fetchone()
        if user:
            print(f"\n✅ User found:")
            print(f"  ID: {user[0]}")
            print(f"  Phone: {user[1]}")
            print(f"  Email: {user[2]}")
            print(f"  User Data: {json.dumps(user[3], indent=2) if user[3] else 'None'}")
        else:
            print("\n❌ No user found with phone +555197285829")
            
        # Check sessions
        cur.execute("""
            SELECT s.id, s.name, s.user_id, s.created_at
            FROM sessions s
            WHERE s.name = '555197285829' OR s.name LIKE '%555197285829%'
            ORDER BY s.created_at DESC
            LIMIT 3
        """)
        
        sessions = cur.fetchall()
        if sessions:
            print(f"\n✅ Sessions found ({len(sessions)}):")
            for session in sessions:
                print(f"  Session ID: {session[0]}")
                print(f"  Name: {session[1]}")
                print(f"  User ID: {session[2]}")
                print(f"  Created: {session[3]}")
                print()
        else:
            print("\n❌ No sessions found for this phone number")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Database check error: {str(e)}")


async def main():
    """Run the authentication flow test."""
    print("🚀 FLASHINHO AUTHENTICATION FLOW TEST")
    print("="*60)
    print(f"API URL: {API_URL}")
    print(f"Agent: {AGENT_NAME}")
    print(f"Test Phone: +555197285829")
    print(f"Conversation Code: {CONVERSATION_CODE}")
    
    # Check initial database state
    await check_database_state()
    
    # Create HTTP client
    async with httpx.AsyncClient() as client:
        session_id = None
        
        # Send test messages
        for i, message_data in enumerate(TEST_MESSAGES, 1):
            # If we have a session_id from previous response, use it
            if session_id:
                message_data["session_id"] = session_id
                
            result = await send_message(client, message_data, i)
            
            # Extract session_id for next message
            if result.get('session_id'):
                session_id = result['session_id']
                
            # Wait a bit between messages
            await asyncio.sleep(1)
    
    # Check final database state
    print("\n" + "="*60)
    print("FINAL STATE CHECK")
    await check_database_state()
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())