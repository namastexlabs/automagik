"""
Session queue module for handling sequenced message processing.

This module provides a queueing system to ensure that messages for the same session
are processed in order, with ability to cancel/merge in-progress requests.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Awaitable, Callable, TypeVar, Generic, Set, List
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Result type for futures

class SessionQueue:
    """
    Manages per-session ordered message processing.
    Ensures FIFO ordering of messages within a session and allows
    cancelling/merging in-flight requests for the same session.
    """
    
    def __init__(self):
        """Initialize the session queue manager."""
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._closed_sessions: Set[str] = set()
        self._shutdown = False
        # Track current processing for each session
        self._current_processing: Dict[str, Dict[str, Any]] = {}
        
    async def process(self, 
                     session_id: str, 
                     message_content: str,
                     processor_fn: Callable[[str, List[str]], Awaitable[T]],
                     **kwargs) -> T:
        """
        Process a message for a specific session, respecting order and handling cancellations.
        
        Args:
            session_id: The session identifier
            message_content: The message content to process
            processor_fn: Async function that processes message(s), signature: async def fn(session_id, [messages])
            
        Returns:
            The result of processing the message(s)
            
        Note:
            If another message for the same session arrives while this one is being
            processed, this function will cancel the in-progress request and merge them.
        """
        if not session_id:
            # Generate an ephemeral ID for non-session messages
            session_id = f"ephemeral_{str(uuid.uuid4())}"
            
        # Get or create a lock for this session
        lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        
        # Create a future to represent this message's completion
        loop = asyncio.get_event_loop()
        future: asyncio.Future[T] = loop.create_future()
        
        # Critical section - under session lock
        async with lock:
            if session_id in self._closed_sessions or self._shutdown:
                # Session was closed while we were waiting
                raise ValueError(f"Session {session_id} has been closed or system is shutting down")
                
            # Check if there's already processing happening for this session
            if session_id in self._current_processing:
                current = self._current_processing[session_id]
                
                # Cancel the existing future
                if not current["future"].done():
                    logger.info(f"📝 Detected in-flight request for session {session_id}, merging messages")
                    current["future"].cancel()
                
                # Merge the messages
                current["messages"].append(message_content)
                current["future"] = future
                current["kwargs"] = kwargs
                current["processor_fn"] = processor_fn
                
                # Cancel the existing processing task if it exists
                if "task" in current and not current["task"].done():
                    current["task"].cancel()
                
                # Start a new processing task with the merged messages
                task = asyncio.create_task(
                    self._process_with_delay(session_id, current)
                )
                current["task"] = task
            else:
                # No current processing - start new
                processing_info = {
                    "messages": [message_content],
                    "future": future,
                    "kwargs": kwargs,
                    "processor_fn": processor_fn
                }
                self._current_processing[session_id] = processing_info
                
                # Start processing with a small delay to allow for merging
                task = asyncio.create_task(
                    self._process_with_delay(session_id, processing_info)
                )
                processing_info["task"] = task
                
        # Return the future that will be completed by the processor
        return await future
        
    async def _process_with_delay(self, session_id: str, processing_info: Dict[str, Any]) -> None:
        """
        Process messages after a small delay to allow for potential merging.
        
        Args:
            session_id: The session ID
            processing_info: Dictionary containing messages, future, etc.
        """
        try:
            # Small delay to allow for message merging
            await asyncio.sleep(0.005)
            
            # Get the lock and check if we're still the current processor
            lock = self._session_locks.get(session_id)
            if not lock:
                return
                
            async with lock:
                current = self._current_processing.get(session_id)
                if not current or current is not processing_info:
                    # We've been replaced by a newer processing request
                    return
                
                # Extract the information
                messages = current["messages"]
                future = current["future"]
                kwargs = current.get("kwargs", {})
                processor_fn = current["processor_fn"]
                
                # Remove from current processing
                del self._current_processing[session_id]
            
            # Process outside the lock
            try:
                if future.done():
                    # Future was already cancelled/completed
                    return
                    
                # Call the processor function
                result = await processor_fn(session_id, messages, **kwargs)
                
                # Complete the future with the result
                if not future.done():
                    future.set_result(result)
                    
            except asyncio.CancelledError:
                # Expected cancellation
                logger.debug(f"Processing for session {session_id} was cancelled")
                if not future.done():
                    future.cancel()
            except Exception as e:
                # Unexpected error
                logger.error(f"Error processing message for session {session_id}: {str(e)}")
                if not future.done():
                    future.set_exception(e)
                    
        except asyncio.CancelledError:
            # Task was cancelled
            logger.debug(f"🔍 Processing task for session {session_id} cancelled")
        except Exception as e:
            # Unexpected error in the processing task
            logger.error(f"Session processing task error: {str(e)}")
            
    async def close_session(self, session_id: str) -> None:
        """
        Close a session and clean up resources.
        
        Args:
            session_id: The session to close
        """
        lock = self._session_locks.get(session_id)
        if not lock:
            return
            
        async with lock:
            # Mark session as closed
            self._closed_sessions.add(session_id)
            
            # Cancel any current processing
            current = self._current_processing.get(session_id)
            if current:
                if "task" in current and not current["task"].done():
                    current["task"].cancel()
                    
                if not current["future"].done():
                    current["future"].cancel()
                    
                del self._current_processing[session_id]
            
    async def shutdown(self) -> None:
        """
        Shutdown the queue manager, cancelling all active workers and futures.
        """
        logger.debug("🔍 Shutting down SessionQueue")
        self._shutdown = True
        
        # Cancel all current processing
        for current in list(self._current_processing.values()):
            if "task" in current and not current["task"].done():
                current["task"].cancel()
                
            if not current["future"].done():
                current["future"].cancel()
                
        # Wait for tasks to finish
        tasks = [current["task"] for current in self._current_processing.values() 
                if "task" in current and not current["task"].done()]
        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("Some processing tasks did not shut down within timeout")
                
        # Clear all data structures
        self._current_processing.clear()
        self._session_locks.clear()
        self._closed_sessions.clear()

# Global instance for app-wide use
_session_queues = SessionQueue()

def get_session_queue() -> SessionQueue:
    """Get the global session queue instance."""
    global _session_queues
    return _session_queues

async def shutdown_session_queue() -> None:
    """Shutdown the global session queue instance."""
    global _session_queues
    await _session_queues.shutdown() 