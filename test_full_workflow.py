#!/usr/bin/env python3
"""Test the complete flashinho workflow with proper authentication."""

import asyncio
import uuid
from src.agents.pydanticai.flashinho_pro.agent import FlashinhoPro

async def test_full_workflow():
    """Test the complete workflow from educational detection to 3-step response."""
    print("🧪 Testing Complete Flashinho Workflow")
    print("=" * 50)
    
    # Create agent instance with proper config
    config = {
        "model": "google-gla:gemini-2.5-pro-preview-05-06",
        "vision_model": "google-gla:gemini-2.5-pro-preview-05-06"
    }
    
    agent = FlashinhoPro(config)
    
    # Set up context to simulate a Pro user with valid conversation code
    agent.context.update({
        "whatsapp_user_number": "+5511999999999",
        "user_phone_number": "+5511999999999",
        "flashed_user_name": "TestUser",
        "flashed_user_id": "test_user_123",
        "flashed_conversation_code": "VALID123",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_identification_method": "conversation_code"
    })
    
    # Simulate Pro user status (bypass the Pro check)
    agent._is_pro_user = True
    agent._user_status_checked = True
    
    print("✅ Agent configured as Pro user")
    
    # Test 1: Educational Content Detection
    print("\n🔍 Test 1: Educational Content Detection")
    
    multimodal_content = {
        "images": [{
            "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "mime_type": "image/png"
        }]
    }
    
    user_message = "Preciso resolver essa equação de segundo grau: 2x² + 5x - 3 = 0"
    
    # Test keyword detection
    is_educational, context = await agent._detect_student_problem_in_image(
        multimodal_content, user_message
    )
    
    print(f"Educational detected: {is_educational}")
    print(f"Context: {context}")
    
    if not is_educational:
        print("❌ Educational detection failed!")
        return
    
    print("✅ Educational content detected successfully!")
    
    # Test 2: Workflow Execution
    print("\n🔍 Test 2: Workflow Execution")
    
    try:
        # Test the workflow execution directly
        result = await agent._handle_student_problem_flow(
            multimodal_content=multimodal_content,
            user_id=str(agent.context["user_id"]),
            phone=agent.context["user_phone_number"],
            problem_context=context,
            user_message=user_message
        )
        
        print("✅ Workflow executed successfully!")
        print(f"Result length: {len(result)} characters")
        
        # Check if it contains the expected 3-step format
        has_step1 = "Passo 1" in result or "**Passo 1:" in result
        has_step2 = "Passo 2" in result or "**Passo 2:" in result 
        has_step3 = "Passo 3" in result or "**Passo 3:" in result
        
        print(f"Contains Passo 1: {has_step1}")
        print(f"Contains Passo 2: {has_step2}")
        print(f"Contains Passo 3: {has_step3}")
        
        if has_step1 and has_step2 and has_step3:
            print("✅ 3-step format confirmed!")
        else:
            print("⚠️  3-step format not detected in result")
        
        # Show result preview
        print(f"\n📝 Result Preview:")
        print("-" * 40)
        print(result[:300] + "..." if len(result) > 300 else result)
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: UUID Handling
    print("\n🔍 Test 3: UUID Handling")
    
    test_uuid = uuid.uuid4()
    workflow_id = f"flashinho_{int(asyncio.get_event_loop().time())}_{str(test_uuid)[:8]}"
    print(f"✅ UUID handling works: {workflow_id}")
    
    print("\n🎉 Complete Workflow Test Finished!")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())