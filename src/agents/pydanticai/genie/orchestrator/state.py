"""LangGraph state orchestration for Genie."""

from typing import Dict, List, Any, Optional
from datetime import datetime

# Try to import langgraph components, handle gracefully if not available
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
    LANGGRAPH_AVAILABLE = True
    # Try to import PostgresSaver separately as it requires PostgreSQL libs
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        # PostgreSQL libraries not available, we'll use in-memory checkpointing
        PostgresSaver = None
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    START = None
    END = None
    add_messages = None
    PostgresSaver = None
    ToolNode = None

from ..models import EpicState, WorkflowType, EpicPhase
from .router import WorkflowRouter
from .claude_client import ClaudeCodeClient
from .approvals import ApprovalManager
import logging

logger = logging.getLogger(__name__)


def create_orchestration_graph(
    database_url: str,
    claude_code_base_url: str = "http://localhost:8000"
) -> Optional[StateGraph]:
    """Create the LangGraph orchestration graph.
    
    Args:
        database_url: PostgreSQL connection string for checkpointing
        claude_code_base_url: Base URL for Claude Code API
        
    Returns:
        Compiled StateGraph with checkpointing, or None if LangGraph not available
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("LangGraph not available, cannot create orchestration graph")
        return None
        
    if PostgresSaver is None:
        logger.info("PostgreSQL checkpointing not available (missing libpq), using in-memory state")
        # Continue without checkpointing for now
        # TODO: Implement alternative checkpointing strategy
        
    # Initialize components
    router = WorkflowRouter()
    claude_client = ClaudeCodeClient(claude_code_base_url)
    approval_manager = ApprovalManager()
    
    # Define the graph
    workflow = StateGraph(EpicState)
    
    # Add nodes
    workflow.add_node("plan_epic", plan_epic_node)
    workflow.add_node("route_workflow", route_workflow_node) 
    workflow.add_node("execute_workflow", execute_workflow_node)
    workflow.add_node("check_approval", check_approval_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("complete_epic", complete_epic_node)
    workflow.add_node("handle_failure", handle_failure_node)
    
    # Add edges
    workflow.add_edge(START, "plan_epic")
    workflow.add_edge("plan_epic", "route_workflow")
    
    # Conditional routing from route_workflow
    workflow.add_conditional_edges(
        "route_workflow",
        route_to_next_step,
        {
            "execute": "execute_workflow",
            "complete": "complete_epic",
            "failed": "handle_failure"
        }
    )
    
    # After workflow execution, check for approvals
    workflow.add_edge("execute_workflow", "check_approval")
    
    # Conditional routing from approval check
    workflow.add_conditional_edges(
        "check_approval",
        check_approval_decision,
        {
            "continue": "route_workflow",
            "approve": "human_review",
            "complete": "complete_epic",
            "failed": "handle_failure"
        }
    )
    
    # Human review outcomes
    workflow.add_conditional_edges(
        "human_review",
        human_decision_router,
        {
            "approved": "route_workflow",
            "denied": "handle_failure",
            "rollback": "handle_failure"
        }
    )
    
    # Terminal nodes
    workflow.add_edge("complete_epic", END)
    workflow.add_edge("handle_failure", END)
    
    # Create checkpointer
    checkpointer = PostgresSaver.from_conn_string(database_url)
    
    # Compile with checkpointer
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]  # Pause for human input
    )
    
    # Store components in app for node access
    app.router = router
    app.claude_client = claude_client
    app.approval_manager = approval_manager
    
    return app


async def plan_epic_node(state: EpicState) -> Dict[str, Any]:
    """Plan the epic execution based on the request."""
    logger.info(f"Planning epic {state['epic_id']}")
    
    # Analyze the request to determine workflows
    epic_analysis = {
        "description": state["original_request"],
        "keywords": extract_keywords(state["original_request"]),
        "complexity": estimate_complexity(state["original_request"]),
        "explicit_workflows": extract_explicit_workflows(state["original_request"])
    }
    
    # Get workflow sequence from router
    router = WorkflowRouter()
    planned_workflows = router.select_workflows(epic_analysis)
    
    # Estimate costs
    cost_estimates = {}
    total_estimated_cost = 0.0
    for workflow in planned_workflows:
        cost = router.estimate_workflow_cost(workflow, epic_analysis["complexity"])
        cost_estimates[workflow.value] = cost
        total_estimated_cost += cost
    
    # Update state
    return {
        "planned_workflows": [w.value for w in planned_workflows],
        "complexity_score": epic_analysis["complexity"],
        "cost_estimates": cost_estimates,
        "phase": EpicPhase.EXECUTING.value,
        "messages": [{
            "role": "system",
            "content": f"Epic planned with {len(planned_workflows)} workflows. Estimated cost: ${total_estimated_cost:.2f}"
        }]
    }


async def route_workflow_node(state: EpicState) -> Dict[str, Any]:
    """Route to the next workflow or completion."""
    completed = set(state["completed_workflows"])
    planned = state["planned_workflows"]
    
    # Find next workflow to execute
    next_workflow = None
    for workflow in planned:
        if workflow not in completed:
            next_workflow = workflow
            break
    
    if next_workflow:
        logger.info(f"Routing to workflow: {next_workflow}")
        return {
            "current_workflow": next_workflow,
            "messages": [{
                "role": "system",
                "content": f"Starting {next_workflow} workflow"
            }]
        }
    else:
        # All workflows completed
        return {
            "current_workflow": None,
            "phase": EpicPhase.COMPLETE.value,
            "messages": [{
                "role": "system", 
                "content": "All planned workflows completed"
            }]
        }


async def execute_workflow_node(state: EpicState) -> Dict[str, Any]:
    """Execute the current workflow via Claude Code API."""
    workflow = state["current_workflow"]
    if not workflow:
        return {}
    
    logger.info(f"Executing {workflow} workflow for epic {state['epic_id']}")
    
    # Get Claude client from app context
    claude_client = ClaudeCodeClient()
    
    # Build task context from previous results
    task_context = build_workflow_context(state, workflow)
    
    # Execute workflow
    start_time = datetime.now()
    result = await claude_client.execute_workflow(
        workflow_name=workflow,
        task_context=task_context,
        epic_state=state
    )
    end_time = datetime.now()
    
    # Update workflow results
    workflow_results = state.get("workflow_results", {})
    workflow_results[workflow] = result
    
    # Update completed workflows
    completed_workflows = list(state["completed_workflows"])
    if result["status"] == "completed":
        completed_workflows.append(workflow)
    
    # Update costs
    cost_accumulated = state["cost_accumulated"] + result.get("cost_usd", 0.0)
    
    # Add to container history
    container_history = list(state.get("container_history", []))
    container_history.append({
        "workflow": workflow,
        "container_id": result.get("container_id"),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": result["status"],
        "cost_usd": result.get("cost_usd", 0.0)
    })
    
    # Create message about execution
    if result["status"] == "completed":
        message = f"✅ {workflow} completed successfully. Cost: ${result.get('cost_usd', 0):.2f}"
    else:
        message = f"❌ {workflow} failed: {result.get('error', 'Unknown error')}"
    
    return {
        "workflow_results": workflow_results,
        "completed_workflows": completed_workflows,
        "cost_accumulated": cost_accumulated,
        "container_history": container_history,
        "active_container_id": None,
        "messages": [{"role": workflow, "content": message}],
        "updated_at": datetime.now().isoformat()
    }


async def check_approval_node(state: EpicState) -> Dict[str, Any]:
    """Check if human approval is needed."""
    approval_manager = ApprovalManager()
    
    # Get last workflow result
    last_workflow = state.get("current_workflow")
    last_result = state["workflow_results"].get(last_workflow) if last_workflow else None
    
    # Check if approval needed
    approval_request = await approval_manager.check_approval_needed(state, last_result)
    
    if approval_request:
        # Add to pending approvals
        pending_approvals = list(state.get("pending_approvals", []))
        pending_approvals.append(approval_request["approval_id"])
        
        # Add approval point
        approval_points = list(state.get("approval_points", []))
        approval_points.append(approval_request)
        
        return {
            "pending_approvals": pending_approvals,
            "approval_points": approval_points,
            "messages": [{
                "role": "system",
                "content": f"🚨 Approval required: {approval_request['description']}"
            }]
        }
    
    return {}


async def human_review_node(state: EpicState) -> Dict[str, Any]:
    """Handle human review and approval."""
    # This node will be interrupted by LangGraph
    # The actual approval will come through external means (Slack, API, etc.)
    # and will be injected when the graph resumes
    
    return {
        "messages": [{
            "role": "system",
            "content": "Waiting for human approval..."
        }]
    }


async def complete_epic_node(state: EpicState) -> Dict[str, Any]:
    """Complete the epic and generate summary."""
    logger.info(f"Completing epic {state['epic_id']}")
    
    # Calculate summary statistics
    total_cost = state["cost_accumulated"]
    workflows_completed = len(state["completed_workflows"])
    total_workflows = len(state["planned_workflows"])
    success_rate = (workflows_completed / total_workflows * 100) if total_workflows > 0 else 0
    
    # Collect all git commits
    all_commits = []
    all_files = []
    for result in state["workflow_results"].values():
        all_commits.extend(result.get("git_commits", []))
        all_files.extend(result.get("files_changed", []))
    
    # Generate summary
    summary = f"""
Epic {state['epic_id']} completed successfully!

**Title**: {state['epic_title']}
**Workflows**: {workflows_completed}/{total_workflows} completed ({success_rate:.0f}%)
**Total Cost**: ${total_cost:.2f}
**Git Commits**: {len(set(all_commits))}
**Files Changed**: {len(set(all_files))}
"""
    
    return {
        "phase": EpicPhase.COMPLETE.value,
        "completed_at": datetime.now().isoformat(),
        "messages": [{
            "role": "system",
            "content": summary
        }]
    }


async def handle_failure_node(state: EpicState) -> Dict[str, Any]:
    """Handle epic failure and provide recovery options."""
    logger.error(f"Epic {state['epic_id']} failed")
    
    # Increment error count
    error_count = state.get("error_count", 0) + 1
    
    # Collect failure reasons
    failure_reasons = list(state.get("failure_reasons", []))
    
    # Add current failure
    current_workflow = state.get("current_workflow")
    if current_workflow and current_workflow in state.get("workflow_results", {}):
        error = state["workflow_results"][current_workflow].get("error", "Unknown error")
        failure_reasons.append(f"{current_workflow}: {error}")
    
    return {
        "phase": EpicPhase.FAILED.value,
        "error_count": error_count,
        "failure_reasons": failure_reasons,
        "completed_at": datetime.now().isoformat(),
        "messages": [{
            "role": "system",
            "content": f"Epic failed after {error_count} errors. Last error in {current_workflow}"
        }]
    }


# Router functions
def route_to_next_step(state: EpicState) -> str:
    """Determine next step after routing."""
    if state.get("current_workflow"):
        return "execute"
    elif state.get("phase") == EpicPhase.COMPLETE.value:
        return "complete"
    else:
        return "failed"


def check_approval_decision(state: EpicState) -> str:
    """Route based on approval check."""
    if state.get("pending_approvals"):
        return "approve"
    elif state.get("phase") == EpicPhase.FAILED.value:
        return "failed"
    elif all(w in state["completed_workflows"] for w in state["planned_workflows"]):
        return "complete"
    else:
        return "continue"


def human_decision_router(state: EpicState) -> str:
    """Route based on human decision."""
    # This will be set when the graph resumes with human input
    last_approval = state.get("approval_history", {})
    if last_approval:
        last_decision = list(last_approval.values())[-1]
        if last_decision.get("decision") == "approved":
            return "approved"
        elif last_decision.get("decision") == "rollback":
            return "rollback"
    return "denied"


# Helper functions
def extract_keywords(text: str) -> List[str]:
    """Extract keywords from request text."""
    # Simple keyword extraction - could be enhanced with NLP
    import re
    words = re.findall(r'\b\w+\b', text.lower())
    # Filter common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    return [w for w in words if w not in common_words and len(w) > 3]


def estimate_complexity(text: str) -> int:
    """Estimate epic complexity from 1-10."""
    # Simple heuristic based on length and keywords
    complexity_keywords = {
        'complex': 2, 'difficult': 2, 'challenging': 2,
        'simple': -1, 'basic': -1, 'straightforward': -1,
        'integrate': 1, 'migration': 2, 'refactor': 1,
        'multiple': 1, 'system': 1, 'architecture': 2
    }
    
    base_complexity = min(5 + len(text) // 100, 8)
    
    for keyword, adjustment in complexity_keywords.items():
        if keyword in text.lower():
            base_complexity += adjustment
    
    return max(1, min(10, base_complexity))


def extract_explicit_workflows(text: str) -> List[WorkflowType]:
    """Extract explicitly mentioned workflows."""
    workflows = []
    text_lower = text.lower()
    
    for workflow in WorkflowType:
        if workflow.value in text_lower:
            workflows.append(workflow)
    
    return workflows


def build_workflow_context(state: EpicState, workflow: str) -> str:
    """Build context for workflow execution."""
    context_parts = [
        f"Epic: {state['epic_title']}",
        f"Description: {state['epic_description']}",
        f"Original Request: {state['original_request']}"
    ]
    
    # Add previous workflow results
    if state["completed_workflows"]:
        context_parts.append(f"\\nCompleted Workflows: {', '.join(state['completed_workflows'])}")
        
        # Add relevant results from previous workflows
        for prev_workflow in state["completed_workflows"]:
            if prev_workflow in state["workflow_results"]:
                result = state["workflow_results"][prev_workflow]
                if result.get("summary"):
                    context_parts.append(f"\\n{prev_workflow} Summary: {result['summary']}")
    
    # Add specific instructions for the workflow
    workflow_instructions = {
        "architect": "Design the system architecture and create technical plans",
        "implement": "Implement the features based on the architecture",
        "test": "Create comprehensive tests for the implementation",
        "fix": "Fix any bugs or issues identified",
        "refactor": "Improve code quality and structure",
        "document": "Create documentation for the implementation",
        "review": "Review the code for quality and security",
        "pr": "Prepare the changes for merge"
    }
    
    if workflow in workflow_instructions:
        context_parts.append(f"\\nTask: {workflow_instructions[workflow]}")
    
    return "\\n".join(context_parts)