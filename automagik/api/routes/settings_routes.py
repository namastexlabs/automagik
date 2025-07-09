"""Settings API routes for application configuration management."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, status, Depends
from pydantic import BaseModel, Field

from automagik.auth import verify_api_key

from automagik.db.repository.settings import (
    create_setting,
    get_setting,
    get_setting_by_key,
    list_settings,
    update_setting,
    delete_setting,
    delete_setting_by_key,
    get_settings_by_category
)
from automagik.db.models import Setting, SettingCreate, SettingUpdate

# Create router for settings endpoints
settings_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)


# Response models
class SettingResponse(BaseModel):
    """Response model for setting operations."""
    id: str
    key: str
    value: str
    encrypted: bool
    description: Optional[str] = None
    category: str
    created_by: Optional[str] = None
    created_at: str
    updated_at: str


class SettingsListResponse(BaseModel):
    """Response model for listing settings."""
    settings: List[SettingResponse]
    total: int
    category: Optional[str] = None


class SettingCreateRequest(BaseModel):
    """Request model for creating settings."""
    key: str = Field(..., description="Unique setting key")
    value: str = Field(..., description="Setting value")
    encrypted: bool = Field(default=False, description="Whether to encrypt the value")
    description: Optional[str] = Field(None, description="Setting description")
    category: str = Field(default="general", description="Setting category")
    created_by: Optional[str] = Field(None, description="Creator identifier")


class SettingUpdateRequest(BaseModel):
    """Request model for updating settings."""
    value: Optional[str] = Field(None, description="Updated setting value")
    encrypted: Optional[bool] = Field(None, description="Updated encryption status")
    description: Optional[str] = Field(None, description="Updated description")
    category: Optional[str] = Field(None, description="Updated category")


@settings_router.get(
    "/settings",
    response_model=SettingsListResponse,
    tags=["Settings"],
    summary="List Settings",
    description="Get all settings with optional filtering by category or encryption status.\n\n**Requires Authentication**: This endpoint requires an API key."
)
async def list_settings_route(
    category: Optional[str] = Query(None, description="Filter by category"),
    exclude_encrypted: bool = Query(False, description="Exclude encrypted settings from results"),
    _: bool = Depends(verify_api_key)
):
    """Get a list of all settings with optional filtering."""
    try:
        settings = list_settings(category=category, exclude_encrypted=exclude_encrypted)
        
        setting_responses = [
            SettingResponse(
                id=setting.id,
                key=setting.key,
                value=setting.value if not setting.encrypted or not exclude_encrypted else "[ENCRYPTED]",
                encrypted=setting.encrypted,
                description=setting.description,
                category=setting.category,
                created_by=setting.created_by,
                created_at=setting.created_at.isoformat() if hasattr(setting.created_at, 'isoformat') else str(setting.created_at),
                updated_at=setting.updated_at.isoformat() if hasattr(setting.updated_at, 'isoformat') else str(setting.updated_at)
            )
            for setting in settings
        ]
        
        return SettingsListResponse(
            settings=setting_responses,
            total=len(setting_responses),
            category=category
        )
    
    except Exception as e:
        logger.error(f"Error listing settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings"
        )


@settings_router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    tags=["Settings"],
    summary="Get Setting by Key",
    description="Retrieve a specific setting by its key.\n\n**Requires Authentication**: This endpoint requires an API key."
)
async def get_setting_route(
    key: str = Path(..., description="The setting key"),
    _: bool = Depends(verify_api_key)
):
    """Get a setting by its key."""
    try:
        setting = get_setting_by_key(key)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with key '{key}' not found"
            )
        
        return SettingResponse(
            id=setting.id,
            key=setting.key,
            value=setting.value,
            encrypted=setting.encrypted,
            description=setting.description,
            category=setting.category,
            created_by=setting.created_by,
            created_at=setting.created_at.isoformat() if hasattr(setting.created_at, 'isoformat') else str(setting.created_at),
            updated_at=setting.updated_at.isoformat() if hasattr(setting.updated_at, 'isoformat') else str(setting.updated_at)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve setting"
        )


@settings_router.post(
    "/settings",
    response_model=SettingResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Settings"],
    summary="Create or Update Setting",
    description="Create a new setting or update an existing one (upsert behavior).\n\n**Requires Authentication**: This endpoint requires an API key."
)
async def create_setting_route(
    setting_request: SettingCreateRequest,
    _: bool = Depends(verify_api_key)
):
    """Create or update a setting."""
    try:
        # Validate category
        valid_categories = ['api_keys', 'urls', 'features', 'ui_config', 'general']
        if setting_request.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {valid_categories}"
            )
        
        # Create setting model
        setting_create = SettingCreate(
            key=setting_request.key,
            value=setting_request.value,
            encrypted=setting_request.encrypted,
            description=setting_request.description,
            category=setting_request.category,
            created_by=setting_request.created_by
        )
        
        # Create or update setting
        setting_id = create_setting(setting_create)
        
        # Retrieve the created/updated setting
        setting = get_setting(setting_id)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created setting"
            )
        
        return SettingResponse(
            id=setting.id,
            key=setting.key,
            value=setting.value,
            encrypted=setting.encrypted,
            description=setting.description,
            category=setting.category,
            created_by=setting.created_by,
            created_at=setting.created_at.isoformat() if hasattr(setting.created_at, 'isoformat') else str(setting.created_at),
            updated_at=setting.updated_at.isoformat() if hasattr(setting.updated_at, 'isoformat') else str(setting.updated_at)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create setting"
        )


@settings_router.put(
    "/settings/{key}",
    response_model=SettingResponse,
    tags=["Settings"],
    summary="Update Setting",
    description="Update an existing setting by its key.\n\n**Requires Authentication**: This endpoint requires an API key."
)
async def update_setting_route(
    setting_update: SettingUpdateRequest,
    key: str = Path(..., description="The setting key"),
    _: bool = Depends(verify_api_key)
):
    """Update a setting by its key."""
    try:
        # Get existing setting
        existing_setting = get_setting_by_key(key)
        if not existing_setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with key '{key}' not found"
            )
        
        # Validate category if provided
        if setting_update.category:
            valid_categories = ['api_keys', 'urls', 'features', 'ui_config', 'general']
            if setting_update.category not in valid_categories:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Must be one of: {valid_categories}"
                )
        
        # Create update model
        update_data = SettingUpdate(
            value=setting_update.value,
            encrypted=setting_update.encrypted,
            description=setting_update.description,
            category=setting_update.category
        )
        
        # Update setting
        success = update_setting(existing_setting.id, update_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update setting"
            )
        
        # Retrieve updated setting
        updated_setting = get_setting(existing_setting.id)
        if not updated_setting:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated setting"
            )
        
        return SettingResponse(
            id=updated_setting.id,
            key=updated_setting.key,
            value=updated_setting.value,
            encrypted=updated_setting.encrypted,
            description=updated_setting.description,
            category=updated_setting.category,
            created_by=updated_setting.created_by,
            created_at=updated_setting.created_at.isoformat() if hasattr(updated_setting.created_at, 'isoformat') else str(updated_setting.created_at),
            updated_at=updated_setting.updated_at.isoformat() if hasattr(updated_setting.updated_at, 'isoformat') else str(updated_setting.updated_at)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update setting"
        )


@settings_router.delete(
    "/settings/{key}",
    tags=["Settings"],
    summary="Delete Setting",
    description="Delete a setting by its key.\n\n**Requires Authentication**: This endpoint requires an API key."
)
async def delete_setting_route(
    key: str = Path(..., description="The setting key"),
    _: bool = Depends(verify_api_key)
):
    """Delete a setting by its key."""
    try:
        # Check if setting exists
        existing_setting = get_setting_by_key(key)
        if not existing_setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with key '{key}' not found"
            )
        
        # Delete setting
        success = delete_setting_by_key(key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete setting"
            )
        
        return {"success": True, "message": f"Setting '{key}' deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete setting"
        )