"""
Graphiti Queue Statistics Tracker

Tracks performance metrics for the asynchronous Graphiti queue operations.
"""

import time
from typing import List, Dict, Any
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class GraphitiQueueStats:
    """Track Graphiti queue performance metrics"""
    
    def __init__(self):
        """Initialize statistics tracker"""
        self._lock = Lock()
        self.total_processed = 0
        self.total_failed = 0
        self.total_retries = 0
        self.processing_times: List[float] = []
        self.start_time = time.time()
        self.last_reset_time = time.time()
        
        # Keep only recent processing times for rolling averages
        self._max_processing_times = 1000
        
        # Queue size tracking
        self.peak_queue_size = 0
        self.current_queue_size = 0
        
    def record_processing(self, duration: float, success: bool, retry_count: int = 0) -> None:
        """
        Record a processing attempt.
        
        Args:
            duration: Processing time in seconds
            success: Whether the operation succeeded
            retry_count: Number of retries for this operation
        """
        with self._lock:
            self.total_processed += 1
            if not success:
                self.total_failed += 1
            
            self.total_retries += retry_count
            
            # Track processing times (keep only recent ones)
            self.processing_times.append(duration)
            if len(self.processing_times) > self._max_processing_times:
                self.processing_times = self.processing_times[-self._max_processing_times:]
                
    def record_queue_size(self, size: int) -> None:
        """Record current queue size for tracking"""
        with self._lock:
            self.current_queue_size = size
            if size > self.peak_queue_size:
                self.peak_queue_size = size
                
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        with self._lock:
            if self.total_processed == 0:
                return 100.0
            return ((self.total_processed - self.total_failed) / self.total_processed) * 100.0
    
    def get_avg_processing_time(self) -> float:
        """Calculate average processing time in seconds"""
        with self._lock:
            if not self.processing_times:
                return 0.0
            return sum(self.processing_times) / len(self.processing_times)
    
    def get_median_processing_time(self) -> float:
        """Calculate median processing time in seconds"""
        with self._lock:
            if not self.processing_times:
                return 0.0
            sorted_times = sorted(self.processing_times)
            n = len(sorted_times)
            if n % 2 == 0:
                return (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
            else:
                return sorted_times[n//2]
    
    def get_p95_processing_time(self) -> float:
        """Calculate 95th percentile processing time in seconds"""
        with self._lock:
            if not self.processing_times:
                return 0.0
            sorted_times = sorted(self.processing_times)
            index = int(0.95 * len(sorted_times))
            if index >= len(sorted_times):
                index = len(sorted_times) - 1
            return sorted_times[index]
    
    def get_throughput(self) -> float:
        """Calculate operations per second since start"""
        with self._lock:
            elapsed = time.time() - self.start_time
            if elapsed == 0:
                return 0.0
            return self.total_processed / elapsed
    
    def get_recent_throughput(self, window_seconds: int = 300) -> float:
        """Calculate operations per second in recent window (default 5 minutes)"""
        with self._lock:
            # For simplicity, we'll use overall throughput
            # In a production system, you'd track timestamps for each operation
            return self.get_throughput()
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get comprehensive statistics summary"""
        with self._lock:
            uptime = time.time() - self.start_time
            
            return {
                # Basic counts
                "total_processed": self.total_processed,
                "total_failed": self.total_failed,
                "total_retries": self.total_retries,
                
                # Success metrics
                "success_rate": round(self.get_success_rate(), 2),
                "error_rate": round(100.0 - self.get_success_rate(), 2),
                
                # Performance metrics
                "avg_processing_time_ms": round(self.get_avg_processing_time() * 1000, 2),
                "median_processing_time_ms": round(self.get_median_processing_time() * 1000, 2),
                "p95_processing_time_ms": round(self.get_p95_processing_time() * 1000, 2),
                
                # Throughput metrics
                "operations_per_second": round(self.get_throughput(), 2),
                "operations_per_minute": round(self.get_throughput() * 60, 2),
                
                # Queue metrics
                "current_queue_size": self.current_queue_size,
                "peak_queue_size": self.peak_queue_size,
                
                # Uptime
                "uptime_seconds": round(uptime, 2),
                "uptime_hours": round(uptime / 3600, 2),
                
                # Retry metrics
                "avg_retries_per_operation": round(
                    self.total_retries / max(self.total_processed, 1), 2
                ),
            }
    
    def reset_stats(self) -> None:
        """Reset all statistics (useful for testing)"""
        with self._lock:
            self.total_processed = 0
            self.total_failed = 0
            self.total_retries = 0
            self.processing_times.clear()
            self.start_time = time.time()
            self.last_reset_time = time.time()
            self.peak_queue_size = 0
            self.current_queue_size = 0
            
    def log_stats_summary(self) -> None:
        """Log current statistics summary"""
        stats = self.get_stats_summary()
        logger.info(
            f"📊 Graphiti Queue Stats: "
            f"Processed: {stats['total_processed']}, "
            f"Success Rate: {stats['success_rate']}%, "
            f"Avg Time: {stats['avg_processing_time_ms']}ms, "
            f"Throughput: {stats['operations_per_second']} ops/sec, "
            f"Queue: {stats['current_queue_size']}/{stats['peak_queue_size']} (current/peak)"
        ) 