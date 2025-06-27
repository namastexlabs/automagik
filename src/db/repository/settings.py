"""Repository for settings database operations."""

import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..models import Setting, SettingCreate, SettingUpdate
from ..connection import execute_query

logger = logging.getLogger(__name__)


def create_setting(setting: SettingCreate) -> str:
    """Create or update a setting (upsert behavior).
    
    Args:
        setting: SettingCreate model with setting data
        
    Returns:
        str: The UUID of the created/updated setting
        
    Raises:
        DatabaseError: If database operation fails
    """
    # Check if setting with this key already exists
    existing = get_setting_by_key(setting.key)
    if existing:
        # Update existing setting
        update_data = SettingUpdate(
            value=setting.value,
            encrypted=setting.encrypted,
            description=setting.description,
            category=setting.category
        )
        success = update_setting(existing.id, update_data)
        if success:
            return existing.id
        else:
            raise RuntimeError(f"Failed to update existing setting: {setting.key}")
    
    # Create new setting
    setting_id = str(uuid.uuid4())
    
    query = """
        INSERT INTO settings (
            id, key, value, encrypted, description, category, 
            created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        setting_id,
        setting.key,
        setting.value,
        1 if setting.encrypted else 0,
        setting.description,
        setting.category,
        setting.created_by,
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    )
    
    execute_query(query, params)
    return setting_id


def get_setting(setting_id: str) -> Optional[Setting]:
    """Get setting by ID.
    
    Args:
        setting_id: UUID string of the setting
        
    Returns:
        Setting model or None if not found
    """
    query = """
        SELECT id, key, value, encrypted, description, category,
               created_by, created_at, updated_at
        FROM settings 
        WHERE id = ?
    """
    
    result = execute_query(query, (setting_id,), fetch=True)
    if not result:
        return None
    
    return Setting.from_db_row(result[0])


def get_setting_by_key(key: str) -> Optional[Setting]:
    """Get setting by key.
    
    Args:
        key: Setting key
        
    Returns:
        Setting model or None if not found
    """
    query = """
        SELECT id, key, value, encrypted, description, category,
               created_by, created_at, updated_at
        FROM settings 
        WHERE key = ?
    """
    
    result = execute_query(query, (key,), fetch=True)
    if not result:
        return None
    
    return Setting.from_db_row(result[0])


def list_settings(
    category: Optional[str] = None,
    exclude_encrypted: bool = False
) -> List[Setting]:
    """List all settings with optional filtering.
    
    Args:
        category: Optional category filter
        exclude_encrypted: If True, exclude encrypted settings from results
        
    Returns:
        List of Setting models
    """
    where_conditions = []
    params = []
    
    if category:
        where_conditions.append("category = ?")
        params.append(category)
    
    if exclude_encrypted:
        where_conditions.append("encrypted = 0")
    
    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    
    query = f"""
        SELECT id, key, value, encrypted, description, category,
               created_by, created_at, updated_at
        FROM settings 
        {where_clause}
        ORDER BY category, key
    """
    
    result = execute_query(query, params, fetch=True)
    if not result:
        return []
    
    settings = []
    for row in result:
        setting = Setting.from_db_row(row)
        settings.append(setting)
    
    return settings


def update_setting(setting_id: str, update_data: SettingUpdate) -> bool:
    """Update an existing setting.
    
    Args:
        setting_id: UUID string of the setting
        update_data: SettingUpdate model with updated fields
        
    Returns:
        bool: True if update successful, False if setting not found
    """
    # Build dynamic update query
    update_fields = []
    params = []
    
    if update_data.value is not None:
        update_fields.append("value = ?")
        params.append(update_data.value)
    
    if update_data.encrypted is not None:
        update_fields.append("encrypted = ?")
        params.append(1 if update_data.encrypted else 0)
    
    if update_data.description is not None:
        update_fields.append("description = ?")
        params.append(update_data.description)
    
    if update_data.category is not None:
        update_fields.append("category = ?")
        params.append(update_data.category)
    
    if not update_fields:
        return True  # No fields to update
    
    # Add updated timestamp
    update_fields.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    
    # Add WHERE clause
    params.append(setting_id)
    
    query = f"""
        UPDATE settings 
        SET {', '.join(update_fields)}
        WHERE id = ?
    """
    
    try:
        execute_query(query, params, fetch=False, commit=True)
        return True
    except Exception as e:
        logger.error(f"Failed to update setting {setting_id}: {e}")
        return False


def delete_setting(setting_id: str) -> bool:
    """Delete a setting by ID.
    
    Args:
        setting_id: UUID string of the setting
        
    Returns:
        bool: True if deletion successful, False if not found
    """
    query = "DELETE FROM settings WHERE id = ?"
    try:
        execute_query(query, (setting_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to delete setting {setting_id}: {e}")
        return False


def delete_setting_by_key(key: str) -> bool:
    """Delete a setting by key.
    
    Args:
        key: Setting key
        
    Returns:
        bool: True if deletion successful, False if not found
    """
    query = "DELETE FROM settings WHERE key = ?"
    try:
        execute_query(query, (key,))
        return True
    except Exception as e:
        logger.error(f"Failed to delete setting with key {key}: {e}")
        return False


def get_settings_by_category(category: str) -> List[Setting]:
    """Get all settings in a specific category.
    
    Args:
        category: Category name
        
    Returns:
        List of Setting models
    """
    return list_settings(category=category)


def get_api_keys() -> List[Setting]:
    """Get all API key settings (encrypted settings in api_keys category).
    
    Returns:
        List of Setting models for API keys
    """
    query = """
        SELECT id, key, value, encrypted, description, category,
               created_by, created_at, updated_at
        FROM settings 
        WHERE category = 'api_keys' AND encrypted = 1
        ORDER BY key
    """
    
    result = execute_query(query, (), fetch=True)
    if not result:
        return []
    
    settings = []
    for row in result:
        setting = Setting.from_db_row(row)
        settings.append(setting)
    
    return settings