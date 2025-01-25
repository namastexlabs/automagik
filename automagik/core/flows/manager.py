"""
Flow management module.

Provides the main interface for managing flows, combining functionality
from flow_analyzer and flow_sync.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..config import LANGFLOW_API_URL
from ..database.models import Flow, FlowComponent, Schedule, Task
from ..database.session import get_session
from .sync import FlowSync

logger = logging.getLogger(__name__)


class FlowManager:
    """Flow management class."""
    
    def __init__(self, session: AsyncSession):
        """Initialize flow manager."""
        self.session = session
        self.flow_sync = FlowSync(session)

    async def list_remote_flows(self, include_examples: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """List flows from LangFlow.
        
        Args:
            include_examples: Whether to include example flows
            
        Returns:
            Dictionary of flow data dictionaries grouped by folder
        """
        # Get flows from LangFlow
        client = httpx.AsyncClient(base_url=LANGFLOW_API_URL)
        try:
            # Get folders first to identify examples folder
            folders_response = await client.get("/folders/")
            folders_response.raise_for_status()
            folders = folders_response.json()
            valid_folder_ids = {f["id"] for f in folders}
            folder_names = {f["id"]: f["name"] for f in folders}
            
            # Get flows
            response = await client.get("/flows/")
            response.raise_for_status()
            flows = response.json()
            
            # Filter out example flows (flows in folders that don't exist)
            if not include_examples:
                flows = [
                    f for f in flows 
                    if f.get("folder_id") in valid_folder_ids
                ]
                
            # Group flows by folder
            flows_by_folder = {}
            for flow in flows:
                folder_id = flow.get("folder_id")
                folder_name = folder_names.get(folder_id, "No Folder")
                if folder_name not in flows_by_folder:
                    flows_by_folder[folder_name] = []
                flows_by_folder[folder_name].append(flow)
                
            return flows_by_folder
            
        finally:
            await client.aclose()

    async def get_flow_components(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get components for a flow.
        
        Args:
            flow_id: Flow ID to get components for
            
        Returns:
            List of component data dictionaries
        """
        # Get flow data from LangFlow
        client = httpx.AsyncClient(base_url=LANGFLOW_API_URL)
        try:
            response = await client.get(f"/flows/{flow_id}")
            response.raise_for_status()
            flow_data = response.json()
            
            # Extract components
            components = []
            for node in flow_data.get("data", {}).get("nodes", []):
                if "data" not in node or "type" not in node["data"]:
                    continue
                    
                component = {
                    "id": node["id"],
                    "type": node["data"]["type"],
                    "name": node["data"].get("display_name", node["data"].get("node", {}).get("name", "Unknown"))
                }
                components.append(component)
            return components
        except Exception as e:
            logger.error(f"Error getting flow components: {e}")
            return []
        finally:
            await client.aclose()

    async def sync_flow(
        self,
        flow_id: str,
        input_component: str,
        output_component: str
    ) -> Optional[UUID]:
        """Sync a flow from LangFlow.
        
        Args:
            flow_id: Flow ID to sync
            input_component: Input component ID
            output_component: Output component ID
            
        Returns:
            UUID of created/updated flow if successful, None otherwise
        """
        # Get flow data from LangFlow
        client = httpx.AsyncClient(base_url=LANGFLOW_API_URL)
        try:
            response = await client.get(f"/flows/{flow_id}")
            response.raise_for_status()
            flow_data = response.json()
            
            # Create or update flow
            flow = Flow(
                id=uuid4(),
                name=flow_data.get("name", "Untitled Flow"),
                description=flow_data.get("description", ""),
                data=flow_data.get("data", {}),
                source="langflow",
                source_id=flow_id,
                flow_version=1,
                input_component=input_component,
                output_component=output_component,
                folder_id=flow_data.get("folder_id"),
                folder_name=flow_data.get("folder_name"),
                icon=flow_data.get("icon"),
                icon_bg_color=flow_data.get("icon_bg_color"),
                gradient=bool(flow_data.get("gradient", False)),
                liked=bool(flow_data.get("liked", False)),
                tags=flow_data.get("tags", [])
            )
            
            # Verify components exist
            components = await self.get_flow_components(flow_id)
            component_ids = {c["id"] for c in components}
            if input_component not in component_ids or output_component not in component_ids:
                logger.error(f"Invalid component IDs: {input_component}, {output_component}")
                # Still create the flow, just log the error
                pass
            
            # Save flow
            self.session.add(flow)
            await self.session.commit()
            await self.session.refresh(flow)
            return flow.id
            
        except Exception as e:
            logger.error(f"Error syncing flow: {e}")
            return None
        finally:
            await client.aclose()

    async def create_schedule(
        self,
        flow_id: UUID,
        schedule_type: str,
        schedule_expr: str,
        flow_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Schedule]:
        """Create a schedule for a flow.
        
        Args:
            flow_id: Flow ID to schedule
            schedule_type: Type of schedule (cron, interval)
            schedule_expr: Schedule expression
            flow_params: Parameters to pass to flow
            
        Returns:
            Created Schedule object if successful
        """
        try:
            schedule = Schedule(
                id=uuid4(),
                flow_id=flow_id,
                schedule_type=schedule_type,
                schedule_expr=schedule_expr,
                flow_params=flow_params or {},
                next_run_at=datetime.utcnow()  # TODO: Calculate based on schedule
            )
            
            self.session.add(schedule)
            await self.session.commit()
            await self.session.refresh(schedule)
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            return None

    async def run_flow(
        self,
        flow_id: UUID,
        input_data: Dict[str, Any]
    ) -> Optional[UUID]:
        """Run a flow with input data.
        
        Args:
            flow_id: Flow ID to run
            input_data: Input data for flow
            
        Returns:
            UUID of created task if successful
        """
        try:
            # Get flow
            result = await self.session.execute(
                select(Flow).where(Flow.id == flow_id)
            )
            flow = result.scalar_one()
            
            # Create task
            task = Task(
                id=uuid4(),
                flow_id=flow.id,
                status="pending",
                input_data=input_data,
                tries=0,
                max_retries=3
            )
            self.session.add(task)
            await self.session.commit()
            
            # Execute flow
            try:
                output = await self.flow_sync.execute_flow(
                    flow=flow,
                    task=task,
                    input_data=input_data,
                    debug=True
                )
                return task.id
                
            except Exception as e:
                logger.error(f"Error executing flow: {e}")
                task.status = "failed"
                task.error = str(e)
                await self.session.commit()
                return None
            
        except Exception as e:
            logger.error(f"Error running flow: {e}")
            return None

    async def list_schedules(self) -> List[Schedule]:
        """
        List all schedules from database.
        
        Returns:
            List of Schedule objects
        """
        result = await self.session.execute(
            select(Schedule)
            .options(joinedload(Schedule.flow))
            .order_by(Schedule.created_at)
        )
        return list(result.scalars().all())

    async def update_schedule_status(self, schedule_id: str, action: str) -> bool:
        """
        Update schedule status.
        
        Args:
            schedule_id: ID of schedule to update
            action: Action to perform (pause/resume/stop)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            status_map = {
                'pause': 'paused',
                'resume': 'active',
                'stop': 'stopped'
            }
            
            new_status = status_map.get(action)
            if not new_status:
                logger.error(f"Invalid action: {action}")
                return False
            
            result = await self.session.execute(
                select(Schedule)
                .where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return False
            
            schedule.status = new_status
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating schedule status: {str(e)}")
            await self.session.rollback()
            return False

    async def update_schedule_next_run(self, schedule_id: str, next_run: datetime) -> bool:
        """
        Update schedule next run time.
        
        Args:
            schedule_id: ID of schedule to update
            next_run: Next run time
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.session.execute(
                select(Schedule)
                .where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return False
            
            # Ensure next_run is timezone-aware
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=datetime.utcnow().tzinfo)
            
            schedule.next_run_at = next_run
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating schedule next run: {str(e)}")
            await self.session.rollback()
            return False

    async def list_tasks(
        self,
        flow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Task]:
        """
        List tasks from database.
        
        Args:
            flow_id: Optional flow ID to filter by
            status: Optional status to filter by
            limit: Maximum number of tasks to return
            
        Returns:
            List of Task objects
        """
        query = select(Task).options(
            joinedload(Task.flow)
        ).order_by(Task.created_at.desc())
        
        if flow_id:
            query = query.where(Task.flow_id == flow_id)
        if status:
            query = query.where(Task.status == status)
            
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of task to get
            
        Returns:
            Task object if found, None otherwise
        """
        result = await self.session.execute(
            select(Task)
            .options(
                joinedload(Task.flow)
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def retry_task(self, task_id: str) -> Optional[Task]:
        """
        Retry a failed task.
        
        Args:
            task_id: ID of task to retry
            
        Returns:
            New Task object if successful, None otherwise
        """
        try:
            # Get original task
            original_task = await self.get_task(task_id)
            if not original_task:
                logger.error(f"Task {task_id} not found")
                return None
                
            if original_task.status != 'failed':
                logger.error(f"Can only retry failed tasks")
                return None
                
            # Create new task
            new_task = Task(
                id=uuid4(),
                flow_id=original_task.flow_id,
                schedule_id=original_task.schedule_id,
                status='pending',
                input_data=original_task.input_data,
                created_at=datetime.utcnow(),
                max_retries=original_task.max_retries,
                tries=0  # Reset tries count for the new task
            )
            
            self.session.add(new_task)
            await self.session.commit()
            await self.session.refresh(new_task)
            
            return new_task
            
        except Exception as e:
            logger.error(f"Error retrying task: {str(e)}")
            await self.session.rollback()
            return None

    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a flow by ID."""
        try:
            flow = await self.session.get(Flow, flow_id)
            return flow
        except Exception as e:
            logger.error(f"Failed to get flow: {str(e)}")
            return None

    async def list_flows(self) -> List[Flow]:
        """
        List all flows from the local database.
        
        Returns:
            List of Flow objects
        """
        result = await self.session.execute(
            select(Flow)
            .options(joinedload(Flow.schedules))
            .order_by(Flow.name)
        )
        return list(result.scalars().unique().all())

    async def delete_flow(self, flow_id: str) -> bool:
        """Delete a flow from local database.
        
        Args:
            flow_id: ID of the flow to delete (can be full UUID or truncated)
            
        Returns:
            True if flow was deleted successfully from local database
        """
        try:
            # Try exact match first (for full UUID)
            try:
                uuid_obj = UUID(flow_id)
                exact_match = True
            except ValueError:
                exact_match = False
            
            # Build query based on match type
            query = select(Flow).options(
                joinedload(Flow.components),
                joinedload(Flow.schedules),
                joinedload(Flow.tasks)
            )
            
            if exact_match:
                query = query.where(Flow.id == uuid_obj)
            else:
                query = query.where(cast(Flow.id, String).like(f"{flow_id}%"))
            
            # Execute query
            result = await self.session.execute(query)
            flow = result.unique().scalar_one_or_none()
            
            if not flow:
                logger.error(f"Flow {flow_id} not found in local database")
                return False
            
            # Delete all related objects first
            for component in flow.components:
                await self.session.delete(component)
            for schedule in flow.schedules:
                await self.session.delete(schedule)
            for task in flow.tasks:
                await self.session.delete(task)
            
            # Now delete the flow
            await self.session.delete(flow)
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting flow: {e}")
            await self.session.rollback()
            return False

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a schedule.
        
        Args:
            schedule_id: ID of schedule to delete
            
        Returns:
            True if schedule was deleted successfully
        """
        try:
            result = await self.session.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return False
            
            await self.session.delete(schedule)
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            return False

    async def get_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """Get a schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule if found, None otherwise
        """
        result = await self.session.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        return result.scalar_one_or_none()
