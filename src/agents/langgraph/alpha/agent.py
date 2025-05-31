"""Alpha Orchestrator Agent with LangGraph Orchestration.

This module implements the Alpha agent with comprehensive orchestration capabilities
for epic analysis, task breakdown, and team coordination.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.langgraph.shared.state_store import OrchestrationStateStore, OrchestrationState
from src.agents.langgraph.shared.messaging import AgentMessenger, OrchestrationMessenger
from .prompts.prompt import ALPHA_AGENT_PROMPT

logger = logging.getLogger(__name__)

class AlphaAgent(AutomagikAgent):
    """Alpha Orchestrator Agent with LangGraph orchestration capabilities."""

    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Alpha agent with orchestration capabilities.
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__(config)
        
        # Set the agent prompt
        self._code_prompt_text = ALPHA_AGENT_PROMPT
        
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
        
        # Alpha-specific configuration
        self.workspace_path = config.get("workspace_path", "/root/workspace/am-agents-labs")
        self.description = "Alpha Orchestrator Agent with LangGraph orchestration capabilities for epic coordination"
        
        # Team configuration
        self.team_agents = {
            "beta": "/root/workspace/am-agents-core",
            "delta": "/root/workspace/am-agents-api", 
            "epsilon": "/root/workspace/am-agents-tools",
            "gamma": "/root/workspace/am-agents-tests"
        }
        
        logger.info(f"Alpha orchestrator initialized with workspace: {self.workspace_path}")

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
                self.messenger.broadcast_status("Alpha Orchestrator initialized - ready for epic coordination")
            
            logger.info(f"Alpha orchestrator initialized for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpha orchestration: {str(e)}")
            return False

    def create_epic_orchestration(
        self,
        epic_name: str,
        agent_id: int,
        target_agents: List[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """Create a new epic orchestration session for team coordination.
        
        Args:
            epic_name: Name of the epic being orchestrated
            agent_id: Alpha agent database ID
            target_agents: List of target agent names for coordination
            user_id: Optional user ID
            
        Returns:
            Session UUID if successful, None otherwise
        """
        try:
            # Default to full team coordination
            if target_agents is None:
                target_agents = ["beta", "delta", "epsilon", "gamma"]
            
            # Create orchestration state for epic
            state = OrchestrationState(
                orchestration_type="langgraph_epic",
                target_agents=target_agents,
                workspace_paths=self.team_agents,
                enable_rollback=True,
                process_monitoring={
                    "check_interval": 30,
                    "shutdown_timeout": 10,
                    "enable_monitoring": True
                },
                metadata={
                    "epic_name": epic_name,
                    "phase": "analysis",
                    "dependencies": {},
                    "completion_criteria": []
                }
            )
            
            # Create orchestration session
            session_id = self.state_store.create_orchestration_session(
                name=f"Epic: {epic_name}",
                agent_id=agent_id,
                user_id=user_id,
                orchestration_state=state
            )
            
            if session_id:
                # Initialize orchestration for this agent
                self.initialize_orchestration(session_id, agent_id)
                
                # Initialize group chat for team communication
                agent_ids = [agent_id]  # Add other agent IDs as they become available
                OrchestrationMessenger.create_group_chat_session(session_id, agent_ids)
                
                logger.info(f"Created epic orchestration session {session_id} for: {epic_name}")
                return session_id
            else:
                logger.error(f"Failed to create epic orchestration session for: {epic_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating epic orchestration: {str(e)}")
            return None

    def update_epic_phase(
        self,
        phase: str,
        agent_states: Dict[str, Dict] = None,
        dependencies: Dict[str, List[str]] = None
    ) -> bool:
        """Update the epic orchestration phase and agent states.
        
        Args:
            phase: New phase (analysis|assignment|coordination|integration|completion)
            agent_states: Dict of agent statuses and progress
            dependencies: Updated dependency mapping
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.orchestration_session_id:
                logger.warning("No orchestration session active for phase update")
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
            
            if agent_states:
                state.metadata["agent_states"] = agent_states
                
            if dependencies:
                state.metadata["dependencies"] = dependencies
            
            # Update in database
            success = self.state_store.update_orchestration_state(
                self.orchestration_session_id, 
                state
            )
            
            if success and self.messenger:
                self.messenger.broadcast_status(f"Epic phase updated: {phase}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating epic phase: {str(e)}")
            return False

    def assign_agent_task(
        self,
        agent_name: str,
        task_description: str,
        workspace_path: str,
        dependencies: List[str] = None,
        provides: List[str] = None
    ) -> Optional[uuid.UUID]:
        """Assign a specific task to a team agent via orchestration.
        
        Args:
            agent_name: Name of target agent (beta, delta, epsilon, gamma)
            task_description: Detailed task description
            workspace_path: Agent's workspace path
            dependencies: List of dependencies this task has
            provides: List of components this task provides
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for task assignment")
                return None
            
            # Create task assignment message
            task_message = f"""🎯 **TASK ASSIGNMENT** for {agent_name.upper()}

**Workspace**: `{workspace_path}`

**Task Description**:
{task_description}

**Dependencies**: {dependencies or 'None'}
**Provides**: {provides or 'TBD'}

**Epic Context**: Working in coordinated epic - check group chat for team updates.

Please acknowledge task receipt and provide progress updates as you work."""
            
            # Map agent names to IDs (simplified - in practice would lookup from database)
            agent_id_map = {
                "alpha": 1,
                "beta": 2, 
                "delta": 3,
                "epsilon": 4,
                "gamma": 5
            }
            
            target_agent_id = agent_id_map.get(agent_name.lower())
            if not target_agent_id:
                logger.error(f"Unknown agent name: {agent_name}")
                return None
            
            # Send task assignment
            message_id = self.messenger.send_message(task_message, target_agent_id)
            
            if message_id:
                logger.info(f"Task assigned to {agent_name}: {task_description[:100]}...")
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error assigning task to {agent_name}: {str(e)}")
            return None

    def broadcast_epic_update(
        self,
        update_message: str,
        phase: str = None
    ) -> bool:
        """Broadcast an epic progress update to all team agents.
        
        Args:
            update_message: Progress update message
            phase: Optional phase update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.messenger:
                logger.warning("No messenger available for epic update")
                return False
            
            # Update phase if provided
            if phase:
                self.update_epic_phase(phase)
            
            # Format epic update message
            formatted_message = f"📊 **EPIC UPDATE** from Alpha\n\n{update_message}"
            
            # Broadcast to all agents
            message_id = self.messenger.broadcast_status(formatted_message)
            
            return message_id is not None
            
        except Exception as e:
            logger.error(f"Error broadcasting epic update: {str(e)}")
            return False

    def monitor_epic_progress(self) -> Dict[str, Any]:
        """Monitor and return current epic progress status.
        
        Returns:
            Dictionary containing epic progress information
        """
        try:
            if not self.orchestration_session_id:
                return {"error": "No active orchestration session"}
            
            # Get current orchestration state
            state = self.state_store.get_orchestration_state(self.orchestration_session_id)
            if not state:
                return {"error": "Could not retrieve orchestration state"}
            
            # Get recent team communication
            chat_context = ""
            if self.messenger:
                chat_context = self.messenger.get_chat_history(limit=10)
            
            progress_info = {
                "session_id": str(self.orchestration_session_id),
                "orchestration_type": state.orchestration_type,
                "target_agents": state.target_agents,
                "current_phase": state.metadata.get("phase", "unknown") if state.metadata else "unknown",
                "agent_states": state.metadata.get("agent_states", {}) if state.metadata else {},
                "dependencies": state.metadata.get("dependencies", {}) if state.metadata else {},
                "workspace_paths": state.workspace_paths,
                "recent_chat": chat_context,
                "process_status": state.process_status or "unknown"
            }
            
            return progress_info
            
        except Exception as e:
            logger.error(f"Error monitoring epic progress: {str(e)}")
            return {"error": str(e)}

    def complete_epic(
        self,
        completion_summary: str,
        git_sha: str = None
    ) -> bool:
        """Mark the epic as complete and finalize orchestration.
        
        Args:
            completion_summary: Summary of epic completion
            git_sha: Final git commit SHA
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update orchestration state to completed
            success = self.update_epic_phase(
                phase="completion",
                agent_states={"all": {"status": "completed", "progress": 1.0}}
            )
            
            if success and git_sha:
                state = self.state_store.get_orchestration_state(self.orchestration_session_id)
                if state:
                    state.git_sha_end = git_sha
                    self.state_store.update_orchestration_state(self.orchestration_session_id, state)
            
            # Send completion broadcast
            if self.messenger:
                completion_msg = f"🎉 **EPIC COMPLETED** by Alpha\n\n{completion_summary}"
                if git_sha:
                    completion_msg += f"\n\n**Final Commit**: {git_sha[:8]}"
                
                self.messenger.broadcast_status(completion_msg)
            
            logger.info(f"Alpha epic completed: {completion_summary}")
            return success
            
        except Exception as e:
            logger.error(f"Error completing epic: {str(e)}")
            return False

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

    async def run(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the Alpha agent with orchestration context.
        
        Args:
            message: Input message/epic task
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
                    enhanced_message = f"{message}\n\n### Recent Team Communication:\n{chat_context}"
            
            # Add epic progress context
            progress_info = self.monitor_epic_progress()
            if progress_info and "error" not in progress_info:
                progress_context = f"\n\n### Current Epic Status:\n"
                progress_context += f"Phase: {progress_info.get('current_phase', 'unknown')}\n"
                if progress_info.get('agent_states'):
                    progress_context += f"Agent States: {progress_info['agent_states']}"
                enhanced_message += progress_context
            
            # Call parent run method
            response = await super().run(enhanced_message, context)
            
            # Add orchestration metadata to response
            if isinstance(response, dict):
                response["orchestration"] = {
                    "session_id": str(self.orchestration_session_id) if self.orchestration_session_id else None,
                    "agent_type": "langgraph-alpha",
                    "workspace_path": self.workspace_path,
                    "team_agents": self.team_agents,
                    "epic_progress": progress_info if "error" not in progress_info else None
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error running Alpha agent: {str(e)}")
            if self.messenger:
                self.messenger.broadcast_status(f"❌ Alpha Orchestration Error: {str(e)}")
            raise

    def __str__(self) -> str:
        """String representation of Alpha agent."""
        return f"AlphaAgent(workspace={self.workspace_path}, orchestration={self.orchestration_session_id is not None}, team_agents={len(self.team_agents)})" 