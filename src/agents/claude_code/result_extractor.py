"""Result extraction for Claude Code workflows.

This module provides intelligent extraction of meaningful results from
Claude workflow execution logs and messages.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultExtractor:
    """Extracts meaningful final results from Claude workflow execution."""
    
    def __init__(self):
        """Initialize result extractor with compiled patterns for better performance."""
        # Compile regex patterns once for better performance
        self.completion_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r"## 🎯.*Complete.*Summary",
                r"## ✅.*Completed",
                r"## Summary",
                r"## Results",
                r"Task completed successfully",
                r"Implementation complete",
                r"All tests passing",
                r"Successfully",
                r"✅.*complete",
                r"✅.*success",
            ]
        ]
        
        self.error_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r"## ❌.*Error",
                r"## ⚠️.*Warning",
                r"Failed to",
                r"Error:",
                r"Exception:",
                r"FAILED",
                r"❌",
            ]
        ]
        
        self.max_turns_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r"max_turns",
                r"maximum turns",
                r"turn limit",
                r"reached.*limit",
                r"⏰.*turns",
            ]
        ]
        
        # Fast lookups for success indicators
        self.success_indicators: Set[str] = {
            "complete", "success", "done", "finished",
            "implemented", "fixed", "resolved", "working"
        }
        
        # Cache for expensive pattern matching
        self._pattern_cache: Dict[str, bool] = {}
        
        # Compiled file creation patterns for better performance
        self.file_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r'File created.*?: (.+\.py)',
                r'Created file: (.+)',
                r'Writing.*to (.+\.py)',
                r'Saved to (.+)'
            ]
        ]
    
    def extract_final_result(
        self,
        log_entries: List[Dict],
        messages: List[Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract meaningful final result from workflow execution.
        
        Args:
            log_entries: Raw log entries from log manager
            messages: Assistant messages from database
            metadata: Session metadata
            
        Returns:
            Dictionary with result information:
            - success: bool
            - completion_type: str
            - message: str
            - final_output: str
        """
        try:
            # Extract completion information
            completion_type = self._determine_completion_type(log_entries, metadata)
            final_message = self._get_last_substantial_message(messages, log_entries, metadata)
            success = self._is_successful_completion(completion_type, final_message)
            user_message = self._generate_user_message(completion_type, final_message)
            
            result = {
                "success": success,
                "completion_type": completion_type,
                "message": user_message,
                "final_output": final_message
            }
            
            logger.debug(f"Result extraction - metadata keys: {list(metadata.keys())}, completion_type: {completion_type}, success: {success}")
            logger.debug(f"Extracted result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting result: {e}")
            return {
                "success": False,
                "completion_type": "error",
                "message": "❌ Error extracting workflow results",
                "final_output": None
            }
    
    def _determine_completion_type(
        self,
        log_entries: List[Dict],
        metadata: Dict[str, Any]
    ) -> str:
        """Determine how the workflow completed.
        
        Args:
            log_entries: Log entries to analyze
            metadata: Session metadata
            
        Returns:
            Completion type string
        """
        # Check metadata first - it's the most reliable source
        success = metadata.get("success")
        if success is True:
            return "completed_successfully"
        elif success is False:
            return "failed"
        
        # Check run status in metadata FIRST (more reliable than other indicators)
        run_status = metadata.get("run_status", "").lower()
        if "completed" in run_status:
            return "completed_successfully"
        elif "failed" in run_status or "error" in run_status:
            return "failed"
        elif "running" in run_status:
            return "running"
        
        # Check for explicit completion indicators in metadata
        completed_at = metadata.get("completed_at")
        final_result = metadata.get("final_result")
        
        if completed_at and final_result:
            # If we have both completion time and final result, it's completed
            return "completed_successfully"
        
        # Check for max turns reached
        current_turns = metadata.get("current_turns", metadata.get("total_turns", 0))
        max_turns = metadata.get("max_turns")  # No default, unlimited if not specified
        
        if max_turns and current_turns >= max_turns:
            return "max_turns_reached"
        
        # Check run status in metadata
        run_status = metadata.get("run_status", "").lower()
        if "completed" in run_status:
            return "completed_successfully"
        elif "failed" in run_status or "error" in run_status:
            return "failed"
        elif "running" in run_status:
            return "running"
        
        # Fallback to log analysis for older workflows
        if log_entries:
            recent_logs = log_entries[-10:]
            recent_text = " ".join(str(entry) for entry in recent_logs)
            
            # Check for errors first
            if self._contains_pattern(recent_text, self.error_patterns):
                return "failed"
            
            # Check for explicit completion
            if self._contains_pattern(recent_text, self.completion_patterns):
                return "completed_successfully"
            
            # Check for max turns patterns in logs
            if self._contains_pattern(recent_text, self.max_turns_patterns):
                return "max_turns_reached"
        
        return "unknown"
    
    def _get_last_substantial_message(
        self,
        messages: List[Any],
        log_entries: List[Dict],
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Get the last substantial message from Claude.
        
        Args:
            messages: Assistant messages from database
            log_entries: Log entries to supplement
            metadata: Session metadata (primary source)
            
        Returns:
            Last substantial message text
        """
        # First try metadata - most reliable source
        if metadata:
            final_result = metadata.get("final_result")
            if final_result and isinstance(final_result, str) and len(final_result.strip()) > 50:
                return final_result.strip()
        
        # Try assistant messages from database
        if messages:
            for message in reversed(messages):
                content = getattr(message, 'content', '')
                if isinstance(content, str) and len(content.strip()) > 50:
                    # Filter out just tool calls
                    if not content.strip().startswith('```') and not all(
                        line.strip().startswith(('<', 'Tool:', 'Result:'))
                        for line in content.split('\n')
                        if line.strip()
                    ):
                        return content.strip()
        
        # Fallback to log entries
        for entry in reversed(log_entries[-20:] if log_entries else []):
            if isinstance(entry, dict):
                event_type = entry.get("event_type", "")
                data = entry.get("data", {})
                
                # Check Claude stream assistant messages
                if event_type == "claude_stream_assistant" and isinstance(data, dict):
                    message = data.get("message", {})
                    content = message.get("content", [])
                    
                    # Look for text content
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            if isinstance(text, str) and len(text.strip()) > 50:
                                return text.strip()
                
                # Look for other content in data
                elif isinstance(data, dict):
                    content = data.get('content', '')
                    if isinstance(content, str) and len(content.strip()) > 50:
                        return content.strip()
        
        return None
    
    def _is_successful_completion(
        self,
        completion_type: str,
        final_message: Optional[str]
    ) -> bool:
        """Determine if completion was successful.
        
        Args:
            completion_type: Type of completion
            final_message: Final message content
            
        Returns:
            True if successful completion
        """
        if completion_type == "failed":
            return False
        
        if completion_type == "completed_successfully":
            return True
        
        if completion_type == "max_turns_reached":
            # Check if final message indicates success despite max turns
            if final_message:
                final_lower = final_message.lower()
                # Use set intersection for O(1) lookups instead of O(n) iteration
                final_words = set(final_lower.split())
                return bool(final_words & self.success_indicators)
            return False
        
        return False  # unknown type
    
    def _generate_user_message(
        self,
        completion_type: str,
        final_output: Optional[str]
    ) -> str:
        """Generate user-friendly completion message.
        
        Args:
            completion_type: Type of completion
            final_output: Final output text
            
        Returns:
            User-friendly message
        """
        base_messages = {
            "completed_successfully": "✅ Workflow completed successfully",
            "max_turns_reached": "⏰ Reached maximum turns - workflow stopped at turn limit",
            "failed": "❌ Workflow failed with errors",
            "unknown": "⚠️ Workflow status unclear - check logs for details",
            "error": "❌ Error processing workflow results"
        }
        
        base_message = base_messages.get(completion_type, base_messages["unknown"])
        
        # Add context based on final output
        if final_output and len(final_output) > 100:
            final_lower = final_output.lower()
            
            if "test" in final_lower and "pass" in final_lower:
                base_message += " - Tests completed"
            elif "implement" in final_lower and ("complete" in final_lower or "done" in final_lower):
                base_message += " - Implementation finished"
            elif "fix" in final_lower and ("complete" in final_lower or "resolved" in final_lower):
                base_message += " - Fixes applied"
            elif "error" in final_lower or "fail" in final_lower:
                base_message = "⚠️ Workflow completed with issues - review results"
        
        return base_message
    
    def _contains_pattern(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text contains any of the given compiled patterns.
        
        Args:
            text: Text to search
            patterns: Compiled regex patterns to match
            
        Returns:
            True if any pattern matches
        """
        # Use cache for expensive pattern matching
        cache_key = f"{hash(text)}_{len(patterns)}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]
        
        result = any(pattern.search(text) for pattern in patterns)
        
        # Cache result but limit cache size to prevent memory issues
        if len(self._pattern_cache) < 1000:
            self._pattern_cache[cache_key] = result
        
        return result
    
    def extract_files_created(self, log_entries: List[Dict]) -> List[str]:
        """Extract list of files created during workflow.
        
        Args:
            log_entries: Log entries to analyze
            
        Returns:
            List of file paths created
        """
        # Use set for O(1) lookups to avoid duplicates, then convert to list
        files_created_set: Set[str] = set()
        
        for entry in log_entries:
            if isinstance(entry, dict):
                data = entry.get('data', {})
                
                # Look for file creation patterns
                if isinstance(data, dict):
                    # Tool usage data - direct lookup is faster
                    if data.get('tool_name') == 'Write':
                        input_data = data.get('input', {})
                        if isinstance(input_data, dict):
                            file_path = input_data.get('file_path')
                            if file_path:
                                files_created_set.add(file_path)
                
                # Look for file creation messages using compiled patterns
                content = str(data.get('content', ''))
                if content:  # Only process non-empty content
                    for pattern in self.file_patterns:
                        matches = pattern.findall(content)
                        files_created_set.update(matches)
        
        return list(files_created_set)