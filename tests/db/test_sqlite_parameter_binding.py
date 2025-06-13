#!/usr/bin/env python3
"""
Comprehensive tests for SQLite parameter binding to prevent regressions.

This test suite specifically tests type conversion and parameter binding
edge cases that can cause "Error binding parameter X - probably unsupported type"
errors in SQLite.
"""

import pytest
import uuid
import json
from datetime import datetime

from src.db.providers.sqlite import SQLiteProvider


class TestSQLiteParameterBinding:
    """Test SQLite parameter binding with various data types."""
    
    @pytest.fixture
    def sqlite_provider(self, tmp_path):
        """Create a temporary SQLite provider for testing."""
        db_path = tmp_path / "test_binding.db"
        provider = SQLiteProvider(str(db_path))
        
        # Initialize the schema
        provider._initialize_schema()
        
        return provider
    
    def test_uuid_parameter_conversion(self, sqlite_provider):
        """Test that UUID objects are properly converted to strings."""
        test_uuid = uuid.uuid4()
        
        # Test with tuple parameters
        result = sqlite_provider._convert_params_to_sqlite((test_uuid, "test"))
        assert isinstance(result[0], str)
        assert result[0] == str(test_uuid)
        assert result[1] == "test"
        
        # Test with list parameters  
        result = sqlite_provider._convert_params_to_sqlite([test_uuid, "test"])
        assert isinstance(result[0], str)
        assert result[0] == str(test_uuid)
        assert result[1] == "test"
        
        # Test with dict parameters
        result = sqlite_provider._convert_params_to_sqlite({"id": test_uuid, "name": "test"})
        assert isinstance(result["id"], str)
        assert result["id"] == str(test_uuid)
        assert result["name"] == "test"
    
    def test_datetime_parameter_conversion(self, sqlite_provider):
        """Test that datetime objects are properly converted to ISO strings."""
        test_datetime = datetime.now()
        
        # Test with tuple parameters
        result = sqlite_provider._convert_params_to_sqlite((test_datetime, "test"))
        assert isinstance(result[0], str)
        assert result[0] == test_datetime.isoformat()
        
        # Test with list parameters
        result = sqlite_provider._convert_params_to_sqlite([test_datetime, "test"])
        assert isinstance(result[0], str)
        assert result[0] == test_datetime.isoformat()
        
        # Test with dict parameters
        result = sqlite_provider._convert_params_to_sqlite({"created_at": test_datetime, "name": "test"})
        assert isinstance(result["created_at"], str)
        assert result["created_at"] == test_datetime.isoformat()
    
    def test_mixed_parameter_types(self, sqlite_provider):
        """Test parameter conversion with mixed data types."""
        test_uuid = uuid.uuid4()
        test_datetime = datetime.now()
        test_dict = {"key": "value"}
        
        params = [
            test_uuid,           # UUID object
            test_datetime,       # datetime object
            "string_value",      # string
            42,                  # int
            3.14,               # float
            None,               # None
            test_dict,          # dict (should be converted to string)
            True,               # bool (should be converted to string)
        ]
        
        result = sqlite_provider._convert_params_to_sqlite(params)
        
        assert isinstance(result[0], str)  # UUID -> string
        assert isinstance(result[1], str)  # datetime -> string
        assert isinstance(result[2], str)  # string unchanged
        assert isinstance(result[3], int)  # int unchanged
        assert isinstance(result[4], float)  # float unchanged
        assert result[5] is None  # None unchanged
        assert isinstance(result[6], str)  # dict -> string
        assert isinstance(result[7], int)  # bool -> integer
    
    def test_user_creation_with_uuid(self, sqlite_provider):
        """Test creating a user with UUID to ensure no parameter binding errors."""
        user_id = uuid.uuid4()
        
        query = """
        INSERT INTO users (id, email, created_at, updated_at)
        VALUES (%s, %s, %s, %s)
        """
        
        params = [
            user_id,
            "test@example.com", 
            datetime.now(),
            datetime.now()
        ]
        
        # This should not raise a parameter binding error
        sqlite_provider.execute_query(query, params, fetch=False)
        
        # Verify the user was created
        result = sqlite_provider.execute_query(
            "SELECT id, email FROM users WHERE email = %s",
            ["test@example.com"]
        )
        
        assert len(result) == 1
        assert result[0]["id"] == str(user_id)
        assert result[0]["email"] == "test@example.com"
    
    def test_session_creation_with_mixed_types(self, sqlite_provider):
        """Test session creation with various parameter types."""
        # First create a user and agent
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        # Create user
        sqlite_provider.execute_query(
            "INSERT INTO users (id, email, created_at, updated_at) VALUES (%s, %s, %s, %s)",
            [user_id, "session_test@example.com", datetime.now(), datetime.now()],
            fetch=False
        )
        
        # Create agent
        sqlite_provider.execute_query(
            "INSERT INTO agents (name, type, model, config, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
            ["test_agent", "simple", "gpt-4", json.dumps({"test": True}), datetime.now(), datetime.now()],
            fetch=False
        )
        
        # Get agent ID
        agent_result = sqlite_provider.execute_query("SELECT id FROM agents WHERE name = %s", ["test_agent"])
        agent_id = agent_result[0]["id"]
        
        # Create session with mixed parameter types
        query = """
        INSERT INTO sessions (id, user_id, agent_id, name, platform, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        params = [
            session_id,          # UUID
            user_id,            # UUID  
            agent_id,           # int
            "test_session",     # string
            "test_platform",    # string
            datetime.now(),     # datetime
            datetime.now()      # datetime
        ]
        
        # This should not raise a parameter binding error
        sqlite_provider.execute_query(query, params, fetch=False)
        
        # Verify session was created
        result = sqlite_provider.execute_query(
            "SELECT id, name FROM sessions WHERE name = %s",
            ["test_session"]
        )
        
        assert len(result) == 1
        assert result[0]["id"] == str(session_id)
    
    def test_message_creation_with_complex_data(self, sqlite_provider):
        """Test message creation with complex data types including JSON."""
        # Create prerequisite data
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        
        # Create user
        sqlite_provider.execute_query(
            "INSERT INTO users (id, email, created_at, updated_at) VALUES (%s, %s, %s, %s)",
            [user_id, "message_test@example.com", datetime.now(), datetime.now()],
            fetch=False
        )
        
        # Create agent
        sqlite_provider.execute_query(
            "INSERT INTO agents (name, type, model, config, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
            ["message_agent", "simple", "gpt-4", json.dumps({"test": True}), datetime.now(), datetime.now()],
            fetch=False
        )
        
        agent_result = sqlite_provider.execute_query("SELECT id FROM agents WHERE name = %s", ["message_agent"])
        agent_id = agent_result[0]["id"]
        
        # Create session
        sqlite_provider.execute_query(
            "INSERT INTO sessions (id, user_id, agent_id, name, platform, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [session_id, user_id, agent_id, "message_session", "test", datetime.now(), datetime.now()],
            fetch=False
        )
        
        # Create message with complex data
        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "bool": True,
            "number": 42.5
        }
        
        query = """
        INSERT INTO messages (
            id, session_id, user_id, agent_id, role, text_content, 
            message_type, raw_payload, context, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = [
            message_id,                      # UUID
            session_id,                     # UUID
            user_id,                        # UUID
            agent_id,                       # int
            "user",                         # string
            "Test message content",         # string
            "text",                         # string
            json.dumps(complex_metadata),   # JSON string
            json.dumps({"context": True}),  # JSON string
            datetime.now(),                 # datetime
            datetime.now()                  # datetime
        ]
        
        # This should not raise a parameter binding error
        sqlite_provider.execute_query(query, params, fetch=False)
        
        # Verify message was created and JSON is parsed back correctly
        result = sqlite_provider.execute_query(
            "SELECT id, raw_payload, context FROM messages WHERE id = %s",
            [message_id]
        )
        
        assert len(result) == 1
        assert result[0]["id"] == str(message_id)
        # SQLite provider should auto-parse JSON fields
        assert isinstance(result[0]["raw_payload"], dict)
        assert result[0]["raw_payload"]["nested"]["key"] == "value"
    
    def test_none_parameters(self, sqlite_provider):
        """Test that None parameters are handled correctly."""
        result = sqlite_provider._convert_params_to_sqlite(None)
        assert result is None
        
        result = sqlite_provider._convert_params_to_sqlite([None, "test", None])
        assert result[0] is None
        assert result[1] == "test"
        assert result[2] is None
    
    def test_edge_case_parameter_types(self, sqlite_provider):
        """Test edge case parameter types that might cause binding errors."""
        # Test with empty containers
        result = sqlite_provider._convert_params_to_sqlite([])
        assert result == []
        
        result = sqlite_provider._convert_params_to_sqlite(())
        assert result == ()
        
        result = sqlite_provider._convert_params_to_sqlite({})
        assert result == {}
        
        # Test with complex objects that should be stringified
        class CustomObject:
            def __str__(self):
                return "custom_object_string"
        
        custom_obj = CustomObject()
        result = sqlite_provider._convert_params_to_sqlite([custom_obj])
        assert result[0] == "custom_object_string"


class TestParameterBindingRegression:
    """Regression tests for specific parameter binding issues found in production."""
    
    def test_session_creation_parameter_binding(self):
        """Regression test for session creation parameter binding error."""
        from src.db.models import Session
        from src.db.repository.session import create_session
        
        # This previously failed with "Error binding parameter 1 - probably unsupported type"
        test_session = Session(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),  # This was causing the binding error
            agent_id=1,
            name=f'test_session_{uuid.uuid4().hex[:8]}',
            platform='test',
            metadata={'test': True},
            run_finished_at=datetime.now()
        )
        
        # This should not raise a parameter binding error anymore
        # (It may fail with FK constraint, but not parameter binding)
        try:
            create_session(test_session)
        except Exception as e:
            # Should not be a parameter binding error
            assert "Error binding parameter" not in str(e)
    
    def test_message_creation_parameter_binding(self):
        """Regression test for message creation parameter binding error."""
        from src.db.models import Message
        from src.db.repository.message import create_message
        
        # This previously failed with "Error binding parameter 0 - probably unsupported type"
        test_message = Message(
            id=uuid.uuid4(),        # This was causing the binding error
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            agent_id=1,
            role='user',
            text_content='Test message',
            message_type='text',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # This should not raise a parameter binding error anymore
        try:
            create_message(test_message)
        except Exception as e:
            # Should not be a parameter binding error
            assert "Error binding parameter" not in str(e)
    
    def test_list_messages_parameter_binding(self):
        """Regression test for list_messages parameter binding error."""
        from src.db.repository.message import list_messages
        
        # This previously failed with parameter binding for session_id UUID
        session_id = uuid.uuid4()
        
        try:
            messages, count = list_messages(session_id=session_id)
        except Exception as e:
            # Should not be a parameter binding error
            assert "Error binding parameter" not in str(e)