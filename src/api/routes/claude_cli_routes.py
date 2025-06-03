"""API routes for Claude CLI workflow orchestration."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from ...auth import verify_api_key_ws, verify_api_key
from ...db.connection import Database
from ...db.repository.claude_cli import ClaudeCLIRepository
from ...agents.claude_code.cli_environment import CLIEnvironmentManager
from ...agents.claude_code.cli_executor import ClaudeCLIExecutor, ClaudeSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/claude-code", tags=["claude-cli"])

# Global instances (in production, these would be dependency injected)
environment_manager = CLIEnvironmentManager()
cli_executor = ClaudeCLIExecutor()

# Active WebSocket connections for streaming
active_connections: Dict[str, List[WebSocket]] = {}


class WorkflowType(str):
    """Valid workflow types."""
    ARCHITECT = "architect"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    DOCUMENT = "document"
    FIX = "fix"
    REFACTOR = "refactor"
    PR = "pr"


class RunWorkflowRequest(BaseModel):
    """Request to run a Claude Code workflow."""
    branch: str = Field(..., description="Git branch to checkout")
    message: str = Field(..., description="User message/prompt")
    max_turns: int = Field(2, description="Maximum conversation turns")
    session_id: Optional[str] = Field(None, description="Resume existing session")
    stream: bool = Field(True, description="Enable streaming output")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RunWorkflowResponse(BaseModel):
    """Response from workflow execution."""
    run_id: str
    session_id: Optional[str]
    status: str
    stream_url: Optional[str]
    workspace_path: Optional[str]


class RunStatus(BaseModel):
    """Run status information."""
    run_id: str
    session_id: Optional[str]
    status: str
    progress: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    started_at: str
    completed_at: Optional[str]
    execution_time_seconds: Optional[float]


@router.post("/{workflow_name}/run", response_model=RunWorkflowResponse)
async def run_workflow(
    workflow_name: WorkflowType,
    request: RunWorkflowRequest,
    api_key: str = Depends(verify_api_key),
    db: Database = Depends(Database.get_db)
) -> RunWorkflowResponse:
    """Execute a Claude Code workflow.
    
    Args:
        workflow_name: Workflow to execute
        request: Execution request details
        api_key: API authentication
        db: Database connection
        
    Returns:
        Workflow execution details
    """
    try:
        # Create repository instance
        repo = ClaudeCLIRepository(db)
        
        # Extract user/agent context from API key
        # (In production, this would be properly implemented)
        user_id = None  # TODO: Extract from api_key
        agent_id = None  # TODO: Extract from api_key
        
        # Create run record
        run = await repo.create_run(
            workflow_name=workflow_name,
            branch=request.branch,
            user_id=user_id,
            agent_id=agent_id,
            metadata={
                "message": request.message,
                "max_turns": request.max_turns,
                "session_id": request.session_id,
                "stream": request.stream,
                **(request.metadata or {})
            }
        )
        
        run_id = run['run_id']
        
        # Update status to running
        await repo.update_run(UUID(run_id), status='running')
        
        # Start async task for execution
        asyncio.create_task(
            _execute_workflow(
                run_id=run_id,
                workflow_name=workflow_name,
                request=request,
                repo=repo
            )
        )
        
        # Prepare response
        stream_url = f"/api/v1/agent/claude-code/run/{run_id}/stream" if request.stream else None
        
        return RunWorkflowResponse(
            run_id=run_id,
            session_id=request.session_id,
            status='running',
            stream_url=stream_url,
            workspace_path=None  # Will be updated during execution
        )
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/{run_id}/status", response_model=RunStatus)
async def get_run_status(
    run_id: str,
    api_key: str = Depends(verify_api_key),
    db: Database = Depends(Database.get_db)
) -> RunStatus:
    """Get workflow run status.
    
    Args:
        run_id: Run identifier
        api_key: API authentication
        db: Database connection
        
    Returns:
        Run status information
    """
    try:
        repo = ClaudeCLIRepository(db)
        
        # Get run record
        run = await repo.get_run(UUID(run_id))
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get latest outputs for progress
        outputs = await repo.get_outputs(UUID(run_id), limit=10)
        
        # Calculate progress
        progress = {
            "turns_completed": len([o for o in outputs if o.get('output_type') == 'result']),
            "max_turns": run['metadata'].get('max_turns', 2),
            "last_output": outputs[-1]['content'] if outputs else None
        }
        
        # Prepare result if completed
        result = None
        if run['status'] == 'completed':
            # Get final result from outputs
            result_outputs = [o for o in outputs if o['output_type'] == 'result']
            if result_outputs:
                result = result_outputs[-1]['content']
        
        return RunStatus(
            run_id=run_id,
            session_id=run.get('session_id'),
            status=run['status'],
            progress=progress,
            result=result,
            error=run.get('error_message'),
            started_at=run['started_at'],
            completed_at=run.get('completed_at'),
            execution_time_seconds=run.get('execution_time_seconds')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/run/{run_id}/stream")
async def stream_output(
    websocket: WebSocket,
    run_id: str,
    api_key: str = Depends(verify_api_key_ws)
):
    """WebSocket endpoint for streaming output.
    
    Args:
        websocket: WebSocket connection
        run_id: Run identifier
        api_key: API authentication
    """
    await websocket.accept()
    
    # Add to active connections
    if run_id not in active_connections:
        active_connections[run_id] = []
    active_connections[run_id].append(websocket)
    
    try:
        # Keep connection alive until run completes
        while True:
            # Check if client is still connected
            if websocket.client_state != WebSocketState.CONNECTED:
                break
                
            # Send heartbeat
            try:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                break
                
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove from active connections
        if run_id in active_connections:
            active_connections[run_id].remove(websocket)
            if not active_connections[run_id]:
                del active_connections[run_id]


@router.get("/runs", response_model=List[Dict[str, Any]])
async def list_runs(
    workflow_name: Optional[str] = None,
    status: Optional[str] = None,
    branch: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    api_key: str = Depends(verify_api_key),
    db: Database = Depends(Database.get_db)
) -> List[Dict[str, Any]]:
    """List Claude CLI runs with filters.
    
    Args:
        workflow_name: Filter by workflow
        status: Filter by status
        branch: Filter by branch
        limit: Maximum results
        offset: Results offset
        api_key: API authentication
        db: Database connection
        
    Returns:
        List of run records
    """
    try:
        repo = ClaudeCLIRepository(db)
        
        runs = await repo.list_runs(
            workflow_name=workflow_name,
            status=status,
            branch=branch,
            limit=limit,
            offset=offset
        )
        
        return runs
        
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    api_key: str = Depends(verify_api_key),
    db: Database = Depends(Database.get_db)
) -> Dict[str, str]:
    """Cancel a running workflow.
    
    Args:
        run_id: Run identifier
        api_key: API authentication
        db: Database connection
        
    Returns:
        Cancellation status
    """
    try:
        repo = ClaudeCLIRepository(db)
        
        # Get run record
        run = await repo.get_run(UUID(run_id))
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        if run['status'] not in ['queued', 'running']:
            raise HTTPException(status_code=400, detail=f"Cannot cancel run in {run['status']} state")
        
        # Cancel execution
        cancelled = await cli_executor.cancel_execution(run_id)
        
        if cancelled:
            # Update database
            await repo.update_run(
                UUID(run_id),
                status='cancelled',
                error_message='Cancelled by user'
            )
            
            # Cleanup workspace
            if run.get('workspace_path'):
                await environment_manager.cleanup(Path(run['workspace_path']))
            
            return {"status": "cancelled", "run_id": run_id}
        else:
            return {"status": "not_found", "run_id": run_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_workflow(
    run_id: str,
    workflow_name: str,
    request: RunWorkflowRequest,
    repo: ClaudeCLIRepository
) -> None:
    """Execute workflow asynchronously.
    
    Args:
        run_id: Run identifier
        workflow_name: Workflow to execute
        request: Execution request
        repo: Database repository
    """
    start_time = datetime.utcnow()
    workspace_path = None
    
    try:
        # Create workspace
        workspace_path = await environment_manager.create_workspace(run_id)
        
        # Update run with workspace path
        await repo.update_run(UUID(run_id), workspace_path=str(workspace_path))
        
        # Setup repository
        await environment_manager.setup_repository(workspace_path, request.branch)
        
        # Copy configurations
        await environment_manager.copy_configs(workspace_path, workflow_name)
        
        # Create streaming callback
        sequence_number = 0
        
        async def stream_callback(message: Dict[str, Any]):
            nonlocal sequence_number
            
            # Save to database
            await repo.save_output(
                run_id=UUID(run_id),
                output_type=message.get('type', 'text'),
                content=message,
                sequence_number=sequence_number
            )
            sequence_number += 1
            
            # Stream to WebSocket connections
            if run_id in active_connections:
                for ws in active_connections[run_id]:
                    try:
                        await ws.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send to WebSocket: {e}")
        
        # Execute CLI
        result = await cli_executor.execute(
            workflow=workflow_name,
            message=request.message,
            workspace=workspace_path,
            session_id=request.session_id,
            max_turns=request.max_turns,
            stream_callback=stream_callback if request.stream else None
        )
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Update run with results
        await repo.update_run(
            UUID(run_id),
            status='completed' if result.success else 'failed',
            session_id=result.session_id,
            exit_code=result.exit_code,
            execution_time_seconds=execution_time,
            error_message=result.error if not result.success else None,
            metadata_update={
                'git_commits': result.git_commits,
                'final_result': result.result
            }
        )
        
        # Create/update session if successful
        if result.success and result.session_id:
            await repo.create_session(
                session_id=result.session_id,
                run_id=UUID(run_id),
                workflow_name=workflow_name,
                max_turns=request.max_turns
            )
        
        # Send completion message to WebSocket
        if run_id in active_connections:
            completion_message = {
                "type": "completion",
                "success": result.success,
                "session_id": result.session_id,
                "result": result.result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for ws in active_connections[run_id]:
                try:
                    await ws.send_json(completion_message)
                except Exception as e:
                    logger.error(f"Failed to send completion: {e}")
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        
        # Update run with error
        await repo.update_run(
            UUID(run_id),
            status='failed',
            error_message=str(e),
            execution_time_seconds=(datetime.utcnow() - start_time).total_seconds()
        )
        
        # Send error to WebSocket
        if run_id in active_connections:
            error_message = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for ws in active_connections[run_id]:
                try:
                    await ws.send_json(error_message)
                except Exception:
                    pass
    
    finally:
        # Cleanup workspace if configured
        if workspace_path and environment_manager.cleanup_on_complete:
            await environment_manager.cleanup(workspace_path)
        
        # Close WebSocket connections
        if run_id in active_connections:
            for ws in active_connections[run_id]:
                try:
                    await ws.close()
                except Exception:
                    pass
            del active_connections[run_id]