"""
Database models for the application.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UUID
from sqlalchemy.orm import relationship

from automagik.core.database.base import Base


class Flow(Base):
    """Flow model."""
    __tablename__ = "flows"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    data = Column(JSON)  # Additional flow data
    
    # Source system info
    source = Column(String(50), nullable=False)  # e.g., "langflow"
    source_id = Column(String(255), nullable=False)  # ID in the source system (UUID)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="flow")
    schedules = relationship("Schedule", back_populates="flow")
    components = relationship("FlowComponent", back_populates="flow")


class FlowComponent(Base):
    """Flow component model."""
    __tablename__ = "flow_components"

    id = Column(UUID(as_uuid=True), primary_key=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id"), nullable=False)
    
    # Component info
    component_id = Column(String(255), nullable=False)  # ID in source system (e.g., "ChatOutput-WHzRB")
    type = Column(String(50), nullable=False)
    template = Column(JSON)  # Component template/configuration
    tweakable_params = Column(JSON)  # Parameters that can be modified
    
    # Input/Output flags
    is_input = Column(Boolean, default=False)
    is_output = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    flow = relationship("Flow", back_populates="components")


class Task(Base):
    """Task model."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id"), nullable=False)
    
    # Execution info
    status = Column(String(50), nullable=False, default="pending")
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    error = Column(Text)
    
    # Retry info
    tries = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    # Relationships
    flow = relationship("Flow", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", order_by="TaskLog.created_at")


class TaskLog(Base):
    """Task execution log model."""
    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    
    # Log info
    level = Column(String(20), nullable=False)  # debug, info, warning, error
    message = Column(Text, nullable=False)
    component_id = Column(String(255))  # Which component generated this log
    data = Column(JSON)  # Additional log data/context
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="logs")


class Schedule(Base):
    """Schedule model."""
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id"), nullable=False)
    
    # Schedule info
    schedule_type = Column(String(50), nullable=False)  # cron, interval, etc.
    schedule_expr = Column(String(255), nullable=False)  # Cron expression or interval
    flow_params = Column(JSON)  # Parameters to pass to flow
    status = Column(String(50), nullable=False, default="active")
    
    # Next run tracking
    next_run_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    flow = relationship("Flow", back_populates="schedules")
