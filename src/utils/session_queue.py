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
        self._queues: Dict[str, asyncio.Queue] = {}
        self._active_futures: Dict[str, asyncio.Future] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._closed_sessions: Set[str] = set()
        
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
        
        # Ensure queue exists for this session
        queue = self._queues.setdefault(session_id, asyncio.Queue())
        
        # Create a future to represent this message's completion
        loop = asyncio.get_event_loop()
        future: asyncio.Future[T] = loop.create_future()
        
        # Critical section - under session lock
        async with lock:
            if session_id in self._closed_sessions:
                # Session was closed while we were waiting
                raise ValueError(f"Session {session_id} has been closed")
                
            # Check if there's an active task already
            if session_id in self._active_futures and not self._active_futures[session_id].done():
                # Cancel the existing task - we'll merge messages
                logger.info(f"Detected in-flight request for session {session_id}, merging messages")
                old_future = self._active_futures[session_id]
                old_future.cancel()
                
                # If there are pending items in the queue, get the old message content
                if not queue.empty():
                    old_message = await queue.get()
                    # Put a merged message on the queue 
                    await queue.put({
                        "message_contents": [old_message["message_contents"][0], message_content],
                        "future": future,
                        "kwargs": kwargs
                    })
                else:
                    # This shouldn't normally happen - put the new message only
                    await queue.put({
                        "message_contents": [message_content],
                        "future": future,
                        "kwargs": kwargs
                    })
            else:
                # No active task or it's already completed - enqueue normally
                await queue.put({
                    "message_contents": [message_content],
                    "future": future,
                    "kwargs": kwargs
                })
            
            # Store the future for potential cancellation
            self._active_futures[session_id] = future
            
            # Start/ensure a worker is running for this session
            if session_id not in self._workers or self._workers[session_id].done():
                worker = asyncio.create_task(
                    self._worker_loop(session_id, processor_fn)
                )
                self._workers[session_id] = worker
                
        # Return the future that will be completed by the worker
        return await future
        
    async def _worker_loop(self, 
                          session_id: str, 
                          processor_fn: Callable[[str, List[str]], Awaitable[T]]) -> None:
        """
        Worker loop that processes messages from a session's queue.
        
        Args:
            session_id: The session ID to process messages for
            processor_fn: The function to call with message(s)
        """
        try:
            queue = self._queues[session_id]
            logger.debug(f"Starting worker loop for session {session_id}")
            
            while True:
                # Get the next message from the queue
                item = await queue.get()
                
                message_contents = item["message_contents"]
                future = item["future"]
                kwargs = item.get("kwargs", {})
                
                try:
                    # Process the message(s)
                    result = await processor_fn(session_id, message_contents, **kwargs)
                    
                    # Complete the future with the result
                    if not future.done():
                        future.set_result(result)
                except asyncio.CancelledError:
                    # Expected cancellation (e.g. merged with newer message)
                    logger.debug(f"Processing for session {session_id} was cancelled")
                    if not future.done():
                        future.cancel()
                except Exception as e:
                    # Unexpected error
                    logger.error(f"Error processing message for session {session_id}: {str(e)}")
                    if not future.done():
                        future.set_exception(e)
                finally:
                    # Mark the task as done in the queue
                    queue.task_done()
                
        except asyncio.CancelledError:
            # Worker task was cancelled
            logger.debug(f"Worker for session {session_id} cancelled")
        except Exception as e:
            # Unexpected error in the worker loop
            logger.error(f"Session worker error: {str(e)}")
        finally:
            logger.debug(f"Worker loop for session {session_id} exiting")
            
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
            
            # Cancel any active worker
            worker = self._workers.get(session_id)
            if worker and not worker.done():
                worker.cancel()
                
            # Cancel any active future
            future = self._active_futures.get(session_id)
            if future and not future.done():
                future.cancel()
                
            # Clean up resources
            self._queues.pop(session_id, None)
            self._workers.pop(session_id, None)
            self._active_futures.pop(session_id, None)
            

# Global instance for app-wide use
_session_queues = SessionQueue()

def get_session_queue() -> SessionQueue:
    """Get the global session queue instance."""
    global _session_queues
    return _session_queues 