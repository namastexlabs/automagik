"""Workflow routing logic for Genie orchestrator."""

import re
from typing import List, Dict, Set
from ..models import WorkflowType
import logging

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """Intelligent routing based on epic analysis."""
    
    WORKFLOW_PATTERNS = {
        WorkflowType.ARCHITECT: [
            "design", "architecture", "planning", "system", "schema",
            "structure", "blueprint", "approach", "strategy"
        ],
        WorkflowType.IMPLEMENT: [
            "build", "create", "develop", "feature", "implement",
            "add", "code", "functionality", "endpoint", "api"
        ],
        WorkflowType.TEST: [
            "test", "validate", "verify", "check", "coverage",
            "unit test", "integration", "testing", "validation"
        ],
        WorkflowType.FIX: [
            "bug", "fix", "repair", "issue", "error", "broken",
            "crash", "failing", "debug", "resolve"
        ],
        WorkflowType.REFACTOR: [
            "refactor", "improve", "optimize", "cleanup", "restructure",
            "performance", "efficiency", "reorganize", "simplify"
        ],
        WorkflowType.DOCUMENT: [
            "document", "docs", "readme", "explain", "documentation",
            "guide", "tutorial", "api docs", "comments", "user guide"
        ],
        WorkflowType.REVIEW: [
            "review", "analyze", "audit", "inspect", "security",
            "code review", "assessment", "evaluation", "check"
        ],
        WorkflowType.PR: [
            "pr", "pull request", "merge", "complete", "finish",
            "prepare merge", "ready", "ship", "deploy"
        ]
    }
    
    # Workflow dependencies and typical sequences
    WORKFLOW_SEQUENCES = {
        "feature": [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST, WorkflowType.PR],
        "bugfix": [WorkflowType.FIX, WorkflowType.TEST, WorkflowType.PR],
        "refactor": [WorkflowType.REFACTOR, WorkflowType.TEST, WorkflowType.PR],
        "documentation": [WorkflowType.DOCUMENT, WorkflowType.PR],
        "full_cycle": [
            WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, 
            WorkflowType.TEST, WorkflowType.DOCUMENT, WorkflowType.PR
        ]
    }
    
    def __init__(self):
        """Initialize the WorkflowRouter."""
        self.workflow_patterns = self.WORKFLOW_PATTERNS
        self.cost_estimates = {
            WorkflowType.ARCHITECT: 5.0,
            WorkflowType.IMPLEMENT: 12.0,
            WorkflowType.TEST: 8.0,
            WorkflowType.FIX: 6.0,
            WorkflowType.REFACTOR: 10.0,
            WorkflowType.DOCUMENT: 4.0,
            WorkflowType.REVIEW: 5.0,
            WorkflowType.PR: 3.0
        }
    
    def select_workflows(self, epic_analysis) -> List[WorkflowType]:
        """Select and sequence workflows based on epic analysis.
        
        Args:
            epic_analysis: Dictionary containing analysis data, or string description
                
        Returns:
            Ordered list of workflows to execute
        """
        # Handle both string and dict inputs for backwards compatibility
        if isinstance(epic_analysis, str):
            description = epic_analysis.lower()
            keywords = []
            complexity = 5
            explicit_workflows = []
        else:
            description = epic_analysis.get("description", "").lower()
            keywords = epic_analysis.get("keywords", [])
            complexity = epic_analysis.get("complexity", 5)
            explicit_workflows = epic_analysis.get("explicit_workflows", [])
        
        # If workflows are explicitly mentioned, use them
        if explicit_workflows:
            return self._validate_workflow_sequence(explicit_workflows)
        
        # Try custom sequence first for complex multi-workflow requests
        custom_sequence = self._build_custom_sequence(description, keywords)
        
        # If we have multiple workflows detected, use custom sequence
        if len(custom_sequence) >= 2:
            base_sequence = custom_sequence
        else:
            # Fall back to predefined sequences for simple requests
            epic_type = self._detect_epic_type(description, keywords)
            if epic_type in self.WORKFLOW_SEQUENCES:
                base_sequence = self.WORKFLOW_SEQUENCES[epic_type]
            else:
                base_sequence = custom_sequence
        
        # Adjust based on complexity
        if complexity >= 8 and WorkflowType.REVIEW not in base_sequence:
            # Add review for complex epics
            idx = base_sequence.index(WorkflowType.PR) if WorkflowType.PR in base_sequence else len(base_sequence)
            base_sequence.insert(idx, WorkflowType.REVIEW)
        
        # Always ensure we have at least implement if nothing else matched
        if not base_sequence:
            base_sequence = [WorkflowType.IMPLEMENT, WorkflowType.TEST, WorkflowType.PR]
        
        logger.info(f"Selected workflow sequence: {[w.value for w in base_sequence]}")
        return base_sequence
    
    def _detect_epic_type(self, description: str, keywords: List[str]) -> str:
        """Detect the type of epic from description and keywords."""
        desc_lower = description.lower()
        keywords_lower = [k.lower() for k in keywords]
        all_text = desc_lower + " " + " ".join(keywords_lower)
        
        # Check for specific epic types (order matters - more specific first)
        if any(word in all_text for word in ["document", "docs", "readme", "documentation", "guide"]):
            return "documentation"
        elif any(word in all_text for word in ["bug", "fix", "broken", "error", "issue"]):
            return "bugfix"
        elif any(word in all_text for word in ["refactor", "optimize", "improve", "cleanup"]):
            return "refactor"
        elif any(word in all_text for word in ["feature", "implement", "add", "create", "new"]):
            return "feature"
        else:
            return "feature"  # Default to feature
    
    def _build_custom_sequence(self, description: str, keywords: List[str]) -> List[WorkflowType]:
        """Build a custom workflow sequence based on keyword matching."""
        workflows: List[WorkflowType] = []
        matched_workflows: Set[WorkflowType] = set()
        
        # Combine description and keywords for matching
        text = (description + " " + " ".join(keywords)).lower()
        
        # Check each workflow's patterns with priority for longer/more specific matches
        pattern_matches = []
        for workflow, patterns in self.WORKFLOW_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    pattern_matches.append((workflow, pattern, len(pattern)))
        
        # Sort by pattern length (longer patterns are more specific)
        pattern_matches.sort(key=lambda x: x[2], reverse=True)
        
        # Add workflows based on pattern specificity
        for workflow, pattern, length in pattern_matches:
            if workflow not in matched_workflows:
                matched_workflows.add(workflow)
        
        # Order workflows logically
        workflow_order = [
            WorkflowType.ARCHITECT,
            WorkflowType.IMPLEMENT,
            WorkflowType.FIX,
            WorkflowType.REFACTOR,
            WorkflowType.TEST,
            WorkflowType.DOCUMENT,
            WorkflowType.REVIEW,
            WorkflowType.PR
        ]
        
        for workflow in workflow_order:
            if workflow in matched_workflows:
                workflows.append(workflow)
        
        # Ensure logical workflow combinations
        if WorkflowType.IMPLEMENT in workflows:
            # If implementing something new/complex, should include architecture
            complex_keywords = ["new", "system", "module", "service", "platform", "framework"]
            if any(keyword in text for keyword in complex_keywords):
                if WorkflowType.ARCHITECT not in workflows:
                    workflows.insert(0, WorkflowType.ARCHITECT)
        
        # For documentation-focused requests, prioritize DOCUMENT workflow
        doc_keywords = ["documentation", "document", "docs", "readme", "guide"]
        if any(keyword in text for keyword in doc_keywords):
            if WorkflowType.DOCUMENT not in workflows:
                workflows.append(WorkflowType.DOCUMENT)
            # If it's primarily documentation, remove implementation workflows unless explicitly mentioned
            pure_doc_patterns = ["create documentation", "write documentation", "document the", "write user guide"]
            if any(pattern in text for pattern in pure_doc_patterns):
                # Keep only doc-related workflows
                workflows = [w for w in workflows if w in [WorkflowType.DOCUMENT, WorkflowType.PR]]
        
        return workflows
    
    def _validate_workflow_sequence(self, workflows: List[WorkflowType]) -> List[WorkflowType]:
        """Validate and potentially adjust workflow sequence for logical flow."""
        validated = []
        
        # Ensure architect comes before implement if both present
        if WorkflowType.IMPLEMENT in workflows and WorkflowType.ARCHITECT in workflows:
            architect_idx = workflows.index(WorkflowType.ARCHITECT)
            implement_idx = workflows.index(WorkflowType.IMPLEMENT)
            if architect_idx > implement_idx:
                workflows[architect_idx], workflows[implement_idx] = workflows[implement_idx], workflows[architect_idx]
        
        # Ensure test comes after implement/fix/refactor
        code_changing_workflows = [WorkflowType.IMPLEMENT, WorkflowType.FIX, WorkflowType.REFACTOR]
        if WorkflowType.TEST in workflows:
            test_idx = workflows.index(WorkflowType.TEST)
            for workflow in code_changing_workflows:
                if workflow in workflows:
                    workflow_idx = workflows.index(workflow)
                    if test_idx < workflow_idx:
                        # Move test after the code-changing workflow
                        workflows.remove(WorkflowType.TEST)
                        workflows.insert(workflow_idx + 1, WorkflowType.TEST)
                        break
        
        # Ensure PR comes last if present
        if WorkflowType.PR in workflows and workflows[-1] != WorkflowType.PR:
            workflows.remove(WorkflowType.PR)
            workflows.append(WorkflowType.PR)
        
        return workflows
    
    def estimate_cost(self, workflows: List[WorkflowType], complexity: int = 5) -> float:
        """Estimate total cost for a list of workflows.
        
        Args:
            workflows: List of workflows to estimate
            complexity: Complexity score 1-10
            
        Returns:
            Estimated total cost in USD
        """
        total_cost = 0.0
        for workflow in workflows:
            total_cost += self.estimate_workflow_cost(workflow, complexity)
        return total_cost
    
    def estimate_duration(self, workflows: List[WorkflowType], complexity: int = 5) -> int:
        """Estimate total duration for a list of workflows.
        
        Args:
            workflows: List of workflows to estimate
            complexity: Complexity score 1-10
            
        Returns:
            Estimated duration in minutes
        """
        # Base duration per workflow type (in minutes)
        durations = {
            WorkflowType.ARCHITECT: 15,
            WorkflowType.IMPLEMENT: 30,
            WorkflowType.TEST: 20,
            WorkflowType.FIX: 15,
            WorkflowType.REFACTOR: 25,
            WorkflowType.DOCUMENT: 10,
            WorkflowType.REVIEW: 12,
            WorkflowType.PR: 8
        }
        
        total_duration = 0
        complexity_multiplier = 1.0 + (complexity - 5) * 0.2  # Scale based on complexity
        
        for workflow in workflows:
            base_duration = durations.get(workflow, 20)  # Default 20 minutes
            total_duration += int(base_duration * complexity_multiplier)
        
        return total_duration

    def estimate_workflow_cost(self, workflow: WorkflowType, complexity: int) -> float:
        """Estimate cost for a specific workflow based on complexity.
        
        Args:
            workflow: The workflow type
            complexity: Complexity score (1-10)
            
        Returns:
            Estimated cost in USD
        """
        # Base costs per workflow (average)
        base_costs = {
            WorkflowType.ARCHITECT: 8.0,
            WorkflowType.IMPLEMENT: 12.0,
            WorkflowType.TEST: 6.0,
            WorkflowType.REVIEW: 4.0,
            WorkflowType.FIX: 8.0,
            WorkflowType.REFACTOR: 10.0,
            WorkflowType.DOCUMENT: 5.0,
            WorkflowType.PR: 3.0
        }
        
        base_cost = base_costs.get(workflow, 5.0)
        
        # Adjust for complexity (0.5x to 1.5x)
        complexity_multiplier = 0.5 + (complexity / 10)
        
        return round(base_cost * complexity_multiplier, 2)