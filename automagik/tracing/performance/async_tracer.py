"""High-performance asynchronous tracer with minimal overhead."""

import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AsyncTracer:
    """High-performance async tracer with minimal overhead.
    
    Features:
    - Non-blocking event submission
    - Background thread processing
    - Batch processing for efficiency
    - Graceful degradation under load
    """
    
    def __init__(
        self, 
        max_workers: int = 2, 
        queue_size: int = 10000,
        batch_size: int = 50,
        batch_timeout_ms: int = 100,
        processor: Optional[Callable[[List[Dict[str, Any]]], None]] = None
    ):
        """Initialize the async tracer.
        
        Args:
            max_workers: Number of background worker threads
            queue_size: Maximum queue size before dropping events
            batch_size: Maximum events per batch
            batch_timeout_ms: Maximum time to wait for batch to fill
            processor: Function to process event batches
        """
        self.event_queue = queue.Queue(maxsize=queue_size)
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="tracer"
        )
        self.batch_size = batch_size
        self.batch_timeout_s = batch_timeout_ms / 1000.0
        self.processor = processor
        self.running = True
        
        # Metrics
        self.events_queued = 0
        self.events_processed = 0
        self.events_dropped = 0
        
        # Start background workers
        self._start_background_workers()
    
    def _start_background_workers(self):
        """Start background threads for trace processing."""
        for i in range(self.executor._max_workers):
            self.executor.submit(self._process_events, worker_id=i)
            logger.debug(f"Started tracer worker thread {i}")
    
    def _process_events(self, worker_id: int):
        """Process events in background thread."""
        logger.debug(f"Tracer worker {worker_id} started")
        
        while self.running:
            try:
                batch = self._collect_batch()
                if batch and self.processor:
                    try:
                        self.processor(batch)
                        self.events_processed += len(batch)
                    except Exception as e:
                        # Never crash the worker thread
                        logger.debug(f"Tracer processor error: {e}")
                        
            except Exception as e:
                # Catch any unexpected errors
                logger.debug(f"Tracer worker {worker_id} error: {e}")
                time.sleep(0.1)  # Brief pause before retrying
        
        logger.debug(f"Tracer worker {worker_id} stopped")
    
    def _collect_batch(self) -> List[Dict[str, Any]]:
        """Collect a batch of events from the queue."""
        batch = []
        
        try:
            # Wait for first event with timeout
            first_event = self.event_queue.get(timeout=self.batch_timeout_s)
            batch.append(first_event)
            
            # Collect additional events without waiting
            while len(batch) < self.batch_size:
                try:
                    event = self.event_queue.get_nowait()
                    batch.append(event)
                except queue.Empty:
                    break
                    
        except queue.Empty:
            # Normal timeout, no events available
            pass
            
        return batch
    
    def trace_event(self, event: Dict[str, Any]) -> bool:
        """Add event to queue - returns immediately.
        
        Args:
            event: Event data to trace
            
        Returns:
            True if event was queued, False if dropped
        """
        try:
            # Non-blocking put
            self.event_queue.put_nowait(event)
            self.events_queued += 1
            return True
        except queue.Full:
            # Drop event rather than block
            self.events_dropped += 1
            if self.events_dropped % 100 == 0:  # Log every 100 drops
                logger.debug(f"Trace queue full, dropped {self.events_dropped} events total")
            return False
    
    def get_metrics(self) -> Dict[str, int]:
        """Get tracer performance metrics."""
        return {
            "queued": self.events_queued,
            "processed": self.events_processed,
            "dropped": self.events_dropped,
            "queue_size": self.event_queue.qsize()
        }
    
    def shutdown(self, timeout: float = 5.0):
        """Shutdown the tracer gracefully.
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        logger.debug("Shutting down async tracer")
        self.running = False
        
        # Process remaining events
        start_time = time.time()
        while self.event_queue.qsize() > 0 and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=timeout)
        
        # Log final metrics
        metrics = self.get_metrics()
        logger.debug(f"Tracer shutdown complete. Final metrics: {metrics}")