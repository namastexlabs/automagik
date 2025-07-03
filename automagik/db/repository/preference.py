"""Repository for preference-related database operations.

[EPIC-SIMULATION-TEST]
"""

import uuid
from typing import Dict, List, Optional, Any

from automagik.db.connection import get_db_connection
from automagik.db.models import Preference, PreferenceCreate, PreferenceUpdate, PreferenceHistory
from automagik.utils.logging import get_logger

logger = get_logger(__name__)


class PreferenceRepository:
    """Repository for managing user preferences in the database."""
    
    @staticmethod
    async def create(preference_data: PreferenceCreate) -> Preference:
        """Create a new preference entry.
        
        Args:
            preference_data: PreferenceCreate model with user_id, category, and preferences
            
        Returns:
            Created Preference instance
            
        Raises:
            Exception: If preference for user/category already exists
        """
        async with get_db_connection() as conn:
            try:
                query = """
                    INSERT INTO preferences (user_id, category, preferences, version)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                """
                
                result = await conn.fetchrow(
                    query,
                    preference_data.user_id,
                    preference_data.category,
                    preference_data.preferences,
                    preference_data.version
                )
                
                logger.info(f"Created preferences for user {preference_data.user_id} in category {preference_data.category}")
                return Preference.from_db_row(dict(result))
                
            except Exception as e:
                logger.error(f"Error creating preferences: {e}")
                raise
    
    @staticmethod
    async def get_by_user_and_category(user_id: uuid.UUID, category: str) -> Optional[Preference]:
        """Get preferences for a specific user and category.
        
        Args:
            user_id: User UUID
            category: Preference category
            
        Returns:
            Preference instance if found, None otherwise
        """
        async with get_db_connection() as conn:
            query = """
                SELECT * FROM preferences 
                WHERE user_id = $1 AND category = $2
            """
            
            result = await conn.fetchrow(query, user_id, category)
            
            if result:
                return Preference.from_db_row(dict(result))
            return None
    
    @staticmethod
    async def get_all_by_user(user_id: uuid.UUID) -> List[Preference]:
        """Get all preferences for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of Preference instances
        """
        async with get_db_connection() as conn:
            query = """
                SELECT * FROM preferences 
                WHERE user_id = $1
                ORDER BY category
            """
            
            results = await conn.fetch(query, user_id)
            
            return [Preference.from_db_row(dict(row)) for row in results]
    
    @staticmethod
    async def update(
        user_id: uuid.UUID, 
        category: str, 
        update_data: PreferenceUpdate,
        changed_by: Optional[uuid.UUID] = None
    ) -> Optional[Preference]:
        """Update preferences for a user and category.
        
        Args:
            user_id: User UUID
            category: Preference category
            update_data: PreferenceUpdate model with new values
            changed_by: UUID of user making the change (for audit log)
            
        Returns:
            Updated Preference instance if successful, None if not found
        """
        async with get_db_connection() as conn:
            async with conn.transaction():
                # Get current preference for history
                current = await conn.fetchrow(
                    "SELECT * FROM preferences WHERE user_id = $1 AND category = $2",
                    user_id, category
                )
                
                if not current:
                    return None
                
                # Update preference
                update_fields = []
                update_values = []
                
                if update_data.preferences is not None:
                    update_fields.append("preferences = $1")
                    update_values.append(update_data.preferences)
                
                if update_data.version is not None:
                    update_fields.append(f"version = ${len(update_values) + 1}")
                    update_values.append(update_data.version)
                
                if not update_fields:
                    return Preference.from_db_row(dict(current))
                
                # Add WHERE clause parameters
                update_values.extend([user_id, category])
                
                query = f"""
                    UPDATE preferences 
                    SET {', '.join(update_fields)}
                    WHERE user_id = ${len(update_values) - 1} 
                    AND category = ${len(update_values)}
                    RETURNING *
                """
                
                result = await conn.fetchrow(query, *update_values)
                
                # Log to history
                if update_data.preferences is not None:
                    await conn.execute("""
                        INSERT INTO preference_history 
                        (preference_id, old_value, new_value, changed_by)
                        VALUES ($1, $2, $3, $4)
                    """, 
                    current['id'], 
                    current['preferences'], 
                    update_data.preferences,
                    changed_by
                    )
                
                logger.info(f"Updated preferences for user {user_id} in category {category}")
                return Preference.from_db_row(dict(result))
    
    @staticmethod
    async def delete(user_id: uuid.UUID, category: str) -> bool:
        """Delete preferences for a user and category.
        
        Args:
            user_id: User UUID
            category: Preference category
            
        Returns:
            True if deleted, False if not found
        """
        async with get_db_connection() as conn:
            result = await conn.execute(
                "DELETE FROM preferences WHERE user_id = $1 AND category = $2",
                user_id, category
            )
            
            deleted = result.split()[-1] != '0'
            if deleted:
                logger.info(f"Deleted preferences for user {user_id} in category {category}")
            
            return deleted
    
    @staticmethod
    async def get_history(
        preference_id: uuid.UUID, 
        limit: int = 10
    ) -> List[PreferenceHistory]:
        """Get change history for a preference.
        
        Args:
            preference_id: Preference UUID
            limit: Maximum number of history entries to return
            
        Returns:
            List of PreferenceHistory instances
        """
        async with get_db_connection() as conn:
            query = """
                SELECT * FROM preference_history 
                WHERE preference_id = $1
                ORDER BY changed_at DESC
                LIMIT $2
            """
            
            results = await conn.fetch(query, preference_id, limit)
            
            return [
                PreferenceHistory(
                    id=row['id'],
                    preference_id=row['preference_id'],
                    old_value=row['old_value'],
                    new_value=row['new_value'],
                    changed_by=row['changed_by'],
                    changed_at=row['changed_at']
                )
                for row in results
            ]
    
    @staticmethod
    async def merge_preferences(
        user_id: uuid.UUID,
        category: str,
        new_preferences: Dict[str, Any],
        changed_by: Optional[uuid.UUID] = None
    ) -> Optional[Preference]:
        """Merge new preferences with existing ones.
        
        This method performs a deep merge, preserving existing values
        that are not specified in new_preferences.
        
        Args:
            user_id: User UUID
            category: Preference category
            new_preferences: New preference values to merge
            changed_by: UUID of user making the change
            
        Returns:
            Updated Preference instance
        """
        async with get_db_connection():
            # Get existing preferences
            existing = await PreferenceRepository.get_by_user_and_category(user_id, category)
            
            if existing:
                # Merge preferences
                merged = {**existing.preferences, **new_preferences}
                update_data = PreferenceUpdate(preferences=merged)
                return await PreferenceRepository.update(user_id, category, update_data, changed_by)
            else:
                # Create new preferences
                create_data = PreferenceCreate(
                    user_id=user_id,
                    category=category,
                    preferences=new_preferences
                )
                return await PreferenceRepository.create(create_data)