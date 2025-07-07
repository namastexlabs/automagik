#!/usr/bin/env python3
"""Simple test to demonstrate enhanced LangWatch integration.

This script shows the improved tracing capabilities without requiring the full agent stack.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockLangWatchProvider:
    """Mock LangWatch provider to demonstrate the enhanced API structure."""
    
    def __init__(self):
        self.current_trace_id = None
        self.current_span_id = None
        self.events = []
        
    def start_trace(self, name: str, kind: str, attributes: Dict[str, Any]):
        self.current_trace_id = str(uuid.uuid4())
        self.current_span_id = str(uuid.uuid4())
        
        logger.info(f"🎬 Started trace: {name} (ID: {self.current_trace_id})")
        logger.info(f"📋 Attributes: {attributes}")
        
        return self
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"🎬 Ended trace: {self.current_trace_id}")
        
    def log_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any, 
                     duration_ms: float = None, error: str = None):
        """Log enhanced tool call with proper categorization."""
        
        tool_category = self._categorize_tool(tool_name)
        tool_span_id = str(uuid.uuid4())
        
        event = {
            "type": "tool_call",
            "trace_id": self.current_trace_id,
            "span_id": tool_span_id,
            "parent_span_id": self.current_span_id,
            "name": f"{tool_category}: {tool_name}",
            "tool_name": tool_name,
            "args": self._sanitize_tool_args(args),
            "result": self._sanitize_tool_result(result),
            "duration_ms": duration_ms or 100,
            "status": "error" if error else "success",
            "error": error,
            "timestamp": time.time()
        }
        
        self.events.append(event)
        
        status_emoji = "❌" if error else "✅"
        logger.info(f"{status_emoji} Tool Call: {tool_category}: {tool_name}")
        logger.info(f"   📥 Input: {args}")
        logger.info(f"   📤 Output: {str(result)[:100]}{'...' if len(str(result)) > 100 else ''}")
        if duration_ms:
            logger.info(f"   ⏱️  Duration: {duration_ms:.2f}ms")
        if error:
            logger.info(f"   🚨 Error: {error}")
    
    def log_memory_operation(self, operation: str, key: str = None, content: str = None, 
                           result: Any = None, duration_ms: float = None, error: str = None):
        """Log memory operations as dedicated spans."""
        
        memory_span_id = str(uuid.uuid4())
        
        event = {
            "type": "memory_operation",
            "trace_id": self.current_trace_id,
            "span_id": memory_span_id,
            "parent_span_id": self.current_span_id,
            "name": f"Memory: {operation}",
            "operation": operation,
            "key": key,
            "content_length": len(str(content)) if content else 0,
            "result": str(result)[:500] if result else None,
            "duration_ms": duration_ms or 50,
            "status": "error" if error else "success",
            "error": error,
            "timestamp": time.time()
        }
        
        self.events.append(event)
        
        status_emoji = "❌" if error else "✅"
        logger.info(f"{status_emoji} Memory Operation: {operation}")
        logger.info(f"   🔑 Key: {key}")
        if content:
            logger.info(f"   📝 Content Length: {len(str(content))} chars")
        logger.info(f"   📤 Result: {str(result)[:100]}{'...' if len(str(result)) > 100 else ''}")
        if duration_ms:
            logger.info(f"   ⏱️  Duration: {duration_ms:.2f}ms")
    
    def log_llm_call(self, model: str, messages: list, response: str, usage: Dict[str, Any]):
        """Log LLM call with enhanced structure."""
        
        llm_span_id = str(uuid.uuid4())
        vendor = self._detect_llm_vendor(model)
        
        event = {
            "type": "llm_call",
            "trace_id": self.current_trace_id,
            "span_id": llm_span_id,
            "parent_span_id": self.current_span_id,
            "vendor": vendor,
            "model": model,
            "messages": messages,
            "response": response,
            "usage": usage,
            "timestamp": time.time()
        }
        
        self.events.append(event)
        
        logger.info(f"🤖 LLM Call: {vendor} - {model}")
        logger.info(f"   💬 Messages: {len(messages)}")
        logger.info(f"   📤 Response: {response[:100]}{'...' if len(response) > 100 else ''}")
        logger.info(f"   📊 Usage: {usage}")
    
    def log_metadata(self, metadata: Dict[str, Any]):
        """Log enhanced metadata."""
        
        metadata_event = {
            "type": "trace_metadata",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
        self.events.append(metadata_event)
        
        logger.info("📋 Enhanced Metadata Logged:")
        for key, value in metadata.items():
            logger.info(f"   {key}: {value}")
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool for better span naming."""
        tool_lower = tool_name.lower()
        if "memory" in tool_lower or "store" in tool_lower or "get_memory" in tool_lower:
            return "Memory"
        elif "time" in tool_lower or "date" in tool_lower:
            return "DateTime"
        elif "search" in tool_lower:
            return "Search"
        elif "message" in tool_lower or "send" in tool_lower:
            return "Communication"
        elif "multimodal" in tool_lower or "image" in tool_lower or "audio" in tool_lower:
            return "Multimodal"
        else:
            return "Tool"
    
    def _detect_llm_vendor(self, model: str) -> str:
        """Detect LLM vendor from model name."""
        model_lower = model.lower()
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower or "google" in model_lower:
            return "google"
        else:
            return "unknown"
    
    def _sanitize_tool_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool arguments."""
        sanitized = {}
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "... [truncated]"
            elif key.lower() in ['password', 'token', 'key', 'secret']:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_tool_result(self, result: Any) -> str:
        """Sanitize tool result."""
        result_str = str(result)
        if len(result_str) > 2000:
            return result_str[:2000] + "... [truncated]"
        return result_str
    
    def get_summary(self):
        """Get summary of captured events."""
        event_counts = {}
        for event in self.events:
            event_type = event["type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "total_events": len(self.events),
            "event_types": event_counts,
            "trace_id": self.current_trace_id
        }

async def demonstrate_enhanced_langwatch():
    """Demonstrate the enhanced LangWatch integration."""
    
    logger.info("🚀 Demonstrating Enhanced LangWatch Integration")
    logger.info("=" * 60)
    
    # Create mock provider
    provider = MockLangWatchProvider()
    
    # Start a trace with rich metadata
    with provider.start_trace(
        name="Agent Execution with Tool Calls",
        kind="agent_session",
        attributes={
            "agent.name": "SimpleAgent",
            "agent.framework": "pydantic_ai",
            "user.id": "user-123",
            "thread.id": "thread-456",
            "session.id": "session-789"
        }
    ):
        
        # Simulate datetime tool calls
        logger.info("\n🕰️ DateTime Tool Calls:")
        logger.info("-" * 30)
        
        start_time = time.time()
        await asyncio.sleep(0.05)  # Simulate work
        provider.log_tool_call(
            tool_name="get_current_time",
            args={"format": None},
            result={"result": "14:30:25", "timestamp": time.time(), "metadata": {}},
            duration_ms=(time.time() - start_time) * 1000
        )
        
        start_time = time.time()
        await asyncio.sleep(0.03)
        provider.log_tool_call(
            tool_name="get_current_date",
            args={"format": "iso"},
            result={"result": "2024-07-07", "timestamp": time.time(), "metadata": {}},
            duration_ms=(time.time() - start_time) * 1000
        )
        
        # Simulate memory operations
        logger.info("\n💾 Memory Operations:")
        logger.info("-" * 30)
        
        start_time = time.time()
        await asyncio.sleep(0.08)
        provider.log_memory_operation(
            operation="store",
            key="user_preferences",
            content="User prefers detailed explanations and examples",
            result="Memory stored successfully with ID: mem_456",
            duration_ms=(time.time() - start_time) * 1000
        )
        
        start_time = time.time()
        await asyncio.sleep(0.04)
        provider.log_memory_operation(
            operation="retrieve",
            key="user_preferences",
            result="User prefers detailed explanations and examples",
            duration_ms=(time.time() - start_time) * 1000
        )
        
        # Simulate communication tool (with error)
        logger.info("\n📱 Communication Tools:")
        logger.info("-" * 30)
        
        start_time = time.time()
        await asyncio.sleep(0.02)
        provider.log_tool_call(
            tool_name="send_text_message",
            args={"phone": "+1234567890", "message": "Your request has been processed"},
            result=None,
            duration_ms=(time.time() - start_time) * 1000,
            error="Network timeout: Unable to reach messaging service"
        )
        
        # Simulate LLM call
        logger.info("\n🤖 LLM Interaction:")
        logger.info("-" * 30)
        
        provider.log_llm_call(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with tool access."},
                {"role": "user", "content": "What time is it and save my preference for detailed responses?"}
            ],
            response="I've checked the current time (14:30:25) and saved your preference for detailed responses in memory.",
            usage={
                "prompt_tokens": 145,
                "completion_tokens": 32,
                "total_tokens": 177
            }
        )
        
        # Log enhanced metadata
        logger.info("\n📋 Enhanced Metadata:")
        logger.info("-" * 30)
        
        provider.log_metadata({
            "agent_name": "SimpleAgent",
            "agent_id": "simple-001",
            "framework": "pydantic_ai",
            "session_id": "session-789",
            "user_id": "user-123",
            "thread_id": "thread-456",
            "customer_id": "customer-abc",
            "multimodal": False,
            "model": "gpt-4-turbo",
            "temperature": 0.1,
            "max_tokens": 1000,
            "tools_used": ["get_current_time", "get_current_date", "store_memory", "retrieve_memory", "send_text_message"],
            "execution_duration_ms": 250,
            "success": True
        })
    
    # Show summary
    logger.info("\n📊 Trace Summary:")
    logger.info("-" * 30)
    summary = provider.get_summary()
    logger.info(f"Trace ID: {summary['trace_id']}")
    logger.info(f"Total Events: {summary['total_events']}")
    logger.info("Event Types:")
    for event_type, count in summary['event_types'].items():
        logger.info(f"  - {event_type}: {count}")

def main():
    """Main function."""
    logger.info("🧪 Enhanced LangWatch Integration Demo")
    logger.info("This demonstrates the improved tracing capabilities with:")
    logger.info("  ✅ Proper tool categorization (Memory, DateTime, Communication)")
    logger.info("  ✅ Memory operations as dedicated spans")
    logger.info("  ✅ Enhanced metadata with user/thread/customer IDs")
    logger.info("  ✅ Error handling and duration tracking")
    logger.info("  ✅ Input/output sanitization for security")
    logger.info("  ✅ Parent-child span relationships")
    logger.info("")
    
    asyncio.run(demonstrate_enhanced_langwatch())
    
    logger.info("\n🎉 Demo completed!")
    logger.info("\n📝 In a real LangWatch dashboard, you would see:")
    logger.info("  - Beautiful, categorized tool spans")
    logger.info("  - Proper hierarchical relationships")
    logger.info("  - Rich metadata for filtering and analysis")
    logger.info("  - Performance metrics and error tracking")
    logger.info("  - Conversation flows grouped by thread_id")

if __name__ == "__main__":
    main()