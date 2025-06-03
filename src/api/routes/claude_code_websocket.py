"""WebSocket endpoints for Claude Code real-time streaming.

This module provides WebSocket endpoints for streaming Claude CLI execution
output in real-time.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from websockets.exceptions import ConnectionClosed

from src.agents.models.agent_factory import AgentFactory
from src.agents.claude_code.cli_executor import ClaudeCLIExecutor
from src.db.repository import session as session_repo

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
ws_router = APIRouter(prefix="/agent/claude-code/ws", tags=["Claude-Code WebSocket"])

# Track active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = set()
        self.active_connections[run_id].add(websocket)
        logger.info(f"WebSocket connected for run {run_id}")
    
    def disconnect(self, websocket: WebSocket, run_id: str):
        """Remove a WebSocket connection."""
        if run_id in self.active_connections:
            self.active_connections[run_id].discard(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        logger.info(f"WebSocket disconnected for run {run_id}")
    
    async def send_message(self, run_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a run."""
        if run_id in self.active_connections:
            # Send to all connected clients for this run
            disconnected = set()
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except (WebSocketDisconnect, ConnectionClosed):
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, run_id)
    
    async def broadcast_claude_message(self, run_id: str, claude_message: Dict[str, Any]):
        """Broadcast a Claude CLI streaming message."""
        # Add metadata
        message = {
            "type": "claude_stream",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": claude_message
        }
        await self.send_message(run_id, message)


# Global connection manager
manager = ConnectionManager()


@ws_router.websocket("/stream/{run_id}")
async def websocket_stream(
    websocket: WebSocket,
    run_id: str,
    api_key: Optional[str] = Query(None)
):
    """WebSocket endpoint for streaming Claude CLI output.
    
    Args:
        websocket: WebSocket connection
        run_id: Run ID to stream
        api_key: API key for authentication
    """
    # Verify API key
    if not api_key:
        await websocket.close(code=1008, reason="API key required")
        return
    
    # TODO: Properly verify API key
    # For now, we'll just check if it's provided
    
    await manager.connect(websocket, run_id)
    
    try:
        # Send initial connection message
        await manager.send_message(run_id, {
            "type": "connection",
            "status": "connected",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for messages from client (mainly for ping/pong)
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for run {run_id}: {e}")
                break
                
    finally:
        manager.disconnect(websocket, run_id)


async def stream_claude_output(run_id: str, message: Dict[str, Any]):
    """Stream Claude CLI output to WebSocket clients.
    
    This function is called by the CLI executor to stream messages.
    
    Args:
        run_id: Run ID
        message: Claude CLI JSON message
    """
    await manager.broadcast_claude_message(run_id, message)


# Export for use in CLI executor
__all__ = ['ws_router', 'stream_claude_output']