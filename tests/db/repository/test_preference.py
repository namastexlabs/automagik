"""Tests for preference repository.

[EPIC-SIMULATION-TEST]
"""

import pytest
import uuid
from datetime import datetime

from src.db.models import Preference, PreferenceCreate, PreferenceUpdate
from src.db.repository.preference import PreferenceRepository


@pytest.mark.asyncio
class TestPreferenceRepository:
    """Test suite for PreferenceRepository."""
    
    async def test_create_preference(self, db_session, test_user):
        """Test creating a new preference."""
        preference_data = PreferenceCreate(
            user_id=test_user.id,
            category="behavior",
            preferences={
                "response_style": "concise",
                "language": "en",
                "timezone": "UTC"
            }
        )
        
        result = await PreferenceRepository.create(preference_data)
        
        assert result is not None
        assert result.user_id == test_user.id
        assert result.category == "behavior"
        assert result.preferences["response_style"] == "concise"
        assert result.version == 1
    
    async def test_get_by_user_and_category(self, db_session, test_user):
        """Test retrieving preferences by user and category."""
        # Create test preference
        preference_data = PreferenceCreate(
            user_id=test_user.id,
            category="ui",
            preferences={"theme": "dark", "font_size": "medium"}
        )
        created = await PreferenceRepository.create(preference_data)
        
        # Retrieve preference
        result = await PreferenceRepository.get_by_user_and_category(
            test_user.id, "ui"
        )
        
        assert result is not None
        assert result.id == created.id
        assert result.preferences["theme"] == "dark"
    
    async def test_get_all_by_user(self, db_session, test_user):
        """Test retrieving all preferences for a user."""
        # Create multiple preferences
        categories = ["ui", "behavior", "notifications"]
        for category in categories:
            await PreferenceRepository.create(
                PreferenceCreate(
                    user_id=test_user.id,
                    category=category,
                    preferences={"test": f"{category}_value"}
                )
            )
        
        # Get all preferences
        results = await PreferenceRepository.get_all_by_user(test_user.id)
        
        assert len(results) == 3
        assert all(r.user_id == test_user.id for r in results)
        assert sorted([r.category for r in results]) == sorted(categories)
    
    async def test_update_preference(self, db_session, test_user):
        """Test updating preferences."""
        # Create preference
        original = await PreferenceRepository.create(
            PreferenceCreate(
                user_id=test_user.id,
                category="behavior",
                preferences={"response_style": "verbose"}
            )
        )
        
        # Update preference
        update_data = PreferenceUpdate(
            preferences={"response_style": "concise", "new_key": "new_value"}
        )
        result = await PreferenceRepository.update(
            test_user.id, "behavior", update_data
        )
        
        assert result is not None
        assert result.preferences["response_style"] == "concise"
        assert result.preferences["new_key"] == "new_value"
        assert result.updated_at > original.created_at
    
    async def test_merge_preferences(self, db_session, test_user):
        """Test merging preferences."""
        # Create initial preferences
        await PreferenceRepository.create(
            PreferenceCreate(
                user_id=test_user.id,
                category="ui",
                preferences={"theme": "light", "font_size": "small"}
            )
        )
        
        # Merge new preferences
        result = await PreferenceRepository.merge_preferences(
            test_user.id,
            "ui",
            {"theme": "dark", "sidebar": "collapsed"}
        )
        
        assert result is not None
        assert result.preferences["theme"] == "dark"  # Updated
        assert result.preferences["font_size"] == "small"  # Preserved
        assert result.preferences["sidebar"] == "collapsed"  # Added
    
    async def test_delete_preference(self, db_session, test_user):
        """Test deleting preferences."""
        # Create preference
        await PreferenceRepository.create(
            PreferenceCreate(
                user_id=test_user.id,
                category="notifications",
                preferences={"email": True}
            )
        )
        
        # Delete preference
        deleted = await PreferenceRepository.delete(test_user.id, "notifications")
        assert deleted is True
        
        # Verify deletion
        result = await PreferenceRepository.get_by_user_and_category(
            test_user.id, "notifications"
        )
        assert result is None
    
    async def test_preference_history(self, db_session, test_user):
        """Test preference change history."""
        # Create and update preference multiple times
        preference = await PreferenceRepository.create(
            PreferenceCreate(
                user_id=test_user.id,
                category="behavior",
                preferences={"version": 1}
            )
        )
        
        for i in range(2, 5):
            await PreferenceRepository.update(
                test_user.id,
                "behavior",
                PreferenceUpdate(preferences={"version": i}),
                changed_by=test_user.id
            )
        
        # Get history
        history = await PreferenceRepository.get_history(preference.id, limit=5)
        
        assert len(history) == 3  # 3 updates
        assert history[0].new_value["version"] == 4  # Most recent first
        assert history[-1].new_value["version"] == 2  # Oldest last
        assert all(h.changed_by == test_user.id for h in history)