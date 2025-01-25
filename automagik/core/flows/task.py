"""Task management module."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..database.models import Task, Flow
from .sync import FlowSync

logger = logging.getLogger(__name__)

class TaskManager:
    """Task management class."""
    
    def __init__(self, session: AsyncSession):
        """Initialize task manager."""
        self.session = session
        self.flow_sync = FlowSync(session)

    async def run_flow(
        self,
        flow_id: UUID,
        input_data: Dict[str, Any]
    ) -> Optional[UUID]:
        """Run a flow with input data."""
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

    async def list_tasks(
        self,
        flow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Task]:
        """List tasks from database."""
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
        """Get a task by ID."""
        result = await self.session.execute(
            select(Task)
            .options(
                joinedload(Task.flow)
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def retry_task(self, task_id: str) -> Optional[Task]:
        """Retry a failed task."""
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
