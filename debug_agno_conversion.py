#!/usr/bin/env python3
"""
Debug Agno Content Conversion
Trace exactly what happens when AutomagikAgent content gets converted to Agno format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json

async def test_conversion_process():
    """Test the exact conversion process step by step."""
    print("🔍 DEBUGGING AGNO CONTENT CONVERSION")
    print("="*60)
    
    try:
        from src.agents.pydanticai.simple.agent import SimpleAgent
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create agent
        config = {
            "name": "debug_conversion",
            "model": "openai:gpt-4o", 
            "framework_type": "agno"  # Force Agno
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        print(f"✅ Agent created with framework: {type(agent.ai_framework).__name__}")
        
        # Original multimodal content from context
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        print(f"\n📥 STEP 1: Original multimodal content from API")
        print(f"   Keys: {list(multimodal_content.keys())}")
        print(f"   Image count: {len(multimodal_content['images'])}")
        print(f"   Image data starts with: {multimodal_content['images'][0]['data'][:50]}...")
        
        # Step 2: Call _process_multimodal_input_for_agno
        print(f"\n🔄 STEP 2: Convert to Agno format using _process_multimodal_input_for_agno")
        agno_input = agent._process_multimodal_input_for_agno(
            "What color is this image?",
            multimodal_content
        )
        
        print(f"   Agno input type: {type(agno_input)}")
        print(f"   Agno input length: {len(agno_input)}")
        for i, item in enumerate(agno_input):
            if isinstance(item, str):
                print(f"   Item {i}: String - '{item}'")
            elif isinstance(item, dict):
                print(f"   Item {i}: Dict - {list(item.keys())}")
                if "data" in item:
                    print(f"     Data starts with: {item['data'][:50]}...")
        
        # Step 3: Call Agno framework directly with this input
        print(f"\n🚀 STEP 3: Call Agno framework run method")
        
        # Add debugging to see what Agno does with this input
        agno_framework = agent.ai_framework
        
        # Call the run method and capture what happens
        print(f"   Calling agno.run with input length: {len(agno_input)}")
        
        # Let's manually trace what happens in the Agno run method
        print(f"\n🔍 STEP 4: Manual trace of Agno processing")
        
        # Check if it's a list (multimodal)
        print(f"   Is list input: {isinstance(agno_input, list)}")
        
        if isinstance(agno_input, list):
            print(f"   Processing multimodal list input...")
            
            # Trace the Agno processing logic
            text_input = None
            images = []
            
            for i, item in enumerate(agno_input):
                print(f"   Processing item {i}: {type(item)}")
                
                if isinstance(item, str):
                    text_input = item
                    print(f"     Found text: '{item}'")
                elif isinstance(item, dict):
                    media_type = item.get("type", "")
                    print(f"     Found dict with type: '{media_type}'")
                    
                    if media_type == "image":
                        print(f"     Processing image...")
                        # Call the _create_agno_image method
                        try:
                            agno_image = agno_framework._create_agno_image(item)
                            if agno_image:
                                images.append(agno_image)
                                print(f"     ✅ Created Agno image object: {type(agno_image)}")
                            else:
                                print(f"     ❌ Failed to create Agno image object")
                        except Exception as e:
                            print(f"     ❌ Error creating Agno image: {e}")
            
            print(f"\n📊 PROCESSING RESULTS:")
            print(f"   Text input: '{text_input}'")
            print(f"   Images created: {len(images)}")
            print(f"   Image objects: {[type(img) for img in images]}")
            
            # Test if we can create the actual Agno Image object
            print(f"\n🧪 STEP 5: Test Agno Image creation directly")
            try:
                from agno.media import Image
                test_data = agno_input[1]["data"]  # Get the image data
                print(f"   Image data format: {test_data[:50]}...")
                
                if test_data.startswith("data:"):
                    # Extract base64 from data URL
                    _, data = test_data.split(",", 1)
                    print(f"   Extracted base64 length: {len(data)}")
                    
                    import base64
                    content = base64.b64decode(data)
                    print(f"   Decoded content length: {len(content)} bytes")
                    
                    agno_image = Image(content=content)
                    print(f"   ✅ Successfully created Agno Image: {type(agno_image)}")
                
            except Exception as e:
                print(f"   ❌ Error creating Agno Image directly: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run conversion debugging."""
    await test_conversion_process()

if __name__ == "__main__":
    asyncio.run(main())