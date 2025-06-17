"""Claude Code API client for workflow execution."""

import asyncio
from typing import Dict, Any, Optional
from httpx import AsyncClient, HTTPError
from ..models import WorkflowType, ClaudeCodeRequest, ClaudeCodeResponse, EpicState
import logging

logger = logging.getLogger(__name__)


class ClaudeCodeClient:
    """Client for executing workflows via Claude Code API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the Claude Code API client.
        
        Args:
            base_url: Base URL for the API
        """
        self.base_url = base_url.rstrip("/")
        self.client = AsyncClient(timeout=300.0)  # 5 minute timeout for long workflows
        
    async def execute_workflow(
        self, 
        workflow_name: str,
        task_context: str,
        epic_state: EpicState,
        max_turns: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a workflow via Claude Code API.
        
        Args:
            workflow_name: Name of the workflow to execute
            task_context: Task description for the workflow
            epic_state: Current epic state
            max_turns: Maximum conversation turns
            
        Returns:
            Workflow execution result
        """
        # Prepare the request
        request = ClaudeCodeRequest(
            workflow=WorkflowType(workflow_name),
            message=task_context,
            session_id=f"{epic_state['epic_id']}-{workflow_name}",
            config={
                "max_turns": max_turns,
                "git_branch": f"genie/{epic_state['epic_id']}/{workflow_name}",
                "epic_context": {
                    "epic_id": epic_state["epic_id"],
                    "title": epic_state["epic_title"],
                    "previous_workflows": epic_state["completed_workflows"],
                    "workflow_results": epic_state["workflow_results"]
                }
            }
        )
        
        try:
            # Start workflow execution
            logger.info(f"Starting {workflow_name} workflow for epic {epic_state['epic_id']}")
            response = await self.client.post(
                f"{self.base_url}/api/v1/workflows/claude-code/run/{workflow_name}",
                json=request.model_dump()
            )
            response.raise_for_status()
            
            initial_response = ClaudeCodeResponse(**response.json())
            run_id = initial_response.run_id
            
            # Poll for completion
            result = await self._poll_for_completion(run_id, workflow_name)
            
            # Extract relevant information
            return {
                "status": result.status,
                "container_id": result.container_id,
                "cost_usd": result.cost_usd,
                "result": result.result or {},
                "error": result.error,
                "summary": result.result.get("summary", "") if result.result else "",
                "git_commits": result.result.get("git_commits", []) if result.result else [],
                "files_changed": result.result.get("files_changed", []) if result.result else []
            }
            
        except HTTPError as e:
            logger.error(f"HTTP error executing {workflow_name}: {e}")
            return {
                "status": "failed",
                "error": f"HTTP error: {str(e)}",
                "cost_usd": 0.0
            }
        except Exception as e:
            logger.error(f"Error executing {workflow_name}: {e}")
            return {
                "status": "failed", 
                "error": str(e),
                "cost_usd": 0.0
            }
            
    async def _poll_for_completion(
        self, 
        run_id: str, 
        workflow_name: str,
        poll_interval: float = 5.0,
        max_wait_time: float = 3600.0  # 1 hour max
    ) -> ClaudeCodeResponse:
        """Poll for workflow completion.
        
        Args:
            run_id: The run ID to poll
            workflow_name: Name of the workflow
            poll_interval: Seconds between polls
            max_wait_time: Maximum time to wait
            
        Returns:
            Final workflow response
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                logger.error(f"Workflow {workflow_name} timed out after {elapsed:.1f}s")
                return ClaudeCodeResponse(
                    run_id=run_id,
                    status="timeout",
                    error="Workflow execution timed out"
                )
            
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v1/workflows/claude-code/run/{run_id}/status"
                )
                response.raise_for_status()
                
                status_response = ClaudeCodeResponse(**response.json())
                
                if status_response.status in ["completed", "failed", "timeout"]:
                    logger.info(
                        f"Workflow {workflow_name} finished with status: {status_response.status}"
                    )
                    return status_response
                
                # Log progress
                if elapsed % 30 < poll_interval:  # Log every 30 seconds
                    logger.info(f"Workflow {workflow_name} still running... ({elapsed:.0f}s)")
                
            except Exception as e:
                logger.error(f"Error polling status for {workflow_name}: {e}")
                # Continue polling on transient errors
                
            await asyncio.sleep(poll_interval)
            
    async def get_workflow_logs(self, run_id: str) -> Optional[str]:
        """Get logs from a workflow run via status endpoint.
        
        Args:
            run_id: The run ID
            
        Returns:
            Container logs or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/workflows/claude-code/run/{run_id}/status"
            )
            response.raise_for_status()
            return response.json().get("logs", "")
        except Exception as e:
            logger.error(f"Error fetching logs for run {run_id}: {e}")
            return None
            
    async def stop_workflow(self, run_id: str) -> bool:
        """Stop a running workflow.
        
        Note: Stop endpoint is not currently implemented in the Claude Code API.
        
        Args:
            run_id: The run ID to stop
            
        Returns:
            False - stopping workflows is not currently supported
        """
        logger.warning(f"Stop workflow requested for {run_id} but stop endpoint not implemented")
        return False
            
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()