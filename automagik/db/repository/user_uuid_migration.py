"""User UUID migration utilities for FlashinhoV2 Flashed integration.

This module provides functions to safely migrate a user's UUID to match
the Flashed system's user_id, ensuring unified identity across applications.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from automagik.db.connection import execute_query, get_db_connection
from automagik.db.models import User
from automagik.db.repository.user import get_user, create_user, delete_user

logger = logging.getLogger(__name__)


async def migrate_user_uuid_to_flashed_id(
    current_user_id: str, 
    flashed_user_id: str,
    preserve_phone_number: Optional[str] = None,
    flashed_user_data: Optional[Dict[str, Any]] = None
) -> bool:
    """Migrate user's UUID to match Flashed user_id while preserving all data.
    
    This function performs a complete user identity migration:
    1. Creates new user record with Flashed UUID as primary key
    2. Migrates all related data (messages, sessions, memories)
    3. Deletes old user record
    4. Preserves phone number from API payload
    
    Args:
        current_user_id: Current user UUID in our database
        flashed_user_id: Target Flashed user_id to migrate to
        preserve_phone_number: Phone number from API to preserve (optional)
        flashed_user_data: Additional user data from Flashed API (optional)
        
    Returns:
        True if migration successful, False otherwise
    """
    try:
        logger.info(f"Starting UUID migration: {current_user_id} → {flashed_user_id}")
        
        # Step 1: Validate inputs
        if current_user_id == flashed_user_id:
            logger.info("UUIDs already match, no migration needed")
            return True
            
        current_uuid = uuid.UUID(current_user_id)
        flashed_uuid = uuid.UUID(flashed_user_id)
        
        # Step 2: Get current user data
        current_user = get_user(current_uuid)
        if not current_user:
            logger.error(f"Current user {current_user_id} not found")
            return False
            
        # Step 3: Check if target UUID already exists
        existing_flashed_user = get_user(flashed_uuid)
        if existing_flashed_user:
            logger.warning(f"Target UUID {flashed_user_id} already exists")
            # If target user exists, merge data instead of migrating
            return await merge_user_data_to_existing(
                current_user, existing_flashed_user, preserve_phone_number, flashed_user_data
            )
        
        # Step 4: Create new user with Flashed UUID
        # 🔧 SURGICAL FIX: Merge existing user_data with flashed_user_data
        merged_user_data = (current_user.user_data or {}).copy()
        if flashed_user_data:
            if flashed_user_data.get("conversation_code"):
                merged_user_data["flashed_conversation_code"] = flashed_user_data.get("conversation_code")
            if flashed_user_data.get("name"):
                merged_user_data["flashed_user_name"] = flashed_user_data.get("name")
            if flashed_user_data.get("email"):
                merged_user_data["flashed_user_email"] = flashed_user_data.get("email")
            if flashed_user_data.get("phone"):
                merged_user_data["flashed_user_phone"] = flashed_user_data.get("phone")
            # Ensure we have the flashed_user_id
            merged_user_data["flashed_user_id"] = flashed_user_id
        
        new_user = User(
            id=flashed_uuid,
            email=current_user.email,
            phone_number=preserve_phone_number or current_user.phone_number,
            user_data=merged_user_data,
            created_at=current_user.created_at,
            updated_at=datetime.now()
        )
        
        # Step 5: Perform migration in transaction
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Begin transaction
                    cursor.execute("BEGIN")
                    
                    # Create new user record
                    cursor.execute("""
                        INSERT INTO users (id, email, phone_number, user_data, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        str(flashed_uuid), 
                        new_user.email,
                        new_user.phone_number,
                        new_user.user_data,
                        new_user.created_at,
                        new_user.updated_at
                    ))
                    
                    # Migrate related data
                    await _migrate_related_data(cursor, current_uuid, flashed_uuid)
                    
                    # Delete old user record
                    cursor.execute("DELETE FROM users WHERE id = %s", (str(current_uuid),))
                    
                    # Commit transaction
                    cursor.execute("COMMIT")
                    
                    logger.info(f"Successfully migrated user UUID: {current_user_id} → {flashed_user_id}")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    cursor.execute("ROLLBACK")
                    logger.error(f"Migration transaction failed: {str(e)}")
                    raise
                    
    except Exception as e:
        logger.error(f"Error migrating user UUID: {str(e)}")
        return False


async def merge_user_data_to_existing(
    source_user: User, 
    target_user: User, 
    preserve_phone_number: Optional[str] = None,
    flashed_user_data: Optional[Dict[str, Any]] = None
) -> bool:
    """Merge source user data into existing target user.
    
    Args:
        source_user: User to merge data from
        target_user: Existing user to merge data into
        preserve_phone_number: Phone number from API to preserve
        flashed_user_data: Additional user data from Flashed API (optional)
        
    Returns:
        True if merge successful, False otherwise
    """
    try:
        logger.info(f"Merging user data: {source_user.id} → {target_user.id}")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute("BEGIN")
                    
                    # Merge user_data fields
                    merged_user_data = (target_user.user_data or {}).copy()
                    if source_user.user_data:
                        merged_user_data.update(source_user.user_data)
                    
                    # 🔧 SURGICAL FIX: Merge flashed_user_data
                    if flashed_user_data:
                        if flashed_user_data.get("conversation_code"):
                            merged_user_data["flashed_conversation_code"] = flashed_user_data.get("conversation_code")
                        if flashed_user_data.get("name"):
                            merged_user_data["flashed_user_name"] = flashed_user_data.get("name")
                        if flashed_user_data.get("email"):
                            merged_user_data["flashed_user_email"] = flashed_user_data.get("email")
                        if flashed_user_data.get("phone"):
                            merged_user_data["flashed_user_phone"] = flashed_user_data.get("phone")
                    
                    # Update target user with merged data
                    cursor.execute("""
                        UPDATE users 
                        SET 
                            email = COALESCE(%s, email),
                            phone_number = %s,
                            user_data = %s,
                            updated_at = %s
                        WHERE id = %s
                    """, (
                        source_user.email if source_user.email else None,
                        preserve_phone_number or target_user.phone_number,
                        merged_user_data,
                        datetime.now(),
                        str(target_user.id)
                    ))
                    
                    # Migrate related data from source to target
                    await _migrate_related_data(cursor, source_user.id, target_user.id)
                    
                    # Delete source user
                    cursor.execute("DELETE FROM users WHERE id = %s", (str(source_user.id),))
                    
                    cursor.execute("COMMIT")
                    
                    logger.info(f"Successfully merged user data: {source_user.id} → {target_user.id}")
                    return True
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    logger.error(f"Merge transaction failed: {str(e)}")
                    raise
                    
    except Exception as e:
        logger.error(f"Error merging user data: {str(e)}")
        return False


async def _migrate_related_data(cursor, source_uuid: uuid.UUID, target_uuid: uuid.UUID) -> None:
    """Migrate all related data from source user to target user.
    
    Args:
        cursor: Database cursor within transaction
        source_uuid: Source user UUID
        target_uuid: Target user UUID
    """
    try:
        # Update sessions
        cursor.execute("""
            UPDATE sessions 
            SET user_id = %s 
            WHERE user_id = %s
        """, (str(target_uuid), str(source_uuid)))
        
        logger.debug(f"Migrated sessions: {cursor.rowcount} rows")
        
        # Update messages 
        cursor.execute("""
            UPDATE messages 
            SET user_id = %s 
            WHERE user_id = %s
        """, (str(target_uuid), str(source_uuid)))
        
        logger.debug(f"Migrated messages: {cursor.rowcount} rows")
        
        # Update memories
        cursor.execute("""
            UPDATE memories 
            SET user_id = %s 
            WHERE user_id = %s
        """, (str(target_uuid), str(source_uuid)))
        
        logger.debug(f"Migrated memories: {cursor.rowcount} rows")
        
        # Update preferences
        cursor.execute("""
            UPDATE preferences 
            SET user_id = %s 
            WHERE user_id = %s
        """, (str(target_uuid), str(source_uuid)))
        
        logger.debug(f"Migrated preferences: {cursor.rowcount} rows")
        
    except Exception as e:
        logger.error(f"Error migrating related data: {str(e)}")
        raise


def find_user_by_flashed_id(flashed_user_id: str) -> Optional[User]:
    """Find user by Flashed user_id stored in user_data.
    
    Args:
        flashed_user_id: Flashed user_id to search for
        
    Returns:
        User if found, None otherwise
    """
    try:
        result = execute_query("""
            SELECT * FROM users 
            WHERE user_data->>'flashed_user_id' = %s
        """, (flashed_user_id,))
        
        return User.from_db_row(result[0]) if result else None
        
    except Exception as e:
        logger.error(f"Error finding user by Flashed ID {flashed_user_id}: {str(e)}")
        return None


def find_user_by_phone_number(phone_number: str) -> Optional[User]:
    """Find user by phone number.
    
    Args:
        phone_number: Phone number to search for
        
    Returns:
        User if found, None otherwise
    """
    try:
        result = execute_query("""
            SELECT * FROM users 
            WHERE phone_number = %s
        """, (phone_number,))
        
        return User.from_db_row(result[0]) if result else None
        
    except Exception as e:
        logger.error(f"Error finding user by phone {phone_number}: {str(e)}")
        return None


async def ensure_user_uuid_matches_flashed_id(
    phone_number: str, 
    flashed_user_id: str,
    flashed_user_data: Dict[str, Any]
) -> str:
    """Ensure user with phone_number has UUID matching flashed_user_id.
    
    This is the main function for FlashinhoV2 integration.
    
    Args:
        phone_number: Phone number from API payload
        flashed_user_id: User ID from Flashed system
        flashed_user_data: Additional user data from Flashed API
        
    Returns:
        Final user UUID (should match flashed_user_id)
    """
    try:
        logger.info(f"Ensuring UUID synchronization for phone {phone_number} → {flashed_user_id}")
        
        # Find existing user by phone number
        existing_user = find_user_by_phone_number(phone_number)
        
        if not existing_user:
            # No existing user, create new one with Flashed UUID
            logger.info(f"Creating new user with Flashed UUID: {flashed_user_id}")
            
            new_user = User(
                id=uuid.UUID(flashed_user_id),
                email=flashed_user_data.get("email"),
                phone_number=phone_number,  # Always preserve API phone
                user_data={
                    "flashed_user_id": flashed_user_id,
                    "flashed_conversation_code": flashed_user_data.get("conversation_code"),
                    "flashed_user_name": flashed_user_data.get("name"),
                    "flashed_user_email": flashed_user_data.get("email"),
                    "flashed_user_phone": flashed_user_data.get("phone"),
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            created_id = create_user(new_user)
            logger.info(f"Created user with UUID: {created_id}")
            return str(created_id)
            
        elif str(existing_user.id) != flashed_user_id:
            # User exists but UUID doesn't match - migrate
            logger.info(f"Migrating existing user UUID: {existing_user.id} → {flashed_user_id}")
            
            success = await migrate_user_uuid_to_flashed_id(
                str(existing_user.id),
                flashed_user_id,
                phone_number,  # Preserve API phone number
                flashed_user_data  # Pass flashed user data
            )
            
            if success:
                logger.info(f"Successfully migrated user UUID to: {flashed_user_id}")
                return flashed_user_id
            else:
                logger.error("UUID migration failed")
                return str(existing_user.id)
                
        else:
            # User exists and UUID already matches - but ensure user_data is updated
            logger.info(f"User UUID already matches Flashed ID: {flashed_user_id}")
            
            # 🔧 SURGICAL FIX: Ensure flashed_conversation_code is persisted
            current_user_data = existing_user.user_data or {}
            needs_update = False
            
            # Check if we need to update any flashed data
            if flashed_user_data.get("conversation_code") and \
               current_user_data.get("flashed_conversation_code") != flashed_user_data.get("conversation_code"):
                current_user_data["flashed_conversation_code"] = flashed_user_data.get("conversation_code")
                needs_update = True
            
            if flashed_user_data.get("name") and \
               current_user_data.get("flashed_user_name") != flashed_user_data.get("name"):
                current_user_data["flashed_user_name"] = flashed_user_data.get("name")
                needs_update = True
            
            if flashed_user_data.get("email") and \
               current_user_data.get("flashed_user_email") != flashed_user_data.get("email"):
                current_user_data["flashed_user_email"] = flashed_user_data.get("email")
                needs_update = True
            
            if flashed_user_data.get("phone") and \
               current_user_data.get("flashed_user_phone") != flashed_user_data.get("phone"):
                current_user_data["flashed_user_phone"] = flashed_user_data.get("phone")
                needs_update = True
            
            # Update user_data if needed
            if needs_update:
                from automagik.db.repository.user import update_user_data
                update_user_data(existing_user.id, current_user_data)
                logger.info(f"Updated user_data for existing user {existing_user.id} with conversation code")
            
            return str(existing_user.id)
            
    except Exception as e:
        logger.error(f"Error ensuring UUID synchronization: {str(e)}")
        raise