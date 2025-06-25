#!/usr/bin/env python
"""Test session persistence for authenticated users."""

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

# Test message
TEST_MESSAGE = {
    "message_content": "[Cezar Vasconcelos]: Oi, ainda lembro de você?",
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


async def send_message(client: httpx.AsyncClient, message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message to the API and return the response."""
    print(f"\n{'='*60}")
    print(f"Sending message: {message_data['message_content']}")
    
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
        print(f"Session ID: {result.get('session_id')}")
        
        if result.get('message'):
            print(f"\nAgent Response: {result['message']}")
            
            # Check if agent is asking for conversation code
            if "código" in result['message'].lower() or "conversation code" in result['message'].lower():
                print("\n❌ ISSUE: Agent is asking for conversation code again!")
                print("   User should already be authenticated from previous session.")
            else:
                print("\n✅ SUCCESS: Agent recognized the authenticated user!")
                
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return {"error": str(e)}


async def check_session_data():
    """Check session data in database."""
    print("\n" + "="*60)
    print("SESSION DATA CHECK")
    print("="*60)
    
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Check session
        cur.execute("""
            SELECT s.id, s.name, s.user_id, u.phone_number, u.email,
                   u.user_data->>'flashed_conversation_code' as conv_code
            FROM sessions s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.name = '555197285829'
            ORDER BY s.created_at DESC
            LIMIT 1
        """)
        
        session = cur.fetchone()
        if session:
            print(f"✅ Session found:")
            print(f"  Session ID: {session[0]}")
            print(f"  Name: {session[1]}")
            print(f"  User ID: {session[2]}")
            print(f"  Phone: {session[3]}")
            print(f"  Email: {session[4]}")
            print(f"  Conversation Code: {session[5]}")
            
            if session[5] == "1bl1UKm0JC":
                print("\n✅ User has valid conversation code!")
            else:
                print("\n❌ User missing conversation code")
        else:
            print("\n❌ No session found")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Database check error: {str(e)}")


async def main():
    """Test session persistence."""
    print("🚀 SESSION PERSISTENCE TEST")
    print("="*60)
    print(f"Testing if authenticated user is recognized in existing session")
    
    # Check session state
    await check_session_data()
    
    # Send test message
    async with httpx.AsyncClient() as client:
        await send_message(client, TEST_MESSAGE)
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())