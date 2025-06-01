"""Slack-based messaging system for LangGraph agent orchestration.

This module provides Slack integration for multi-agent communication,
replacing the file-based messaging system with a shared Slack channel
where both agents and humans can collaborate.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Represents a message in the Slack channel."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thread_ts: Optional[str] = None
    sender: str = ""
    recipient: Optional[str] = None
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SlackOrchestrationMessenger:
    """Handles Slack-based communication for agent orchestration."""
    
    # Slack channel configuration
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C08UF878N3Z")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "xoxb-5623053499716-8993096493953-Fc50mQbITECgtUQDWJK3CbSW")
    SLACK_TEAM_ID = os.getenv("SLACK_TEAM_ID", "T05JB1KEPM2")
    
    # Agent emoji mapping for visual identification
    AGENT_EMOJIS = {
        "alpha": "🎯",
        "beta": "🔨", 
        "delta": "🏗️",
        "epsilon": "🔧",
        "gamma": "🧪",
        "orchestrator": "🎼",
        "human": "👤"
    }
    
    @staticmethod
    async def send_to_slack(
        message: str,
        sender: str = "orchestrator",
        thread_ts: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Send a message to the Slack channel.
        
        Args:
            message: The message content
            sender: The sender identifier (agent name or 'human')
            thread_ts: Thread timestamp to reply in a thread
            metadata: Additional metadata for the message
            
        Returns:
            Thread timestamp if successful, None otherwise
        """
        try:
            # Format message with sender identification
            emoji = SlackOrchestrationMessenger.AGENT_EMOJIS.get(sender.lower(), "🤖")
            formatted_message = f"{emoji} **{sender.upper()}**: {message}"
            
            # Add metadata if provided
            if metadata:
                formatted_message += f"\n```json\n{json.dumps(metadata, indent=2)}\n```"
            
            # Here we would use the Slack API or MCP tool
            # For now, we'll use a placeholder that logs the message
            logger.info(f"Slack message from {sender}: {message}")
            
            # In production, this would call the Slack API
            # response = await slack_client.chat_postMessage(
            #     channel=SlackOrchestrationMessenger.SLACK_CHANNEL_ID,
            #     text=formatted_message,
            #     thread_ts=thread_ts
            # )
            # return response.get('ts')
            
            # For now, return a mock timestamp
            return datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return None
    
    @staticmethod
    async def create_orchestration_thread(
        orchestration_id: str,
        epic_name: str,
        epic_id: str,
        agents: List[str]
    ) -> Optional[str]:
        """Create a new thread for an orchestration session.
        
        Args:
            orchestration_id: Unique orchestration session ID
            epic_name: Name of the epic being worked on
            epic_id: Linear epic ID (e.g., NMSTX-187)
            agents: List of agent names participating
            
        Returns:
            Thread timestamp if successful, None otherwise
        """
        try:
            # Create the initial thread message
            agent_list = "\n".join([
                f"• {SlackOrchestrationMessenger.AGENT_EMOJIS.get(agent, '🤖')} {agent.upper()}"
                for agent in agents
            ])
            
            message = f"""🚀 **New Orchestration Session Started**
            
📋 Epic: {epic_name}
🆔 ID: {epic_id}
🔄 Session: {orchestration_id}
⏰ Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

🤖 **Active Agents:**
{agent_list}

💬 This thread will contain all agent communications for this orchestration.
👥 Humans can participate by replying in this thread.
"""
            
            # Send the message and get thread timestamp
            thread_ts = await SlackOrchestrationMessenger.send_to_slack(
                message=message,
                sender="orchestrator",
                metadata={
                    "orchestration_id": orchestration_id,
                    "epic_id": epic_id,
                    "type": "orchestration_start"
                }
            )
            
            return thread_ts
            
        except Exception as e:
            logger.error(f"Failed to create orchestration thread: {e}")
            return None
    
    @staticmethod
    async def send_agent_message(
        agent_name: str,
        message: str,
        thread_ts: str,
        recipient: Optional[str] = None,
        message_type: str = "communication"
    ) -> bool:
        """Send a message from an agent to the Slack thread.
        
        Args:
            agent_name: Name of the sending agent
            message: Message content
            thread_ts: Thread to send to
            recipient: Optional specific recipient agent
            message_type: Type of message (communication, status, error, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format recipient if specified
            if recipient:
                recipient_emoji = SlackOrchestrationMessenger.AGENT_EMOJIS.get(recipient.lower(), "🤖")
                message = f"@{recipient} {recipient_emoji} - {message}"
            
            # Add message type indicator
            type_indicators = {
                "communication": "💬",
                "status": "📊",
                "error": "❌",
                "success": "✅",
                "question": "❓",
                "task": "📋"
            }
            
            type_emoji = type_indicators.get(message_type, "💬")
            formatted_message = f"{type_emoji} {message}"
            
            # Send to thread
            result = await SlackOrchestrationMessenger.send_to_slack(
                message=formatted_message,
                sender=agent_name,
                thread_ts=thread_ts,
                metadata={
                    "message_type": message_type,
                    "recipient": recipient
                }
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to send agent message: {e}")
            return False
    
    @staticmethod
    async def get_thread_messages(
        thread_ts: str,
        since_ts: Optional[str] = None
    ) -> List[SlackMessage]:
        """Retrieve messages from a Slack thread.
        
        Args:
            thread_ts: Thread timestamp to retrieve from
            since_ts: Only get messages after this timestamp
            
        Returns:
            List of SlackMessage objects
        """
        try:
            # In production, this would call the Slack API
            # response = await slack_client.conversations_replies(
            #     channel=SlackOrchestrationMessenger.SLACK_CHANNEL_ID,
            #     ts=thread_ts,
            #     oldest=since_ts
            # )
            
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get thread messages: {e}")
            return []
    
    @staticmethod
    async def extract_human_input(
        thread_ts: str,
        since_ts: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract human input from a thread since a given timestamp.
        
        Args:
            thread_ts: Thread to check
            since_ts: Only get messages after this timestamp
            
        Returns:
            List of human messages with metadata
        """
        try:
            messages = await SlackOrchestrationMessenger.get_thread_messages(
                thread_ts=thread_ts,
                since_ts=since_ts
            )
            
            # Filter for human messages (not from bots)
            human_messages = []
            for msg in messages:
                if msg.sender == "human" or not msg.metadata.get("is_bot", False):
                    human_messages.append({
                        "id": msg.id,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "metadata": msg.metadata
                    })
            
            return human_messages
            
        except Exception as e:
            logger.error(f"Failed to extract human input: {e}")
            return []
    
    @staticmethod
    async def send_orchestration_summary(
        thread_ts: str,
        orchestration_id: str,
        summary: Dict[str, Any]
    ) -> bool:
        """Send an orchestration summary to the thread.
        
        Args:
            thread_ts: Thread to send to
            orchestration_id: Orchestration session ID
            summary: Summary data including results, metrics, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format summary message
            duration = summary.get("duration", "Unknown")
            status = summary.get("status", "Unknown")
            results = summary.get("results", {})
            
            status_emoji = "✅" if status == "completed" else "❌"
            
            message = f"""{status_emoji} **Orchestration Session Complete**

🔄 Session: {orchestration_id}
⏱️ Duration: {duration}
📊 Status: {status}

**Results by Agent:**"""
            
            for agent, result in results.items():
                agent_emoji = SlackOrchestrationMessenger.AGENT_EMOJIS.get(agent, "🤖")
                status = "✅" if result.get("success") else "❌"
                message += f"\n{agent_emoji} {agent.upper()}: {status} - {result.get('summary', 'No summary')}"
            
            # Add any errors
            if summary.get("errors"):
                message += "\n\n**Errors:**"
                for error in summary["errors"]:
                    message += f"\n❌ {error}"
            
            # Send summary
            result = await SlackOrchestrationMessenger.send_to_slack(
                message=message,
                sender="orchestrator",
                thread_ts=thread_ts,
                metadata={
                    "orchestration_id": orchestration_id,
                    "type": "orchestration_summary",
                    "summary": summary
                }
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to send orchestration summary: {e}")
            return False


class SlackAgentAdapter:
    """Adapter for individual agents to communicate via Slack."""
    
    def __init__(self, agent_name: str, thread_ts: str):
        """Initialize the adapter for a specific agent.
        
        Args:
            agent_name: Name of the agent
            thread_ts: Slack thread timestamp for the orchestration
        """
        self.agent_name = agent_name
        self.thread_ts = thread_ts
        self.last_check_ts = None
    
    async def send_message(
        self,
        message: str,
        recipient: Optional[str] = None,
        message_type: str = "communication"
    ) -> bool:
        """Send a message to the Slack thread.
        
        Args:
            message: Message content
            recipient: Optional specific recipient
            message_type: Type of message
            
        Returns:
            True if successful
        """
        return await SlackOrchestrationMessenger.send_agent_message(
            agent_name=self.agent_name,
            message=message,
            thread_ts=self.thread_ts,
            recipient=recipient,
            message_type=message_type
        )
    
    async def check_for_messages(self) -> List[Dict[str, Any]]:
        """Check for new messages directed to this agent.
        
        Returns:
            List of messages for this agent
        """
        try:
            # Get all messages since last check
            messages = await SlackOrchestrationMessenger.get_thread_messages(
                thread_ts=self.thread_ts,
                since_ts=self.last_check_ts
            )
            
            # Update last check timestamp
            if messages:
                self.last_check_ts = messages[-1].timestamp.isoformat()
            
            # Filter for messages directed to this agent
            agent_messages = []
            for msg in messages:
                # Check if message is directed to this agent
                if (msg.recipient and msg.recipient.lower() == self.agent_name.lower()) or \
                   f"@{self.agent_name}" in msg.content:
                    agent_messages.append({
                        "id": msg.id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata
                    })
            
            return agent_messages
            
        except Exception as e:
            logger.error(f"Failed to check for messages: {e}")
            return []
    
    async def send_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Send a status update to the thread.
        
        Args:
            status: Status message
            details: Optional additional details
            
        Returns:
            True if successful
        """
        message = f"Status Update: {status}"
        if details:
            message += f"\nDetails: {json.dumps(details, indent=2)}"
        
        return await self.send_message(message, message_type="status")
    
    async def ask_question(self, question: str, recipient: Optional[str] = None) -> bool:
        """Ask a question in the thread.
        
        Args:
            question: Question to ask
            recipient: Optional specific recipient
            
        Returns:
            True if successful
        """
        return await self.send_message(question, recipient=recipient, message_type="question")