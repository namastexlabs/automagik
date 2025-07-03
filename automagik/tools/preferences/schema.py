"""
Preference Tool Schemas

[EPIC-SIMULATION-TEST]
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum


class PreferenceCategory(str, Enum):
    """Valid preference categories"""
    UI = "ui"
    NOTIFICATIONS = "notifications"
    BEHAVIOR = "behavior"
    LANGUAGE = "language"
    PRIVACY = "privacy"
    ACCESSIBILITY = "accessibility"


class PreferenceInput(BaseModel):
    """Input schema for preference operations"""
    user_id: str = Field(..., description="User ID")
    category: PreferenceCategory = Field(..., description="Preference category")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Preference values")


class PreferenceOutput(BaseModel):
    """Output schema for preference operations"""
    success: bool
    user_id: str
    category: Optional[PreferenceCategory] = None
    preferences: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None


class PreferenceList(BaseModel):
    """Schema for listing all user preferences"""
    user_id: str
    preferences: Dict[PreferenceCategory, Dict[str, Any]]
    total_categories: int