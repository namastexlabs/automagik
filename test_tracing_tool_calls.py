#!/usr/bin/env python3
"""Enhanced test script to verify LangWatch tracing of tool calls in SimpleAgent.

This script demonstrates:
1. Direct tool testing to verify functionality
2. Enhanced LangWatch span creation with proper structure
3. SimpleAgent integration with tool call tracing
4. Beautiful, properly categorized spans following LangWatch best practices

Features demonstrated:
- Tool call spans with proper categorization (Memory, DateTime, Communication)
- Memory operation spans with detailed context
- LLM call spans with full conversation history
- Proper parent-child span relationships
- Rich metadata with user/thread/customer IDs
- Error handling and duration tracking
- Sanitized input/output for security
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, '/home/cezar/automagik/am-agents-labs')

from automagik.agents.pydanticai.simple.agent import SimpleAgent
from automagik.tracing import get_tracing_manager
from automagik.tracing.observability.providers.langwatch import LangWatchProvider

# Set up logging with enhanced formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# Enable debug logging for tracing components
logging.getLogger('automagik.tracing').setLevel(logging.DEBUG)
logging.getLogger('automagik.tracing.observability.providers.langwatch').setLevel(logging.INFO)

async def test_enhanced_tool_tracing():
    """Test enhanced tool tracing with proper LangWatch spans."""
    
    # Enable tracing with enhanced logging
    os.environ["LANGWATCH_API_KEY"] = "test-key-for-enhanced-tracing"
    os.environ["AUTOMAGIK_ENABLE_TRACING"] = "true"
    os.environ["AUTOMAGIK_OBSERVABILITY_ENABLED"] = "true"
    
    logger.info("🚀 Starting enhanced tool call tracing test...")
    
    # Get tracing manager and test LangWatch provider directly
    tracing_manager = get_tracing_manager()
    langwatch_provider = None
    
    try:
        if tracing_manager and tracing_manager.observability:
            # Initialize LangWatch provider
            langwatch_provider = LangWatchProvider()
            langwatch_provider.initialize({})
            logger.info("✅ LangWatch provider initialized")
            
            # Start a trace for our test session
            with langwatch_provider.start_trace(
                name="SimpleAgent Tool Testing",
                kind="agent_session",
                attributes={
                    "agent.name": "SimpleAgent",
                    "agent.framework": "pydantic_ai",
                    "test.session": "tool_tracing_demo",
                    "user.id": "test-user-123",
                    "thread.id": "test-thread-456"
                }
            ) as trace_context:
                logger.info(f"📍 Started trace: {trace_context.trace_id}")
                
                # Simulate tool calls that would happen during agent execution
                await simulate_tool_calls(langwatch_provider)
                
                # Simulate LLM call
                await simulate_llm_call(langwatch_provider)
                
                # Log enhanced metadata
                langwatch_provider.log_metadata({
                    "agent_name": "SimpleAgent",
                    "agent_id": "simple-agent-001",
                    "framework": "pydantic_ai",
                    "session_id": "session-123",
                    "user_id": "test-user-123",
                    "thread_id": "test-thread-456",
                    "customer_id": "customer-789",
                    "multimodal": False,
                    "model": "gpt-4-turbo",
                    "temperature": 0.1,
                    "max_tokens": 1000
                })
                
                logger.info("✅ Enhanced trace completed")
        
        # Allow time for async processing
        await asyncio.sleep(2)
        
        # Flush any pending traces
        if langwatch_provider:
            langwatch_provider.flush()
            logger.info("🔄 Flushed all pending traces")
        
        logger.info("🎉 Enhanced tool tracing test completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced test: {e}")
        raise

async def simulate_tool_calls(langwatch_provider: LangWatchProvider):
    """Simulate various tool calls with timing and results."""
    
    logger.info("🔧 Simulating tool calls...")
    
    # Simulate getting current time
    start_time = time.time()
    await asyncio.sleep(0.05)  # Simulate tool execution time
    duration_ms = (time.time() - start_time) * 1000
    
    langwatch_provider.log_tool_call(
        tool_name="get_current_time",
        args={"format": None},
        result={"result": "14:30", "timestamp": time.time(), "metadata": {}},
        duration_ms=duration_ms
    )
    
    # Simulate getting current date
    start_time = time.time()
    await asyncio.sleep(0.03)
    duration_ms = (time.time() - start_time) * 1000
    
    langwatch_provider.log_tool_call(
        tool_name="get_current_date",
        args={"format": None},
        result={"result": "2024-07-07", "timestamp": time.time(), "metadata": {}},
        duration_ms=duration_ms
    )
    
    # Simulate memory storage operation
    start_time = time.time()
    await asyncio.sleep(0.08)
    duration_ms = (time.time() - start_time) * 1000
    
    langwatch_provider.log_memory_operation(
        operation="store",
        key="test_memory",
        content="This is a test memory for LangWatch tracing",
        result="Memory stored successfully with ID: mem_123",
        duration_ms=duration_ms
    )
    
    # Simulate memory retrieval operation
    start_time = time.time()
    await asyncio.sleep(0.04)
    duration_ms = (time.time() - start_time) * 1000
    
    langwatch_provider.log_memory_operation(
        operation="retrieve",
        key="test_memory",
        result="This is a test memory for LangWatch tracing",
        duration_ms=duration_ms
    )
    
    # Simulate a tool call with error
    start_time = time.time()
    await asyncio.sleep(0.02)
    duration_ms = (time.time() - start_time) * 1000
    
    langwatch_provider.log_tool_call(
        tool_name="send_text_message",
        args={"phone": "+1234567890", "message": "Test message"},
        result=None,
        duration_ms=duration_ms,
        error="Connection timeout: Unable to reach messaging service"
    )
    
    logger.info("✅ Tool calls simulation completed")

async def simulate_llm_call(langwatch_provider: LangWatchProvider):
    """Simulate an LLM call with proper message structure."""
    
    logger.info("🤖 Simulating LLM call...")
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools for time, date, and memory operations."
        },
        {
            "role": "user",
            "content": "What's the current time and date? Also store a memory about this conversation."
        }
    ]
    
    response = "Based on the tools I just used:\\n\\n- Current time: 14:30\\n- Current date: 2024-07-07\\n\\nI've also stored a memory about our conversation for future reference."
    
    usage = {
        "prompt_tokens": 156,
        "completion_tokens": 45,
        "total_tokens": 201
    }
    
    langwatch_provider.log_llm_call(
        model="gpt-4-turbo",
        messages=messages,
        response=response,
        usage=usage
    )
    
    logger.info("✅ LLM call simulation completed")

async def test_simple_agent_tool_calls():
    """Test SimpleAgent with tool calls to verify LangWatch tracing."""
    
    # Enable tracing
    os.environ["LANGWATCH_API_KEY"] = "test-key-for-tracing"
    os.environ["AUTOMAGIK_ENABLE_TRACING"] = "true"
    
    # Create agent configuration
    config = {
        "model_name": "openai:gpt-4-turbo",
        "model_provider": "openai",
        "temperature": "0.1",
        "max_tokens": "1000",
        "agent_id": "test-simple-agent",
        "user_id": "test-user"
    }
    
    logger.info("🚀 Starting SimpleAgent tool call tracing test...")
    
    try:
        # Create the agent
        agent = SimpleAgent(config)
        logger.info("✅ SimpleAgent created successfully")
        
        # Check what tools are available
        registered_tools = agent.tool_registry.get_registered_tools()
        logger.info(f"📋 Available tools: {list(registered_tools.keys())}")
        
        # Test messages that should trigger tool calls
        test_messages = [
            "What's the current time?",
            "What's today's date?",
            "Can you format the date '2024-01-15' as 'January 15, 2024'?",
            "Store a memory with key 'test' and content 'This is a test memory'",
            "List all available memories"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info(f"\\n🔍 Test {i}/5: {message}")
            
            try:
                # Initialize the framework if needed
                if not agent.is_framework_ready:
                    await agent.initialize_framework()
                
                # Run the agent with the message
                response = await agent.run(message)
                
                logger.info(f"✅ Response: {response}")
                
                # Small delay between tests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error in test {i}: {e}")
                # Continue with next test
                continue
        
        logger.info("🎉 All tool call tests completed!")
        
        # Get tracing manager to check metrics
        tracing_manager = get_tracing_manager()
        if tracing_manager and hasattr(tracing_manager, 'observability'):
            logger.info("📊 Tracing manager is active")
            
            # Flush any pending traces
            if tracing_manager.observability:
                tracing_manager.observability.flush()
                logger.info("🔄 Flushed pending traces")
        
    except Exception as e:
        logger.error(f"❌ Critical error in test: {e}")
        raise

async def test_datetime_tools_directly():
    """Test datetime tools directly to verify they work."""
    
    logger.info("\\n🔧 Testing datetime tools directly...")
    
    try:
        from automagik.tools.datetime.tool import get_current_time, get_current_date, format_date
        from pydantic_ai import RunContext
        
        # Create a mock context
        mock_context = RunContext(deps={})
        
        logger.info("📋 Testing all datetime tools with timing...")
        
        # Test current time
        logger.info("⏰ Testing get_current_time...")
        start_time = time.time()
        time_result = await get_current_time(mock_context)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ Current time: {time_result} (took {duration_ms:.2f}ms)")
        
        # Test current date
        logger.info("📅 Testing get_current_date...")
        start_time = time.time()
        date_result = await get_current_date(mock_context)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ Current date: {date_result} (took {duration_ms:.2f}ms)")
        
        # Test format date
        logger.info("🔄 Testing format_date...")
        start_time = time.time()
        format_result = await format_date(mock_context, "2024-01-15", "%Y-%m-%d", "%B %d, %Y")
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ Formatted date: {format_result} (took {duration_ms:.2f}ms)")
        
        logger.info("🎉 Direct tool tests completed!")
        
        # Test memory tools if available
        try:
            from automagik.tools.memory.tool import store_memory_tool, get_memory_tool
            
            # Test memory storage
            logger.info("💾 Testing memory storage...")
            context = {"agent_id": "test-agent", "user_id": "test-user"}
            start_time = time.time()
            store_result = await store_memory_tool(context, "test_key", "test_content")
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Memory stored: {store_result} (took {duration_ms:.2f}ms)")
            
            # Test memory retrieval
            logger.info("🔍 Testing memory retrieval...")
            start_time = time.time()
            get_result = await get_memory_tool(context, "test_key")
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Memory retrieved: {get_result} (took {duration_ms:.2f}ms)")
            
        except ImportError as e:
            logger.warning(f"⚠️ Memory tools not available: {e}")
        except Exception as me:
            logger.warning(f"⚠️ Memory tool error: {me}")
        
    except Exception as e:
        logger.error(f"❌ Error testing tools directly: {e}")
        raise

def main():
    """Main function to run the tests."""
    
    logger.info("🧪 Starting LangWatch tracing tests for tool calls...")
    
    # Test tools directly first
    asyncio.run(test_datetime_tools_directly())
    
    # Test enhanced tool tracing with proper spans
    asyncio.run(test_enhanced_tool_tracing())
    
    # Then test through SimpleAgent
    asyncio.run(test_simple_agent_tool_calls())
    
    logger.info("🏁 All tests completed!")
    logger.info("\\n📝 Check your LangWatch dashboard to see the beautiful, properly structured spans!")
    logger.info("🔍 You should see:")
    logger.info("   - Enhanced tool call spans with proper categorization")
    logger.info("   - Memory operation spans with detailed context")
    logger.info("   - LLM call spans with full conversation history")
    logger.info("   - Proper parent-child span relationships")
    logger.info("   - Rich metadata with user/thread/customer IDs")
    logger.info("   - Error handling and duration tracking")

if __name__ == "__main__":
    main()