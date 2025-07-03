"""Enhanced JSONL parser for comprehensive workflow detail data extraction.

This service builds on the existing StreamParser to provide comprehensive
workflow execution data including file changes, detailed conversation flow,
execution logs, and enhanced metrics for the workflow detail UI.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Handle import path for StreamParser
current_file = Path(__file__)
repo_root = current_file.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from automagik.agents.claude_code.stream_parser import StreamParser

logger = logging.getLogger(__name__)


class FileChange:
    """Represents a file change during workflow execution."""
    
    def __init__(self, path: str, status: str, additions: int = 0, deletions: int = 0, diff: str = ""):
        self.path = path
        self.status = status  # "added", "modified", "deleted"
        self.additions = additions
        self.deletions = deletions
        self.diff = diff
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
            "diff": self.diff
        }


class LogEntry:
    """Represents an execution log entry."""
    
    def __init__(self, timestamp: str, level: str, message: str, tool: str = ""):
        self.timestamp = timestamp
        self.level = level  # "info", "error", "warning"
        self.message = message
        self.tool = tool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "tool": self.tool
        }


class WorkflowJSONLParser:
    """Enhanced parser for comprehensive workflow detail data extraction."""
    
    @staticmethod
    def parse_workflow_details(run_id: str) -> Dict[str, Any]:
        """Parse complete workflow details from JSONL file.
        
        Args:
            run_id: The workflow run ID
            
        Returns:
            Comprehensive workflow details dictionary
        """
        try:
            # Use existing StreamParser for base data
            events = StreamParser.parse_stream_file(run_id)
            
            if not events:
                logger.warning(f"No events found for run {run_id}")
                return WorkflowJSONLParser._empty_response(run_id)
            
            # Extract all data components
            session_info = StreamParser.extract_session_info(events)
            status = StreamParser.get_current_status(events)
            result = StreamParser.extract_result(events)
            metrics = StreamParser.extract_metrics(events)
            progress = StreamParser.get_progress_info(events)
            messages = StreamParser.extract_messages(events)
            
            # Extract additional details
            file_changes = WorkflowJSONLParser.extract_file_changes(events)
            execution_logs = WorkflowJSONLParser.extract_execution_logs(events)
            git_info = WorkflowJSONLParser.extract_git_info(events)
            enhanced_metrics = WorkflowJSONLParser.calculate_enhanced_metrics(events, metrics)
            
            # Build comprehensive response
            workflow_details = {
                "run_id": run_id,
                "workflow_name": "builder",  # Could be extracted from events
                "status": status,
                "started_at": WorkflowJSONLParser._extract_start_time(events),
                "completed_at": WorkflowJSONLParser._extract_completion_time(events),
                "execution_time_seconds": WorkflowJSONLParser._calculate_execution_time(events),
                "ai_model": session_info.get("model") if session_info else "claude-sonnet-4-20250514",
                
                "repository": git_info,
                "files_changed": [fc.to_dict() for fc in file_changes],
                "conversation": WorkflowJSONLParser._format_conversation(messages, events),
                "execution_logs": [log.to_dict() for log in execution_logs],
                "metrics": enhanced_metrics
            }
            
            return workflow_details
            
        except Exception as e:
            logger.error(f"Error parsing workflow details for {run_id}: {e}")
            return WorkflowJSONLParser._empty_response(run_id, error=str(e))
    
    @staticmethod
    def extract_file_changes(events: List[Dict[str, Any]]) -> List[FileChange]:
        """Extract file changes from tool operations.
        
        Args:
            events: List of JSONL events
            
        Returns:
            List of FileChange objects
        """
        file_changes = []
        file_operations = {}  # Track operations per file
        
        try:
            for event in events:
                if event.get("type") != "assistant":
                    continue
                
                content = event.get("message", {}).get("content", [])
                timestamp = event.get("_timestamp", "")
                
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_use":
                        continue
                    
                    tool_name = item.get("name")
                    tool_input = item.get("input", {})
                    
                    if tool_name in ["Edit", "MultiEdit"]:
                        # Extract file path and changes
                        file_path = tool_input.get("file_path", "")
                        if file_path:
                            if tool_name == "Edit":
                                old_string = tool_input.get("old_string", "")
                                new_string = tool_input.get("new_string", "")
                                additions, deletions = WorkflowJSONLParser._count_diff_lines(old_string, new_string)
                                
                                file_operations[file_path] = {
                                    "status": "modified",
                                    "additions": additions,
                                    "deletions": deletions,
                                    "timestamp": timestamp,
                                    "diff": WorkflowJSONLParser._create_diff(old_string, new_string)
                                }
                                
                            elif tool_name == "MultiEdit":
                                edits = tool_input.get("edits", [])
                                total_additions = 0
                                total_deletions = 0
                                diff_parts = []
                                
                                for edit in edits:
                                    old_str = edit.get("old_string", "")
                                    new_str = edit.get("new_string", "")
                                    additions, deletions = WorkflowJSONLParser._count_diff_lines(old_str, new_str)
                                    total_additions += additions
                                    total_deletions += deletions
                                    diff_parts.append(WorkflowJSONLParser._create_diff(old_str, new_str))
                                
                                file_operations[file_path] = {
                                    "status": "modified",
                                    "additions": total_additions,
                                    "deletions": total_deletions,
                                    "timestamp": timestamp,
                                    "diff": "\n".join(diff_parts)
                                }
                    
                    elif tool_name == "Write":
                        # New file creation
                        file_path = tool_input.get("file_path", "")
                        content = tool_input.get("content", "")
                        if file_path:
                            lines = content.count('\n') + 1 if content else 0
                            file_operations[file_path] = {
                                "status": "added",
                                "additions": lines,
                                "deletions": 0,
                                "timestamp": timestamp,
                                "diff": f"+++ {file_path}\n" + "\n".join(f"+{line}" for line in content.split('\n'))
                            }
            
            # Convert to FileChange objects
            for file_path, operation in file_operations.items():
                file_changes.append(FileChange(
                    path=file_path,
                    status=operation["status"],
                    additions=operation["additions"],
                    deletions=operation["deletions"],
                    diff=operation["diff"]
                ))
                
        except Exception as e:
            logger.error(f"Error extracting file changes: {e}")
        
        return file_changes
    
    @staticmethod
    def extract_execution_logs(events: List[Dict[str, Any]]) -> List[LogEntry]:
        """Extract execution logs from tool operations and results.
        
        Args:
            events: List of JSONL events
            
        Returns:
            List of LogEntry objects
        """
        logs = []
        
        try:
            for event in events:
                timestamp = event.get("_timestamp", "")
                event_type = event.get("type", "")
                
                if event_type == "assistant":
                    # Tool usage logs
                    content = event.get("message", {}).get("content", [])
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_name = item.get("name")
                            logs.append(LogEntry(
                                timestamp=timestamp,
                                level="info",
                                message=f"Executing {tool_name} tool",
                                tool=tool_name
                            ))
                
                elif event_type == "user":
                    # Tool results
                    is_error = event.get("is_error", False)
                    content = event.get("content", [])
                    
                    if isinstance(content, list) and content:
                        text_content = ""
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "tool_result":
                                    tool_id = item.get("tool_use_id", "")
                                    content_text = item.get("content", "")
                                    if isinstance(content_text, list) and content_text:
                                        text_content = content_text[0].get("text", "") if isinstance(content_text[0], dict) else str(content_text[0])
                                    else:
                                        text_content = str(content_text)
                            elif isinstance(item, str):
                                text_content = item
                        
                        if text_content:
                            logs.append(LogEntry(
                                timestamp=timestamp,
                                level="error" if is_error else "info",
                                message=text_content[:200] + "..." if len(text_content) > 200 else text_content,
                                tool="system"
                            ))
                
                elif event_type == "result":
                    # Final result
                    result_text = event.get("result", "")
                    is_error = event.get("is_error", False)
                    logs.append(LogEntry(
                        timestamp=timestamp,
                        level="error" if is_error else "info",
                        message=f"Workflow completed: {result_text}",
                        tool="system"
                    ))
                    
        except Exception as e:
            logger.error(f"Error extracting execution logs: {e}")
        
        return logs
    
    @staticmethod
    def extract_git_info(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract git repository information.
        
        Args:
            events: List of JSONL events
            
        Returns:
            Git information dictionary
        """
        git_info = {
            "url": "",
            "branch": "main",
            "commit_hash": "",
            "workspace_path": ""
        }
        
        try:
            # Extract from system init event
            for event in events:
                if event.get("type") == "system" and event.get("subtype") == "init":
                    workspace_path = event.get("cwd", "")
                    git_info["workspace_path"] = workspace_path
                    
                    # Try to extract repo info from workspace path
                    if "worktrees" in workspace_path:
                        # Pattern: /workspace/worktrees/builder_run_{id}
                        git_info["url"] = "https://github.com/namastexlabs/am-agents-labs"
                        
                        # Extract branch from git operations
                        for git_event in events:
                            if git_event.get("type") == "user":
                                content = git_event.get("content", [])
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "tool_result":
                                        text = item.get("content", "")
                                        if isinstance(text, list) and text:
                                            text = text[0].get("text", "") if isinstance(text[0], dict) else str(text[0])
                                        
                                        # Look for git branch info
                                        if "builder/" in str(text):
                                            branch_match = re.search(r'builder/[a-zA-Z0-9_-]+', str(text))
                                            if branch_match:
                                                git_info["branch"] = branch_match.group()
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting git info: {e}")
        
        return git_info
    
    @staticmethod
    def calculate_enhanced_metrics(events: List[Dict[str, Any]], base_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics with detailed breakdown.
        
        Args:
            events: List of JSONL events
            base_metrics: Base metrics from StreamParser
            
        Returns:
            Enhanced metrics dictionary
        """
        # Start with base metrics
        enhanced = base_metrics.copy()
        
        # Add enhanced calculations
        tool_usage_count = {}
        tools_used = []
        
        for event in events:
            if event.get("type") == "assistant":
                content = event.get("message", {}).get("content", [])
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name")
                        if tool_name:
                            tool_usage_count[tool_name] = tool_usage_count.get(tool_name, 0) + 1
                            if tool_name not in tools_used:
                                tools_used.append(tool_name)
        
        # Calculate performance metrics
        start_time = WorkflowJSONLParser._extract_start_time(events)
        end_time = WorkflowJSONLParser._extract_completion_time(events)
        duration_seconds = 0
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_seconds = (end_dt - start_dt).total_seconds()
            except Exception:
                pass
        
        avg_response_time = duration_seconds / max(enhanced.get("turns", 1), 1) if duration_seconds > 0 else 0
        
        # Error analysis
        error_count = 0
        for event in events:
            if event.get("is_error", False):
                error_count += 1
        
        success_rate = 100.0 - (error_count / max(len(events), 1) * 100) if events else 0
        
        enhanced.update({
            "total_turns": enhanced.get("turns", 0),
            "tools_used": tools_used,
            "tool_usage_count": tool_usage_count,
            "token_usage": {
                "total_input": enhanced.get("input_tokens", 0),
                "total_output": enhanced.get("output_tokens", 0),
                "cache_created": enhanced.get("cache_created", 0),
                "cache_read": enhanced.get("cache_read", 0)
            },
            "performance": {
                "avg_response_time_seconds": round(avg_response_time, 2),
                "error_count": error_count,
                "success_rate": round(success_rate, 1)
            }
        })
        
        return enhanced
    
    @staticmethod
    def _format_conversation(messages: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format conversation messages with tool call information.
        
        Args:
            messages: Raw messages from StreamParser
            events: Full event list for tool call context
            
        Returns:
            Formatted conversation messages
        """
        formatted = []
        
        for i, message in enumerate(messages, 1):
            formatted_msg = {
                "role": message["role"],
                "content": message["content"],
                "timestamp": message["timestamp"],
                "turn": i
            }
            
            # Add tool calls for assistant messages
            if message["role"] == "assistant":
                tool_calls = []
                for event in events:
                    if (event.get("type") == "assistant" and 
                        event.get("_timestamp") == message["timestamp"]):
                        content = event.get("message", {}).get("content", [])
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                tool_calls.append({
                                    "tool": item.get("name"),
                                    "success": True
                                })
                formatted_msg["tool_calls"] = tool_calls
            
            formatted.append(formatted_msg)
        
        return formatted
    
    @staticmethod
    def _count_diff_lines(old_string: str, new_string: str) -> tuple[int, int]:
        """Count additions and deletions between two strings."""
        old_lines = old_string.split('\n')
        new_lines = new_string.split('\n')
        
        # Simple diff calculation
        additions = max(0, len(new_lines) - len(old_lines))
        deletions = max(0, len(old_lines) - len(new_lines))
        
        # Count actual content changes
        min_lines = min(len(old_lines), len(new_lines))
        for i in range(min_lines):
            if old_lines[i] != new_lines[i]:
                if not old_lines[i].strip():  # Old line was empty
                    additions += 1
                elif not new_lines[i].strip():  # New line is empty
                    deletions += 1
                else:  # Line modified
                    additions += 1
                    deletions += 1
        
        return additions, deletions
    
    @staticmethod
    def _create_diff(old_string: str, new_string: str) -> str:
        """Create a unified diff between two strings."""
        old_lines = old_string.split('\n')
        new_lines = new_string.split('\n')
        
        diff_lines = []
        diff_lines.append("@@ -1,{} +1,{} @@".format(len(old_lines), len(new_lines)))
        
        # Simple diff - mark all old lines as removed, new lines as added
        for line in old_lines:
            diff_lines.append(f"-{line}")
        for line in new_lines:
            diff_lines.append(f"+{line}")
        
        return '\n'.join(diff_lines)
    
    @staticmethod
    def _extract_start_time(events: List[Dict[str, Any]]) -> Optional[str]:
        """Extract workflow start time."""
        for event in events:
            if event.get("type") == "system" and event.get("subtype") == "init":
                return event.get("_timestamp")
        return events[0].get("_timestamp") if events else None
    
    @staticmethod
    def _extract_completion_time(events: List[Dict[str, Any]]) -> Optional[str]:
        """Extract workflow completion time."""
        for event in reversed(events):
            if event.get("type") == "result":
                return event.get("_timestamp")
        return None
    
    @staticmethod
    def _calculate_execution_time(events: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate total execution time in seconds."""
        start_time = WorkflowJSONLParser._extract_start_time(events)
        end_time = WorkflowJSONLParser._extract_completion_time(events)
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return (end_dt - start_dt).total_seconds()
            except Exception:
                pass
        
        return None
    
    @staticmethod
    def _empty_response(run_id: str, error: str = "") -> Dict[str, Any]:
        """Return empty response structure for missing data."""
        return {
            "run_id": run_id,
            "workflow_name": "unknown",
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "execution_time_seconds": None,
            "ai_model": "claude-sonnet-4-20250514",
            "repository": {
                "url": "",
                "branch": "main",
                "commit_hash": "",
                "workspace_path": ""
            },
            "files_changed": [],
            "conversation": [],
            "execution_logs": [],
            "metrics": {
                "total_turns": 0,
                "tools_used": [],
                "tool_usage_count": {},
                "token_usage": {
                    "total_input": 0,
                    "total_output": 0,
                    "cache_created": 0,
                    "cache_read": 0
                },
                "performance": {
                    "avg_response_time_seconds": 0.0,
                    "error_count": 0,
                    "success_rate": 0.0
                }
            },
            "error": error
        }