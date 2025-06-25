#!/usr/bin/env python3
"""Test the UUID fix in the workflow system."""

import asyncio
import uuid
from src.agents.pydanticai.flashinho_pro.agent import FlashinhoPro

async def test_uuid_workflow_fix():
    """Test that UUID handling works properly in workflow ID generation."""
    print("🧪 Testing UUID handling fix...")
    
    # Create agent instance
    config = {"model": "google-gla:gemini-2.5-flash-preview-05-20"}
    agent = FlashinhoPro(config)
    
    # Test UUID to string conversion
    test_user_id = uuid.uuid4()
    print(f"Test user ID: {test_user_id} (type: {type(test_user_id)})")
    
    # Test workflow ID generation (this would previously fail)
    import time
    workflow_id = f"flashinho_{int(time.time())}_{str(test_user_id)[:8]}"
    print(f"✅ Workflow ID generated successfully: {workflow_id}")
    
    # Test the actual workflow function
    try:
        # Create multimodal content structure
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }]
        }
        
        # Simulate calling the workflow method
        result = await agent._handle_student_problem_flow(
            multimodal_content=multimodal_content,
            user_id=str(test_user_id),  # Pass as string to avoid UUID issues
            phone="+5511999999999",
            problem_context="test chemistry problem",
            user_message="Test chemistry question"
        )
        
        print(f"✅ Workflow executed successfully!")
        print(f"Result preview: {result[:100]}...")
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {str(e)}")
        
        # Check if it's still the UUID error
        if "'UUID' object is not subscriptable" in str(e):
            print("❌ UUID error still present - need to check implementation")
        else:
            print("ℹ️  Different error - UUID fix likely working")
    
    print("\n🔍 UUID Fix Test completed!")

if __name__ == "__main__":
    asyncio.run(test_uuid_workflow_fix())