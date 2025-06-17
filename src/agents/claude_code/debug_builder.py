"""Debug response builder for Claude Code workflows.

This module builds comprehensive debug information for Claude workflow
status responses, providing detailed insights for troubleshooting.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DebugBuilder:
    """Builds comprehensive debug information for status responses."""
    
    def __init__(self):
        """Initialize debug builder."""
        self.section_builders = {
            "session_info": self._build_session_info,
            "execution_details": self._build_execution_details,
            "tool_usage": self._build_tool_usage,
            "timing_analysis": self._build_timing_analysis,
            "cost_breakdown": self._build_cost_breakdown,
            "workflow_phases": self._build_workflow_phases,
            "performance_metrics": self._build_performance_metrics,
            "error_analysis": self._build_error_analysis,
            "raw_stream_sample": self._build_raw_stream_sample
        }
    
    def build_debug_response(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Build comprehensive debug response.
        
        Args:
            metadata: Session metadata
            log_entries: Raw log entries
            messages: Assistant messages
            stream_metrics: Optional stream processing metrics
            
        Returns:
            Complete debug information dictionary
        """
        debug_info = {}
        
        try:
            # Build each debug section
            for section_name, builder_func in self.section_builders.items():
                try:
                    debug_info[section_name] = builder_func(
                        metadata, log_entries, messages, stream_metrics
                    )
                except Exception as e:
                    logger.warning(f"Error building debug section {section_name}: {e}")
                    debug_info[section_name] = {"error": f"Failed to build: {e}"}
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Error building debug response: {e}")
            return {"error": f"Debug build failed: {e}"}
    
    def _build_session_info(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build session information section."""
        return {
            "session_id": metadata.get("session_id"),
            "claude_session_id": metadata.get("claude_session_id"),
            "container_id": metadata.get("container_id"),
            "run_id": metadata.get("run_id"),
            "workflow_name": metadata.get("workflow_name"),
            "started_at": metadata.get("started_at"),
            "git_branch": metadata.get("git_branch"),
            "repository_url": metadata.get("repository_url")
        }
    
    def _build_execution_details(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build execution details section."""
        return {
            "exit_code": metadata.get("exit_code"),
            "max_turns": metadata.get("max_turns"),
            "current_turns": metadata.get("current_turns", 0),
            "timeout_seconds": metadata.get("timeout_seconds", 3600),
            "execution_time": metadata.get("execution_time"),
            "run_status": metadata.get("run_status"),
            "git_commits": metadata.get("git_commits", []),
            "container_status": metadata.get("container_status")
        }
    
    def _build_tool_usage(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build tool usage analysis section."""
        tool_stats = {}
        total_tool_calls = 0
        
        # Analyze tool usage from log entries
        for entry in log_entries:
            if isinstance(entry, dict):
                data = entry.get('data', {})
                if isinstance(data, dict):
                    tool_name = data.get('tool_name')
                    if tool_name:
                        total_tool_calls += 1
                        if tool_name not in tool_stats:
                            tool_stats[tool_name] = {
                                "count": 0,
                                "success": 0,
                                "errors": 0,
                                "last_used": None
                            }
                        
                        tool_stats[tool_name]["count"] += 1
                        
                        # Check for success/error
                        if data.get('status') == 'success':
                            tool_stats[tool_name]["success"] += 1
                        elif data.get('status') == 'error':
                            tool_stats[tool_name]["errors"] += 1
        
        return {
            "total_tool_calls": total_tool_calls,
            "unique_tools_used": len(tool_stats),
            "tool_breakdown": tool_stats,
            "most_used_tool": max(tool_stats, key=lambda k: tool_stats[k]["count"]) if tool_stats else None
        }
    
    def _build_timing_analysis(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build timing analysis section."""
        started_at = metadata.get("started_at")
        execution_time = metadata.get("execution_time", 0)
        current_turns = metadata.get("current_turns", 0)
        
        # Calculate timing metrics
        avg_turn_time = execution_time / current_turns if current_turns > 0 else 0
        
        return {
            "started_at": started_at,
            "execution_time_seconds": execution_time,
            "current_turns": current_turns,
            "average_turn_time_seconds": round(avg_turn_time, 2),
            "estimated_total_duration": metadata.get("estimated_duration"),
            "last_activity": metadata.get("last_activity")
        }
    
    def _build_cost_breakdown(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build cost breakdown section."""
        cost_data = stream_metrics or {}
        
        return {
            "total_cost_usd": cost_data.get("cost_usd", 0.0),
            "input_tokens": cost_data.get("input_tokens", 0),
            "output_tokens": cost_data.get("output_tokens", 0),
            "cache_creation_tokens": cost_data.get("cache_creation_tokens", 0),
            "cache_read_tokens": cost_data.get("cache_read_tokens", 0),
            "total_tokens": cost_data.get("total_tokens", 0),
            "cost_per_token": cost_data.get("cost_per_token", 0.0),
            "cache_efficiency_percent": self._calculate_cache_efficiency(cost_data)
        }
    
    def _build_workflow_phases(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build workflow phases section."""
        # Import here to avoid circular imports
        from .progress_tracker import ProgressTracker
        
        tracker = ProgressTracker()
        phase_summary = tracker.get_phase_summary(log_entries, metadata.get("current_phase", "unknown"))
        
        return phase_summary
    
    def _build_performance_metrics(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build performance metrics section."""
        current_turns = metadata.get("current_turns", 0)
        max_turns = metadata.get("max_turns")
        execution_time = metadata.get("execution_time", 0)
        
        return {
            "turn_efficiency_percent": round((current_turns / max_turns) * 100, 1) if max_turns and max_turns > 0 else 0,
            "time_per_turn_seconds": round(execution_time / current_turns, 2) if current_turns > 0 else 0,
            "estimated_completion_percent": min(100, (current_turns / max_turns) * 100) if max_turns and max_turns > 0 else 0,
            "resource_utilization": self._calculate_resource_utilization(metadata, stream_metrics)
        }
    
    def _build_error_analysis(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build error analysis section."""
        errors = []
        error_count = 0
        
        # Analyze errors from log entries
        for entry in log_entries:
            if isinstance(entry, dict):
                data = entry.get('data', {})
                if isinstance(data, dict):
                    if data.get('status') == 'error' or 'error' in str(data).lower():
                        error_count += 1
                        errors.append({
                            "timestamp": entry.get('timestamp'),
                            "error_type": data.get('error_type', 'unknown'),
                            "message": str(data.get('content', ''))[:200],
                            "tool": data.get('tool_name')
                        })
        
        return {
            "total_errors": error_count,
            "error_rate_percent": round((error_count / len(log_entries)) * 100, 1) if log_entries else 0,
            "recent_errors": errors[-5:],  # Last 5 errors
            "error_patterns": self._identify_error_patterns(errors)
        }
    
    def _build_raw_stream_sample(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any],
        stream_metrics: Optional[Dict]
    ) -> List[Dict]:
        """Build raw stream sample section."""
        # Return last 5 log entries for debugging
        recent_entries = log_entries[-5:] if log_entries else []
        
        sample = []
        for entry in recent_entries:
            if isinstance(entry, dict):
                sample.append({
                    "timestamp": entry.get("timestamp"),
                    "event_type": entry.get("event_type"),
                    "data_preview": str(entry.get("data", {}))[:200]
                })
        
        return sample
    
    def _calculate_cache_efficiency(self, cost_data: Dict) -> float:
        """Calculate cache efficiency percentage."""
        cache_read = cost_data.get("cache_read_tokens", 0)
        cache_creation = cost_data.get("cache_creation_tokens", 0)
        
        if cache_read + cache_creation > 0:
            return round((cache_read / (cache_read + cache_creation)) * 100, 1)
        return 0.0
    
    def _calculate_resource_utilization(
        self,
        metadata: Dict[str, Any],
        stream_metrics: Optional[Dict]
    ) -> Dict[str, Any]:
        """Calculate resource utilization metrics."""
        return {
            "memory_usage": "normal",  # Would need container stats
            "cpu_usage": "normal",     # Would need container stats
            "disk_usage": "low",       # Would need container stats
            "network_usage": "minimal" # Would need container stats
        }
    
    def _identify_error_patterns(self, errors: List[Dict]) -> List[str]:
        """Identify common error patterns."""
        patterns = []
        
        if not errors:
            return patterns
        
        # Common error patterns
        error_messages = [error.get("message", "") for error in errors]
        
        if any("permission" in msg.lower() for msg in error_messages):
            patterns.append("permission_errors")
        
        if any("timeout" in msg.lower() for msg in error_messages):
            patterns.append("timeout_errors")
        
        if any("network" in msg.lower() or "connection" in msg.lower() for msg in error_messages):
            patterns.append("network_errors")
        
        if any("file not found" in msg.lower() for msg in error_messages):
            patterns.append("file_not_found_errors")
        
        return patterns