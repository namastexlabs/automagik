"""LangGraph Orchestrator with State Management for Multi-Agent Coordination.

This module implements the core orchestration workflow using LangGraph with proper
state management, control flow, breakpoints, and rollback functionality.
"""

import asyncio
import logging
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal, Annotated
from typing_extensions import TypedDict
from enum import Enum
from operator import add

# Import LangGraph components with correct imports
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback for development
    StateGraph = None
    START = None
    END = None
    MemorySaver = None
    LANGGRAPH_AVAILABLE = False

from .cli_node import EnhancedCLINode, CLIExecutionError
from .git_manager import GitManager, GitOperationError
from .process_manager import ProcessManager, ProcessStatus
from .state_store import OrchestrationStateStore, OrchestrationState as StateStoreOrchestrationState
from .messaging import OrchestrationMessenger

logger = logging.getLogger(__name__)

class OrchestrationPhase(Enum):
    """Orchestration workflow phases."""
    INITIALIZATION = "initialization"
    GIT_SNAPSHOT = "git_snapshot"
    AGENT_EXECUTION = "agent_execution"
    PROCESS_MONITORING = "process_monitoring"
    DECISION = "decision"
    BREAKPOINT = "breakpoint"
    ROLLBACK = "rollback"
    COMPLETION = "completion"
    ERROR = "error"

class OrchestrationState(TypedDict):
    """Enhanced state for LangGraph orchestration with kill switch and monitoring."""
    # Core identifiers
    session_id: uuid.UUID
    orchestration_session_id: uuid.UUID
    current_agent: str
    target_agents: List[str]
    
    # Workflow state
    phase: str  # OrchestrationPhase value
    round_number: int
    max_rounds: int
    
    # Git tracking
    workspace_paths: Dict[str, str]
    git_sha_start: Optional[str]
    git_sha_end: Optional[str]
    
    # Process management
    claude_session_id: Optional[str]
    process_pid: Optional[int]
    process_status: Optional[str]  # ProcessStatus value
    active_process_pid: Optional[int]  # Currently running Claude process
    kill_requested: bool  # Kill switch for active process
    
    # Communication
    group_chat_id: Optional[str]  # Changed to str for UUID serialization
    task_message: str
    slack_thread_ts: Optional[str]  # Slack thread timestamp
    slack_channel_id: str  # Slack channel ID
    
    # Control flow
    breakpoint_requested: bool
    rollback_requested: bool
    rollback_reason: str
    rollback_to_sha: Optional[str]  # Specific SHA to rollback to
    continue_requested: bool
    
    # Results
    execution_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    completed_runs: List[Dict[str, Any]]  # All Claude session results
    agent_handoffs: List[str]  # History of agent transitions
    
    # Configuration
    orchestration_config: Dict[str, Any]
    metadata: Dict[str, Any]
    
    # Supervisor decision
    next_agent: Optional[str]
    routing_reason: str
    agent_context: str  # Context to pass to next agent
    
    # Human-in-the-loop
    awaiting_human_feedback: bool
    human_feedback_context: Optional[str]
    whatsapp_alert_sent: bool
    human_phone_number: Optional[str]
    
    # Monitoring
    recent_slack_messages: List[Dict[str, Any]]
    last_slack_check: Optional[float]
    stall_counter: int  # Track how long we've been waiting
    last_progress_timestamp: float  # Last time we saw real progress
    epic_id: Optional[str]  # Linear epic ID
    linear_project_id: Optional[str]  # Linear project ID
    epic_may_be_complete: bool  # Flag when all tasks done
    
    # History tracking for LangGraph
    messages: Annotated[List[Dict[str, Any]], add]

class LangGraphOrchestrator:
    """LangGraph-based orchestrator for multi-agent coordination."""
    
    def __init__(self):
        """Initialize the orchestrator with all required components."""
        self.cli_node = EnhancedCLINode()
        self.git_manager = GitManager()
        self.process_manager = ProcessManager()
        self.state_store = OrchestrationStateStore()
        self.messenger = OrchestrationMessenger()
        
        # Set up process state change callback
        self.process_manager.add_state_change_callback(self._on_process_state_change)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        logger.info(f"LangGraph orchestrator initialized (LangGraph available: {LANGGRAPH_AVAILABLE})")
    
    def _build_workflow(self) -> Optional[StateGraph]:
        """Build the enhanced LangGraph workflow with supervisor pattern.
        
        Returns:
            Compiled LangGraph workflow
        """
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, using fallback orchestration")
            return None
        
        try:
            # Import supervisor nodes
            from .supervisor_nodes import (
                supervisor_node, slack_monitor_node, progress_monitor_node,
                human_feedback_node, wait_node, rollback_node
            )
            
            # Create the state graph with proper TypedDict state
            workflow = StateGraph(OrchestrationState)
            
            # Add supervisor and monitoring nodes
            workflow.add_node("supervisor", supervisor_node)
            workflow.add_node("slack_monitor", slack_monitor_node)
            workflow.add_node("progress_monitor", progress_monitor_node)
            workflow.add_node("human_feedback", human_feedback_node)
            workflow.add_node("wait", wait_node)
            workflow.add_node("rollback", rollback_node)
            
            # Add agent execution nodes (wrapped for the supervisor pattern)
            # Use direct method references instead of lambdas to avoid coroutine issues
            async def run_alpha(state): return await self._run_agent_node(state, "alpha")
            async def run_beta(state): return await self._run_agent_node(state, "beta")
            async def run_gamma(state): return await self._run_agent_node(state, "gamma")
            async def run_delta(state): return await self._run_agent_node(state, "delta")
            async def run_epsilon(state): return await self._run_agent_node(state, "epsilon")
            async def run_genie(state): return await self._run_agent_node(state, "genie")
            
            workflow.add_node("alpha", run_alpha)
            workflow.add_node("beta", run_beta)
            workflow.add_node("gamma", run_gamma)
            workflow.add_node("delta", run_delta)
            workflow.add_node("epsilon", run_epsilon)
            workflow.add_node("genie", run_genie)
            
            # Entry point: Always check Slack first
            workflow.add_edge(START, "slack_monitor")
            
            # Main flow: Slack → Progress → Supervisor
            workflow.add_edge("slack_monitor", "progress_monitor")
            workflow.add_edge("progress_monitor", "supervisor")
            
            # Supervisor can route to any agent, wait, feedback, or rollback
            def supervisor_router(state):
                next_agent = state.get("next_agent")
                if next_agent == END:
                    return END
                elif next_agent:
                    return next_agent
                elif state.get("awaiting_human_feedback"):
                    return "human_feedback"
                else:
                    return "wait"
            
            workflow.add_conditional_edges(
                "supervisor",
                supervisor_router,
                {
                    "alpha": "alpha",
                    "beta": "beta",
                    "gamma": "gamma",
                    "delta": "delta",
                    "epsilon": "epsilon",
                    "genie": "genie",
                    "wait": "wait",
                    "human_feedback": "human_feedback",
                    "rollback": "rollback",
                    END: END  # For completion
                }
            )
            
            # All nodes eventually go back to slack monitor (except END)
            for node in ["alpha", "beta", "gamma", "delta", "epsilon", "genie", "wait", "human_feedback", "rollback"]:
                workflow.add_edge(node, "slack_monitor")
            
            # Compile the workflow with checkpointer for persistence
            checkpointer = MemorySaver() if MemorySaver else None
            app = workflow.compile(checkpointer=checkpointer)
            
            logger.info("Enhanced LangGraph workflow with supervisor compiled successfully")
            return app
            
        except Exception as e:
            logger.error(f"Failed to build enhanced LangGraph workflow: {str(e)}")
            return None
    
    async def _run_agent_node(self, state: OrchestrationState, agent_name: str) -> OrchestrationState:
        """Wrapper for running an agent within the supervisor pattern.
        
        Args:
            state: Current orchestration state
            agent_name: Name of agent to run
            
        Returns:
            Updated state
        """
        # Update current agent
        state["current_agent"] = agent_name
        
        # Use the agent context provided by supervisor
        if state.get("agent_context"):
            state["task_message"] = state["agent_context"]
        
        # Run the standard agent execution flow
        state = await self._git_snapshot(state)
        state = await self._run_agent(state)
        
        # Clear routing info for next iteration
        state["next_agent"] = None
        state["agent_context"] = ""
        
        return state
    
    async def execute_orchestration(
        self,
        session_id: uuid.UUID,
        agent_name: str,
        task_message: str,
        orchestration_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute the full orchestration workflow.
        
        Args:
            session_id: Orchestration session ID
            agent_name: Name of the primary agent
            task_message: Task description
            orchestration_config: Configuration parameters
            
        Returns:
            Orchestration results
        """
        try:
            # Initialize orchestration state
            state = await self._initialize_state(
                session_id=session_id,
                agent_name=agent_name,
                task_message=task_message,
                orchestration_config=orchestration_config or {}
            )
            
            if self.workflow:
                # Execute using LangGraph
                result = await self._execute_langgraph_workflow(state)
            else:
                # Fallback to direct execution
                result = await self._execute_fallback_workflow(state)
            
            return result
            
        except Exception as e:
            logger.error(f"Orchestration execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(session_id)
            }
    
    async def _initialize_state(
        self,
        session_id: uuid.UUID,
        agent_name: str,
        task_message: str,
        orchestration_config: Dict[str, Any]
    ) -> OrchestrationState:
        """Initialize the orchestration state.
        
        Args:
            session_id: Session ID
            agent_name: Agent name
            task_message: Task message
            orchestration_config: Configuration
            
        Returns:
            Initialized orchestration state
        """
        # Extract agent IDs from orchestration config
        target_agents = orchestration_config.get("target_agents", [agent_name])
        # Skip group chat creation for now - focus on orchestration execution
        # Group chat will be enabled once agents are properly registered in database
        logger.info(f"Target agents for orchestration: {target_agents}")
        group_chat_success = False  # Temporarily disable group chat
        
        # Use session_id as group_chat_id if creation succeeded
        group_chat_id = str(session_id) if group_chat_success else None
        
        # Get workspace paths from config
        workspace_paths = orchestration_config.get("workspace_paths", {})
        if not workspace_paths:
            # Default workspace paths for all agents - use the current labs directory
            workspace_paths = {
                "alpha": "/root/prod/am-agents-labs",
                "beta": "/root/prod/am-agents-labs", 
                "gamma": "/root/prod/am-agents-labs",
                "delta": "/root/prod/am-agents-labs",
                "epsilon": "/root/prod/am-agents-labs",
                "genie": "/root/prod/am-agents-labs"
            }
        
        # Initialize state as TypedDict
        state: OrchestrationState = {
            "session_id": uuid.uuid4(),  # Individual workflow session
            "orchestration_session_id": session_id,  # Parent orchestration session
            "current_agent": agent_name,
            "target_agents": target_agents,
            "phase": OrchestrationPhase.INITIALIZATION.value,
            "round_number": 0,
            "max_rounds": orchestration_config.get("max_rounds", 3),
            "workspace_paths": workspace_paths,
            "git_sha_start": None,
            "git_sha_end": None,
            "claude_session_id": None,
            "process_pid": None,
            "process_status": None,
            "active_process_pid": None,
            "kill_requested": False,
            "group_chat_id": group_chat_id,
            "task_message": task_message,
            "slack_thread_ts": orchestration_config.get("slack_thread_ts"),
            "slack_channel_id": orchestration_config.get("slack_channel_id", "C08UF878N3Z"),
            "breakpoint_requested": False,
            "rollback_requested": False,
            "rollback_reason": "",
            "rollback_to_sha": None,
            "continue_requested": True,
            "execution_result": None,
            "error_message": None,
            "completed_runs": [],
            "agent_handoffs": [],
            "orchestration_config": orchestration_config,
            "metadata": {},
            "next_agent": None,
            "routing_reason": "",
            "agent_context": "",
            "awaiting_human_feedback": False,
            "human_feedback_context": None,
            "whatsapp_alert_sent": False,
            "human_phone_number": orchestration_config.get("human_phone_number"),
            "recent_slack_messages": [],
            "last_slack_check": None,
            "stall_counter": 0,
            "last_progress_timestamp": time.time(),
            "epic_id": orchestration_config.get("epic_id"),
            "linear_project_id": orchestration_config.get("linear_project_id"),
            "epic_may_be_complete": False,
            "slack_thread_ts": orchestration_config.get("slack_thread_ts"),
            "slack_channel_id": "C08UF878N3Z",  # The genie group channel
            "messages": []
        }
        
        # Create orchestration session in database to avoid foreign key issues
        orchestration_state = StateStoreOrchestrationState(
            claude_session_id=state["claude_session_id"],
            workspace_paths=state["workspace_paths"],
            target_agents=state["target_agents"],
            max_rounds=state["max_rounds"],
            enable_rollback=orchestration_config.get("enable_rollback", True)
        )
        
        # Skip session creation in database for now - focus on orchestration execution
        # The session will be created by the agent controller if needed
        logger.info(f"Orchestration session ID: {state['orchestration_session_id']}")
        
        return state
    
    async def _execute_langgraph_workflow(self, state: OrchestrationState) -> Dict[str, Any]:
        """Execute the workflow using LangGraph.
        
        Args:
            state: Initial orchestration state
            
        Returns:
            Execution results
        """
        try:
            # Get run_count from orchestration config if available
            run_count = state["orchestration_config"].get("run_count", state["max_rounds"])
            effective_max_rounds = min(state["max_rounds"], run_count)
            
            # Update state with effective max rounds
            state["max_rounds"] = effective_max_rounds
            
            logger.info(f"Executing LangGraph workflow with effective max rounds: {effective_max_rounds}")
            
            # Execute the workflow
            config = {
                "recursion_limit": 50,
                "configurable": {
                    "thread_id": str(state["orchestration_session_id"])
                }
            }
            final_state = await self.workflow.ainvoke(state, config=config)
            
            return {
                "success": True,
                "session_id": str(final_state["orchestration_session_id"]),
                "final_phase": final_state["phase"],
                "rounds_completed": final_state["round_number"],
                "execution_result": final_state["execution_result"],
                "git_sha_end": final_state["git_sha_end"]
            }
            
        except Exception as e:
            logger.error(f"LangGraph workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(state["orchestration_session_id"])
            }
    
    async def _execute_fallback_workflow(self, state: OrchestrationState) -> Dict[str, Any]:
        """Execute workflow without LangGraph as fallback.
        
        For enhanced orchestration, this should not be used in production.
        The supervisor pattern requires LangGraph.
        
        Args:
            state: Initial orchestration state
            
        Returns:
            Execution results
        """
        logger.warning("Fallback workflow does not support enhanced supervisor pattern")
        logger.info("Executing basic single-agent workflow")
        
        try:
            # Execute single agent run
            state["round_number"] = 1
            state = await self._git_snapshot(state)
            state = await self._run_agent(state)
            
            return {
                "success": True,
                "session_id": str(state["orchestration_session_id"]),
                "final_phase": "completed",
                "rounds_completed": 1,
                "execution_result": state["execution_result"],
                "git_sha_end": state["git_sha_end"]
            }
            
        except Exception as e:
            logger.error(f"Fallback workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(state["orchestration_session_id"])
            }
    
    # Workflow node implementations
    
    async def _start_round(self, state: OrchestrationState) -> OrchestrationState:
        """Start a new orchestration round."""
        state["phase"] = OrchestrationPhase.INITIALIZATION.value
        
        logger.info(f"Starting orchestration round {state['round_number']} for {state['current_agent']}")
        
        # Send round start message to group chat
        await self.messenger.send_group_message(
            group_session_id=state["group_chat_id"],
            from_agent_name=state["current_agent"],
            message=f"Starting round {state['round_number']}: {state['task_message']}"
        )
        
        return state
    
    async def _git_snapshot(self, state: OrchestrationState) -> OrchestrationState:
        """Create git snapshot of workspace."""
        state["phase"] = OrchestrationPhase.GIT_SNAPSHOT.value
        
        try:
            workspace_path = state["workspace_paths"].get(state["current_agent"])
            if workspace_path:
                message = f"Pre-orchestration snapshot - Round {state['round_number']}"
                state["git_sha_start"] = await self.git_manager.snapshot_workspace(
                    workspace_path, message
                )
                logger.info(f"Created git snapshot: {state['git_sha_start']}")
            else:
                logger.warning(f"No workspace path configured for {state['current_agent']}")
                
        except GitOperationError as e:
            logger.error(f"Git snapshot failed: {str(e)}")
            state["error_message"] = f"Git snapshot failed: {str(e)}"
        
        return state
    
    async def _run_agent(self, state: OrchestrationState) -> OrchestrationState:
        """Execute the claude agent."""
        state["phase"] = OrchestrationPhase.AGENT_EXECUTION.value
        
        try:
            workspace_path = state["workspace_paths"].get(state["current_agent"])
            if not workspace_path:
                raise CLIExecutionError(f"No workspace configured for {state['current_agent']}")
            
            # Prepare context with group chat history
            group_context = await self.messenger.prepare_chat_context(state["group_chat_id"])
            enhanced_message = f"{state['task_message']}\n\n{group_context}"
            
            # Execute claude agent
            result = await self.cli_node.run_claude_agent(
                agent_name=state["current_agent"],
                task_message=enhanced_message,
                workspace_path=workspace_path,
                resume_session=state["claude_session_id"],
                max_turns=state["orchestration_config"].get("max_turns", 1),  # Default to 1 for tests
                orchestration_config=state["orchestration_config"]
            )
            
            # Update state with results
            state["claude_session_id"] = result.get("claude_session_id")
            state["process_pid"] = result.get("pid")
            state["active_process_pid"] = result.get("pid")  # Track active process
            state["execution_result"] = result
            state["git_sha_end"] = result.get("git_sha_end")
            
            # Add to completed runs
            state["completed_runs"].append({
                "agent": state["current_agent"],
                "result": result,
                "timestamp": time.time()
            })
            
            # Clear active process after completion
            state["active_process_pid"] = None
            
            logger.info(f"Agent execution completed: {state['current_agent']}")
            
        except CLIExecutionError as e:
            logger.error(f"Agent execution failed: {str(e)}")
            state["error_message"] = f"Agent execution failed: {str(e)}"
        
        return state
    
    async def _monitor_process(self, state: OrchestrationState) -> OrchestrationState:
        """Monitor the agent process."""
        state["phase"] = OrchestrationPhase.PROCESS_MONITORING.value
        
        if state["process_pid"]:
            # Check if process has already completed (from CLI node execution)
            if state.get("execution_result") and state["execution_result"].get("exit_code") is not None:
                # Process already completed during execution
                logger.info(f"Process {state['process_pid']} already completed with exit code {state['execution_result']['exit_code']}")
                state["process_status"] = ProcessStatus.STOPPED
                return state
            
            # Start monitoring for long-running processes
            monitor_config = state["orchestration_config"].get("process_monitoring", {})
            check_interval = monitor_config.get("check_interval", 30)
            
            success = await self.process_manager.start_monitoring(
                session_id=state["session_id"],
                pid=state["process_pid"],
                check_interval=check_interval,
                metadata={"agent_name": state["current_agent"]}
            )
            
            if success:
                logger.info(f"Started monitoring process {state['process_pid']}")
                # Wait for process completion or timeout
                await self._wait_for_process_completion(state)
            else:
                logger.warning(f"Failed to start monitoring process {state['process_pid']}")
        
        return state
    
    async def _decision(self, state: OrchestrationState) -> OrchestrationState:
        """Make decisions about workflow continuation."""
        state["phase"] = OrchestrationPhase.DECISION.value
        
        # Check for errors
        if state["error_message"]:
            logger.error(f"Error detected: {state['error_message']}")
            return state
        
        # Check process status
        if state["process_status"] == ProcessStatus.FAILED:
            state["error_message"] = "Agent process failed"
            return state
        
        # Check if rollback requested
        if state["rollback_requested"]:
            return state
        
        # Check if breakpoint requested
        if state["breakpoint_requested"]:
            return state
        
        # Continue normal flow
        state["continue_requested"] = True
        return state
    
    async def _breakpoint(self, state: OrchestrationState) -> OrchestrationState:
        """Handle breakpoint for human intervention."""
        state["phase"] = OrchestrationPhase.BREAKPOINT.value
        
        logger.info("Breakpoint triggered - waiting for human intervention")
        
        # Send breakpoint notification
        await self.messenger.send_group_message(
            group_session_id=state["group_chat_id"],
            from_agent_name="SYSTEM",
            message="🛑 BREAKPOINT: Human intervention required"
        )
        
        # In a real implementation, this would wait for human input
        # For now, we'll continue automatically
        state["breakpoint_requested"] = False
        state["continue_requested"] = True
        
        return state
    
    async def _rollback(self, state: OrchestrationState) -> OrchestrationState:
        """Handle rollback to previous state."""
        state["phase"] = OrchestrationPhase.ROLLBACK.value
        
        try:
            workspace_path = state["workspace_paths"].get(state["current_agent"])
            if workspace_path and state["git_sha_start"]:
                logger.warning(f"Rolling back to {state['git_sha_start']}: {state['rollback_reason']}")
                
                success = await self.git_manager.rollback_workspace(
                    workspace_path=workspace_path,
                    target_sha=state["git_sha_start"],
                    reason=state["rollback_reason"]
                )
                
                if success:
                    # Prepare rollback context for next attempt
                    rollback_context = self.git_manager.prepare_rollback_context(
                        state["git_sha_end"] or "unknown",
                        state["rollback_reason"]
                    )
                    state["task_message"] = f"{state['task_message']}\n\n{rollback_context}"
                    
                    # Reset for retry
                    state["rollback_requested"] = False
                    state["error_message"] = None
                    state["claude_session_id"] = None
                    
                    logger.info("Rollback completed successfully")
                else:
                    state["error_message"] = "Rollback operation failed"
            
        except GitOperationError as e:
            logger.error(f"Rollback failed: {str(e)}")
            state["error_message"] = f"Rollback failed: {str(e)}"
        
        return state
    
    async def _end_round(self, state: OrchestrationState) -> OrchestrationState:
        """Complete the current round."""
        state["phase"] = OrchestrationPhase.COMPLETION.value
        
        # Send completion message
        await self.messenger.send_group_message(
            group_session_id=state["group_chat_id"],
            from_agent_name=state["current_agent"],
            message=f"Round {state['round_number']} completed successfully"
        )
        
        # Check if we should continue to next round
        if state["round_number"] >= state["max_rounds"]:
            state["continue_requested"] = False
            logger.info(f"Maximum rounds ({state['max_rounds']}) reached")
        
        return state
    
    async def _error_handler(self, state: OrchestrationState) -> OrchestrationState:
        """Handle errors in the workflow."""
        state["phase"] = OrchestrationPhase.ERROR.value
        
        logger.error(f"Workflow error: {state['error_message']}")
        
        # Send error notification
        await self.messenger.send_group_message(
            group_session_id=state["group_chat_id"],
            from_agent_name="SYSTEM",
            message=f"❌ ERROR: {state['error_message']}"
        )
        
        state["continue_requested"] = False
        return state
    
    # Decision routers for LangGraph
    
    def _decision_router(self, state: OrchestrationState) -> str:
        """Router for decision node."""
        if state["error_message"]:
            return "error"
        if state["rollback_requested"]:
            return "rollback"
        if state["breakpoint_requested"]:
            return "breakpoint"
        return "continue"
    
    def _breakpoint_router(self, state: OrchestrationState) -> str:
        """Router for breakpoint node."""
        if state["rollback_requested"]:
            return "rollback"
        if state["error_message"]:
            return "error"
        return "continue"
    
    # Helper methods
    
    async def _wait_for_process_completion(self, state: OrchestrationState):
        """Wait for process to complete or timeout."""
        timeout = state["orchestration_config"].get("process_timeout", 3600)  # 1 hour default
        check_interval = 10
        elapsed = 0
        
        while elapsed < timeout:
            status = await self.process_manager.get_process_status(state["session_id"])
            state["process_status"] = status
            
            if status in [ProcessStatus.STOPPED, ProcessStatus.FAILED, ProcessStatus.TERMINATED]:
                break
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        if elapsed >= timeout:
            logger.warning(f"Process monitoring timed out after {timeout}s")
            state["process_status"] = ProcessStatus.UNKNOWN
    
    async def _on_process_state_change(self, session_id: uuid.UUID, new_status: ProcessStatus, process_info):
        """Callback for process state changes."""
        logger.info(f"Process state changed: {session_id} -> {new_status.value}")
        
        # Could trigger rollback on process failures
        if new_status == ProcessStatus.FAILED:
            logger.warning(f"Process {process_info.pid} failed - considering rollback")
    
    async def shutdown(self):
        """Shutdown the orchestrator and clean up resources."""
        logger.info("Shutting down LangGraph orchestrator")
        await self.process_manager.shutdown()
        logger.info("Orchestrator shutdown complete") 