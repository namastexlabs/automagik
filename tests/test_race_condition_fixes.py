"""Tests for race condition fixes in workflow creation.

This test suite verifies that the race condition fixes properly handle:
1. Concurrent workflow creation with same run_id
2. Worktree path collisions
3. Invalid session_id handling
"""

import asyncio
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from src.agents.claude_code.utils.race_condition_helpers import (
    generate_unique_run_id,
    create_workflow_with_retry,
    ensure_unique_worktree_path,
    validate_session_id
)


@pytest.mark.asyncio
async def test_generate_unique_run_id_no_collision():
    """Test generating unique run ID when no collision exists."""
    with patch('src.agents.claude_code.utils.race_condition_helpers.get_workflow_run_by_run_id') as mock_get:
        mock_get.return_value = None  # No existing workflow
        
        run_id = await generate_unique_run_id()
        
        assert run_id is not None
        assert len(run_id) == 36  # Standard UUID length
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_generate_unique_run_id_with_collision():
    """Test generating unique run ID with collision handling."""
    call_count = 0
    
    def mock_get_workflow(run_id):
        nonlocal call_count
        call_count += 1
        # First call returns existing workflow, second returns None
        return MagicMock() if call_count == 1 else None
    
    with patch('src.agents.claude_code.utils.race_condition_helpers.get_workflow_run_by_run_id', 
               side_effect=mock_get_workflow):
        
        run_id = await generate_unique_run_id()
        
        assert run_id is not None
        assert call_count == 2  # Should have tried twice


@pytest.mark.asyncio
async def test_create_workflow_with_retry_success():
    """Test successful workflow creation on first attempt."""
    test_data = {
        'run_id': 'test-run-123',
        'workflow_name': 'test',
        'status': 'pending'
    }
    
    with patch('src.agents.claude_code.utils.race_condition_helpers.create_workflow_run') as mock_create:
        mock_create.return_value = 'workflow-id-123'
        
        result = await create_workflow_with_retry(test_data)
        
        assert result == 'workflow-id-123'
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_create_workflow_with_retry_race_condition():
    """Test workflow creation with race condition handling."""
    test_data = {
        'run_id': 'test-run-123',
        'workflow_name': 'test',
        'status': 'pending'
    }
    
    existing_workflow = MagicMock()
    existing_workflow.id = 'existing-workflow-id'
    existing_workflow.status = 'pending'
    
    with patch('src.agents.claude_code.utils.race_condition_helpers.create_workflow_run') as mock_create:
        with patch('src.agents.claude_code.utils.race_condition_helpers.get_workflow_run_by_run_id') as mock_get:
            with patch('src.agents.claude_code.utils.race_condition_helpers.generate_unique_run_id') as mock_gen_id:
                # First create fails with "already exists"
                mock_create.side_effect = [
                    ValueError("Workflow run with run_id 'test-run-123' already exists"),
                    'new-workflow-id'
                ]
                mock_get.return_value = None  # Workflow doesn't exist anymore
                mock_gen_id.return_value = 'new-run-id-456'
                
                result = await create_workflow_with_retry(test_data)
                
                assert result == 'new-workflow-id'
                assert mock_create.call_count == 2
                assert test_data['run_id'] == 'new-run-id-456'  # Run ID was updated


@pytest.mark.asyncio
async def test_ensure_unique_worktree_path_no_collision():
    """Test worktree path generation without collision."""
    base_path = Path('/tmp/worktrees')
    branch_name = 'feature/test-branch'
    run_id = 'test-run-123'
    
    with patch('pathlib.Path.exists', return_value=False):
        path = await ensure_unique_worktree_path(base_path, branch_name, run_id, persistent=False)
        
        assert str(path) == '/tmp/worktrees/feature-test-branch-test-run'


@pytest.mark.asyncio
async def test_ensure_unique_worktree_path_with_collision():
    """Test worktree path generation with collision handling."""
    base_path = Path('/tmp/worktrees')
    branch_name = 'feature/test-branch'
    run_id = 'test-run-123'
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('time.time', return_value=1234567890.123):
            path = await ensure_unique_worktree_path(base_path, branch_name, run_id, persistent=False)
            
            assert 'feature-test-branch-test-run-1234567890123' in str(path)


def test_validate_session_id_valid():
    """Test validation of valid session IDs."""
    valid_uuid = str(uuid.uuid4())
    result = validate_session_id(valid_uuid)
    assert result == valid_uuid


def test_validate_session_id_invalid():
    """Test validation of invalid session IDs."""
    assert validate_session_id(None) is None
    assert validate_session_id('') is None
    assert validate_session_id('not-a-uuid') is None
    assert validate_session_id('123') is None


def test_validate_session_id_various_formats():
    """Test validation of various UUID formats."""
    # Standard UUID
    uuid1 = '550e8400-e29b-41d4-a716-446655440000'
    assert validate_session_id(uuid1) == uuid1
    
    # UUID without hyphens (should fail)
    uuid2 = '550e8400e29b41d4a716446655440000'
    assert validate_session_id(uuid2) is None
    
    # Uppercase UUID
    uuid3 = '550E8400-E29B-41D4-A716-446655440000'
    assert validate_session_id(uuid3) == uuid3