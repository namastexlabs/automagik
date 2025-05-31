"""Epsilon Tool Builder Agent with LangGraph Orchestration.

This module implements the Epsilon agent with enhanced orchestration capabilities
for tool development, external integrations, and utility creation.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.langgraph.shared.state_store import OrchestrationStateStore, OrchestrationState
from src.agents.langgraph.shared.messaging import AgentMessenger, OrchestrationMessenger
from .prompts.prompt import EPSILON_AGENT_PROMPT

logger = logging.getLogger(__name__)

class EpsilonAgent(AutomagikAgent):
    """Epsilon Tool Builder Agent with LangGraph orchestration capabilities."""

    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Epsilon agent with orchestration capabilities.
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__(config)
        
        # Set the agent prompt
        self._code_prompt_text = EPSILON_AGENT_PROMPT
        
        # Initialize dependencies with correct constructor
        self.dependencies = AutomagikAgentsDependencies(
            user_id=config.get("user_id"),
            session_id=config.get("session_id"),
            api_keys=config.get("api_keys", {}),
            model_name=config.get("model_name", "claude-3-5-sonnet-20241022"),
            test_mode=config.get("test_mode", False)
        )
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Orchestration components
        self.orchestration_session_id: Optional[uuid.UUID] = None
        self.messenger: Optional[AgentMessenger] = None
        self.state_store = OrchestrationStateStore()
        
        # Epsilon-specific configuration
        self.workspace_path = config.get("workspace_path", "/root/workspace/am-agents-tools")
        self.description = "Epsilon Tool Builder Agent with LangGraph orchestration capabilities for external integrations"
        
        # Tool development focus areas
        self.tool_categories = {
            "authentication": "JWT, OAuth, API key management",
            "communication": "Slack, Discord, email, WhatsApp",
            "data_processing": "CSV, JSON, XML parsing and validation",
            "external_apis": "GitHub, Twitter, REST/GraphQL clients",
            "utilities": "File operations, encryption, validation"
        }
        
        logger.info(f"Epsilon tool builder initialized with workspace: {self.workspace_path}")

    def initialize_orchestration(
        self, 
        session_id: uuid.UUID,
        agent_id: int
    ) -> bool:
        """Initialize orchestration capabilities for this agent.
        
        Args:
            session_id: Orchestration session UUID
            agent_id: Database agent ID
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.orchestration_session_id = session_id
            self.messenger = AgentMessenger(session_id, agent_id)
            
            # Send initialization message
            if self.messenger:
                self.messenger.broadcast_status("Epsilon Tool Builder initialized - ready for tool development")
            
            logger.info(f"Epsilon tool builder initialized for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Epsilon orchestration: {str(e)}")
            return False

    def create_orchestration_session(
        self,
        session_name: str,
        agent_id: int,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """Create a new orchestration session for tool development.
        
        Args:
            session_name: Name of the tool development session
            agent_id: Epsilon agent database ID
            user_id: Optional user ID
            
        Returns:
            Session UUID if successful, None otherwise
        """
        try:
            # Create orchestration state for tool development
            state = OrchestrationState(
                orchestration_type="langgraph_tool_development",
                target_agents=["epsilon"],
                workspace_paths={"epsilon": self.workspace_path},
                enable_rollback=True,
                process_monitoring={
                    "check_interval": 30,
                    "shutdown_timeout": 10,
                    "enable_monitoring": True
                },
                metadata={
                    "session_name": session_name,
                    "phase": "analysis",
                    "tool_categories": self.tool_categories,
                    "development_status": "starting"
                }
            )
            
            # Create orchestration session
            session_id = self.state_store.create_orchestration_session(
                name=f"Tool Development: {session_name}",
                agent_id=agent_id,
                user_id=user_id,
                orchestration_state=state
            )
            
            if session_id:
                # Initialize orchestration for this agent
                self.initialize_orchestration(session_id, agent_id)
                
                logger.info(f"Created tool development session {session_id} for: {session_name}")
                return session_id
            else:
                logger.error(f"Failed to create tool development session for: {session_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating tool development session: {str(e)}")
            return None

    def update_orchestration_state(
        self,
        phase: str,
        development_status: str = None,
        tool_progress: Dict[str, Any] = None
    ) -> bool:
        """Update the tool development orchestration state.
        
        Args:
            phase: New phase (analysis|design|implementation|testing|completion)
            development_status: Current development status
            tool_progress: Progress information for tools being developed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.orchestration_session_id:
                logger.warning("No orchestration session active for state update")
                return False
            
            # Get current state
            state = self.state_store.get_orchestration_state(self.orchestration_session_id)
            if not state:
                logger.error("Could not retrieve orchestration state")
                return False
            
            # Update metadata
            if not state.metadata:
                state.metadata = {}
            
            state.metadata["phase"] = phase
            
            if development_status:
                state.metadata["development_status"] = development_status
                
            if tool_progress:
                state.metadata["tool_progress"] = tool_progress
            
            # Update in database
            success = self.state_store.update_orchestration_state(
                self.orchestration_session_id, 
                state
            )
            
            if success and self.messenger:
                self.messenger.broadcast_status(f"Tool development phase updated: {phase}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating tool development state: {str(e)}")
            return False

    def send_tool_progress_update(
        self,
        tool_name: str,
        progress_message: str,
        completion_percentage: int = None
    ) -> bool:
        """Send a progress update for tool development.
        
        Args:
            tool_name: Name of the tool being developed
            progress_message: Progress description
            completion_percentage: Optional completion percentage (0-100)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for progress update")
                return False
            
            # Format progress message
            progress_update = f"🔧 **TOOL PROGRESS** - {tool_name}\n\n{progress_message}"
            
            if completion_percentage is not None:
                progress_bar = "█" * (completion_percentage // 10) + "░" * (10 - completion_percentage // 10)
                progress_update += f"\n\n**Progress**: {progress_bar} {completion_percentage}%"
            
            # Send progress update
            message_id = self.messenger.broadcast_status(progress_update)
            
            return message_id is not None
            
        except Exception as e:
            logger.error(f"Error sending tool progress update: {str(e)}")
            return False

    def report_tool_completion(
        self,
        tool_name: str,
        tool_description: str,
        features: List[str] = None,
        usage_example: str = None
    ) -> bool:
        """Report completion of a tool development.
        
        Args:
            tool_name: Name of the completed tool
            tool_description: Description of what the tool does
            features: List of key features implemented
            usage_example: Optional usage example
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for completion report")
                return False
            
            # Format completion message
            completion_msg = f"✅ **TOOL COMPLETED** - {tool_name}\n\n"
            completion_msg += f"**Description**: {tool_description}\n\n"
            
            if features:
                completion_msg += "**Features**:\n"
                for feature in features:
                    completion_msg += f"• {feature}\n"
                completion_msg += "\n"
            
            if usage_example:
                completion_msg += f"**Usage Example**:\n```python\n{usage_example}\n```\n\n"
            
            completion_msg += "**Status**: Ready for agent integration"
            
            # Send completion report
            message_id = self.messenger.broadcast_status(completion_msg)
            
            # Update orchestration state
            self.update_orchestration_state(
                phase="completion",
                development_status="tool_ready",
                tool_progress={tool_name: {"status": "completed", "progress": 100}}
            )
            
            logger.info(f"Epsilon tool completion reported: {tool_name}")
            return message_id is not None
            
        except Exception as e:
            logger.error(f"Error reporting tool completion: {str(e)}")
            return False

    def request_tool_feedback(
        self,
        tool_name: str,
        question: str,
        context: str = None
    ) -> Optional[uuid.UUID]:
        """Request feedback or clarification about tool development.
        
        Args:
            tool_name: Name of the tool being developed
            question: Specific question or request for feedback
            context: Optional context information
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for feedback request")
                return None
            
            # Format feedback request
            feedback_msg = f"❓ **TOOL FEEDBACK REQUEST** - {tool_name}\n\n"
            feedback_msg += f"**Question**: {question}\n\n"
            
            if context:
                feedback_msg += f"**Context**: {context}\n\n"
            
            feedback_msg += "**Requesting**: Team input on tool design/implementation"
            
            # Send feedback request
            message_id = self.messenger.broadcast_status(feedback_msg)
            
            if message_id:
                logger.info(f"Tool feedback requested for {tool_name}: {question[:100]}...")
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error requesting tool feedback: {str(e)}")
            return None

    def get_tool_development_context(self, limit: int = 15) -> str:
        """Get tool development context for prompt injection.
        
        Args:
            limit: Maximum messages to include
            
        Returns:
            Formatted development context string
        """
        try:
            if not self.orchestration_session_id or not self.messenger:
                return ""
            
            return self.messenger.get_chat_history(limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting tool development context: {str(e)}")
            return ""

    async def run(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the Epsilon agent with tool development context.
        
        Args:
            message: Input message/tool development task
            context: Optional context including orchestration info
            
        Returns:
            Agent response with tool development metadata
        """
        try:
            # Inject tool development context if available
            enhanced_message = message
            if self.orchestration_session_id and self.messenger:
                dev_context = self.get_tool_development_context()
                if dev_context:
                    enhanced_message = f"{message}\n\n### Recent Tool Development:\n{dev_context}"
            
            # Add tool categories context
            categories_context = f"\n\n### Tool Categories Available:\n"
            for category, description in self.tool_categories.items():
                categories_context += f"- **{category}**: {description}\n"
            enhanced_message += categories_context
            
            # Call parent run method
            response = await super().run(enhanced_message, context)
            
            # Add tool development metadata to response
            if isinstance(response, dict):
                response["tool_development"] = {
                    "session_id": str(self.orchestration_session_id) if self.orchestration_session_id else None,
                    "agent_type": "langgraph-epsilon",
                    "workspace_path": self.workspace_path,
                    "tool_categories": self.tool_categories,
                    "development_focus": "external_integrations_and_utilities"
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error running Epsilon agent: {str(e)}")
            if self.messenger:
                self.messenger.broadcast_status(f"❌ Epsilon Tool Development Error: {str(e)}")
            raise

    def __str__(self) -> str:
        """String representation of Epsilon agent."""
        return f"EpsilonAgent(workspace={self.workspace_path}, orchestration={self.orchestration_session_id is not None}, tool_categories={len(self.tool_categories)})" 