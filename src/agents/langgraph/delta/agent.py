"""Delta API Builder Agent with LangGraph Orchestration.

This module implements the Delta agent with enhanced orchestration capabilities
for API development, endpoint design, and FastAPI integration.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.langgraph.shared.state_store import OrchestrationStateStore, OrchestrationState
from src.agents.langgraph.shared.messaging import AgentMessenger, OrchestrationMessenger
from .prompts.prompt import DELTA_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class DeltaAgent(AutomagikAgent):
    """Delta API Builder Agent with LangGraph orchestration capabilities."""

    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Delta agent with orchestration capabilities.
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__(config)
        
        # Set the agent prompt
        self._code_prompt_text = DELTA_SYSTEM_PROMPT
        
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
        
        # Delta-specific configuration
        self.workspace_path = config.get("workspace_path", "/root/workspace/am-agents-api")
        self.description = "API Builder Agent with LangGraph orchestration capabilities for FastAPI development"
        
        logger.info(f"Delta agent initialized with workspace: {self.workspace_path}")

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
                self.messenger.broadcast_status("Delta agent orchestration initialized")
            
            logger.info(f"Delta agent orchestration initialized for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Delta orchestration: {str(e)}")
            return False

    def update_workspace_path(self, workspace_path: str) -> bool:
        """Update the workspace path for API development.
        
        Args:
            workspace_path: New workspace path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.workspace_path = workspace_path
            if self.messenger:
                self.messenger.broadcast_status(f"Delta workspace updated to: {workspace_path}")
            logger.info(f"Delta workspace path updated to: {workspace_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update workspace path: {str(e)}")
            return False

    def create_api_development_session(
        self,
        name: str,
        agent_id: int,
        api_endpoints: List[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """Create a new orchestration session for API development.
        
        Args:
            name: Session name (e.g., "User Authentication API")
            agent_id: Delta agent database ID
            api_endpoints: List of API endpoints to develop
            user_id: Optional user ID
            
        Returns:
            Session UUID if successful, None otherwise
        """
        try:
            # Create orchestration state for API development
            if api_endpoints is None:
                api_endpoints = [
                    "POST /api/v1/auth/login",
                    "POST /api/v1/auth/register", 
                    "GET /api/v1/users",
                    "POST /api/v1/agents/run"
                ]
            
            state = OrchestrationState(
                orchestration_type="langgraph_api",
                target_agents=["delta", "beta", "gamma"],
                workspace_paths={
                    "delta": self.workspace_path,
                    "beta": "/root/workspace/am-agents-core",
                    "gamma": "/root/workspace/am-agents-tests"
                },
                enable_rollback=True,
                api_endpoints_planned=api_endpoints,
                api_endpoints_ready=[],
                api_documentation_status="pending"
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
                
                # Initialize group chat for API development coordination
                agent_ids = [agent_id]  # Add other agent IDs as they become available
                OrchestrationMessenger.create_group_chat_session(session_id, agent_ids)
                
                logger.info(f"Created API development session {session_id} for: {name}")
                return session_id
            else:
                logger.error(f"Failed to create API development session for: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating API development session: {str(e)}")
            return None

    def update_api_development_state(
        self,
        endpoint_completed: str = None,
        documentation_updated: bool = False,
        tests_ready: bool = False,
        **kwargs
    ) -> bool:
        """Update the API development state for this session.
        
        Args:
            endpoint_completed: API endpoint that was completed (e.g., "POST /api/v1/users")
            documentation_updated: Whether API documentation was updated
            tests_ready: Whether tests are ready for the endpoint
            **kwargs: Additional state updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.orchestration_session_id:
                logger.warning("No orchestration session active for API state update")
                return False
            
            # Get current state
            state = self.state_store.get_orchestration_state(self.orchestration_session_id)
            if not state:
                logger.error("Could not retrieve orchestration state")
                return False
            
            # Update API-specific state fields
            if endpoint_completed:
                if not hasattr(state, 'api_endpoints_ready'):
                    state.api_endpoints_ready = []
                if endpoint_completed not in state.api_endpoints_ready:
                    state.api_endpoints_ready.append(endpoint_completed)
                    
            if documentation_updated:
                state.api_documentation_status = "updated"
                
            if tests_ready:
                if not hasattr(state, 'api_tests_ready'):
                    state.api_tests_ready = []
                if endpoint_completed and endpoint_completed not in state.api_tests_ready:
                    state.api_tests_ready.append(endpoint_completed)
            
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
                if endpoint_completed:
                    self.messenger.broadcast_status(f"API endpoint completed: {endpoint_completed}")
                elif documentation_updated:
                    self.messenger.broadcast_status("API documentation updated")
                else:
                    self.messenger.broadcast_status("API development state updated")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating API development state: {str(e)}")
            return False

    def request_service_implementation(
        self,
        service_name: str,
        method_signature: str,
        target_agent: str = "beta"
    ) -> Optional[uuid.UUID]:
        """Request service implementation from another agent (typically Beta).
        
        Args:
            service_name: Name of the service class (e.g., "UserService")
            method_signature: Method signature needed (e.g., "authenticate(email: str, password: str) -> Optional[User]")
            target_agent: Target agent to implement the service
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            if not self.messenger:
                logger.error("No messenger available for service request")
                return None
            
            message = f"""🔌 Service Implementation Request

**Service**: {service_name}
**Method**: {method_signature}
**For**: API endpoint integration
**Priority**: Blocking Delta development

Please implement and notify when ready for integration."""

            message_id = self.messenger.send_message(message, target_agent)
            if message_id:
                logger.info(f"Requested {service_name} implementation from {target_agent}")
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error requesting service implementation: {str(e)}")
            return None

    def announce_api_ready(
        self,
        endpoint: str,
        status_code_success: int = 200,
        target_agent: str = "gamma"
    ) -> Optional[uuid.UUID]:
        """Announce that an API endpoint is ready for testing.
        
        Args:
            endpoint: API endpoint that's ready (e.g., "POST /api/v1/users")
            status_code_success: Expected success status code
            target_agent: Agent to notify for testing (typically Gamma)
            
        Returns:
            Message UUID if successful, None otherwise
        """
        try:
            if not self.messenger:
                logger.error("No messenger available for API announcement")
                return None
            
            message = f"""✅ API Endpoint Ready for Testing

**Endpoint**: {endpoint}
**Expected Success Code**: {status_code_success}
**Authentication**: Required (API key in header)
**OpenAPI Docs**: Available at /docs

Ready for integration and testing."""

            message_id = self.messenger.send_message(message, target_agent)
            if message_id:
                logger.info(f"Announced {endpoint} ready to {target_agent}")
                # Also update orchestration state
                self.update_api_development_state(endpoint_completed=endpoint)
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error announcing API readiness: {str(e)}")
            return None

    def get_group_chat_context(self, limit: int = 20) -> str:
        """Get recent group chat messages for context.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            Formatted string of recent messages
        """
        try:
            if not self.messenger:
                return "No group chat context available (no active session)"
            
            messages = self.messenger.get_messages(limit=limit)
            if not messages:
                return "No recent group chat messages"
            
            context_lines = ["Recent Group Chat Context:", "=" * 30]
            for msg in messages[-limit:]:
                timestamp = msg.get('created_at', 'Unknown time')
                agent = msg.get('agent_name', 'Unknown agent')
                content = msg.get('content', '')
                context_lines.append(f"[{timestamp}] {agent}: {content}")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Error getting group chat context: {str(e)}")
            return f"Error retrieving group chat context: {str(e)}"

    def complete_api_development_task(
        self,
        task_name: str,
        endpoints_completed: List[str],
        documentation_ready: bool = True
    ) -> bool:
        """Mark an API development task as complete.
        
        Args:
            task_name: Name of the completed task
            endpoints_completed: List of API endpoints that were completed
            documentation_ready: Whether documentation is ready
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.orchestration_session_id:
                logger.warning("No orchestration session for task completion")
                return False
            
            # Update orchestration state
            state = self.state_store.get_orchestration_state(self.orchestration_session_id)
            if not state:
                logger.error("Could not retrieve orchestration state for completion")
                return False
            
            # Mark endpoints as completed
            if not hasattr(state, 'api_endpoints_ready'):
                state.api_endpoints_ready = []
            
            for endpoint in endpoints_completed:
                if endpoint not in state.api_endpoints_ready:
                    state.api_endpoints_ready.append(endpoint)
            
            if documentation_ready:
                state.api_documentation_status = "complete"
            
            # Update completion status
            state.process_status = "completed"
            
            success = self.state_store.update_orchestration_state(
                self.orchestration_session_id,
                state
            )
            
            if success and self.messenger:
                completion_message = f"""✅ API Development Task Completed

**Task**: {task_name}
**Endpoints**: {', '.join(endpoints_completed)}
**Documentation**: {'✅ Ready' if documentation_ready else '⏳ Pending'}
**Status**: All endpoints operational and tested"""

                self.messenger.broadcast_status(completion_message)
            
            logger.info(f"Completed API development task: {task_name}")
            return success
            
        except Exception as e:
            logger.error(f"Error completing API development task: {str(e)}")
            return False

    async def run(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the Delta agent with orchestration support.
        
        Args:
            message: Input message for the agent
            context: Optional context including orchestration parameters
            
        Returns:
            Agent response with orchestration support
        """
        try:
            # Check for orchestration parameters
            if context and 'parameters' in context:
                parameters = context['parameters']
                
                # Handle workspace path changes
                if 'workspace_path' in parameters:
                    self.update_workspace_path(parameters['workspace_path'])
                
                # Handle orchestration session initialization
                if 'orchestration_session_id' in parameters:
                    session_id = uuid.UUID(parameters['orchestration_session_id'])
                    agent_id = parameters.get('agent_id', 1)  # Default agent ID
                    self.initialize_orchestration(session_id, agent_id)
            
            # Add group chat context to message if in orchestration mode
            enhanced_message = message
            if self.orchestration_session_id:
                chat_context = self.get_group_chat_context()
                enhanced_message = f"{message}\n\n{chat_context}"
            
            # Run the agent with enhanced context
            response = await super().run(enhanced_message, context)
            
            # If response contains API development updates, update state
            if self.orchestration_session_id and self.messenger:
                # Check if response mentions completed endpoints
                response_text = str(response.get('result', ''))
                if 'endpoint' in response_text.lower() and 'complete' in response_text.lower():
                    self.messenger.broadcast_status("Delta: API development progress made")
            
            return response
            
        except Exception as e:
            logger.error(f"Error running Delta agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "agent": "delta"
            }

    def __str__(self) -> str:
        """String representation of the Delta agent."""
        return f"DeltaAgent(workspace={self.workspace_path}, orchestration_session={self.orchestration_session_id})" 