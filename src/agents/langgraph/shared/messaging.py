"""Inter-agent messaging system for LangGraph orchestration.

This module provides group chat messaging capabilities between agents in an
orchestration session, replacing the broken shell-based communication system.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .state_store import OrchestrationStateStore
from src.db.models import Message

logger = logging.getLogger(__name__)

class AgentMessenger:
    """Handles inter-agent communication within orchestration sessions."""

    def __init__(self, session_id: uuid.UUID, agent_id: int):
        """Initialize messenger for an agent.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: ID of this agent
        """
        self.session_id = session_id
        self.agent_id = agent_id
        self.state_store = OrchestrationStateStore()

    def send_message(
        self, 
        message: str, 
        target_agent_id: Optional[int] = None,
        message_type: str = "group_chat"
    ) -> Optional[uuid.UUID]:
        """Send a message to another agent or broadcast to all.
        
        Args:
            message: Message content
            target_agent_id: ID of target agent (None for broadcast to all)
            message_type: Type of message (default: group_chat)
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            # Create group chat message
            message_id = self.state_store.create_group_chat_message(
                session_id=self.session_id,
                sender_agent_id=self.agent_id,
                target_agent_id=target_agent_id,
                message_content=message,
                message_type=message_type
            )
            
            if message_id:
                target_info = f"agent {target_agent_id}" if target_agent_id else "all agents"
                logger.info(f"Agent {self.agent_id} sent message to {target_info}: {message[:50]}...")
                return message_id
            else:
                logger.error(f"Failed to send message from agent {self.agent_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending message from agent {self.agent_id}: {str(e)}")
            return None

    def get_messages(self, limit: int = 50) -> List[Message]:
        """Get messages for this agent (targeted to this agent or broadcasts).
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of Message objects
        """
        try:
            # Get all group chat messages for this session
            all_messages = self.state_store.get_group_chat_messages(
                session_id=self.session_id,
                limit=limit
            )
            
            # Filter for messages targeted to this agent or broadcasts
            agent_messages = []
            for message in all_messages:
                if message.context and isinstance(message.context, dict):
                    target_id = message.context.get("target_agent_id")
                    
                    # Include if targeted to this agent or broadcast (target_id is None)
                    if target_id is None or target_id == self.agent_id:
                        agent_messages.append(message)
            
            return agent_messages
            
        except Exception as e:
            logger.error(f"Error getting messages for agent {self.agent_id}: {str(e)}")
            return []

    def get_unread_messages(self, limit: int = 10) -> List[Message]:
        """Get unread messages for this agent.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of unread Message objects
        """
        try:
            # Get messages for this agent
            messages = self.get_messages(limit=limit)
            
            # Filter for unread (pending status)
            unread_messages = [
                msg for msg in messages 
                if msg.flagged == "pending"
            ]
            
            return unread_messages
            
        except Exception as e:
            logger.error(f"Error getting unread messages for agent {self.agent_id}: {str(e)}")
            return []

    def mark_message_read(self, message_id: uuid.UUID) -> bool:
        """Mark a message as read (delivered).
        
        Args:
            message_id: Message UUID to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.state_store.update_message_status(message_id, "delivered")
        except Exception as e:
            logger.error(f"Error marking message {message_id} as read: {str(e)}")
            return False

    def reply_to_message(
        self, 
        original_message_id: uuid.UUID, 
        reply_content: str
    ) -> Optional[uuid.UUID]:
        """Reply to a specific message.
        
        Args:
            original_message_id: UUID of message being replied to
            reply_content: Reply content
            
        Returns:
            Reply message UUID if successful, None otherwise
        """
        try:
            from src.db.repository.message import get_message
            
            # Get the original message to find sender
            original_message = get_message(original_message_id)
            if not original_message:
                logger.error(f"Original message {original_message_id} not found")
                return None
            
            # Get sender agent ID from original message
            if (original_message.context and 
                isinstance(original_message.context, dict) and
                "sender_agent_id" in original_message.context):
                
                sender_agent_id = original_message.context["sender_agent_id"]
                
                # Send reply to original sender
                reply_message = f"Reply to message {str(original_message_id)[:8]}...: {reply_content}"
                return self.send_message(reply_message, target_agent_id=sender_agent_id)
            else:
                logger.error(f"Could not determine sender of original message {original_message_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error replying to message {original_message_id}: {str(e)}")
            return None

    def broadcast_status(self, status: str) -> Optional[uuid.UUID]:
        """Broadcast status update to all agents.
        
        Args:
            status: Status message
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            status_message = f"[STATUS] Agent {self.agent_id}: {status}"
            return self.send_message(status_message, target_agent_id=None, message_type="status")
        except Exception as e:
            logger.error(f"Error broadcasting status: {str(e)}")
            return None

    def get_chat_history(self, limit: int = 100) -> str:
        """Get formatted chat history for injection into agent prompts.
        
        Args:
            limit: Maximum number of messages to include
            
        Returns:
            Formatted chat history string
        """
        try:
            # Get all messages in the session
            all_messages = self.state_store.get_group_chat_messages(
                session_id=self.session_id,
                limit=limit
            )
            
            # Sort by creation time (oldest first)
            all_messages.sort(key=lambda m: m.created_at or datetime.min)
            
            # Format messages for prompt injection
            chat_lines = []
            chat_lines.append("=== INTER-AGENT CHAT HISTORY ===")
            
            for message in all_messages:
                if message.context and isinstance(message.context, dict):
                    sender_id = message.context.get("sender_agent_id", "unknown")
                    target_id = message.context.get("target_agent_id")
                    
                    # Format target
                    if target_id is None:
                        target_str = "*All*"
                    else:
                        target_str = f"Agent {target_id}"
                    
                    # Format timestamp
                    timestamp = message.created_at.strftime("%H:%M:%S") if message.created_at else "??:??:??"
                    
                    # Format message
                    chat_lines.append(f"[{timestamp}] Agent {sender_id} → {target_str}: {message.text_content}")
            
            if len(chat_lines) == 1:  # Only header
                chat_lines.append("(No messages yet)")
            
            chat_lines.append("=== END CHAT HISTORY ===")
            
            return "\n".join(chat_lines)
            
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return "=== INTER-AGENT CHAT HISTORY ===\n(Error loading chat history)\n=== END CHAT HISTORY ==="

class OrchestrationMessenger:
    """High-level messaging interface for orchestration workflows."""

    @staticmethod
    def create_group_chat_session(
        orchestration_session_id: uuid.UUID,
        agent_ids: List[int]
    ) -> bool:
        """Initialize group chat for an orchestration session.
        
        Args:
            orchestration_session_id: Main orchestration session UUID
            agent_ids: List of agent IDs participating in group chat
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create initial welcome message
            welcome_message = f"Group chat initialized for orchestration session {orchestration_session_id}"
            welcome_message += f"\nParticipating agents: {agent_ids}"
            
            # Use first agent as system messenger
            if agent_ids:
                system_messenger = AgentMessenger(orchestration_session_id, agent_ids[0])
                message_id = system_messenger.send_message(
                    welcome_message, 
                    target_agent_id=None,  # Broadcast
                    message_type="system"
                )
                
                if message_id:
                    logger.info(f"Initialized group chat for session {orchestration_session_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating group chat session: {str(e)}")
            return False

    @staticmethod
    def get_agent_messenger(session_id: uuid.UUID, agent_id: int) -> AgentMessenger:
        """Get a messenger instance for an agent.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: Agent ID
            
        Returns:
            AgentMessenger instance
        """
        return AgentMessenger(session_id, agent_id)

    @staticmethod
    def inject_chat_context(
        session_id: uuid.UUID, 
        agent_id: int, 
        base_prompt: str,
        limit: int = 20
    ) -> str:
        """Inject chat history into an agent's prompt.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: Agent ID
            base_prompt: Base agent prompt
            limit: Maximum messages to include
            
        Returns:
            Enhanced prompt with chat context
        """
        try:
            messenger = AgentMessenger(session_id, agent_id)
            chat_history = messenger.get_chat_history(limit=limit)
            
            # Inject chat history into prompt
            enhanced_prompt = f"{base_prompt}\n\n{chat_history}\n\nYou can send messages to other agents using the send_message tool."
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error injecting chat context: {str(e)}")
            return base_prompt  # Return original prompt on error 

    @staticmethod
    async def send_group_message(
        group_session_id: str,
        from_agent_name: str,
        message: str
    ) -> bool:
        """Send message to group chat from an agent.
        
        Args:
            group_session_id: Group chat session ID (UUID as string)
            from_agent_name: Name of the sending agent
            message: Message content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert group_session_id to UUID
            session_uuid = uuid.UUID(group_session_id)
            
            # Use agent ID 1 as default system messenger
            # In future, this could map agent names to IDs
            system_messenger = AgentMessenger(session_uuid, agent_id=1)
            
            # Format message with sender information
            formatted_message = f"[{from_agent_name}] {message}"
            
            # Send as broadcast message
            message_id = system_messenger.send_message(
                formatted_message,
                target_agent_id=None,  # Broadcast to all
                message_type="orchestration"
            )
            
            if message_id:
                logger.info(f"Group message sent from {from_agent_name}: {message[:50]}...")
                return True
            else:
                logger.error(f"Failed to send group message from {from_agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending group message from {from_agent_name}: {str(e)}")
            return False

    @staticmethod
    async def prepare_chat_context(group_chat_id: str) -> str:
        """Prepare chat context for agent prompts.
        
        Args:
            group_chat_id: Group chat session ID (UUID as string)
            
        Returns:
            Formatted chat context string
        """
        try:
            # Convert group_chat_id to UUID
            session_uuid = uuid.UUID(group_chat_id)
            
            # Use system messenger to get chat history
            system_messenger = AgentMessenger(session_uuid, agent_id=1)
            
            # Get recent chat history
            chat_history = system_messenger.get_chat_history(limit=10)
            
            # Add context header
            context = f"\n\n=== TEAM COORDINATION CONTEXT ===\n"
            context += "Recent inter-agent communications:\n\n"
            context += chat_history
            context += "\n=== END CONTEXT ===\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error preparing chat context: {str(e)}")
            return "\n\n=== TEAM COORDINATION CONTEXT ===\n(Error loading chat context)\n=== END CONTEXT ===\n" 