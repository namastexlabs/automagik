"""
Test script for looking up Flashed users by phone number.

This script demonstrates connecting to the Flashed API and retrieving user data
by their phone number through available endpoints.
"""
import asyncio
import logging
import pprint
from typing import Dict, Any, Optional

from automagik.tools.flashed.provider import FlashedProvider
from automagik.db.repository.user import get_user_by_phone, create_user, update_user_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_flashed_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Find a Flashed user by phone number by querying available user records.
    
    Strategy:
    1. Query all available user_uuid records
    2. For each UUID, get user data 
    3. Check if phone matches
    
    Args:
        phone: Phone number to search for
    
    Returns:
        User data if found, None otherwise
    """
    test_uuids = [
        "6ba9568d-54a2-4f49-a960-7c3fae9b194c",  # Test UUID from memory manager
        "550e8400-e29b-41d4-a716-446655440000",  # Random test UUID
    ]
    
    async with FlashedProvider() as provider:
        for uuid in test_uuids:
            try:
                logger.info(f"Checking user UUID: {uuid}")
                user_data = await provider.get_user_data(uuid)
                
                # Check if this is the user we're looking for
                if user_data and user_data.get("cadastro", {}).get("phone") == phone:
                    logger.info(f"Found matching user with UUID: {uuid}")
                    return user_data
                    
            except Exception as e:
                logger.error(f"Error checking UUID {uuid}: {str(e)}")
                
    logger.warning(f"No user found with phone: {phone}")
    return None

async def ensure_user_in_db(phone: str):
    """
    Ensure a user with the given phone exists in our database.
    
    If Flashed user found:
    - Check if user exists in our DB by phone
    - If not, create user with flashed_user_id in user_data
    - If yes but different ID, update to match Flashed ID
    
    Args:
        phone: Phone number to check
    """
    # First check Flashed API
    flashed_user = await find_flashed_user_by_phone(phone)
    if not flashed_user:
        logger.error(f"No Flashed user found with phone: {phone}")
        return
        
    # Extract user info
    flashed_uuid = flashed_user.get("id")
    user_info = flashed_user.get("cadastro", {})
    user_email = user_info.get("email")
    user_name = user_info.get("name")
    
    logger.info(f"Found Flashed user: {flashed_uuid}")
    logger.info(f"User info: {user_name}, {user_email}, {phone}")
    
    # Check our database
    existing_user = get_user_by_phone(phone)
    
    if existing_user:
        logger.info(f"Found existing user in DB: {existing_user.id}")
        # Update user_data
        update_user_data(existing_user.id, {"flashed_user_id": flashed_uuid})
        logger.info(f"Updated user_data with flashed_user_id: {flashed_uuid}")
    else:
        # Create new user
        import uuid
        try:
            # Use the Flashed UUID as our primary key if it's a valid UUID
            user_id = uuid.UUID(flashed_uuid)
        except (ValueError, TypeError):
            # Otherwise generate a deterministic UUID
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(flashed_uuid))
            
        create_user(
            id=user_id,
            name=user_name or "Flashed User",
            email=user_email,
            phone=phone,
            user_data={"flashed_user_id": flashed_uuid}
        )
        logger.info(f"Created new user with ID: {user_id}")

async def run():
    """Main test function"""
    phone = "5551997285829"
    
    print("\n1. Looking up Flashed user by phone:")
    flashed_user = await find_flashed_user_by_phone(phone)
    if flashed_user:
        print("✅ Found Flashed user:")
        pprint.pprint(flashed_user)
    else:
        print("❌ No Flashed user found")
        
    print("\n2. Ensuring user exists in our database:")
    await ensure_user_in_db(phone)
    
    print("\n3. Checking user in our database:")
    local_user = get_user_by_phone(phone)
    if local_user:
        print("✅ Found local user:")
        pprint.pprint(local_user.model_dump())
    else:
        print("❌ No local user found")

if __name__ == "__main__":
    asyncio.run(run()) 