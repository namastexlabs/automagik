"""Gamma Quality Engineer Agent with LangGraph Orchestration.

This module implements the Gamma agent with enhanced orchestration capabilities
for testing, quality assurance, and documentation management.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.langgraph.shared.state_store import OrchestrationStateStore, OrchestrationState
from src.agents.langgraph.shared.messaging import AgentMessenger, OrchestrationMessenger
from .prompts.prompt import GAMMA_AGENT_PROMPT

logger = logging.getLogger(__name__)

class GammaAgent(AutomagikAgent):
    """Gamma Quality Engineer Agent with LangGraph orchestration capabilities."""

    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Gamma agent with orchestration capabilities.
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__(config)
        
        # Set the agent prompt
        self._code_prompt_text = GAMMA_AGENT_PROMPT
        
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
        
        # Gamma-specific configuration
        self.workspace_path = config.get("workspace_path", "/root/workspace/am-agents-tests")
        self.description = "Quality Engineer Agent with LangGraph orchestration capabilities for testing and QA"
        
        logger.info(f"Gamma agent initialized with workspace: {self.workspace_path}")

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
                self.messenger.broadcast_status("Gamma Quality Engineer orchestration initialized")
            
            logger.info(f"Gamma agent orchestration initialized for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gamma orchestration: {str(e)}")
            return False

    def create_orchestration_session(
        self,
        name: str,
        agent_id: int,
        target_agents: List[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """Create a new orchestration session for epic coordination.
        
        Args:
            name: Session name
            agent_id: Gamma agent database ID
            target_agents: List of target agent names for coordination
            user_id: Optional user ID
            
        Returns:
            Session UUID if successful, None otherwise
        """
        try:
            # Create orchestration state
            if target_agents is None:
                target_agents = ["beta", "delta", "epsilon"]  # Quality testing focused
            
            state = OrchestrationState(
                orchestration_type="langgraph",
                target_agents=target_agents,
                workspace_paths={
                    "gamma": self.workspace_path,
                    "beta": "/root/workspace/am-agents-core",
                    "delta": "/root/workspace/am-agents-api",
                    "epsilon": "/root/workspace/am-agents-tools"
                },
                enable_rollback=True,
                process_monitoring={
                    "check_interval": 30,
                    "shutdown_timeout": 5,
                    "enable_monitoring": True
                }
            )
            
            # Create session
            session_id = self.state_store.create_orchestration_session(
                name=name,
                agent_id=agent_id,
                user_id=user_id,
                orchestration_state=state
            )
            
            if session_id:
                # Initialize orchestration for this agent
                self.initialize_orchestration(session_id, agent_id)
                
                # Initialize group chat
                agent_ids = [agent_id]  # Add other agent IDs as they become available
                OrchestrationMessenger.create_group_chat_session(session_id, agent_ids)
                
                logger.info(f"Created orchestration session {session_id} for epic: {name}")
                return session_id
            else:
                logger.error(f"Failed to create orchestration session for epic: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating orchestration session: {str(e)}")
            return None

    def update_orchestration_state(
        self,
        process_status: str = None,
        git_sha: str = None,
        **kwargs
    ) -> bool:
        """Update the orchestration state for this session.
        
        Args:
            process_status: New process status (running|completed|failed)
            git_sha: Current git commit SHA
            **kwargs: Additional state updates
            
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
            
            # Update state fields
            if process_status:
                state.process_status = process_status
            if git_sha:
                state.git_sha_end = git_sha
            
            # Apply additional updates
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            
            # Update in database
            success = self.state_store.update_orchestration_state(
                self.orchestration_session_id, 
                state
            )
            
            if success and self.messenger:
                self.messenger.broadcast_status(f"Quality state updated: {process_status or 'in progress'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating orchestration state: {str(e)}")
            return False

    def send_coordination_message(
        self,
        message: str,
        target_agent: str = None
    ) -> Optional[uuid.UUID]:
        """Send a coordination message to other agents.
        
        Args:
            message: Message content
            target_agent: Target agent name (None for broadcast)
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for coordination")
                return None
            
            # Map agent names to IDs (simplified - in practice would lookup from database)
            agent_id_map = {
                "alpha": 1,
                "beta": 2, 
                "delta": 3,
                "epsilon": 4,
                "gamma": 5
            }
            
            target_agent_id = agent_id_map.get(target_agent) if target_agent else None
            
            return self.messenger.send_message(message, target_agent_id)
            
        except Exception as e:
            logger.error(f"Error sending coordination message: {str(e)}")
            return None

    def get_group_chat_context(self, limit: int = 20) -> str:
        """Get group chat context for prompt injection.
        
        Args:
            limit: Maximum messages to include
            
        Returns:
            Formatted chat context string
        """
        try:
            if not self.orchestration_session_id or not self.messenger:
                return ""
            
            return self.messenger.get_chat_history(limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting group chat context: {str(e)}")
            return ""

    def send_quality_report(
        self,
        test_results: Dict[str, Any],
        coverage_info: Dict[str, Any] = None
    ) -> bool:
        """Send quality report to the team via WhatsApp and group chat.
        
        Args:
            test_results: Dictionary containing test results
            coverage_info: Optional coverage information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format quality report
            total_tests = test_results.get("total", 0)
            passed_tests = test_results.get("passed", 0)
            failed_tests = test_results.get("failed", 0)
            
            report = f"📊 Quality Report:\n"
            report += f"Tests: {passed_tests}/{total_tests} passing"
            
            if failed_tests > 0:
                report += f" ({failed_tests} failed)"
            
            if coverage_info:
                coverage_pct = coverage_info.get("percentage", 0)
                report += f"\nCoverage: {coverage_pct}%"
                
                if coverage_pct < 80:
                    report += " ⚠️ Below target"
                else:
                    report += " ✅"
            
            # Add status emoji
            if failed_tests == 0 and (not coverage_info or coverage_info.get("percentage", 0) >= 80):
                report = "✅ " + report + "\n\nReady for review!"
            else:
                report = "❌ " + report + "\n\nNeeds attention!"
            
            # Send via group chat if available
            if self.messenger:
                self.messenger.broadcast_status(report)
            
            logger.info(f"Quality report sent: {passed_tests}/{total_tests} tests passing")
            return True
            
        except Exception as e:
            logger.error(f"Error sending quality report: {str(e)}")
            return False

    def complete_task(
        self,
        task_name: str,
        result: str,
        git_sha: str = None
    ) -> bool:
        """Mark a task as complete and notify the team.
        
        Args:
            task_name: Name of completed task
            result: Task completion result
            git_sha: Git commit SHA for the completion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update orchestration state
            success = self.update_orchestration_state(
                process_status="completed",
                git_sha=git_sha
            )
            
            # Send completion message
            if self.messenger:
                completion_msg = f"✅ Quality Task Complete: {task_name}\nResult: {result}"
                if git_sha:
                    completion_msg += f"\nCommit: {git_sha[:8]}"
                
                self.messenger.broadcast_status(completion_msg)
            
            logger.info(f"Gamma task completed: {task_name}")
            return success
            
        except Exception as e:
            logger.error(f"Error completing task: {str(e)}")
            return False

    async def run(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the Gamma agent with orchestration context.
        
        Args:
            message: Input message/task
            context: Optional context including orchestration info
            
        Returns:
            Agent response with orchestration metadata
        """
        try:
            # Inject group chat context if available
            enhanced_message = message
            if self.orchestration_session_id and self.messenger:
                chat_context = self.get_group_chat_context()
                if chat_context:
                    enhanced_message = f"{message}\n\n{chat_context}"
            
            # Call parent run method
            response = await super().run(enhanced_message, context)
            
            # Add orchestration metadata to response
            if isinstance(response, dict):
                response["orchestration"] = {
                    "session_id": str(self.orchestration_session_id) if self.orchestration_session_id else None,
                    "agent_type": "langgraph-gamma",
                    "workspace_path": self.workspace_path
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error running Gamma agent: {str(e)}")
            if self.messenger:
                self.messenger.broadcast_status(f"❌ Quality Check Error: {str(e)}")
            raise

    def __str__(self) -> str:
        """String representation of Gamma agent."""
        return f"GammaAgent(workspace={self.workspace_path}, orchestration={self.orchestration_session_id is not None})" 