"""Parser for Claude CLI JSON stream log files.

This module provides utilities to parse the immutable JSON stream log files
created during Claude CLI execution and extract meaningful events.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamParser:
    """Parse Claude CLI JSON stream log files."""
    
    @staticmethod
    def parse_stream_file(run_id: str) -> List[Dict[str, Any]]:
        """Parse a JSON stream file for a given run ID.
        
        Args:
            run_id: The run ID to parse
            
        Returns:
            List of parsed events from the stream file
        """
        log_path = Path(f"./logs/run_{run_id}_stream.jsonl")
        
        if not log_path.exists():
            logger.warning(f"Stream file not found: {log_path}")
            return []
        
        events = []
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse line: {e}")
                            continue
        except Exception as e:
            logger.error(f"Failed to read stream file: {e}")
            
        return events
    
    @staticmethod
    def extract_session_info(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract session information from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            Session information or None
        """
        for event in events:
            if event.get("type") == "system" and event.get("subtype") == "init":
                return {
                    "session_id": event.get("session_id"),
                    "model": event.get("model"),
                    "tools_available": len(event.get("tools", [])),
                    "mcp_servers": [server.get("name") for server in event.get("mcp_servers", [])],
                    "working_directory": event.get("cwd")
                }
        return None
    
    @staticmethod
    def extract_tool_calls(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool calls from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            List of tool call information
        """
        tool_calls = []
        
        for event in events:
            if event.get("type") == "assistant":
                message = event.get("message", {})
                content = message.get("content", [])
                
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_calls.append({
                            "name": item.get("name"),
                            "id": item.get("id"),
                            "timestamp": event.get("_timestamp"),
                            "input": item.get("input", {})
                        })
                        
        return tool_calls
    
    @staticmethod
    def extract_messages(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract conversation messages from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            List of messages
        """
        messages = []
        
        for event in events:
            if event.get("type") in ["human", "assistant"]:
                message = event.get("message", {})
                content = message.get("content", [])
                
                # Extract text content
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                
                if text_parts:
                    messages.append({
                        "role": event.get("type"),
                        "content": " ".join(text_parts),
                        "timestamp": event.get("_timestamp")
                    })
                    
        return messages
    
    @staticmethod
    def extract_result(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract the final result from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            Final result information or None
        """
        for event in reversed(events):  # Start from the end
            if event.get("type") == "result":
                return {
                    "success": not event.get("is_error", False),
                    "result": event.get("result", ""),
                    "subtype": event.get("subtype"),
                    "duration_ms": event.get("duration_ms"),
                    "cost_usd": event.get("cost_usd"),
                    "num_turns": event.get("num_turns"),
                    "timestamp": event.get("_timestamp")
                }
        return None
    
    @staticmethod
    def extract_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract metrics from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            Aggregated metrics
        """
        metrics = {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_created": 0,
            "cache_read": 0,
            "cost_usd": 0.0,
            "duration_ms": 0,
            "turns": 0,
            "tool_calls": 0
        }
        
        # Count tool calls
        metrics["tool_calls"] = len(StreamParser.extract_tool_calls(events))
        
        # Extract from result
        result = StreamParser.extract_result(events)
        if result:
            metrics["duration_ms"] = result.get("duration_ms", 0)
            metrics["cost_usd"] = result.get("cost_usd", 0.0)
            metrics["turns"] = result.get("num_turns", 0)
        
        # Extract from usage events
        for event in events:
            if event.get("type") == "usage":
                usage = event.get("usage", {})
                metrics["input_tokens"] += usage.get("input_tokens", 0)
                metrics["output_tokens"] += usage.get("output_tokens", 0)
                metrics["cache_created"] += usage.get("cache_creation_input_tokens", 0)
                metrics["cache_read"] += usage.get("cache_read_input_tokens", 0)
        
        metrics["total_tokens"] = metrics["input_tokens"] + metrics["output_tokens"]
        
        return metrics
    
    @staticmethod
    def get_current_status(events: List[Dict[str, Any]]) -> str:
        """Determine current status from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            Status string (pending, running, completed, failed)
        """
        if not events:
            return "pending"
        
        # Check for result
        result = StreamParser.extract_result(events)
        if result:
            return "completed" if result["success"] else "failed"
        
        # Check for session init
        session_info = StreamParser.extract_session_info(events)
        if session_info:
            return "running"
        
        return "pending"
    
    @staticmethod
    def get_progress_info(events: List[Dict[str, Any]], max_turns: Optional[int] = None) -> Dict[str, Any]:
        """Extract progress information from events.
        
        Args:
            events: List of parsed events
            max_turns: Maximum turns allowed
            
        Returns:
            Progress information
        """
        # Count conversation turns
        messages = StreamParser.extract_messages(events)
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        turns = len(assistant_messages)
        
        # Calculate percentage
        if max_turns is not None:
            percentage = min(100, int((turns / max_turns) * 100))
        else:
            # No max_turns limit - show percentage based on activity phases
            percentage = min(100, max(0, turns * 5))  # 5% per turn, capped at 100%
        
        # Determine current phase
        tool_calls = StreamParser.extract_tool_calls(events)
        current_phase = "initializing"
        
        if turns > 0:
            if any(tc["name"] in ["Read", "Glob", "Grep"] for tc in tool_calls[-5:]):
                current_phase = "analyzing"
            elif any(tc["name"] in ["Edit", "Write", "MultiEdit"] for tc in tool_calls[-5:]):
                current_phase = "implementing"
            elif any(tc["name"] == "Bash" for tc in tool_calls[-5:]):
                current_phase = "testing"
            else:
                current_phase = "planning"
        
        return {
            "turns": turns,
            "max_turns": max_turns,
            "completion_percentage": percentage,
            "current_phase": current_phase,
            "is_running": StreamParser.get_current_status(events) == "running"
        }