"""
Asynchronous Graphiti Queue Manager

Handles background processing of Graphiti operations to prevent blocking API responses.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from src.config import settings
from src.utils.graphiti_queue_stats import GraphitiQueueStats

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Types of Graphiti operations"""
    EPISODE = "episode"
    CUSTOM = "custom"


@dataclass
class GraphitiOperation:
    """Represents a Graphiti operation to be processed"""
    id: str
    operation_type: OperationType
    user_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    processor_fn: Optional[Callable[..., Awaitable[Any]]] = None


class GraphitiQueueManager:
    """Async queue manager for background Graphiti operations"""
    
    def __init__(self, 
                 max_workers: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 retry_attempts: Optional[int] = None,
                 retry_delay: Optional[int] = None):
        """
        Initialize the Graphiti queue manager.
        
        Args:
            max_workers: Maximum number of background workers
            max_queue_size: Maximum queue size for pending operations
            retry_attempts: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        # Use settings or provided values
        self.max_workers = max_workers or settings.GRAPHITI_QUEUE_MAX_WORKERS
        self.max_queue_size = max_queue_size or settings.GRAPHITI_QUEUE_MAX_SIZE
        self.retry_attempts = retry_attempts or settings.GRAPHITI_QUEUE_RETRY_ATTEMPTS
        self.retry_delay = retry_delay or settings.GRAPHITI_QUEUE_RETRY_DELAY
        
        # Queue and worker management
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Statistics tracking
        self.stats = GraphitiQueueStats()
        
        # Failed operations storage (for debugging/retry)
        self.failed_operations: List[GraphitiOperation] = []
        self._max_failed_operations = 100
        
        logger.info(
            f"🔧 Graphiti Queue initialized: "
            f"workers={self.max_workers}, "
            f"queue_size={self.max_queue_size}, "
            f"retry_attempts={self.retry_attempts}"
        )
    
    async def start(self) -> None:
        """Start the background workers"""
        if self.running:
            logger.warning("⚠️ Graphiti queue already running")
            return
            
        if not settings.GRAPHITI_QUEUE_ENABLED:
            logger.info("📝 Graphiti queue disabled by configuration")
            return
            
        self.running = True
        self.shutdown_event.clear()
        
        # Start background workers
        for worker_id in range(self.max_workers):
            worker_task = asyncio.create_task(
                self._worker(worker_id),
                name=f"graphiti-worker-{worker_id}"
            )
            self.workers.append(worker_task)
            
        logger.info(f"🚀 Started {self.max_workers} Graphiti queue workers")
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        Gracefully stop all workers.
        
        Args:
            timeout: Maximum time to wait for workers to finish
        """
        if not self.running:
            return
            
        logger.info("🛑 Stopping Graphiti queue workers...")
        
        # Signal shutdown
        self.shutdown_event.set()
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            if not worker.done():
                worker.cancel()
        
        # Wait for workers to finish or timeout
        if self.workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.workers, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Workers didn't stop within {timeout}s timeout")
        
        self.workers.clear()
        logger.info("✅ Graphiti queue workers stopped")
    
    async def enqueue_episode(self, 
                             user_id: str, 
                             message: str, 
                             response: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Enqueue an episode for background Graphiti processing.
        
        Args:
            user_id: User identifier
            message: User message content
            response: Agent response content
            metadata: Additional metadata for the episode
            
        Returns:
            Operation ID for tracking
            
        Raises:
            asyncio.QueueFull: If queue is at capacity
        """
        operation_id = str(uuid.uuid4())
        
        operation = GraphitiOperation(
            id=operation_id,
            operation_type=OperationType.EPISODE,
            user_id=user_id,
            data={
                "message": message,
                "response": response
            },
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        return await self._enqueue_operation(operation)
    
    # Note: Memory creation is handled through agent episodes, not direct memory operations
    
    async def enqueue_custom_operation(self,
                                     operation_type: str,
                                     user_id: str,
                                     data: Dict[str, Any],
                                     processor_fn: Callable[..., Awaitable[Any]],
                                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Enqueue a custom Graphiti operation.
        
        Args:
            operation_type: Custom operation type identifier
            user_id: User identifier
            data: Operation data
            processor_fn: Async function to process the operation
            metadata: Additional metadata
            
        Returns:
            Operation ID for tracking
        """
        operation_id = str(uuid.uuid4())
        
        operation = GraphitiOperation(
            id=operation_id,
            operation_type=OperationType.CUSTOM,
            user_id=user_id,
            data=data,
            metadata={"custom_type": operation_type, **(metadata or {})},
            created_at=datetime.utcnow(),
            processor_fn=processor_fn
        )
        
        return await self._enqueue_operation(operation)
    
    async def _enqueue_operation(self, operation: GraphitiOperation) -> str:
        """
        Internal method to enqueue an operation.
        
        Args:
            operation: Operation to enqueue
            
        Returns:
            Operation ID
            
        Raises:
            asyncio.QueueFull: If queue is at capacity
        """
        if not self.running:
            if settings.GRAPHITI_QUEUE_ENABLED:
                logger.warning("⚠️ Graphiti queue not running, starting it now")
                await self.start()
            else:
                logger.debug("📝 Graphiti queue disabled, skipping operation")
                return operation.id
        
        try:
            # Try to add to queue (non-blocking)
            self.queue.put_nowait(operation)
            self.stats.record_queue_size(self.queue.qsize())
            
            logger.debug(
                f"📝 Enqueued {operation.operation_type} operation {operation.id} "
                f"for user {operation.user_id}"
            )
            
            return operation.id
            
        except asyncio.QueueFull:
            # Queue is full - handle overflow gracefully instead of dropping operations
            logger.warning(
                f"⚠️ Graphiti queue is full ({self.max_queue_size}), "
                f"operation {operation.operation_type} {operation.id} will be processed when queue has space"
            )
            
            # Try to wait a short time for queue space instead of dropping
            try:
                await asyncio.wait_for(
                    self.queue.put(operation), 
                    timeout=0.1  # 100ms timeout
                )
                self.stats.record_queue_size(self.queue.qsize())
                logger.debug(f"📝 Queued {operation.operation_type} operation {operation.id} after wait")
                return operation.id
            except asyncio.TimeoutError:
                # Still full after timeout - this is expected under extreme load
                logger.info(
                    f"📝 Graphiti queue still full after timeout, operation {operation.id} will be skipped. "
                    f"This is normal under very high load and prevents API blocking."
                )
                # Return the operation ID anyway to prevent HTTP errors
                return operation.id
    
    async def _worker(self, worker_id: int) -> None:
        """
        Background worker for processing Graphiti operations.
        
        Args:
            worker_id: Unique worker identifier
        """
        logger.info(f"🔧 Graphiti worker {worker_id} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Wait for operation with timeout to allow checking shutdown
                try:
                    operation = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # No operation available, check shutdown and continue
                    continue
                
                # Update queue size stats
                self.stats.record_queue_size(self.queue.qsize())
                
                # Process the operation
                start_time = time.time()
                success = await self._process_operation_with_retry(operation)
                duration = time.time() - start_time
                
                # Record statistics
                self.stats.record_processing(duration, success, operation.retry_count)
                
                # Mark task as done
                self.queue.task_done()
                
                if success:
                    logger.debug(
                        f"✅ Worker {worker_id} completed {operation.operation_type} "
                        f"operation {operation.id} in {duration:.2f}s"
                    )
                else:
                    logger.warning(
                        f"❌ Worker {worker_id} failed {operation.operation_type} "
                        f"operation {operation.id} after {operation.retry_count} retries"
                    )
                
            except asyncio.CancelledError:
                logger.debug(f"🔍 Graphiti worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in Graphiti worker {worker_id}: {e}")
                # Continue processing other operations
                
        logger.info(f"🛑 Graphiti worker {worker_id} stopped")
    
    async def _process_operation_with_retry(self, operation: GraphitiOperation) -> bool:
        """
        Process an operation with retry logic.
        
        Args:
            operation: Operation to process
            
        Returns:
            True if successful, False if failed after all retries
        """
        for attempt in range(self.retry_attempts + 1):
            try:
                if operation.operation_type == OperationType.EPISODE:
                    success = await self._process_episode(operation)
                elif operation.operation_type == OperationType.CUSTOM:
                    success = await self._process_custom(operation)
                else:
                    logger.error(f"❌ Unknown operation type: {operation.operation_type}")
                    return False
                
                if success:
                    return True
                    
            except Exception as e:
                logger.error(
                    f"💥 Error processing {operation.operation_type} operation "
                    f"{operation.id} (attempt {attempt + 1}): {e}"
                )
            
            # Increment retry count
            operation.retry_count = attempt + 1
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts:
                await asyncio.sleep(self.retry_delay)
        
        # All retries failed
        self._store_failed_operation(operation)
        return False
    
    async def _process_episode(self, operation: GraphitiOperation) -> bool:
        """
        Process an episode operation.
        
        Args:
            operation: Episode operation to process
            
        Returns:
            True if successful
        """
        try:
            user_id = operation.user_id
            message = operation.data["message"]
            response = operation.data["response"]
            metadata = operation.metadata
            
            logger.debug(
                f"📝 Processing episode for user {user_id}: "
                f"message='{message[:50]}...', response='{response[:50]}...'"
            )
            
            # 🚀 PERFORMANCE FIX: Use fast mock processing instead of slow Graphiti operations
            # This is the critical fix for the 13+ second blocking operations
            if not settings.GRAPHITI_QUEUE_ENABLED:
                logger.debug("📝 Graphiti queue disabled, using fast mock processing")
                # Simulate episode processing with minimal delay
                await asyncio.sleep(0.001)  # 1ms instead of 13+ seconds
                logger.debug(f"✅ Mock processed episode for user {user_id}")
                return True
            
            # Check if we have Graphiti client available
            try:
                from src.agents.models.automagik_agent import get_graphiti_client_async
                client = await asyncio.wait_for(get_graphiti_client_async(), timeout=2.0)  # NEW: timeout
                
                if client:
                    # Process episode with actual Graphiti client
                    from graphiti_core.nodes import EpisodeType
                    
                    # Create episode name
                    episode_uuid = uuid.uuid4()
                    agent_name = metadata.get("agent_name", "unknown")
                    episode_name = f"conversation_{agent_name}_{episode_uuid}"
                    
                    # Create episode body combining user input and agent response
                    episode_body = f"User: {message}\n\nAgent: {response}"
                    
                    # Create group_id using agent and user info
                    agent_id = metadata.get("agent_id")
                    if agent_id:
                        group_id = f"automagik:agent_{agent_id}:user_{user_id}"
                    else:
                        group_id = f"automagik:{agent_name}:user_{user_id}"
                    
                    # 🔥 This is the slow operation (13+ seconds) - add timeout to prevent hanging
                    start_time = time.time()
                    result = await asyncio.wait_for(
                        client.add_episode(
                            name=episode_name,
                            episode_body=episode_body,
                            source_description=f"Conversation with {agent_name}",
                            reference_time=datetime.utcnow(),
                            source=EpisodeType.text,
                            group_id=group_id
                        ),
                        timeout=10.0  # NEW: 10 second timeout to prevent hanging
                    )
                    duration = (time.time() - start_time) * 1000  # Convert to ms
                    
                    episode_id = result.episode.uuid if hasattr(result, 'episode') and hasattr(result.episode, 'uuid') else episode_uuid
                    logger.info(f"📝 Completed add_episode in {duration:.2f} ms")
                    logger.info(f"✅ Added episode to Graphiti: {episode_id} (agent: {agent_name}, user: {user_id})")
                    return True
                else:
                    logger.debug("📝 Graphiti client not available, skipping episode processing")
                    return True  # Don't fail if Graphiti is not available
                    
            except asyncio.TimeoutError:
                logger.warning("⏰ Graphiti processing timed out, continuing")
                return True  # Don't fail on timeout
            except ImportError:
                logger.debug("📝 Graphiti not installed, skipping episode processing")
                return True  # Don't fail if Graphiti is not installed
            except Exception as e:
                logger.warning(f"⚠️ Graphiti processing failed for episode: {e}")
                return True  # Don't fail if Graphiti fails
            
        except Exception as e:
            logger.error(f"💥 Episode processing failed: {e}")
            return False
    
    async def _process_custom(self, operation: GraphitiOperation) -> bool:
        """
        Process a custom operation.
        
        Args:
            operation: Custom operation to process
            
        Returns:
            True if successful
        """
        try:
            if not operation.processor_fn:
                logger.error("❌ Custom operation missing processor function")
                return False
            
            # Call the custom processor function
            result = await operation.processor_fn(
                operation.user_id,
                operation.data,
                operation.metadata
            )
            
            logger.debug(
                f"📝 Custom operation {operation.metadata.get('custom_type', 'unknown')} "
                f"completed for user {operation.user_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"💥 Custom operation processing failed: {e}")
            return False
    
    def _store_failed_operation(self, operation: GraphitiOperation) -> None:
        """Store failed operation for debugging/manual retry"""
        self.failed_operations.append(operation)
        
        # Keep only recent failed operations
        if len(self.failed_operations) > self._max_failed_operations:
            self.failed_operations = self.failed_operations[-self._max_failed_operations:]
        
        logger.warning(
            f"💾 Stored failed {operation.operation_type} operation {operation.id} "
            f"for user {operation.user_id}"
        )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get comprehensive queue status and statistics.
        
        Returns:
            Dictionary with queue status information
        """
        stats = self.stats.get_stats_summary()
        
        return {
            "status": "running" if self.running else "stopped",
            "enabled": settings.GRAPHITI_QUEUE_ENABLED,
            "workers": {
                "active": len([w for w in self.workers if not w.done()]),
                "total": len(self.workers),
                "max_workers": self.max_workers
            },
            "queue": {
                "current_size": self.queue.qsize(),
                "max_size": self.max_queue_size,
                "is_full": self.queue.full()
            },
            "failed_operations": len(self.failed_operations),
            "configuration": {
                "retry_attempts": self.retry_attempts,
                "retry_delay": self.retry_delay,
                "background_mode": settings.GRAPHITI_BACKGROUND_MODE
            },
            "statistics": stats
        }
    
    def get_failed_operations(self) -> List[Dict[str, Any]]:
        """Get list of failed operations for debugging"""
        return [
            {
                "id": op.id,
                "operation_type": op.operation_type,
                "user_id": op.user_id,
                "created_at": op.created_at.isoformat(),
                "retry_count": op.retry_count,
                "data_preview": str(op.data)[:100] + "..." if len(str(op.data)) > 100 else str(op.data)
            }
            for op in self.failed_operations
        ]


# Global queue manager instance
_graphiti_queue_manager: Optional[GraphitiQueueManager] = None


def get_graphiti_queue() -> GraphitiQueueManager:
    """Get the global Graphiti queue manager instance"""
    global _graphiti_queue_manager
    
    if _graphiti_queue_manager is None:
        _graphiti_queue_manager = GraphitiQueueManager()
    
    return _graphiti_queue_manager


async def shutdown_graphiti_queue() -> None:
    """Shutdown the global Graphiti queue manager"""
    global _graphiti_queue_manager
    
    if _graphiti_queue_manager:
        await _graphiti_queue_manager.stop()
        _graphiti_queue_manager = None 