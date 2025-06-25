#!/usr/bin/env python
"""Complete test of authentication flow and session persistence."""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# API configuration
API_URL = "http://localhost:18881/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "flashinho_pro"

# Test conversation code
CONVERSATION_CODE = "1bl1UKm0JC"

# Test messages for complete flow
TEST_MESSAGES = [
    {
        "content": "[Cezar Vasconcelos]: Oi, tudo bem?",
        "expect": "conversation_code",
        "description": "First message - should ask for conversation code"
    },
    {
        "content": f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
        "expect": "authenticated",
        "description": "Send conversation code - should authenticate"
    },
    {
        "content": "[Cezar Vasconcelos]: Me ajuda com matemática?",
        "expect": "recognized",
        "description": "Third message - should recognize authenticated user"
    }
]


async def send_message(client: httpx.AsyncClient, message: str, session_name: str, session_id: str = None) -> Dict[str, Any]:
    """Send a message to the API."""
    
    payload = {
        "message_content": message,
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
        "session_name": session_name,
        "preserve_system_prompt": False
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    try:
        response = await client.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}


async def check_database_state(session_name: str):
    """Check current database state."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Check sessions
        cur.execute("""
            SELECT s.id, s.name, s.user_id, u.phone_number,
                   u.user_data->>'flashed_conversation_code' as conv_code
            FROM sessions s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.name = %s
            ORDER BY s.created_at DESC
            LIMIT 1
        """, (session_name,))
        
        session = cur.fetchone()
        if session:
            print(f"\n📊 Session State:")
            print(f"  Session ID: {session[0]}")
            print(f"  User ID: {session[2]}")
            print(f"  Phone: {session[3]}")
            print(f"  Has Conv Code: {'✅' if session[4] else '❌'}")
            return session[0], session[2], bool(session[4])
        
        cur.close()
        conn.close()
        return None, None, False
        
    except Exception as e:
        print(f"❌ DB check error: {e}")
        return None, None, False


async def run_complete_test():
    """Run complete authentication flow test."""
    print("🚀 COMPLETE AUTHENTICATION FLOW TEST")
    print("="*60)
    
    # Use a unique session name for this test
    session_name = f"test-{int(time.time())}"
    print(f"Using test session: {session_name}")
    
    async with httpx.AsyncClient() as client:
        session_id = None
        
        for i, test in enumerate(TEST_MESSAGES, 1):
            print(f"\n{'='*60}")
            print(f"TEST {i}: {test['description']}")
            print(f"Message: {test['content']}")
            
            # Send message
            result = await send_message(client, test['content'], session_name, session_id)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
                
            # Extract session ID for subsequent messages
            if result.get('session_id'):
                session_id = result['session_id']
            
            # Check response
            response_msg = result.get('message', '')
            print(f"\nResponse: {response_msg[:200]}...")
            
            # Validate expectation
            if test['expect'] == 'conversation_code':
                if 'código' in response_msg.lower() or 'conversation code' in response_msg.lower():
                    print("✅ SUCCESS: Agent asking for conversation code as expected")
                else:
                    print("❌ FAIL: Agent should ask for conversation code")
                    
            elif test['expect'] == 'authenticated':
                if 'cezar' in response_msg.lower() and ('autenticad' in response_msg.lower() or 'pronto' in response_msg.lower()):
                    print("✅ SUCCESS: User authenticated successfully")
                else:
                    print("❌ FAIL: Authentication confirmation expected")
                    
            elif test['expect'] == 'recognized':
                if 'código' not in response_msg.lower() and 'conversation code' not in response_msg.lower():
                    print("✅ SUCCESS: Agent recognized authenticated user")
                else:
                    print("❌ FAIL: Agent asking for code again - persistence issue!")
            
            # Check database state
            await check_database_state(session_name)
            
            # Small delay between messages
            await asyncio.sleep(1)
    
    print(f"\n{'='*60}")
    print("✅ Test completed!")


async def test_existing_session_persistence():
    """Test persistence with the existing session."""
    print("\n🔄 TESTING EXISTING SESSION PERSISTENCE")
    print("="*60)
    
    session_name = "555197285829"
    
    # Check initial state
    session_id, user_id, has_code = await check_database_state(session_name)
    
    if not session_id:
        print("❌ No existing session found")
        return
        
    print(f"\nTesting with existing session: {session_id}")
    print(f"User already authenticated: {'✅' if has_code else '❌'}")
    
    async with httpx.AsyncClient() as client:
        # Send a test message
        result = await send_message(
            client, 
            "[Cezar Vasconcelos]: Oi, você lembra de mim?",
            session_name
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
            
        response_msg = result.get('message', '')
        print(f"\nResponse: {response_msg[:200]}...")
        
        # Check if agent recognizes user
        if 'código' not in response_msg.lower() and 'conversation code' not in response_msg.lower():
            print("✅ SUCCESS: Agent recognized authenticated user in existing session!")
        else:
            print("❌ FAIL: Agent asking for code again - session persistence broken!")


async def main():
    """Run all tests."""
    # Test 1: Complete flow with new session
    await run_complete_test()
    
    # Test 2: Existing session persistence
    await test_existing_session_persistence()


if __name__ == "__main__":
    asyncio.run(main())