"""Human approval management for Genie orchestrator."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from ..models import EpicState, ApprovalPoint, ApprovalStatus
import logging

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages human approval checkpoints."""
    
    APPROVAL_TRIGGERS = {
        "breaking_changes": "Architecture includes breaking changes",
        "new_endpoints": "New API endpoints detected", 
        "folder_creation": "New top-level folders planned",
        "strategy_change": "Major strategy deviation detected",
        "cost_threshold": "Approaching cost limit",
        "security_changes": "Security-sensitive modifications",
        "database_changes": "Database schema modifications",
        "external_dependencies": "New external dependencies"
    }
    
    def __init__(self):
        """Initialize the approval manager."""
        self.pending_approvals: Dict[str, ApprovalPoint] = {}
        
    async def check_approval_needed(
        self, 
        state: EpicState,
        workflow_result: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Determine if human approval is needed.
        
        Args:
            state: Current epic state
            workflow_result: Result from last workflow if any
            
        Returns:
            Approval request if needed, None otherwise
        """
        # Check if manual approval mode
        if state.get("approval_mode") == "manual":
            # Always require approval between workflows in manual mode
            if state["current_workflow"] and state["current_workflow"] not in state["completed_workflows"]:
                return self._create_approval_request(
                    state,
                    "manual_checkpoint",
                    f"Manual approval required after {state['current_workflow']}"
                )
        
        # Check cost threshold (80% of limit)
        if state["cost_accumulated"] > state["cost_limit"] * 0.8:
            return self._create_approval_request(
                state,
                "cost_threshold",
                f"Cost at ${state['cost_accumulated']:.2f} (80% of ${state['cost_limit']} limit)"
            )
        
        # Check workflow-specific triggers
        if workflow_result:
            approval_needed = self._check_workflow_triggers(state, workflow_result)
            if approval_needed:
                return approval_needed
                
        return None
        
    def _check_workflow_triggers(
        self, 
        state: EpicState,
        workflow_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for workflow-specific approval triggers.
        
        Args:
            state: Current epic state
            workflow_result: Result from workflow
            
        Returns:
            Approval request if triggered
        """
        # Check architect workflow results
        if state["current_workflow"] == "architect":
            artifacts = workflow_result.get("artifacts", {})
            
            # Check for breaking changes
            if artifacts.get("breaking_changes"):
                return self._create_approval_request(
                    state,
                    "breaking_changes",
                    f"Breaking changes detected: {', '.join(artifacts['breaking_changes'])}"
                )
                
            # Check for new API endpoints
            if artifacts.get("new_endpoints"):
                return self._create_approval_request(
                    state,
                    "new_endpoints", 
                    f"New endpoints: {', '.join(artifacts['new_endpoints'])}"
                )
                
            # Check for database changes
            if artifacts.get("database_changes"):
                return self._create_approval_request(
                    state,
                    "database_changes",
                    f"Database changes: {', '.join(artifacts['database_changes'])}"
                )
        
        # Check for new dependencies in any workflow
        if workflow_result.get("new_dependencies"):
            return self._create_approval_request(
                state,
                "external_dependencies",
                f"New dependencies: {', '.join(workflow_result['new_dependencies'])}"
            )
            
        # Check for security implications
        if self._has_security_implications(workflow_result):
            return self._create_approval_request(
                state,
                "security_changes",
                "Security-sensitive changes detected"
            )
            
        return None
        
    def _has_security_implications(self, workflow_result: Dict[str, Any]) -> bool:
        """Check if workflow result has security implications.
        
        Args:
            workflow_result: Workflow execution result
            
        Returns:
            True if security review needed
        """
        # Check files changed for security-related patterns
        security_patterns = [
            "auth", "security", "token", "password", "secret",
            "key", "credential", "permission", "access"
        ]
        
        files_changed = workflow_result.get("files_changed", [])
        for file in files_changed:
            file_lower = file.lower()
            if any(pattern in file_lower for pattern in security_patterns):
                return True
                
        # Check summary for security keywords
        summary = workflow_result.get("summary", "").lower()
        return any(pattern in summary for pattern in security_patterns)
        
    def _create_approval_request(
        self,
        state: EpicState,
        trigger: str,
        description: str
    ) -> Dict[str, Any]:
        """Create an approval request.
        
        Args:
            state: Current epic state
            trigger: Approval trigger type
            description: Human-readable description
            
        Returns:
            Approval request dictionary
        """
        approval_id = f"{state['epic_id']}-{trigger}-{datetime.now().isoformat()}"
        
        approval_point = ApprovalPoint(
            id=approval_id,
            workflow=state["current_workflow"] or "planning",
            reason=trigger,
            description=description,
            requested_at=datetime.now()
        )
        
        # Store pending approval
        self.pending_approvals[approval_id] = approval_point
        
        return {
            "approval_id": approval_id,
            "trigger": trigger,
            "description": description,
            "workflow": state["current_workflow"],
            "epic_id": state["epic_id"],
            "slack_message": self._format_slack_approval_message(state, approval_point)
        }
        
    def _format_slack_approval_message(
        self,
        state: EpicState,
        approval: ApprovalPoint
    ) -> str:
        """Format approval request for Slack.
        
        Args:
            state: Current epic state
            approval: Approval point
            
        Returns:
            Formatted Slack message
        """
        message = f"""🚨 **HUMAN APPROVAL REQUIRED**

**Epic**: {state['epic_id']} - {state['epic_title']}
**Workflow**: {approval.workflow}
**Reason**: {self.APPROVAL_TRIGGERS.get(approval.reason, approval.reason)}
**Details**: {approval.description}

**Current Progress**:
- Completed: {', '.join(state['completed_workflows']) or 'None'}
- Cost: ${state['cost_accumulated']:.2f} / ${state['cost_limit']}

**Actions**:
- Reply "approve" to continue
- Reply "deny" to stop execution
- Reply "rollback" to revert to previous state

**Approval ID**: {approval.id}
"""
        return message
        
    def record_approval_decision(
        self,
        approval_id: str,
        decision: ApprovalStatus,
        approver: str,
        comments: Optional[str] = None
    ) -> Optional[ApprovalPoint]:
        """Record a human approval decision.
        
        Args:
            approval_id: The approval ID
            decision: The decision made
            approver: Who made the decision
            comments: Optional comments
            
        Returns:
            Updated approval point or None
        """
        if approval_id not in self.pending_approvals:
            logger.warning(f"Approval {approval_id} not found")
            return None
            
        approval = self.pending_approvals[approval_id]
        approval.decided_at = datetime.now()
        approval.decision = decision
        approval.approver = approver
        approval.comments = comments
        
        # Remove from pending
        del self.pending_approvals[approval_id]
        
        logger.info(f"Approval {approval_id} decided: {decision} by {approver}")
        return approval
        
    def get_pending_approvals(self, epic_id: str) -> List[ApprovalPoint]:
        """Get all pending approvals for an epic.
        
        Args:
            epic_id: The epic ID
            
        Returns:
            List of pending approvals
        """
        return [
            approval for approval in self.pending_approvals.values()
            if approval.id.startswith(epic_id)
        ]