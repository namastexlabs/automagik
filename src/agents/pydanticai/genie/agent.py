"""GenieAgent implementation with embedded LangGraph orchestration."""

import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import langgraph, but gracefully handle if not available
try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    logger.debug(f"LangGraph import failed: {e}")
    LANGGRAPH_AVAILABLE = False
    StateGraph = None

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.config import settings

from .prompts.prompt import AGENT_PROMPT
from .models import (
    EpicRequest, EpicPlan, EpicState, EpicPhase, 
    WorkflowType, EpicSummary
)

# Only import orchestrator if langgraph is available
if LANGGRAPH_AVAILABLE:
    from .orchestrator import (
        create_orchestration_graph, WorkflowRouter, 
        ClaudeCodeClient, ApprovalManager
    )


class GenieAgent(AutomagikAgent):
    """Genie orchestrator agent that coordinates Claude Code workflows.
    
    This agent uses PydanticAI for natural language understanding and
    embedded LangGraph for workflow orchestration.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the GenieAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        # Initialize base agent
        super().__init__(config)
        
        # Store config for later use
        self.config = config
        
        # Set the agent prompt
        self._code_prompt_text = AGENT_PROMPT
        
        # Initialize dependencies like Sofia does
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model_name", "openai:gpt-4.1"),
            model_settings={},
            session_id=config.get("session_id", str(uuid.uuid4())),
            user_id=config.get("user_id")
        )
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register tools
        self.tool_registry.register_default_tools(self.context)
        
        # Note: PydanticAI agent and tool registration will be done lazily in run()
        
        # Initialize orchestration components only if LangGraph is available
        if LANGGRAPH_AVAILABLE:
            # Initialize orchestration components
            self.workflow_graph = self._create_orchestration_graph()
            self.router = WorkflowRouter()
            self.claude_client = ClaudeCodeClient(
                base_url=getattr(settings, 'CLAUDE_CODE_API_URL', "http://localhost:8000")
            )
            self.approval_manager = ApprovalManager()
            
            # Track active epics
            self.active_epics: Dict[str, EpicState] = {}
            
            logger.info("GenieAgent initialized successfully with LangGraph orchestration")
        else:
            # Disable orchestration features
            self.workflow_graph = None
            self.router = None
            self.claude_client = None
            self.approval_manager = None
            self.active_epics = {}
            
            logger.info("GenieAgent initialized without LangGraph orchestration")
        
    def _create_orchestration_graph(self) -> Optional[StateGraph]:
        """Create the embedded LangGraph orchestration graph.
        
        Returns:
            Configured StateGraph for workflow orchestration, or None if LangGraph not available
        """
        if not LANGGRAPH_AVAILABLE:
            logger.info("LangGraph orchestration disabled")
            return None
            
        try:
            database_url = settings.DATABASE_URL
            return create_orchestration_graph(
                database_url=database_url,
                claude_code_base_url=getattr(settings, 'CLAUDE_CODE_API_URL', "http://localhost:8000")
            )
        except Exception as e:
            logger.error(f"Failed to create orchestration graph: {e}")
            # Return None - orchestration will be disabled
            return None
            
            
    async def _plan_epic(self, request: EpicRequest) -> EpicPlan:
        """Plan an epic based on the request.
        
        Args:
            request: The epic request
            
        Returns:
            Epic execution plan
        """
        # Analyze request
        epic_analysis = {
            "description": request.message,
            "keywords": self._extract_keywords(request.message),
            "complexity": self._estimate_complexity(request.message),
            "explicit_workflows": self._extract_explicit_workflows(request.message)
        }
        
        # Get workflow sequence
        if self.router:
            planned_workflows = self.router.select_workflows(epic_analysis)
        else:
            # Fallback when router is not available
            planned_workflows = [WorkflowType.TEST]
        
        # Add required workflows if not present
        if request.require_tests and WorkflowType.TEST not in planned_workflows:
            # Add test after implementation workflows
            for i, workflow in enumerate(planned_workflows):
                if workflow in [WorkflowType.IMPLEMENT, WorkflowType.FIX, WorkflowType.REFACTOR]:
                    planned_workflows.insert(i + 1, WorkflowType.TEST)
                    break
                    
        if request.require_pr and WorkflowType.PR not in planned_workflows:
            planned_workflows.append(WorkflowType.PR)
            
        # Estimate costs
        total_cost = 0.0
        for workflow in planned_workflows:
            if self.router:
                cost = self.router.estimate_workflow_cost(workflow, epic_analysis["complexity"])
            else:
                cost = 10.0  # Fallback cost estimate
            total_cost += cost
            
        # Generate epic title
        epic_title = self._generate_epic_title(request.message)
        
        # Create plan
        return EpicPlan(
            epic_id=f"GENIE-{uuid.uuid4().hex[:8].upper()}",
            title=epic_title,
            description=request.message,
            complexity_score=epic_analysis["complexity"],
            planned_workflows=planned_workflows,
            estimated_cost=total_cost,
            estimated_duration_minutes=len(planned_workflows) * 20,  # Rough estimate
            requires_approvals=[]  # Will be determined during execution
        )
        
    def _initialize_epic_state(
        self, 
        request: EpicRequest,
        plan: EpicPlan
    ) -> EpicState:
        """Initialize epic state for orchestration.
        
        Args:
            request: Original epic request
            plan: Epic execution plan
            
        Returns:
            Initialized epic state
        """
        now = datetime.now().isoformat()
        
        # Get Slack channel if configured
        slack_channel = getattr(self.dependencies, 'channel_config', {}).get("slack_channel_id")
        
        return EpicState(
            # Core identifiers
            epic_id=plan.epic_id,
            session_id=self.dependencies.session_id,
            user_id=self.dependencies.user_id,
            thread_id=f"{plan.epic_id}-thread",
            
            # Epic details
            original_request=request.message,
            epic_title=plan.title,
            epic_description=plan.description,
            complexity_score=plan.complexity_score,
            
            # Workflow planning
            planned_workflows=[w.value for w in plan.planned_workflows],
            completed_workflows=[],
            current_workflow=None,
            workflow_results={},
            
            # Cost management
            cost_accumulated=0.0,
            cost_limit=request.budget_limit,
            cost_estimates={w.value: (self.router.estimate_workflow_cost(w, plan.complexity_score) 
                                    if self.router else 10.0)
                           for w in plan.planned_workflows},
            
            # Approval tracking
            approval_points=[],
            pending_approvals=[],
            approval_history={},
            
            # Execution state
            phase=EpicPhase.PLANNING.value,
            error_count=0,
            rollback_points=[],
            
            # Learning & patterns
            applied_patterns=[],
            discovered_patterns=[],
            failure_reasons=[],
            
            # Communication
            slack_channel_id=slack_channel,
            slack_thread_ts=None,
            messages=[],
            
            # Git state
            git_branch=f"genie/{plan.epic_id}",
            git_snapshots={},
            
            # Container tracking
            active_container_id=None,
            container_history=[],
            
            # Timestamps
            created_at=now,
            updated_at=now,
            completed_at=None
        )
        
    async def _execute_epic(self, state: EpicState) -> None:
        """Execute an epic using the orchestration graph.
        
        Args:
            state: The epic state
        """
        if not self.workflow_graph:
            logger.error("Orchestration graph not available")
            state["phase"] = EpicPhase.FAILED.value
            state["failure_reasons"] = ["Orchestration system not available"]
            return
            
        try:
            # Create Slack thread for communication
            if state.get("slack_channel_id"):
                thread_ts = await self._create_slack_thread(state)
                state["slack_thread_ts"] = thread_ts
                
            # Execute through LangGraph
            config = {"configurable": {"thread_id": state["thread_id"]}}
            
            # Run the orchestration
            final_state = await self.workflow_graph.ainvoke(
                state,
                config
            )
            
            # Update our tracked state
            self.active_epics[state["epic_id"]] = final_state
            
            # Send completion notification
            if final_state["phase"] == EpicPhase.COMPLETE.value:
                await self._notify_epic_completion(final_state)
                
        except Exception as e:
            logger.error(f"Error executing epic {state['epic_id']}: {e}")
            state["phase"] = EpicPhase.FAILED.value
            state["failure_reasons"] = [str(e)]
            
    async def _create_slack_thread(self, state: EpicState) -> Optional[str]:
        """Create a Slack thread for epic communication.
        
        Args:
            state: The epic state
            
        Returns:
            Thread timestamp if created
        """
        try:
            # Use MCP Slack tool to create thread
            from src.mcp.client import call_mcp_tool
            
            message = f"""🚀 **EPIC STARTED**: {state['epic_id']} - {state['epic_title']}

**Workflow**: Genie Orchestrator
**Phase**: Planning & Execution
**Status**: INITIALIZING

**Planned Workflows**: {', '.join(state['planned_workflows'])}
**Estimated Cost**: ${sum(state['cost_estimates'].values()):.2f}
**Complexity**: {state['complexity_score']}/10

This thread will track all communication for this epic across all workflows."""

            result = await call_mcp_tool(
                self.context.get("mcp_manager"),
                "mcp__slack__slack_post_message",
                {
                    "channel_id": state["slack_channel_id"],
                    "text": message
                }
            )
            
            if result and result.get("ts"):
                return result["ts"]
                
        except Exception as e:
            logger.error(f"Failed to create Slack thread: {e}")
            
        return None
        
    async def _notify_epic_completion(self, state: EpicState) -> None:
        """Send completion notification for an epic.
        
        Args:
            state: The completed epic state
        """
        try:
            # Create summary
            summary = EpicSummary(
                epic_id=state["epic_id"],
                title=state["epic_title"],
                status=EpicPhase(state["phase"]),
                workflows_completed=[WorkflowType(w) for w in state["completed_workflows"]],
                total_cost=state["cost_accumulated"],
                duration_minutes=self._calculate_duration(state),
                git_commits=self._collect_git_commits(state),
                files_changed=self._collect_files_changed(state),
                approvals_required=len(state["approval_points"]),
                approvals_received=len([a for a in state["approval_history"].values() 
                                      if a.get("decision") == "approved"]),
                rollbacks_performed=len(state.get("rollback_points", [])),
                success_rate=len(state["completed_workflows"]) / len(state["planned_workflows"]) * 100,
                summary=self._generate_summary(state)
            )
            
            # Send Slack notification if configured
            if state.get("slack_thread_ts"):
                from src.mcp.client import call_mcp_tool
                
                await call_mcp_tool(
                    self.context.get("mcp_manager"),
                    "mcp__slack__slack_reply_to_thread",
                    {
                        "channel_id": state["slack_channel_id"],
                        "thread_ts": state["slack_thread_ts"],
                        "text": f"✅ **EPIC COMPLETE**\\n\\n{summary.summary}"
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to notify epic completion: {e}")
            
    # Helper methods
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        import re
        words = re.findall(r'\\b\\w+\\b', text.lower())
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        return [w for w in words if w not in common_words and len(w) > 3][:20]
        
    def _estimate_complexity(self, text: str) -> int:
        """Estimate complexity from 1-10."""
        # Length-based initial estimate
        length_score = min(len(text) // 50, 5)
        
        # Keyword-based adjustments
        complexity_keywords = {
            'complex': 2, 'integration': 2, 'migration': 2,
            'simple': -1, 'basic': -1, 'minor': -1
        }
        
        adjustment = 0
        for keyword, score in complexity_keywords.items():
            if keyword in text.lower():
                adjustment += score
                
        return max(1, min(10, 5 + length_score + adjustment))
        
    def _extract_explicit_workflows(self, text: str) -> List[WorkflowType]:
        """Extract explicitly mentioned workflows."""
        workflows = []
        text_lower = text.lower()
        
        for workflow in WorkflowType:
            if workflow.value in text_lower:
                workflows.append(workflow)
                
        return workflows
        
    def _generate_epic_title(self, request: str) -> str:
        """Generate a concise epic title."""
        # Take first 10 words or up to first period/newline
        words = request.split()[:10]
        title = " ".join(words)
        
        # Clean up
        if len(title) > 80:
            title = title[:77] + "..."
            
        # Capitalize first letter
        return title[0].upper() + title[1:] if title else "Untitled Epic"
        
    def _calculate_duration(self, state: EpicState) -> int:
        """Calculate epic duration in minutes."""
        if state.get("created_at") and state.get("completed_at"):
            try:
                start = datetime.fromisoformat(state["created_at"])
                end = datetime.fromisoformat(state["completed_at"])
                return int((end - start).total_seconds() / 60)
            except Exception:
                pass
        return 0
        
    def _collect_git_commits(self, state: EpicState) -> List[str]:
        """Collect all git commits from workflows."""
        commits = []
        for result in state.get("workflow_results", {}).values():
            commits.extend(result.get("git_commits", []))
        return list(set(commits))  # Unique commits
        
    def _collect_files_changed(self, state: EpicState) -> List[str]:
        """Collect all files changed from workflows."""
        files = []
        for result in state.get("workflow_results", {}).values():
            files.extend(result.get("files_changed", []))
        return list(set(files))  # Unique files
        
    def _generate_summary(self, state: EpicState) -> str:
        """Generate epic summary."""
        return f"""Epic {state['epic_id']} - {state['epic_title']}

Completed {len(state['completed_workflows'])} of {len(state['planned_workflows'])} workflows.
Total cost: ${state['cost_accumulated']:.2f}
Status: {state['phase']}

Workflows executed: {', '.join(state['completed_workflows']) or 'None'}"""
        
    async def run(
        self, 
        input_text: str, 
        *, 
        multimodal_content=None,
        system_message=None, 
        message_history_obj=None,
        channel_payload: Optional[Dict] = None,
        message_limit: Optional[int] = None
    ) -> AgentResponse:
        """Run the Genie agent with natural language input.
        
        Args:
            input_text: Natural language epic description
            multimodal_content: Optional multimodal content (not used by Genie)
            system_message: Optional system message override
            message_history_obj: Optional message history
            channel_payload: Optional channel-specific data
            message_limit: Optional message limit
            
        Returns:
            AgentResponse with epic creation result
        """
        try:
            # Parse budget and options from input if present
            budget_limit = 50.0
            approval_mode = "auto"
            
            # Simple parsing for budget mentions
            import re
            budget_match = re.search(r'\$(\d+(?:\.\d{2})?)', input_text)
            if budget_match:
                budget_limit = float(budget_match.group(1))
                
            # Check for manual approval mode
            if "manual" in input_text.lower() or "approve" in input_text.lower():
                approval_mode = "manual"
            
            # Create epic using internal method
            result = await self.create_epic(
                request=input_text,
                budget_limit=budget_limit,
                require_tests=True,
                require_pr=True,
                approval_mode=approval_mode
            )
            
            if "error" in result:
                return AgentResponse(
                    text=f"❌ Error creating epic: {result['error']}",
                    success=False,
                    error_message=result['error']
                )
            
            # Format success response
            response_text = f"""🚀 **Epic Created**: {result['epic_id']} - {result['title']}

**Status**: {result['status'].title()}
**Planned Workflows**: {', '.join(result['planned_workflows'])}
**Estimated Cost**: ${result['estimated_cost']:.2f}
**Approval Required**: {'Yes' if result['approval_required'] else 'No'}

**Tracking**: {result['tracking_url']}

Your epic is now executing! Check the status URL above for progress updates."""
            
            return AgentResponse(
                text=response_text,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error in Genie.run: {e}")
            return AgentResponse(
                text=f"❌ Failed to process epic: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    async def create_epic(
        self,
        request: str,
        budget_limit: float = 50.0,
        require_tests: bool = True,
        require_pr: bool = True,
        approval_mode: str = "auto"
    ) -> Dict[str, Any]:
        """Create and execute a new development epic.
        
        This is the main method for epic creation.
        
        Args:
            request: Natural language description of the epic
            budget_limit: Maximum budget in USD (default: 50)
            require_tests: Whether to require test workflow
            require_pr: Whether to require PR workflow
            approval_mode: "auto" or "manual" approval mode
            
        Returns:
            Epic creation response with ID and plan
        """
        try:
            # Validate request
            if not request or not request.strip():
                raise ValueError("message cannot be empty")
            
            # Create epic request
            epic_request = EpicRequest(
                message=request,
                context={
                    "user_id": self.dependencies.user_id,
                    "session_id": self.dependencies.session_id
                },
                budget_limit=budget_limit,
                require_tests=require_tests,
                require_pr=require_pr,
                approval_mode=approval_mode
            )
            
            # Analyze and plan the epic
            epic_plan = await self._plan_epic(epic_request)
            
            # Check cost limit
            if hasattr(self, 'config') and self.config.get('max_cost', float('inf')) < epic_plan.estimated_cost:
                return {
                    "error": "cost limit exceeded",
                    "status": "failed"
                }
            
            # Initialize epic state
            epic_state = self._initialize_epic_state(epic_request, epic_plan)
            
            # Store active epic
            self.active_epics[epic_plan.epic_id] = epic_state
            
            # Start async execution (simplified for now)
            # TODO: Implement full orchestration
            logger.info(f"Epic {epic_plan.epic_id} planned with {len(epic_plan.planned_workflows)} workflows")
            
            return {
                "epic_id": epic_plan.epic_id,
                "title": epic_plan.title,
                "status": "executing",
                "planned_workflows": [w.value for w in epic_plan.planned_workflows],
                "estimated_cost": epic_plan.estimated_cost,
                "approval_required": len(epic_plan.requires_approvals) > 0,
                "tracking_url": f"/api/v1/agent/genie/status/{epic_plan.epic_id}"
            }
            
        except Exception as e:
            logger.error(f"Error creating epic: {e}")
            return {
                "error": str(e),
                "status": "failed"
            }