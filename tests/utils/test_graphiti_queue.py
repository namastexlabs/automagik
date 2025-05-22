#!/usr/bin/env python3
"""Test script for Graphiti queue functionality"""

import asyncio
import time
import requests
import pytest
from src.utils.graphiti_queue import get_graphiti_queue
from src.config import settings

class TestGraphitiQueue:
    """Test class for Graphiti queue functionality"""
    
    @pytest.mark.asyncio
    async def test_queue_lifecycle(self):
        """Test queue startup, operation, and shutdown"""
        print("🧪 Testing Graphiti Queue Lifecycle")
        print("=" * 50)
        
        # 1. Test configuration
        print(f"🔧 Configuration:")
        print(f"   Enabled: {settings.GRAPHITI_QUEUE_ENABLED}")
        print(f"   Workers: {settings.GRAPHITI_QUEUE_MAX_WORKERS}")
        print(f"   Queue Size: {settings.GRAPHITI_QUEUE_MAX_SIZE}")
        print(f"   Background Mode: {settings.GRAPHITI_BACKGROUND_MODE}")
        print()
        
        # 2. Create queue instance
        queue = get_graphiti_queue()
        print("✅ Queue instance created")
        
        # 3. Test initial status
        status = queue.get_queue_status()
        print(f"📊 Initial Status: {status['status']}")
        print(f"📊 Workers: {status['workers']['active']}/{status['workers']['total']}")
        print(f"📊 Queue: {status['queue']['current_size']}/{status['queue']['max_size']}")
        
        assert status['status'] == 'stopped'
        assert status['workers']['active'] == 0
        
        # 4. Start queue
        print("\n🚀 Starting queue...")
        await queue.start()
        
        # 5. Check running status
        status = queue.get_queue_status()
        print(f"📊 Running Status: {status['status']}")
        print(f"📊 Active Workers: {status['workers']['active']}/{status['workers']['total']}")
        
        assert status['status'] == 'running'
        assert status['workers']['active'] == settings.GRAPHITI_QUEUE_MAX_WORKERS
        
        # 6. Test enqueue operation
        print("\n📝 Testing episode enqueue...")
        operation_id = await queue.enqueue_episode(
            user_id="test_user",
            message="Hello, this is a test message",
            response="This is a test response from the agent",
            metadata={
                "agent_name": "test_agent",
                "agent_id": "1",
                "test": True
            }
        )
        print(f"✅ Episode enqueued successfully: {operation_id[:8]}...")
        assert len(operation_id) == 36  # UUID length
        
        # 7. Wait a moment for processing
        print("\n⏳ Waiting for processing...")
        await asyncio.sleep(2)
        
        # 8. Check statistics
        status = queue.get_queue_status()
        stats = status['statistics']
        print(f"📊 Statistics:")
        print(f"   Total Processed: {stats['total_processed']}")
        print(f"   Success Rate: {stats['success_rate']}%")
        print(f"   Current Queue Size: {status['queue']['current_size']}")
        
        # Should have processed at least one item
        assert stats['total_processed'] >= 1
        
        # 9. Stop queue
        print("\n🛑 Stopping queue...")
        await queue.stop()
        
        status = queue.get_queue_status()
        print(f"📊 Final Status: {status['status']}")
        assert status['status'] == 'stopped'
        
        print("\n✅ Queue lifecycle test completed successfully!")

    def test_health_endpoint_standalone(self):
        """Test the health endpoint without running server"""
        print("\n🏥 Testing Health Endpoint Logic")
        print("=" * 35)
        
        # Test queue status logic directly
        queue = get_graphiti_queue()
        status = queue.get_queue_status()
        
        print(f"✅ Status structure valid")
        print(f"📊 Status: {status.get('status', 'unknown')}")
        print(f"📊 Enabled: {status.get('enabled', 'unknown')}")
        
        # Verify required fields exist
        assert 'status' in status
        assert 'enabled' in status
        assert 'workers' in status
        assert 'queue' in status
        assert 'statistics' in status
        
        print("✅ Health endpoint data structure validated")

# Standalone async function for manual testing
async def manual_test_queue():
    """Manual test function for running outside pytest"""
    print("🧪 Graphiti Queue Manual Test")
    print("=" * 40)
    
    queue = get_graphiti_queue()
    print("✅ Queue created")
    
    await queue.start()
    print("✅ Queue started")
    
    status = queue.get_queue_status()
    print(f"Status: {status['status']}")
    print(f"Workers: {status['workers']['active']}/{status['workers']['total']}")
    
    # Test enqueue
    operation_id = await queue.enqueue_episode(
        user_id="manual_test_user",
        message="Manual test message",
        response="Manual test response",
        metadata={"test": "manual"}
    )
    print(f"✅ Enqueued: {operation_id[:8]}...")
    
    await asyncio.sleep(1)
    
    await queue.stop()
    print("✅ Queue stopped")

if __name__ == "__main__":
    # Allow running this test file directly for quick testing
    asyncio.run(manual_test_queue()) 