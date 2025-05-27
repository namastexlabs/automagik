"""Test cases for memory routes API endpoints."""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api.memory_routes import memory_router
from src.api.memory_models import MemoryCreate, MemoryUpdate
from src.db.models import Memory
from datetime import datetime


@pytest.fixture
def test_app():
    """Create test app with memory router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def sample_memory():
    """Sample memory for testing."""
    return Memory(
        id=uuid.uuid4(),
        name="test_memory",
        description="Test description",
        content="Test content",
        session_id=None,
        user_id=None,
        agent_id=1,
        read_mode="system_prompt",
        access="read",
        metadata={"test": "data"},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestMemoryValidation:
    """Test memory validation rules for agent global memory."""

    def test_create_memory_user_id_none_agent_id_provided_success(self, test_app):
        """Test successful creation of agent global memory (user_id=None, agent_id=provided)."""
        memory_data = {
            "name": "agent_global_memory",
            "content": "This is agent global memory",
            "user_id": None,
            "agent_id": 1
        }
        
        with patch('src.api.memory_routes.repo_create_memory') as mock_create, \
             patch('src.api.memory_routes.get_memory') as mock_get:
            
            mock_create.return_value = uuid.uuid4()
            mock_get.return_value = Memory(
                id=uuid.uuid4(),
                name="agent_global_memory",
                content="This is agent global memory",
                user_id=None,
                agent_id=1,
                description=None,
                session_id=None,
                read_mode=None,
                access=None,
                metadata=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            response = test_app.post("/api/v1/memories", json=memory_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["name"] == "agent_global_memory"
            assert result["user_id"] is None
            assert result["agent_id"] == 1

    def test_create_memory_user_id_provided_agent_id_provided_success(self, test_app):
        """Test successful creation of user-specific memory (user_id=provided, agent_id=provided)."""
        user_id = str(uuid.uuid4())
        memory_data = {
            "name": "user_specific_memory",
            "content": "This is user-specific memory",
            "user_id": user_id,
            "agent_id": 1
        }
        
        with patch('src.api.memory_routes.ensure_user_exists') as mock_ensure, \
             patch('src.api.memory_routes.repo_create_memory') as mock_create, \
             patch('src.api.memory_routes.get_memory') as mock_get:
            
            mock_ensure.return_value = uuid.UUID(user_id)
            mock_create.return_value = uuid.uuid4()
            mock_get.return_value = Memory(
                id=uuid.uuid4(),
                name="user_specific_memory",
                content="This is user-specific memory",
                user_id=uuid.UUID(user_id),
                agent_id=1,
                description=None,
                session_id=None,
                read_mode=None,
                access=None,
                metadata=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            response = test_app.post("/api/v1/memories", json=memory_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["name"] == "user_specific_memory"
            assert result["user_id"] == user_id
            assert result["agent_id"] == 1

    def test_create_memory_user_id_none_agent_id_none_validation_error(self, test_app):
        """Test validation error when both user_id and agent_id are None."""
        memory_data = {
            "name": "invalid_memory",
            "content": "This should fail validation",
            "user_id": None,
            "agent_id": None
        }
        
        response = test_app.post("/api/v1/memories", json=memory_data)
        
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
        # Verify the validation error mentions the validation rule
        assert any("agent_id is required when user_id is not provided" in str(detail) 
                  for detail in error_detail["detail"] if isinstance(detail, dict))

    def test_update_memory_valid_combination_success(self, test_app, sample_memory):
        """Test successful update maintaining valid user_id/agent_id combination."""
        memory_id = str(sample_memory.id)
        update_data = {
            "content": "Updated content"
        }
        
        with patch('src.api.memory_routes.get_memory') as mock_get, \
             patch('src.api.memory_routes.repo_update_memory') as mock_update:
            
            mock_get.side_effect = [sample_memory, sample_memory]  # Called twice: validation + return
            mock_update.return_value = sample_memory.id
            
            response = test_app.put(f"/api/v1/memories/{memory_id}", json=update_data)
            
            assert response.status_code == 200

    def test_update_memory_creates_invalid_combination_error(self, test_app, sample_memory):
        """Test validation error when update would create invalid state (both None)."""
        memory_id = str(sample_memory.id)
        update_data = {
            "user_id": None,
            "agent_id": None
        }
        
        with patch('src.api.memory_routes.get_memory') as mock_get:
            mock_get.return_value = sample_memory
            
            response = test_app.put(f"/api/v1/memories/{memory_id}", json=update_data)
            
            assert response.status_code == 422  # Pydantic validation error
            error_detail = response.json()
            assert "detail" in error_detail
            # Verify the validation error mentions the validation rule
            assert any("agent_id is required when user_id is not provided" in str(detail) 
                      for detail in error_detail["detail"] if isinstance(detail, dict))

    def test_batch_create_mixed_valid_invalid_memories(self, test_app):
        """Test batch creation with mix of valid and invalid memories."""
        memories_data = [
            {
                "name": "valid_agent_global",
                "content": "Valid agent global memory",
                "user_id": None,
                "agent_id": 1
            },
            {
                "name": "invalid_both_none",
                "content": "Invalid memory",
                "user_id": None,
                "agent_id": None
            },
            {
                "name": "valid_user_specific", 
                "content": "Valid user memory",
                "user_id": str(uuid.uuid4()),
                "agent_id": 1
            }
        ]
        
        # With Pydantic validation at the model level, the entire batch request
        # should fail when any item is invalid (422 validation error)
        response = test_app.post("/api/v1/memories/batch", json=memories_data)
        
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
        # Verify the validation error mentions the validation rule
        assert any("agent_id is required when user_id is not provided" in str(detail) 
                  for detail in error_detail["detail"] if isinstance(detail, dict))


class TestMemoryFiltering:
    """Test memory filtering for agent global vs user-specific memories."""

    def test_list_memories_filter_by_user_id_none(self, test_app):
        """Test listing memories with user_id=None filter (agent global memories)."""
        with patch('src.api.memory_routes.repo_list_memories') as mock_list:
            mock_list.return_value = []
            
            response = test_app.get("/api/v1/memories?user_id=None")
            
            # Should handle None string conversion properly
            assert response.status_code == 400  # Invalid UUID format

    def test_list_memories_filter_by_agent_id(self, test_app):
        """Test listing memories filtered by agent_id."""
        with patch('src.api.memory_routes.repo_list_memories') as mock_list:
            mock_list.return_value = []
            
            response = test_app.get("/api/v1/memories?agent_id=1")
            
            assert response.status_code == 200
            mock_list.assert_called_once_with(agent_id=1, user_id=None, session_id=None)


class TestMemoryModelsValidation:
    """Test validation at the Pydantic model level."""

    def test_memory_create_validation_user_id_none_agent_id_none(self):
        """Test Pydantic validation for invalid combination."""
        with pytest.raises(ValueError, match="agent_id is required when user_id is not provided"):
            MemoryCreate(
                name="test",
                content="test content",
                user_id=None,
                agent_id=None
            )

    def test_memory_create_validation_user_id_none_agent_id_provided(self):
        """Test Pydantic validation for valid agent global memory."""
        memory = MemoryCreate(
            name="test",
            content="test content",
            user_id=None,
            agent_id=1
        )
        assert memory.user_id is None
        assert memory.agent_id == 1

    def test_memory_update_validation_user_id_none_agent_id_none(self):
        """Test Pydantic validation for MemoryUpdate with invalid combination."""
        with pytest.raises(ValueError, match="agent_id is required when user_id is not provided"):
            MemoryUpdate(
                user_id=None,
                agent_id=None
            )

    def test_memory_update_validation_partial_update_valid(self):
        """Test Pydantic validation for partial update with valid values."""
        memory = MemoryUpdate(
            content="Updated content",
            agent_id=1
        )
        assert memory.content == "Updated content"
        assert memory.agent_id == 1
        assert memory.user_id is None  # Default None is OK when agent_id is provided 