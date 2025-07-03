"""Metrics collection and handling for Claude SDK Executor.

This module handles token counting, cost calculation, and tool usage tracking.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from ...db.repository.workflow_run import update_workflow_run_by_run_id
    from ...db.models import WorkflowRunUpdate
except ImportError:
    # Fallback for testing environments
    def update_workflow_run_by_run_id(run_id, data):
        return True
    class WorkflowRunUpdate:
        def __init__(self, **kwargs):
            pass

logger = logging.getLogger(__name__)


class MetricsHandler:
    """Handles comprehensive metrics collection and database persistence."""
    
    def __init__(self):
        self.tools_used: List[str] = []
        self.token_details: Dict[str, int] = {
            'total_tokens': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_created': 0,
            'cache_read': 0
        }
        self.total_cost: float = 0.0
        self.total_turns: int = 0
        self.final_metrics: Optional[Dict[str, Any]] = None
    
    def count_actual_turns(self, collected_messages) -> int:
        """Count actual turns based on AssistantMessage responses.
        
        Args:
            collected_messages: List of SDK messages
            
        Returns:
            Number of actual conversation turns
        """
        from claude_code_sdk import AssistantMessage
        
        turn_count = 0
        for message in collected_messages:
            if isinstance(message, AssistantMessage) and message.content:
                turn_count += 1
                logger.debug(f"SDK Executor: Counted turn {turn_count} from AssistantMessage")
        
        # Ensure at least 1 turn if we have any meaningful messages
        if turn_count == 0 and len(collected_messages) > 0:
            turn_count = 1
            logger.debug("SDK Executor: Set minimum 1 turn for non-empty message collection")
            
        return turn_count
    
    def extract_tools_from_messages(self, collected_messages) -> List[str]:
        """Extract tool usage from collected messages."""
        from claude_code_sdk import AssistantMessage, ToolUseBlock
        
        tools_used = []
        for message in collected_messages:
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        if block.name not in tools_used:
                            tools_used.append(block.name)
                            logger.debug(f"SDK Executor: Captured tool - {block.name}")
        
        # Fallback extraction if primary method fails
        if not tools_used and collected_messages:
            logger.warning("Primary tool extraction failed, trying fallback method")
            import re
            for message in collected_messages:
                msg_str = str(message)
                tool_matches = re.findall(r'ToolUse.*?name["\']?\s*:\s*["\']?(\w+)', msg_str)
                for tool_name in tool_matches:
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                        logger.info(f"SDK Executor: Fallback captured tool - {tool_name}")
        
        return tools_used
    
    def extract_final_metrics(self, collected_messages) -> Optional[Dict[str, Any]]:
        """Extract final metrics from ResultMessage or streaming data."""
        from claude_code_sdk import ResultMessage
        
        for message in collected_messages:
            if isinstance(message, ResultMessage):
                return {
                    'total_cost_usd': message.total_cost_usd or 0.0,
                    'num_turns': message.num_turns,
                    'duration_ms': getattr(message, 'duration_ms', 0),
                    'usage': getattr(message, 'usage', {}),
                    'is_error': getattr(message, 'is_error', False),
                    'result': getattr(message, 'result', ''),
                    'session_id': getattr(message, 'session_id', '')
                }
        return None
    
    def process_token_details(self, final_metrics: Dict[str, Any]) -> Dict[str, int]:
        """Process token usage details from final metrics."""
        if not final_metrics or not final_metrics.get('usage'):
            return self.token_details
        
        usage = final_metrics['usage']
        return {
            'total_tokens': (
                usage.get('input_tokens', 0) +
                usage.get('output_tokens', 0) +
                usage.get('cache_creation_input_tokens', 0) +
                usage.get('cache_read_input_tokens', 0)
            ),
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'cache_created': usage.get('cache_creation_input_tokens', 0),
            'cache_read': usage.get('cache_read_input_tokens', 0)
        }
    
    def update_metrics_from_messages(self, collected_messages, messages: List[str]) -> None:
        """Update all metrics from collected messages."""
        # Extract tools
        self.tools_used = self.extract_tools_from_messages(collected_messages)
        
        # Extract final metrics
        self.final_metrics = self.extract_final_metrics(collected_messages)
        
        if self.final_metrics:
            self.total_cost = self.final_metrics['total_cost_usd']
            self.total_turns = self.final_metrics['num_turns']
            self.token_details = self.process_token_details(self.final_metrics)
        
        # Count actual turns as fallback
        actual_turns = self.count_actual_turns(collected_messages)
        if self.total_turns == 0 and actual_turns > 0:
            self.total_turns = actual_turns
    
    async def persist_to_database(
        self, 
        run_id: str, 
        success: bool, 
        result_text: str, 
        execution_time: float,
        git_commits: List[str] = None
    ) -> bool:
        """Persist comprehensive metrics to workflow_runs database table."""
        if not run_id:
            logger.warning("No run_id available for database persistence")
            return False
        
        try:
            # Build comprehensive metadata
            metadata = {
                "total_turns": self.total_turns,
                "tools_used": self.tools_used,
                "tool_calls": len(self.tools_used),
                "success": success,
                "execution_time": execution_time,
                "git_commits": git_commits or [],
                "run_status": "completed" if success else "failed",
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Create update data with captured metrics
            update_data = WorkflowRunUpdate(
                status="completed" if success else "failed",
                cost_estimate=self.total_cost,
                input_tokens=self.token_details['input_tokens'],
                output_tokens=self.token_details['output_tokens'],
                total_tokens=self.token_details['total_tokens'],
                result=result_text,
                metadata=metadata,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                duration_seconds=int(execution_time)
            )
            
            # Update the workflow_runs table
            update_success = update_workflow_run_by_run_id(run_id, update_data)
            if update_success:
                logger.info(f"Persisted metrics to database for run {run_id}")
                logger.info(f"  - Cost: ${self.total_cost:.4f}")
                logger.info(f"  - Tokens: {self.token_details['total_tokens']} total")
                logger.info(f"  - Tools: {len(self.tools_used)} used")
                return True
            else:
                logger.warning(f"Failed to persist metrics to database for run {run_id}")
                return False
                
        except Exception as db_error:
            logger.error(f"Database persistence failed for run {run_id}: {db_error}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            'cost_usd': self.total_cost,
            'total_turns': self.total_turns,
            'tools_used': self.tools_used,
            'token_details': self.token_details,
            'tool_count': len(self.tools_used)
        }