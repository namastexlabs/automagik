"""Slack-integrated messaging system for LangGraph orchestration.

This module enhances the existing messaging system with Slack integration,
allowing agents to communicate via both database messages and Slack threads.
"""

import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .messaging import AgentMessenger, OrchestrationMessenger as BaseOrchestrationMessenger
from .slack_messenger import SlackOrchestrationMessenger, SlackAgentAdapter
from .state_store import OrchestrationStateStore
from src.db.models import Message

logger = logging.getLogger(__name__)


class SlackEnabledAgentMessenger(AgentMessenger):
    """Agent messenger with Slack integration."""
    
    def __init__(
        self, 
        session_id: uuid.UUID, 
        agent_id: int,
        agent_name: str,
        slack_thread_ts: Optional[str] = None
    ):
        """Initialize messenger with Slack support.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: ID of this agent
            agent_name: Human-readable agent name
            slack_thread_ts: Slack thread timestamp for this session
        """
        super().__init__(session_id, agent_id)
        self.agent_name = agent_name
        self.slack_adapter = None
        
        if slack_thread_ts:
            self.slack_adapter = SlackAgentAdapter(agent_name, slack_thread_ts)
    
    async def send_message_async(
        self, 
        message: str, 
        target_agent_id: Optional[int] = None,
        target_agent_name: Optional[str] = None,
        message_type: str = "group_chat",
        send_to_slack: bool = True
    ) -> Optional[uuid.UUID]:
        """Send a message with Slack integration (async version).
        
        Args:
            message: Message content
            target_agent_id: ID of target agent (None for broadcast to all)
            target_agent_name: Name of target agent (for Slack)
            message_type: Type of message (default: group_chat)
            send_to_slack: Whether to also send to Slack
            
        Returns:
            Message UUID if successful, None otherwise
        """
        # First, send to database (sync call in async context)
        message_id = self.send_message(message, target_agent_id, message_type)
        
        # Then, send to Slack if enabled
        if send_to_slack and self.slack_adapter and message_id:
            try:
                await self.slack_adapter.send_message(
                    message=message,
                    recipient=target_agent_name,
                    message_type=message_type
                )
            except Exception as e:
                logger.error(f"Failed to send to Slack: {str(e)}")
                # Don't fail the whole operation if Slack fails
        
        return message_id
    
    async def check_slack_messages(self) -> List[Dict[str, Any]]:
        """Check for new messages from Slack.
        
        Returns:
            List of new messages from Slack
        """
        if not self.slack_adapter:
            return []
        
        try:
            return await self.slack_adapter.check_for_messages()
        except Exception as e:
            logger.error(f"Error checking Slack messages: {str(e)}")
            return []
    
    async def sync_slack_to_db(self) -> int:
        """Sync messages from Slack to database.
        
        Returns:
            Number of messages synced
        """
        if not self.slack_adapter:
            return 0
        
        try:
            slack_messages = await self.check_slack_messages()
            synced_count = 0
            
            for slack_msg in slack_messages:
                # Check if this is from another agent or human
                sender = slack_msg.get("sender", "unknown")
                if sender != self.agent_name:  # Don't sync our own messages
                    # Create database message
                    message_content = slack_msg.get("content", "")
                    
                    # Try to parse sender agent ID (for now, use a dummy mapping)
                    sender_agent_id = self._get_agent_id_from_name(sender)
                    
                    # Send to database as if received from that agent
                    self.state_store.create_group_chat_message(
                        session_id=self.session_id,
                        sender_agent_id=sender_agent_id,
                        target_agent_id=self.agent_id,  # Directed to us
                        message_content=f"[Via Slack] {message_content}",
                        message_type="slack_sync"
                    )
                    synced_count += 1
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Error syncing Slack to DB: {str(e)}")
            return 0
    
    def _get_agent_id_from_name(self, agent_name: str) -> int:
        """Map agent name to ID (temporary implementation).
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent ID (defaults to 999 for unknown)
        """
        # This would ideally query the database
        name_to_id_map = {
            "alpha": 1,
            "beta": 2,
            "delta": 3,
            "epsilon": 4,
            "gamma": 5,
            "orchestrator": 100,
            "human": 999
        }
        return name_to_id_map.get(agent_name.lower(), 999)


class SlackOrchestrationMessenger(BaseOrchestrationMessenger):
    """Enhanced orchestration messenger with Slack integration."""
    
    @staticmethod
    async def create_slack_orchestration(
        orchestration_session_id: uuid.UUID,
        agent_ids: List[int],
        agent_names: List[str],
        epic_name: str,
        epic_id: str
    ) -> Optional[str]:
        """Create a Slack-enabled orchestration session.
        
        Args:
            orchestration_session_id: Main orchestration session UUID
            agent_ids: List of agent IDs
            agent_names: List of agent names (matching agent_ids order)
            epic_name: Name of the epic
            epic_id: Linear epic ID
            
        Returns:
            Slack thread timestamp if successful, None otherwise
        """
        try:
            # First, create database group chat
            db_success = await SlackOrchestrationMessenger.create_group_chat_session(
                orchestration_session_id, 
                agent_ids
            )
            
            if not db_success:
                logger.error("Failed to create database group chat")
                return None
            
            # Then, create Slack thread
            thread_ts = await SlackOrchestrationMessenger.create_orchestration_thread(
                orchestration_id=str(orchestration_session_id),
                epic_name=epic_name,
                epic_id=epic_id,
                agents=agent_names
            )
            
            if thread_ts:
                logger.info(f"Created Slack thread {thread_ts} for orchestration {orchestration_session_id}")
                return thread_ts
            else:
                logger.error("Failed to create Slack thread")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Slack orchestration: {str(e)}")
            return None
    
    @staticmethod
    def get_slack_enabled_messenger(
        session_id: uuid.UUID, 
        agent_id: int,
        agent_name: str,
        slack_thread_ts: Optional[str] = None
    ) -> SlackEnabledAgentMessenger:
        """Get a Slack-enabled messenger instance for an agent.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: Agent ID
            agent_name: Agent name
            slack_thread_ts: Slack thread timestamp
            
        Returns:
            SlackEnabledAgentMessenger instance
        """
        return SlackEnabledAgentMessenger(
            session_id=session_id,
            agent_id=agent_id,
            agent_name=agent_name,
            slack_thread_ts=slack_thread_ts
        )
    
    @staticmethod
    async def broadcast_to_slack_and_db(
        session_id: uuid.UUID,
        agent_id: int,
        agent_name: str,
        message: str,
        slack_thread_ts: str,
        message_type: str = "orchestration"
    ) -> bool:
        """Broadcast a message to both Slack and database.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: Sending agent ID
            agent_name: Sending agent name
            message: Message content
            slack_thread_ts: Slack thread timestamp
            message_type: Type of message
            
        Returns:
            True if at least one succeeded, False if both failed
        """
        success = False
        
        # Send to database
        try:
            db_messenger = AgentMessenger(session_id, agent_id)
            db_msg_id = db_messenger.send_message(
                message=message,
                target_agent_id=None,  # Broadcast
                message_type=message_type
            )
            if db_msg_id:
                success = True
        except Exception as e:
            logger.error(f"Failed to send to database: {str(e)}")
        
        # Send to Slack
        try:
            slack_success = await SlackOrchestrationMessenger.send_agent_message(
                agent_name=agent_name,
                message=message,
                thread_ts=slack_thread_ts,
                message_type=message_type
            )
            if slack_success:
                success = True
        except Exception as e:
            logger.error(f"Failed to send to Slack: {str(e)}")
        
        return success
    
    @staticmethod
    async def complete_orchestration_with_slack(
        session_id: uuid.UUID,
        slack_thread_ts: str,
        summary: Dict[str, Any]
    ) -> bool:
        """Complete orchestration and send summary to Slack.
        
        Args:
            session_id: Orchestration session UUID
            slack_thread_ts: Slack thread timestamp
            summary: Orchestration summary data
            
        Returns:
            True if successful
        """
        try:
            # Send summary to Slack
            return await SlackOrchestrationMessenger.send_orchestration_summary(
                thread_ts=slack_thread_ts,
                orchestration_id=str(session_id),
                summary=summary
            )
        except Exception as e:
            logger.error(f"Failed to complete orchestration with Slack: {str(e)}")
            return False


# Helper function to migrate existing orchestration to Slack
async def migrate_orchestration_to_slack(
    session_id: uuid.UUID,
    agent_mappings: Dict[int, str],  # agent_id -> agent_name
    epic_name: str,
    epic_id: str
) -> Optional[str]:
    """Migrate an existing orchestration session to use Slack.
    
    Args:
        session_id: Existing orchestration session UUID
        agent_mappings: Dictionary mapping agent IDs to names
        epic_name: Epic name
        epic_id: Epic ID
        
    Returns:
        Slack thread timestamp if successful
    """
    try:
        agent_ids = list(agent_mappings.keys())
        agent_names = list(agent_mappings.values())
        
        # Create Slack thread
        thread_ts = await SlackOrchestrationMessenger.create_orchestration_thread(
            orchestration_id=str(session_id),
            epic_name=epic_name,
            epic_id=epic_id,
            agents=agent_names
        )
        
        if thread_ts:
            # Optionally, sync existing messages to Slack
            state_store = OrchestrationStateStore()
            existing_messages = state_store.get_group_chat_messages(
                session_id=session_id,
                limit=50
            )
            
            # Post existing messages to Slack thread
            for msg in existing_messages:
                if msg.context and isinstance(msg.context, dict):
                    sender_id = msg.context.get("sender_agent_id", 0)
                    sender_name = agent_mappings.get(sender_id, f"Agent{sender_id}")
                    
                    await SlackOrchestrationMessenger.send_agent_message(
                        agent_name=sender_name,
                        message=msg.text_content,
                        thread_ts=thread_ts,
                        message_type="history"
                    )
            
            logger.info(f"Successfully migrated orchestration {session_id} to Slack thread {thread_ts}")
            return thread_ts
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to migrate orchestration to Slack: {str(e)}")
        return None