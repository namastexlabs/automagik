"""
Flow synchronization module.

Handles synchronization of flows between LangFlow and Automagik.
Provides functionality for fetching, filtering, and syncing flows.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import LANGFLOW_API_URL, LANGFLOW_API_KEY
from ..database.models import Flow, FlowComponent, Task, TaskLog
from ..database.session import get_session

logger = logging.getLogger(__name__)


class FlowSync:
    """Flow synchronization class."""
    
    def __init__(self, session: AsyncSession):
        """Initialize flow sync."""
        self.session = session
        self._client = None
        self._base_url = None

    async def execute_flow(
        self,
        flow: Flow,
        task: Task,
        input_data: Dict[str, Any],
        debug: bool = True  # This parameter is kept for backward compatibility
    ) -> Dict[str, Any]:
        """Execute a flow with the given input data.
        
        Args:
            flow: Flow to execute
            task: Task being executed
            input_data: Input data for the flow
            debug: Whether to run in debug mode (always True)
        
        Returns:
            Dict containing the flow output
        """
        # Get the client
        client = await self._get_client()
        
        # Build API payload
        payload = {
            "input_value": input_data.get("input_value", ""),
            "output_type": "debug",
            "input_type": "chat",
            "tweaks": {
                flow.input_component: {},
                flow.output_component: {}
            }
        }
        
        try:
            # Update task status
            task.status = "running"
            task.started_at = datetime.utcnow()
            await self.session.commit()

            # Execute the flow
            logger.debug(f"Executing flow {flow.source_id} with input_data: {input_data}")
            logger.debug(f"API payload: {payload}")
            response = await client.post(
                f"/api/v1/run/{flow.source_id}?stream=false",
                json=payload,
                timeout=600  # 10 minutes
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                # Get error details from response
                error_content = response.text
                logger.error(f"LangFlow API error response: {error_content}")
                raise
                
            result = response.json()
            logger.debug(f"Flow execution result: {result}")

            # Update task with output
            if result.get("outputs"):
                output = result["outputs"][0]
                if "outputs" in output and output["outputs"]:
                    task.output_data = output["outputs"][0].get("outputs", {})
                else:
                    task.output_data = output

            # Update task status
            task.status = "completed"
            task.finished_at = datetime.utcnow()
            await self.session.commit()

            return task.output_data

        except Exception as e:
            import traceback
            # Log the error with a string representation of the traceback
            error_log = TaskLog(
                id=uuid4(),
                task_id=task.id,
                level="error",
                message=str(e),
                data={"traceback": "".join(traceback.format_tb(e.__traceback__))}
            )
            self.session.add(error_log)

            # Update task with error
            task.status = "failed"
            task.finished_at = datetime.utcnow()
            task.error = str(e)
            await self.session.commit()

            raise

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                'accept': 'application/json'
            }
            if LANGFLOW_API_KEY:
                headers["x-api-key"] = LANGFLOW_API_KEY
            logger.debug(f"Using LangFlow API URL: {self._get_base_url()}")
            logger.debug(f"Headers: {headers}")
            self._client = httpx.AsyncClient(
                base_url=self._get_base_url(),
                headers=headers,
                verify=False,
                timeout=30.0
            )
        return self._client

    def _get_base_url(self) -> str:
        """Get base URL for LangFlow API."""
        if self._base_url is None:
            self._base_url = LANGFLOW_API_URL
        return self._base_url

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
