"""Tests for the prompt repository module."""
import pytest
from unittest.mock import patch, MagicMock

from src.db.models import PromptCreate
from src.db.repository.prompt import (
    get_prompt_by_id,
    get_active_prompt,
    get_latest_version_for_status,
    create_prompt,
    set_prompt_active
)

# Sample data
TEST_AGENT_ID = 1
TEST_STATUS_KEY = "default"
TEST_PROMPT_TEXT = "This is a test prompt."
TEST_PROMPT_NAME = "Test Prompt"

@pytest.fixture
def mock_execute_query():
    with patch('src.db.repository.prompt.execute_query') as mock:
        yield mock

class TestPromptRepository:
    """Test suite for prompt repository functions."""
    
    def test_get_prompt_by_id(self, mock_execute_query):
        """Test getting a prompt by ID."""
        # Setup
        mock_result = [{
            "id": 1,
            "agent_id": TEST_AGENT_ID,
            "prompt_text": TEST_PROMPT_TEXT,
            "version": 1,
            "is_active": True,
            "is_default_from_code": True,
            "status_key": TEST_STATUS_KEY,
            "name": TEST_PROMPT_NAME,
            "created_at": "2025-05-13T00:00:00Z",
            "updated_at": "2025-05-13T00:00:00Z",
        }]
        mock_execute_query.return_value = mock_result
        
        # Exercise
        prompt = get_prompt_by_id(1)
        
        # Verify
        assert prompt is not None
        assert prompt.id == 1
        assert prompt.agent_id == TEST_AGENT_ID
        assert prompt.prompt_text == TEST_PROMPT_TEXT
        assert prompt.status_key == TEST_STATUS_KEY
        mock_execute_query.assert_called_once()
    
    def test_get_active_prompt(self, mock_execute_query):
        """Test getting the active prompt for an agent and status key."""
        # Setup
        mock_result = [{
            "id": 1,
            "agent_id": TEST_AGENT_ID,
            "prompt_text": TEST_PROMPT_TEXT,
            "version": 1,
            "is_active": True,
            "is_default_from_code": True,
            "status_key": TEST_STATUS_KEY,
            "name": TEST_PROMPT_NAME,
            "created_at": "2025-05-13T00:00:00Z",
            "updated_at": "2025-05-13T00:00:00Z",
        }]
        mock_execute_query.return_value = mock_result
        
        # Exercise
        prompt = get_active_prompt(TEST_AGENT_ID, TEST_STATUS_KEY)
        
        # Verify
        assert prompt is not None
        assert prompt.agent_id == TEST_AGENT_ID
        assert prompt.status_key == TEST_STATUS_KEY
        assert prompt.is_active
        mock_execute_query.assert_called_once()
        
    def test_get_latest_version_for_status(self, mock_execute_query):
        """Test getting the latest version number for a status."""
        # Setup
        mock_result = [{"max_version": 3}]
        mock_execute_query.return_value = mock_result
        
        # Exercise
        version = get_latest_version_for_status(TEST_AGENT_ID, TEST_STATUS_KEY)
        
        # Verify
        assert version == 3
        mock_execute_query.assert_called_once()
    
    def test_create_prompt(self, mock_execute_query):
        """Test creating a new prompt."""
        # Setup
        mock_execute_query.side_effect = [
            # First call - get_latest_version_for_status
            [{"max_version": 2}],
            # Second call - execute deactivation query
            None,
            # Third call - insert prompt
            [{"id": 3}],
            # Fourth call - update agent's active_default_prompt_id
            None
        ]
        
        # Create prompt data
        prompt_data = PromptCreate(
            agent_id=TEST_AGENT_ID,
            prompt_text=TEST_PROMPT_TEXT,
            is_active=True,
            status_key=TEST_STATUS_KEY,
            name=TEST_PROMPT_NAME
        )
        
        # Exercise
        prompt_id = create_prompt(prompt_data)
        
        # Verify
        assert prompt_id == 3
        assert mock_execute_query.call_count == 4
    
    def test_set_prompt_active(self, mock_execute_query):
        """Test setting a prompt as active."""
        # Setup
        mock_get_prompt = MagicMock()
        mock_get_prompt.return_value.id = 1
        mock_get_prompt.return_value.agent_id = TEST_AGENT_ID
        mock_get_prompt.return_value.status_key = TEST_STATUS_KEY
        mock_get_prompt.return_value.is_active = False
        
        with patch('src.db.repository.prompt.get_prompt_by_id', mock_get_prompt):
            # Exercise
            result = set_prompt_active(1, True)
            
            # Verify
            assert result
            assert mock_execute_query.call_count == 3  # Deactivate others + activate this one + update agent's active_default_prompt_id 