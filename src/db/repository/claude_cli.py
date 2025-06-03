"""Repository for Claude CLI runs and sessions."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
import asyncpg

from ..repository import BaseRepository

logger = logging.getLogger(__name__)


class ClaudeCLIRepository(BaseRepository):
    """Repository for managing Claude CLI runs and sessions."""
    
    async def create_run(
        self,
        workflow_name: str,
        branch: str,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new Claude CLI run.
        
        Args:
            workflow_name: Name of the workflow
            branch: Git branch name
            user_id: Optional user ID
            agent_id: Optional agent ID
            metadata: Optional metadata
            
        Returns:
            Created run record
        """
        query = """
            INSERT INTO claude_cli_runs 
            (workflow_name, branch, status, user_id, agent_id, metadata)
            VALUES ($1, $2, 'queued', $3, $4, $5)
            RETURNING 
                run_id, session_id, workflow_name, branch, status,
                workspace_path, started_at, completed_at, error_message,
                metadata, execution_time_seconds, exit_code,
                user_id, agent_id, created_at, updated_at
        """
        
        metadata = metadata or {}
        
        row = await self.db.fetchrow(
            query, workflow_name, branch, user_id, agent_id, json.dumps(metadata)
        )
        
        return self._row_to_dict(row)
    
    async def update_run(
        self,
        run_id: UUID,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        workspace_path: Optional[str] = None,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time_seconds: Optional[float] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update a Claude CLI run.
        
        Args:
            run_id: Run ID to update
            status: New status
            session_id: Claude session ID
            workspace_path: Workspace path
            error_message: Error message if failed
            exit_code: Process exit code
            execution_time_seconds: Execution time
            metadata_update: Metadata to merge
            
        Returns:
            Updated run record
        """
        # Build update query dynamically
        updates = []
        params = [run_id]
        param_idx = 2
        
        if status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
            
            if status == 'completed' or status == 'failed':
                updates.append(f"completed_at = ${param_idx}")
                params.append(datetime.utcnow())
                param_idx += 1
        
        if session_id is not None:
            updates.append(f"session_id = ${param_idx}")
            params.append(session_id)
            param_idx += 1
        
        if workspace_path is not None:
            updates.append(f"workspace_path = ${param_idx}")
            params.append(workspace_path)
            param_idx += 1
        
        if error_message is not None:
            updates.append(f"error_message = ${param_idx}")
            params.append(error_message)
            param_idx += 1
        
        if exit_code is not None:
            updates.append(f"exit_code = ${param_idx}")
            params.append(exit_code)
            param_idx += 1
        
        if execution_time_seconds is not None:
            updates.append(f"execution_time_seconds = ${param_idx}")
            params.append(execution_time_seconds)
            param_idx += 1
        
        if metadata_update:
            updates.append(f"metadata = metadata || ${param_idx}")
            params.append(json.dumps(metadata_update))
            param_idx += 1
        
        if not updates:
            # Nothing to update
            return await self.get_run(run_id)
        
        query = f"""
            UPDATE claude_cli_runs
            SET {', '.join(updates)}
            WHERE run_id = $1
            RETURNING 
                run_id, session_id, workflow_name, branch, status,
                workspace_path, started_at, completed_at, error_message,
                metadata, execution_time_seconds, exit_code,
                user_id, agent_id, created_at, updated_at
        """
        
        row = await self.db.fetchrow(query, *params)
        
        if not row:
            raise ValueError(f"Run {run_id} not found")
        
        return self._row_to_dict(row)
    
    async def get_run(self, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a Claude CLI run by ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            Run record or None
        """
        query = """
            SELECT 
                run_id, session_id, workflow_name, branch, status,
                workspace_path, started_at, completed_at, error_message,
                metadata, execution_time_seconds, exit_code,
                user_id, agent_id, created_at, updated_at
            FROM claude_cli_runs
            WHERE run_id = $1
        """
        
        row = await self.db.fetchrow(query, run_id)
        
        return self._row_to_dict(row) if row else None
    
    async def list_runs(
        self,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        workflow_name: Optional[str] = None,
        status: Optional[str] = None,
        branch: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List Claude CLI runs with filters.
        
        Args:
            user_id: Filter by user
            agent_id: Filter by agent
            workflow_name: Filter by workflow
            status: Filter by status
            branch: Filter by branch
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List of run records
        """
        # Build query with filters
        where_clauses = []
        params = []
        param_idx = 1
        
        if user_id:
            where_clauses.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1
        
        if agent_id:
            where_clauses.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        
        if workflow_name:
            where_clauses.append(f"workflow_name = ${param_idx}")
            params.append(workflow_name)
            param_idx += 1
        
        if status:
            where_clauses.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
        
        if branch:
            where_clauses.append(f"branch = ${param_idx}")
            params.append(branch)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Add limit and offset
        params.extend([limit, offset])
        limit_idx = param_idx
        offset_idx = param_idx + 1
        
        query = f"""
            SELECT 
                run_id, session_id, workflow_name, branch, status,
                workspace_path, started_at, completed_at, error_message,
                metadata, execution_time_seconds, exit_code,
                user_id, agent_id, created_at, updated_at
            FROM claude_cli_runs
            {where_clause}
            ORDER BY started_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}
        """
        
        rows = await self.db.fetch(query, *params)
        
        return [self._row_to_dict(row) for row in rows]
    
    async def save_output(
        self,
        run_id: UUID,
        output_type: str,
        content: Dict[str, Any],
        sequence_number: int
    ) -> int:
        """Save Claude CLI output.
        
        Args:
            run_id: Run ID
            output_type: Type of output
            content: JSON content
            sequence_number: Sequence number
            
        Returns:
            Output record ID
        """
        query = """
            INSERT INTO claude_cli_outputs
            (run_id, output_type, content, sequence_number)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        
        row = await self.db.fetchrow(
            query, run_id, output_type, json.dumps(content), sequence_number
        )
        
        return row['id']
    
    async def get_outputs(
        self,
        run_id: UUID,
        output_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get outputs for a run.
        
        Args:
            run_id: Run ID
            output_type: Filter by type
            limit: Maximum results
            
        Returns:
            List of output records
        """
        params = [run_id]
        where_clauses = ["run_id = $1"]
        param_idx = 2
        
        if output_type:
            where_clauses.append(f"output_type = ${param_idx}")
            params.append(output_type)
            param_idx += 1
        
        limit_clause = ""
        if limit:
            limit_clause = f"LIMIT ${param_idx}"
            params.append(limit)
        
        query = f"""
            SELECT 
                id, run_id, timestamp, output_type, 
                content, sequence_number, created_at
            FROM claude_cli_outputs
            WHERE {' AND '.join(where_clauses)}
            ORDER BY sequence_number
            {limit_clause}
        """
        
        rows = await self.db.fetch(query, *params)
        
        return [self._row_to_dict(row) for row in rows]
    
    async def create_session(
        self,
        session_id: str,
        run_id: UUID,
        workflow_name: str,
        max_turns: int = 2,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Claude CLI session.
        
        Args:
            session_id: Claude session ID
            run_id: Associated run ID
            workflow_name: Workflow name
            max_turns: Maximum turns
            metadata: Optional metadata
            
        Returns:
            Created session record
        """
        query = """
            INSERT INTO claude_cli_sessions
            (session_id, run_id, workflow_name, max_turns, metadata)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (session_id) DO UPDATE
            SET last_used_at = CURRENT_TIMESTAMP
            RETURNING 
                session_id, run_id, workflow_name, max_turns,
                created_at, last_used_at, metadata
        """
        
        metadata = metadata or {}
        
        row = await self.db.fetchrow(
            query, session_id, run_id, workflow_name, max_turns, json.dumps(metadata)
        )
        
        return self._row_to_dict(row)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a Claude CLI session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session record or None
        """
        query = """
            SELECT 
                session_id, run_id, workflow_name, max_turns,
                created_at, last_used_at, metadata
            FROM claude_cli_sessions
            WHERE session_id = $1
        """
        
        row = await self.db.fetchrow(query, session_id)
        
        return self._row_to_dict(row) if row else None
    
    async def update_session_last_used(self, session_id: str) -> bool:
        """Update session last used timestamp.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if updated
        """
        query = """
            UPDATE claude_cli_sessions
            SET last_used_at = CURRENT_TIMESTAMP
            WHERE session_id = $1
        """
        
        result = await self.db.execute(query, session_id)
        
        return result.split()[-1] != '0'
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up old sessions.
        
        Args:
            days: Days to keep sessions
            
        Returns:
            Number of deleted sessions
        """
        query = """
            DELETE FROM claude_cli_sessions
            WHERE last_used_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            RETURNING session_id
        """
        
        rows = await self.db.fetch(query, days)
        
        return len(rows)
    
    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """Convert database row to dictionary.
        
        Args:
            row: Database row
            
        Returns:
            Dictionary representation
        """
        if not row:
            return {}
        
        result = dict(row)
        
        # Convert UUID to string
        for key in ['run_id', 'user_id', 'agent_id']:
            if key in result and result[key]:
                result[key] = str(result[key])
        
        # Parse JSON fields
        for key in ['metadata', 'content']:
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = json.loads(result[key])
                except json.JSONDecodeError:
                    pass
        
        # Convert timestamps to ISO format
        for key in ['started_at', 'completed_at', 'created_at', 'updated_at', 'timestamp', 'last_used_at']:
            if key in result and result[key]:
                result[key] = result[key].isoformat()
        
        return result