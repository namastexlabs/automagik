import logging
from fastapi import APIRouter, Query, Path
from automagik.api.models import UserCreate, UserUpdate, UserInfo, UserListResponse
from automagik.api.controllers.user_controller import get_users, create_user, get_user, update_user_data, delete_user

# Create router for user endpoints
user_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

@user_router.get("/users", response_model=UserListResponse, tags=["Users"],
           summary="List Users",
           description="Returns a paginated list of users.\n\n**Requires Authentication**: This endpoint requires an API key.")
async def list_users_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get a paginated list of users
    """
    return await get_users(page, page_size)

@user_router.post("/users", response_model=UserInfo, tags=["Users"],
            summary="Create User",
            description="Creates a new user with email, phone_number, and/or user_data fields.\n\n**Requires Authentication**: This endpoint requires an API key.")
async def create_user_route(user_create: UserCreate):
    """
    Create a new user
    """
    return await create_user(user_create)

@user_router.get("/users/{user_identifier}", response_model=UserInfo, tags=["Users"],
            summary="Get User",
            description="Returns details for a specific user by ID, email, or phone number.\n\n**Requires Authentication**: This endpoint requires an API key.")
async def get_user_route(user_identifier: str = Path(..., description="The user ID, email, or phone number")):
    """
    Get a user by ID, email, or phone number
    """
    return await get_user(user_identifier)

@user_router.put("/users/{user_identifier}", response_model=UserInfo, tags=["Users"],
            summary="Update User",
            description="Updates an existing user identified by ID, email, or phone number.\n\n**Requires Authentication**: This endpoint requires an API key.")
async def update_user_route(user_update: UserUpdate, user_identifier: str = Path(..., description="The user ID, email, or phone number")):
    """
    Update a user by ID, email, or phone number
    """
    return await update_user_data(user_identifier, user_update)

@user_router.delete("/users/{user_identifier}", tags=["Users"],
               summary="Delete User",
               description="Deletes a user account by ID, email, or phone number.\n\n**Requires Authentication**: This endpoint requires an API key.")
async def delete_user_route(user_identifier: str = Path(..., description="The user ID, email, or phone number")):
    """
    Delete a user by ID, email, or phone number
    """
    success = await delete_user(user_identifier)
    # Return the format expected by the test
    return {"success": success} 