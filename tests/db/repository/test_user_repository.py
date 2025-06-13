"""Unit tests for user repository functions.

This module tests all user repository database operations
including CRUD operations, error handling, and edge cases.
"""

import pytest
import uuid
import json
from unittest.mock import patch
from datetime import datetime

from src.db.repository.user import (
    get_user,
    get_user_by_email,
    get_user_by_identifier,
    list_users,
    create_user,
    update_user,
    delete_user,
    ensure_default_user_exists,
    update_user_data,
    _deep_update
)
from src.db.models import User


class TestUserRepository:
    """Test suite for user repository functions."""
    
    @pytest.fixture
    def mock_execute_query(self):
        """Fixture to mock execute_query function."""
        with patch('src.db.repository.user.execute_query') as mock:
            yield mock
    
    @pytest.fixture
    def sample_user_data(self):
        """Fixture providing sample user data."""
        return {
            "id": uuid.uuid4(),
            "email": "test@example.com",
            "phone_number": "+1234567890",
            "user_data": {"preferences": {"theme": "dark"}},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def test_get_user_success(self, mock_execute_query, sample_user_data):
        """Test successfully getting a user by ID."""
        mock_execute_query.return_value = [sample_user_data]
        
        user = get_user(sample_user_data["id"])
        
        assert user is not None
        assert user.id == sample_user_data["id"]
        assert user.email == sample_user_data["email"]
        mock_execute_query.assert_called_once()
    
    def test_get_user_not_found(self, mock_execute_query):
        """Test getting a user that doesn't exist."""
        mock_execute_query.return_value = []
        
        user = get_user(uuid.uuid4())
        
        assert user is None
        mock_execute_query.assert_called_once()
    
    def test_get_user_with_string_id(self, mock_execute_query, sample_user_data):
        """Test getting a user with string UUID."""
        mock_execute_query.return_value = [sample_user_data]
        
        user = get_user(str(sample_user_data["id"]))
        
        assert user is not None
        assert user.id == sample_user_data["id"]
    
    def test_get_user_database_error(self, mock_execute_query):
        """Test handling database errors when getting a user."""
        mock_execute_query.side_effect = Exception("Database error")
        
        with patch('src.db.repository.user.logger') as mock_logger:
            user = get_user(uuid.uuid4())
            
            assert user is None
            mock_logger.error.assert_called()
    
    def test_get_user_by_email_success(self, mock_execute_query, sample_user_data):
        """Test getting a user by email."""
        mock_execute_query.return_value = [sample_user_data]
        
        user = get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
        mock_execute_query.assert_called_with(
            "SELECT * FROM users WHERE email = %s",
            ("test@example.com",)
        )
    
    def test_get_user_by_email_not_found(self, mock_execute_query):
        """Test getting a user by email that doesn't exist."""
        mock_execute_query.return_value = []
        
        user = get_user_by_email("nonexistent@example.com")
        assert user is None
    
    def test_get_user_by_identifier_uuid(self, mock_execute_query, sample_user_data):
        """Test getting a user by UUID identifier."""
        user_id = sample_user_data["id"]
        mock_execute_query.return_value = [sample_user_data]
        
        with patch('src.db.repository.user.get_user') as mock_get_user:
            mock_get_user.return_value = User.from_db_row(sample_user_data)
            
            user = get_user_by_identifier(str(user_id))
            
            assert user is not None
            mock_get_user.assert_called_once()
    
    def test_get_user_by_identifier_email(self, mock_execute_query, sample_user_data):
        """Test getting a user by email identifier."""
        mock_execute_query.return_value = []  # No phone match
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email:
            mock_get_email.return_value = User.from_db_row(sample_user_data)
            
            user = get_user_by_identifier("test@example.com")
            
            assert user is not None
            mock_get_email.assert_called_with("test@example.com")
    
    def test_get_user_by_identifier_phone(self, mock_execute_query, sample_user_data):
        """Test getting a user by phone number identifier."""
        mock_execute_query.return_value = [sample_user_data]
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email:
            mock_get_email.return_value = None
            
            user = get_user_by_identifier("+1234567890")
            
            assert user is not None
            assert user.phone_number == "+1234567890"
    
    def test_list_users_success(self, mock_execute_query):
        """Test listing users with pagination."""
        # Mock count query
        mock_execute_query.side_effect = [
            [{"count": 50}],  # Total count
            [  # User list
                {"id": uuid.uuid4(), "email": "user1@example.com"},
                {"id": uuid.uuid4(), "email": "user2@example.com"}
            ]
        ]
        
        users, total = list_users(page=1, page_size=10)
        
        assert len(users) == 2
        assert total == 50
        assert mock_execute_query.call_count == 2
    
    def test_list_users_empty(self, mock_execute_query):
        """Test listing users when none exist."""
        mock_execute_query.side_effect = [
            [{"count": 0}],
            []
        ]
        
        users, total = list_users()
        
        assert users == []
        assert total == 0
    
    def test_list_users_error(self, mock_execute_query):
        """Test handling errors when listing users."""
        mock_execute_query.side_effect = Exception("Database error")
        
        with patch('src.db.repository.user.logger') as mock_logger:
            users, total = list_users()
            
            assert users == []
            assert total == 0
            mock_logger.error.assert_called()
    
    def test_create_user_success(self, mock_execute_query):
        """Test successfully creating a new user."""
        user_id = uuid.uuid4()
        mock_execute_query.return_value = [{"id": user_id}]  # INSERT returns new ID
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email:
            mock_get_email.return_value = None
            
            user = User(
                email="new@example.com",
                phone_number="+1234567890",
                user_data={"name": "Test User"}
            )
            
            created_id = create_user(user)
            
            assert created_id == user_id
            assert mock_execute_query.call_count == 1
    
    def test_create_user_with_existing_email(self, mock_execute_query):
        """Test creating a user with existing email updates instead."""
        existing_user = User(
            id=uuid.uuid4(),
            email="existing@example.com"
        )
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email, \
             patch('src.db.repository.user.update_user') as mock_update:
            
            mock_get_email.return_value = existing_user
            mock_update.return_value = existing_user.id
            
            new_user = User(email="existing@example.com")
            created_id = create_user(new_user)
            
            assert created_id == existing_user.id
            mock_update.assert_called_once()
            assert new_user.id == existing_user.id
    
    def test_create_user_generates_uuid(self, mock_execute_query):
        """Test user creation generates UUID when not provided."""
        mock_execute_query.return_value = [{"id": uuid.uuid4()}]
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email, \
             patch('src.db.repository.user.generate_uuid') as mock_gen_uuid:
            
            mock_get_email.return_value = None
            test_uuid = uuid.uuid4()
            mock_gen_uuid.return_value = test_uuid
            
            user = User(email="test@example.com")
            assert user.id is None
            
            create_user(user)
            
            mock_gen_uuid.assert_called_once()
            assert user.id == test_uuid
    
    def test_update_user_success(self, mock_execute_query):
        """Test successfully updating a user."""
        user_id = uuid.uuid4()
        mock_execute_query.return_value = None
        
        user = User(
            id=user_id,
            email="updated@example.com",
            phone_number="+9876543210",
            user_data={"updated": True}
        )
        
        updated_id = update_user(user)
        
        assert updated_id == user_id
        mock_execute_query.assert_called_once()
    
    def test_update_user_without_id_finds_by_email(self, mock_execute_query):
        """Test updating user without ID finds by email."""
        existing_id = uuid.uuid4()
        
        with patch('src.db.repository.user.get_user_by_email') as mock_get_email:
            existing_user = User(id=existing_id, email="test@example.com")
            mock_get_email.return_value = existing_user
            
            user = User(email="test@example.com")
            updated_id = update_user(user)
            
            assert updated_id == existing_id
            assert user.id == existing_id
    
    def test_update_user_without_id_or_email_creates_new(self, mock_execute_query):
        """Test updating user without ID or email creates new user."""
        with patch('src.db.repository.user.create_user') as mock_create:
            new_id = uuid.uuid4()
            mock_create.return_value = new_id
            
            user = User(phone_number="+1234567890")
            updated_id = update_user(user)
            
            assert updated_id == new_id
            mock_create.assert_called_once()
    
    def test_delete_user_success(self, mock_execute_query):
        """Test successfully deleting a user."""
        user_id = uuid.uuid4()
        mock_execute_query.return_value = None
        
        with patch('src.db.repository.user.safe_uuid') as mock_safe_uuid:
            mock_safe_uuid.return_value = str(user_id)
            
            result = delete_user(user_id)
            
            assert result is True
            mock_execute_query.assert_called_with(
                "DELETE FROM users WHERE id = %s",
                (str(user_id),),
                fetch=False
            )
    
    def test_delete_user_error(self, mock_execute_query):
        """Test handling errors when deleting a user."""
        mock_execute_query.side_effect = Exception("Database error")
        
        with patch('src.db.repository.user.logger') as mock_logger:
            result = delete_user(uuid.uuid4())
            
            assert result is False
            mock_logger.error.assert_called()
    
    def test_ensure_default_user_exists_already_exists(self, mock_execute_query):
        """Test ensure_default_user_exists when user already exists."""
        user_id = uuid.uuid4()
        
        with patch('src.db.repository.user.get_user') as mock_get:
            mock_get.return_value = User(id=user_id)
            
            result = ensure_default_user_exists(user_id)
            
            assert result is True
            mock_get.assert_called_with(user_id)
    
    def test_ensure_default_user_exists_creates_new(self, mock_execute_query):
        """Test ensure_default_user_exists creates new user."""
        with patch('src.db.repository.user.get_user') as mock_get, \
             patch('src.db.repository.user.create_user') as mock_create, \
             patch('src.db.repository.user.generate_uuid') as mock_gen_uuid:
            
            mock_get.return_value = None
            new_id = uuid.uuid4()
            mock_gen_uuid.return_value = new_id
            mock_create.return_value = new_id
            
            result = ensure_default_user_exists()
            
            assert result is True
            mock_create.assert_called_once()
            # Verify the created user has correct email
            created_user = mock_create.call_args[0][0]
            assert created_user.email == "admin@automagik"
    
    def test_update_user_data_success(self, mock_execute_query):
        """Test successfully updating user data."""
        user_id = uuid.uuid4()
        existing_user = User(
            id=user_id,
            user_data={"preferences": {"theme": "light", "lang": "en"}}
        )
        
        with patch('src.db.repository.user.get_user') as mock_get:
            mock_get.return_value = existing_user
            mock_execute_query.return_value = None
            
            # Update only theme
            result = update_user_data(user_id, {"theme": "dark"}, "preferences")
            
            assert result is True
            # Verify the update query was called with merged data
            call_args = mock_execute_query.call_args[0]
            updated_data = json.loads(call_args[1][0])
            assert updated_data["preferences"]["theme"] == "dark"
            assert updated_data["preferences"]["lang"] == "en"  # Preserved
    
    def test_update_user_data_top_level(self, mock_execute_query):
        """Test updating top-level user data."""
        user_id = uuid.uuid4()
        existing_user = User(
            id=user_id,
            user_data={"existing": "value", "nested": {"key": "value"}}
        )
        
        with patch('src.db.repository.user.get_user') as mock_get:
            mock_get.return_value = existing_user
            
            result = update_user_data(
                user_id,
                {"new_key": "new_value", "existing": "updated"}
            )
            
            assert result is True
            call_args = mock_execute_query.call_args[0]
            updated_data = json.loads(call_args[1][0])
            assert updated_data["new_key"] == "new_value"
            assert updated_data["existing"] == "updated"
            assert updated_data["nested"]["key"] == "value"  # Preserved
    
    def test_update_user_data_creates_nested_path(self, mock_execute_query):
        """Test update creates missing nested paths."""
        user_id = uuid.uuid4()
        existing_user = User(id=user_id, user_data={})
        
        with patch('src.db.repository.user.get_user') as mock_get:
            mock_get.return_value = existing_user
            
            result = update_user_data(
                user_id,
                {"deep": "value"},
                "path.to.nested"
            )
            
            assert result is True
            call_args = mock_execute_query.call_args[0]
            updated_data = json.loads(call_args[1][0])
            assert updated_data["path"]["to"]["nested"]["deep"] == "value"
    
    def test_update_user_data_user_not_found(self, mock_execute_query):
        """Test updating data for non-existent user."""
        with patch('src.db.repository.user.get_user') as mock_get:
            mock_get.return_value = None
            
            result = update_user_data(uuid.uuid4(), {"key": "value"})
            
            assert result is False
            mock_execute_query.assert_not_called()
    
    def test_deep_update(self):
        """Test _deep_update helper function."""
        target = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": [1, 2, 3]
        }
        
        source = {
            "a": 10,
            "b": {"c": 20, "f": 4},
            "g": "new"
        }
        
        _deep_update(target, source)
        
        assert target["a"] == 10  # Updated
        assert target["b"]["c"] == 20  # Updated nested
        assert target["b"]["d"] == 3  # Preserved
        assert target["b"]["f"] == 4  # Added
        assert target["e"] == [1, 2, 3]  # Preserved
        assert target["g"] == "new"  # Added
    
    def test_deep_update_non_dict_values(self):
        """Test _deep_update with non-dict values."""
        target = {"a": {"b": "old"}}
        source = {"a": "new_value"}  # Replace dict with string
        
        _deep_update(target, source)
        
        assert target["a"] == "new_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])