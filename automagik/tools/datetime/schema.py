"""Datetime tool schemas.

This module defines the Pydantic models for datetime tool input and output.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime as dt

class DatetimeInput(BaseModel):
    """Input for datetime tools."""
    format: Optional[str] = Field(None, description="Optional format string for date/time")

class DatetimeOutput(BaseModel):
    """Output from datetime tools."""
    result: str = Field(..., description="The formatted date or time string")
    timestamp: float = Field(..., description="Unix timestamp of when the result was generated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @classmethod
    def create(cls, result: str) -> "DatetimeOutput":
        """Create a standard output object.
        
        Args:
            result: The formatted date or time string
            
        Returns:
            A DatetimeOutput object
        """
        now = dt.now()
        return cls(
            result=result,
            timestamp=now.timestamp(),
            metadata={"datetime": now.isoformat()}
        ) 