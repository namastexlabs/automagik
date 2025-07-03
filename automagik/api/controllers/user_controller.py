import logging
import json
from fastapi import HTTPException
from automagik.db import get_user_by_identifier, list_users, update_user, create_user as db_create_user, delete_user as db_delete_user
from automagik.api.models import UserCreate, UserUpdate, UserInfo, UserListResponse
from automagik.db.models import User
from fastapi.concurrency import run_in_threadpool

# Get our module's logger
logger = logging.getLogger(__name__)

async def get_users(page: int, page_size: int) -> UserListResponse:
    """
    Get a paginated list of users
    """
    try:
        users, total_count = await run_in_threadpool(list_users, page=page, page_size=page_size)
        
        # Convert User objects to UserInfo objects
        user_infos = []
        for user in users:
            user_infos.append(UserInfo(
                id=user.id,
                email=user.email,
                phone_number=user.phone_number,
                user_data=user.user_data,
                created_at=user.created_at,
                updated_at=user.updated_at
            ))
        
        # Calculate pagination info
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        has_next = page < total_pages
        has_prev = page > 1
        
        return UserListResponse(
            users=user_infos,
            total=total_count,  # Use 'total' instead of 'total_count' to match the test
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")

async def create_user(user_create: UserCreate) -> UserInfo:
    """
    Create a new user
    """
    try:
        # Check if user already exists with the provided email or phone
        if user_create.email:
            existing_user = await run_in_threadpool(get_user_by_identifier, user_create.email)
            if existing_user:
                raise HTTPException(status_code=400, detail=f"User with email {user_create.email} already exists")
                
        if user_create.phone_number:
            existing_user = await run_in_threadpool(get_user_by_identifier, user_create.phone_number)
            if existing_user:
                raise HTTPException(status_code=400, detail=f"User with phone number {user_create.phone_number} already exists")
        
        # Create a User object
        user = User(
            email=user_create.email,
            phone_number=user_create.phone_number,
            user_data=user_create.user_data
        )
        
        # Use repository function to create the user
        user_id = await run_in_threadpool(db_create_user, user)
        
        if not user_id:
            raise Exception("Failed to create user - no ID returned")
        
        # Get the newly created user
        created_user = await run_in_threadpool(get_user_by_identifier, str(user_id))
        
        return UserInfo(
            id=created_user.id,
            email=created_user.email,
            phone_number=created_user.phone_number,
            user_data=created_user.user_data,
            created_at=created_user.created_at,
            updated_at=created_user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

async def get_user(user_identifier: str) -> UserInfo:
    """
    Get a user by ID, email, or phone number
    """
    try:
        user = await run_in_threadpool(get_user_by_identifier, user_identifier)
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found with identifier: {user_identifier}")
        
        return UserInfo(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            user_data=user.user_data,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

async def update_user_data(user_identifier: str, user_update: UserUpdate) -> UserInfo:
    """
    Update a user by ID, email, or phone number
    """
    try:
        # Check if user exists
        existing_user = await run_in_threadpool(get_user_by_identifier, user_identifier)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"User not found with identifier: {user_identifier}")
        
        # Convert user_data dict to JSON string if it's not None
        json.dumps(user_update.user_data) if user_update.user_data else None
        
        # Create a User object with the updated fields
        updated_user_obj = User(
            id=existing_user.id,
            email=user_update.email if user_update.email is not None else existing_user.email,
            phone_number=user_update.phone_number if user_update.phone_number is not None else existing_user.phone_number,
            user_data=user_update.user_data if user_update.user_data is not None else existing_user.user_data,
            created_at=existing_user.created_at
        )
        
        # Update the user using the repository function
        user_id = await run_in_threadpool(update_user, updated_user_obj)
        
        if not user_id:
            raise HTTPException(status_code=500, detail=f"Failed to update user: {user_identifier}")
        
        # Fetch the updated user to return
        updated_user = await run_in_threadpool(get_user_by_identifier, str(user_id))
        
        return UserInfo(
            id=updated_user.id,
            email=updated_user.email,
            phone_number=updated_user.phone_number,
            user_data=updated_user.user_data,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

async def delete_user(user_identifier: str) -> bool:
    """
    Delete a user by ID, email, or phone number
    """
    try:
        # Check if user exists
        existing_user = await run_in_threadpool(get_user_by_identifier, user_identifier)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"User not found with identifier: {user_identifier}")
        
        # Delete the user using repository function
        success = await run_in_threadpool(db_delete_user, existing_user.id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete user: {user_identifier}")
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}") 