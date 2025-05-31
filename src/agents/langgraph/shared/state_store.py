"""State store for LangGraph orchestration persistence.

This module handles persisting orchestration state to the database using the existing
sessions and messages tables with JSONB metadata fields for orchestration data.
"""

import uuid
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

from src.db.repository.session import create_session, update_session, get_session
from src.db.repository.message import create_message, list_messages
from src.db.models import Session, Message

logger = logging.getLogger(__name__)

@dataclass
class OrchestrationState:
    """Orchestration state for LangGraph workflows."""
    orchestration_type: str = "langgraph"
    claude_session_id: Optional[str] = None
    git_sha_start: Optional[str] = None
    git_sha_end: Optional[str] = None
    workspace_path: Optional[str] = None
    pid: Optional[int] = None
    group_chat_session_id: Optional[str] = None
    rollback_commits: List[Dict[str, Any]] = None
    process_status: str = "running"  # running|hung|failed|stopped
    breakpoint_state: str = "running"  # running|paused|waiting_human
    target_agents: List[str] = None
    workspace_paths: Dict[str, str] = None
    max_rounds: int = 5
    enable_rollback: bool = True
    process_monitoring: Dict[str, Any] = None
    breakpoint_config: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.rollback_commits is None:
            self.rollback_commits = []
        if self.target_agents is None:
            self.target_agents = []
        if self.workspace_paths is None:
            self.workspace_paths = {}
        if self.process_monitoring is None:
            self.process_monitoring = {
                "check_interval": 30,
                "shutdown_timeout": 5,
                "enable_monitoring": True
            }
        if self.breakpoint_config is None:
            self.breakpoint_config = {
                "enable_breakpoints": True,
                "auto_pause_on_error": False
            }

class OrchestrationStateStore:
    """Manages orchestration state persistence in the database."""

    @staticmethod
    def create_orchestration_session(
        name: str,
        agent_id: int,
        user_id: Optional[uuid.UUID] = None,
        orchestration_state: Optional[OrchestrationState] = None
    ) -> Optional[uuid.UUID]:
        """Create a new orchestration session.
        
        Args:
            name: Session name
            agent_id: Agent ID (Alpha orchestrator typically)
            user_id: Optional user ID
            orchestration_state: Initial orchestration state
            
        Returns:
            Session UUID if successful, None otherwise
        """
        try:
            # Create session with orchestration metadata
            session_id = uuid.uuid4()
            
            # Prepare metadata with orchestration state
            metadata = {}
            if orchestration_state:
                metadata.update(asdict(orchestration_state))
            
            # Create session object
            session = Session(
                id=session_id,
                name=name,
                agent_id=agent_id,
                user_id=user_id,
                metadata=metadata,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Create in database
            created_id = create_session(session)
            if created_id:
                logger.info(f"Created orchestration session {created_id} for agent {agent_id}")
                return created_id
            else:
                logger.error(f"Failed to create orchestration session for agent {agent_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating orchestration session: {str(e)}")
            return None

    @staticmethod
    def update_orchestration_state(
        session_id: uuid.UUID,
        orchestration_state: OrchestrationState
    ) -> bool:
        """Update orchestration state for a session.
        
        Args:
            session_id: Session UUID
            orchestration_state: Updated orchestration state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing session
            session = get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found for state update")
                return False
            
            # Update metadata with new orchestration state
            if not session.metadata:
                session.metadata = {}
            
            session.metadata.update(asdict(orchestration_state))
            session.updated_at = datetime.now()
            
            # Update in database
            updated_id = update_session(session)
            if updated_id:
                logger.debug(f"Updated orchestration state for session {session_id}")
                return True
            else:
                logger.error(f"Failed to update orchestration state for session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating orchestration state: {str(e)}")
            return False

    @staticmethod
    def get_orchestration_state(session_id: uuid.UUID) -> Optional[OrchestrationState]:
        """Get orchestration state from a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            OrchestrationState if found, None otherwise
        """
        try:
            session = get_session(session_id)
            if not session or not session.metadata:
                return None
            
            # Extract orchestration data from metadata
            orchestration_data = {}
            for key in OrchestrationState.__dataclass_fields__.keys():
                if key in session.metadata:
                    orchestration_data[key] = session.metadata[key]
            
            if orchestration_data:
                return OrchestrationState(**orchestration_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting orchestration state: {str(e)}")
            return None

    @staticmethod
    def create_group_chat_message(
        session_id: uuid.UUID,
        sender_agent_id: int,
        target_agent_id: Optional[int],
        message_content: str,
        message_type: str = "group_chat"
    ) -> Optional[uuid.UUID]:
        """Create a group chat message between agents.
        
        Args:
            session_id: Orchestration session UUID
            sender_agent_id: ID of sending agent
            target_agent_id: ID of target agent (None for broadcast)
            message_content: Message content
            message_type: Message type (default: group_chat)
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            message_id = uuid.uuid4()
            
            # Create message context for inter-agent communication
            context = {
                "target_agent_id": target_agent_id,
                "sender_agent_id": sender_agent_id,
                "message_type": message_type
            }
            
            # Create message object
            message = Message(
                id=message_id,
                session_id=session_id,
                agent_id=sender_agent_id,
                role="assistant",  # Inter-agent messages are assistant role
                text_content=message_content,
                message_type=message_type,
                context=context,
                flagged="pending",  # pending|delivered|failed
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Create in database
            created_id = create_message(message)
            if created_id:
                logger.info(f"Created group chat message {created_id} from agent {sender_agent_id} to {target_agent_id}")
                return created_id
            else:
                logger.error(f"Failed to create group chat message")
                return None
                
        except Exception as e:
            logger.error(f"Error creating group chat message: {str(e)}")
            return None

    @staticmethod
    def get_group_chat_messages(
        session_id: uuid.UUID,
        target_agent_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Message]:
        """Get group chat messages for an agent.
        
        Args:
            session_id: Orchestration session UUID
            target_agent_id: Filter for specific target agent (None for all)
            limit: Maximum number of messages to return
            
        Returns:
            List of Message objects
        """
        try:
            # Get messages for the session
            messages = list_messages(session_id, limit=limit, sort_desc=True)
            
            # Filter for group chat messages
            group_chat_messages = []
            for message in messages:
                if (message.message_type == "group_chat" and 
                    message.context and 
                    isinstance(message.context, dict)):
                    
                    # Filter by target agent if specified
                    if target_agent_id is not None:
                        msg_target = message.context.get("target_agent_id")
                        if msg_target != target_agent_id and msg_target is not None:
                            continue  # Skip messages not for this agent
                    
                    group_chat_messages.append(message)
            
            return group_chat_messages
            
        except Exception as e:
            logger.error(f"Error getting group chat messages: {str(e)}")
            return []

    @staticmethod
    def update_message_status(message_id: uuid.UUID, status: str) -> bool:
        """Update the delivery status of a group chat message.
        
        Args:
            message_id: Message UUID
            status: New status (pending|delivered|failed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.db.repository.message import update_message, get_message
            
            # Get the message
            message = get_message(message_id)
            if not message:
                logger.error(f"Message {message_id} not found for status update")
                return False
            
            # Update flagged status
            message.flagged = status
            message.updated_at = datetime.now()
            
            # Update in database
            updated_id = update_message(message)
            if updated_id:
                logger.debug(f"Updated message {message_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update message {message_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating message status: {str(e)}")
            return False

    @staticmethod
    def add_rollback_commit(
        session_id: uuid.UUID,
        commit_sha: str,
        reason: str
    ) -> bool:
        """Add a rollback commit to the orchestration state.
        
        Args:
            session_id: Session UUID
            commit_sha: Git commit SHA that was rolled back
            reason: Reason for rollback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current orchestration state
            state = OrchestrationStateStore.get_orchestration_state(session_id)
            if not state:
                logger.error(f"No orchestration state found for session {session_id}")
                return False
            
            # Add rollback commit
            rollback_info = {
                "sha": commit_sha,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            state.rollback_commits.append(rollback_info)
            
            # Update state
            return OrchestrationStateStore.update_orchestration_state(session_id, state)
            
        except Exception as e:
            logger.error(f"Error adding rollback commit: {str(e)}")
            return False 