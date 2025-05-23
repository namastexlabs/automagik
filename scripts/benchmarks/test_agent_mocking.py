#!/usr/bin/env python3
"""
Simple test script for Pydantic AI agent mocking capabilities.
This demonstrates how to test agents without expensive LLM provider calls.
"""

import asyncio
import time
import random
from typing import List

# Test Pydantic AI availability and mocking
try:
    from pydantic_ai import Agent, models
    from pydantic_ai.models.test import TestModel
    from pydantic_ai.models.function import FunctionModel, AgentInfo
    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
    PYDANTIC_AI_AVAILABLE = True
    print("✓ Pydantic AI is available for mocking")
except ImportError as e:
    PYDANTIC_AI_AVAILABLE = False
    print(f"✗ Pydantic AI not available: {e}")


async def test_testmodel():
    """Test using TestModel for simple agent mocking."""
    print("\n🧪 Testing TestModel...")
    
    # Safety measure to prevent accidental real requests
    models.ALLOW_MODEL_REQUESTS = False
    
    # Create agent with TestModel
    agent = Agent(TestModel(), system_prompt="You are a helpful assistant.")
    
    test_messages = [
        "What is the weather like?",
        "Tell me a joke",
        "Explain quantum computing",
        "What's 2 + 2?",
        "Help me write an email"
    ]
    
    results = []
    start_time = time.perf_counter()
    
    for i, message in enumerate(test_messages):
        try:
            result = await agent.run(message)
            results.append({
                'input': message,
                'output': result.output,
                'success': True
            })
            print(f"  {i+1}. Input: {message[:30]}...")
            print(f"     Output: {str(result.output)[:50]}...")
        except Exception as e:
            results.append({
                'input': message,
                'error': str(e),
                'success': False
            })
            print(f"  {i+1}. Error with '{message}': {e}")
    
    duration = time.perf_counter() - start_time
    success_rate = sum(1 for r in results if r['success']) / len(results)
    
    print(f"\n📊 TestModel Results:")
    print(f"  • Messages processed: {len(results)}")
    print(f"  • Success rate: {success_rate:.0%}")
    print(f"  • Duration: {duration:.3f}s")
    print(f"  • Avg per message: {duration/len(results):.3f}s")
    
    return results


async def test_functionmodel():
    """Test using FunctionModel for custom response logic."""
    print("\n🔧 Testing FunctionModel...")
    
    def smart_mock_response(messages: List[ModelMessage], info: AgentInfo) -> ModelResponse:
        """Generate contextual responses based on input."""
        if not messages:
            return ModelResponse(parts=[TextPart("Hello! How can I help you?")])
        
        user_input = messages[-1].parts[-1].content.lower() if messages else ""
        
        # Simple keyword-based responses
        if "weather" in user_input:
            response = "The weather is sunny and 72°F today."
        elif "joke" in user_input:
            response = "Why don't scientists trust atoms? Because they make up everything!"
        elif "quantum" in user_input:
            response = "Quantum computing uses quantum mechanical phenomena like superposition and entanglement."
        elif "+" in user_input or "math" in user_input:
            response = "I can help with basic math! For complex calculations, please specify the exact problem."
        elif "email" in user_input:
            response = "I'd be happy to help you write an email. What's the purpose and who is the recipient?"
        else:
            responses = [
                f"I understand you're asking about: {user_input}",
                f"That's an interesting question regarding: {user_input}",
                f"Let me help you with: {user_input}",
                f"Here's what I think about: {user_input}"
            ]
            response = random.choice(responses)
        
        return ModelResponse(parts=[TextPart(response)])
    
    # Create agent with FunctionModel
    agent = Agent(FunctionModel(smart_mock_response), system_prompt="You are a smart assistant.")
    
    test_messages = [
        "What is the weather like?",
        "Tell me a joke",
        "Explain quantum computing",
        "What's 2 + 2?",
        "Help me write an email",
        "What is the capital of France?"
    ]
    
    results = []
    start_time = time.perf_counter()
    
    for i, message in enumerate(test_messages):
        try:
            result = await agent.run(message)
            results.append({
                'input': message,
                'output': result.output,
                'success': True
            })
            print(f"  {i+1}. Input: {message}")
            print(f"     Output: {result.output}")
        except Exception as e:
            results.append({
                'input': message,
                'error': str(e),
                'success': False
            })
            print(f"  {i+1}. Error with '{message}': {e}")
    
    duration = time.perf_counter() - start_time
    success_rate = sum(1 for r in results if r['success']) / len(results)
    
    print(f"\n📊 FunctionModel Results:")
    print(f"  • Messages processed: {len(results)}")
    print(f"  • Success rate: {success_rate:.0%}")
    print(f"  • Duration: {duration:.3f}s")
    print(f"  • Avg per message: {duration/len(results):.3f}s")
    
    return results


async def test_concurrent_mocking():
    """Test concurrent agent runs with mocking."""
    print("\n🚀 Testing Concurrent Mocking...")
    
    def quick_response(messages: List[ModelMessage], info: AgentInfo) -> ModelResponse:
        user_input = messages[-1].parts[-1].content if messages else "Hello"
        return ModelResponse(parts=[TextPart(f"Quick response to: {user_input[:20]}...")])
    
    agent = Agent(FunctionModel(quick_response), system_prompt="Fast assistant.")
    
    messages = [
        "Question 1", "Question 2", "Question 3", "Question 4", "Question 5",
        "Question 6", "Question 7", "Question 8", "Question 9", "Question 10"
    ]
    
    start_time = time.perf_counter()
    
    # Run all messages concurrently
    tasks = [agent.run(msg) for msg in messages]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.perf_counter() - start_time
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    error_count = len(results) - success_count
    
    print(f"📊 Concurrent Mocking Results:")
    print(f"  • Total requests: {len(messages)}")
    print(f"  • Successful: {success_count}")
    print(f"  • Errors: {error_count}")
    print(f"  • Duration: {duration:.3f}s")
    print(f"  • Throughput: {len(messages)/duration:.1f} req/sec")
    
    return results


async def main():
    """Main test function."""
    print("=" * 60)
    print("🎯 PYDANTIC AI AGENT MOCKING TEST")
    print("=" * 60)
    
    if not PYDANTIC_AI_AVAILABLE:
        print("❌ Cannot run tests - Pydantic AI not available")
        print("Install with: pip install pydantic-ai")
        return
    
    try:
        # Test TestModel
        await test_testmodel()
        
        # Test FunctionModel  
        await test_functionmodel()
        
        # Test concurrent execution
        await test_concurrent_mocking()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\n💡 Key Benefits of Mocking:")
        print("  • No expensive LLM API calls")
        print("  • Fast execution for testing")
        print("  • Predictable responses for CI/CD")
        print("  • No API rate limits")
        print("  • Works offline")
        
        print("\n🔧 Usage in Stress Testing:")
        print("  python scripts/benchmarks/api_stress_test.py \\")
        print("    --mode mock \\")
        print("    --mock-type test \\")
        print("    --concurrency 100 \\")
        print("    --requests 1000")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 