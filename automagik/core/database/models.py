"""
Database models for the application.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UUID
from sqlalchemy.orm import relationship

from automagik.core.database.base import Base


def utcnow():
    """Return current UTC datetime with timezone."""
    return datetime.now(timezone.utc)


class Workflow(Base):
    """Workflow model."""
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    data = Column(JSON)  # Additional workflow data
    
    # Source system info
    source = Column(String(50), nullable=False)  # e.g., "langflow"
    remote_flow_id = Column(String(255), nullable=False)  # ID of the remote flow (UUID)
    flow_version = Column(Integer, default=1)
    
    # Component info
    input_component = Column(String(255))  # Component ID in source system
    output_component = Column(String(255))  # Component ID in source system
    is_component = Column(Boolean, default=False)
    
    # Metadata
    folder_id = Column(String(255))
    folder_name = Column(String(255))
    icon = Column(String(255))
    icon_bg_color = Column(String(50))
    gradient = Column(Boolean, default=False)
    liked = Column(Boolean, default=False)
    tags = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="workflow")
    schedules = relationship("Schedule", back_populates="workflow")
    components = relationship("WorkflowComponent", back_populates="workflow")

    def __str__(self):
        """Return a string representation of the workflow."""
        return f"{self.name} ({self.id})"


class WorkflowComponent(Base):
    """Workflow component model."""
    __tablename__ = "workflow_components"

    id = Column(UUID(as_uuid=True), primary_key=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    
    # Component info
    component_id = Column(String(255), nullable=False)  # ID in source system (e.g., "ChatOutput-WHzRB")
    type = Column(String(50), nullable=False)
    template = Column(JSON)  # Component template/configuration
    tweakable_params = Column(JSON)  # Parameters that can be modified
    
    # Input/Output flags
    is_input = Column(Boolean, default=False)
    is_output = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="components")


class Task(Base):
    """Task model."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    
    # Execution info
    status = Column(String(50), nullable=False, default="pending")
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    error = Column(Text)
    
    # Retry info
    tries = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

    # Relationships
    workflow = relationship("Workflow", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", order_by="TaskLog.created_at")


class TaskLog(Base):
    """Task log entry."""

    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    component_id = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    task = relationship("Task", back_populates="logs")


class Schedule(Base):
    """Schedule model."""
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    schedule_type = Column(String, nullable=False)
    schedule_expr = Column(String, nullable=False)
    workflow_params = Column(JSON, nullable=True)
    params = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="active")
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="schedules")

    def __str__(self):
        """Return a string representation of the schedule."""
        return f"{self.schedule_type}:{self.schedule_expr} ({self.id})"


class Worker(Base):
    """Worker model."""
    __tablename__ = "workers"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hostname = Column(String(255), nullable=False)
    pid = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="active")  # active, paused, stopped
    current_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    stats = Column(JSON)  # Worker statistics
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_heartbeat = Column(DateTime(timezone=True))

    # Relationships
    current_task = relationship("Task")
