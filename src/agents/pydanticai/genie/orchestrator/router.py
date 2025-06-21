"""Workflow routing logic for Genie orchestrator."""

from typing import List, Set, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """Intelligent routing based on epic analysis and dynamic workflow discovery."""
    
    # Pattern-based routing for dynamic workflow discovery
    TASK_PATTERNS = {
        "planning": [
            "design", "architecture", "planning", "system", "schema",
            "structure", "blueprint", "approach", "strategy", "plan"
        ],
        "implementation": [
            "build", "create", "develop", "feature", "implement",
            "add", "code", "functionality", "endpoint", "api"
        ],
        "testing": [
            "test", "validate", "verify", "check", "coverage",
            "unit test", "integration", "testing", "validation"
        ],
        "fixing": [
            "bug", "fix", "repair", "issue", "error", "broken",
            "crash", "failing", "debug", "resolve"
        ],
        "improvement": [
            "refactor", "improve", "optimize", "cleanup", "restructure",
            "performance", "efficiency", "reorganize", "simplify"
        ],
        "documentation": [
            "document", "docs", "readme", "explain", "documentation",
            "guide", "tutorial", "api docs", "comments", "user guide"
        ],
        "review": [
            "review", "analyze", "audit", "inspect", "security",
            "code review", "assessment", "evaluation", "check"
        ],
        "deployment": [
            "deploy", "release", "ship", "publish", "merge", "complete", 
            "finish", "prepare merge", "ready", "pr", "pull request"
        ]
    }
    
    # Common task sequences
    TASK_SEQUENCES = {
        "feature": ["planning", "implementation", "testing", "deployment"],
        "bugfix": ["fixing", "testing", "deployment"],
        "refactor": ["improvement", "testing", "deployment"],
        "documentation": ["documentation", "deployment"],
        "full_cycle": ["planning", "implementation", "testing", "documentation", "deployment"]
    }
    
    def __init__(self):
        """Initialize the WorkflowRouter."""
        self.task_patterns = self.TASK_PATTERNS
        self.cost_estimates = {
            "planning": 5.0,
            "implementation": 12.0,
            "testing": 8.0,
            "fixing": 6.0,
            "improvement": 10.0,
            "documentation": 4.0,
            "review": 5.0,
            "deployment": 3.0
        }
    
    def select_task_sequence(self, epic_analysis) -> List[str]:
        """Select and sequence tasks based on epic analysis.
        
        Args:
            epic_analysis: Dictionary containing analysis data, or string description
                
        Returns:
            Ordered list of task types to execute
        """
        # Handle both string and dict inputs for backwards compatibility
        if isinstance(epic_analysis, str):
            description = epic_analysis.lower()
            keywords = []
            complexity = 5
            explicit_tasks = []
        else:
            description = epic_analysis.get("description", "").lower()
            keywords = epic_analysis.get("keywords", [])
            complexity = epic_analysis.get("complexity", 5)
            explicit_tasks = epic_analysis.get("explicit_tasks", [])
        
        # If tasks are explicitly mentioned, use them
        if explicit_tasks:
            return self._validate_task_sequence(explicit_tasks)
        
        # Try custom sequence first for complex multi-task requests
        custom_sequence = self._build_custom_sequence(description, keywords)
        
        # If we have multiple tasks detected, use custom sequence
        if len(custom_sequence) >= 2:
            base_sequence = custom_sequence
        else:
            # Fall back to predefined sequences for simple requests
            epic_type = self._detect_epic_type(description, keywords)
            if epic_type in self.TASK_SEQUENCES:
                base_sequence = self.TASK_SEQUENCES[epic_type]
            else:
                base_sequence = custom_sequence
        
        # Adjust based on complexity
        if complexity >= 8 and "review" not in base_sequence:
            # Add review for complex epics
            idx = base_sequence.index("deployment") if "deployment" in base_sequence else len(base_sequence)
            base_sequence.insert(idx, "review")
        
        # Always ensure we have at least implementation if nothing else matched
        if not base_sequence:
            base_sequence = ["implementation", "testing", "deployment"]
        
        logger.info(f"Selected task sequence: {base_sequence}")
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
    
    def _build_custom_sequence(self, description: str, keywords: List[str]) -> List[str]:
        """Build a custom task sequence based on keyword matching."""
        tasks: List[str] = []
        matched_tasks: Set[str] = set()
        
        # Combine description and keywords for matching
        text = (description + " " + " ".join(keywords)).lower()
        
        # Check each task's patterns with priority for longer/more specific matches
        pattern_matches = []
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    pattern_matches.append((task_type, pattern, len(pattern)))
        
        # Sort by pattern length (longer patterns are more specific)
        pattern_matches.sort(key=lambda x: x[2], reverse=True)
        
        # Add tasks based on pattern specificity
        for task_type, pattern, length in pattern_matches:
            if task_type not in matched_tasks:
                matched_tasks.add(task_type)
        
        # Order tasks logically
        task_order = [
            "planning",
            "implementation",
            "fixing",
            "improvement",
            "testing",
            "documentation",
            "review",
            "deployment"
        ]
        
        for task_type in task_order:
            if task_type in matched_tasks:
                tasks.append(task_type)
        
        # Ensure logical task combinations
        if "implementation" in tasks:
            # If implementing something new/complex, should include planning
            complex_keywords = ["new", "system", "module", "service", "platform", "framework"]
            if any(keyword in text for keyword in complex_keywords):
                if "planning" not in tasks:
                    tasks.insert(0, "planning")
        
        # For documentation-focused requests, prioritize documentation task
        doc_keywords = ["documentation", "document", "docs", "readme", "guide"]
        if any(keyword in text for keyword in doc_keywords):
            if "documentation" not in tasks:
                tasks.append("documentation")
            # If it's primarily documentation, remove implementation tasks unless explicitly mentioned
            pure_doc_patterns = ["create documentation", "write documentation", "document the", "write user guide"]
            if any(pattern in text for pattern in pure_doc_patterns):
                # Keep only doc-related tasks
                tasks = [t for t in tasks if t in ["documentation", "deployment"]]
        
        return tasks
    
    def _validate_task_sequence(self, tasks: List[str]) -> List[str]:
        """Validate and potentially adjust task sequence for logical flow."""
        
        # Ensure planning comes before implementation if both present
        if "implementation" in tasks and "planning" in tasks:
            planning_idx = tasks.index("planning")
            implement_idx = tasks.index("implementation")
            if planning_idx > implement_idx:
                tasks[planning_idx], tasks[implement_idx] = tasks[implement_idx], tasks[planning_idx]
        
        # Ensure testing comes after implementation/fixing/improvement
        code_changing_tasks = ["implementation", "fixing", "improvement"]
        if "testing" in tasks:
            test_idx = tasks.index("testing")
            for task in code_changing_tasks:
                if task in tasks:
                    task_idx = tasks.index(task)
                    if test_idx < task_idx:
                        # Move testing after the code-changing task
                        tasks.remove("testing")
                        tasks.insert(task_idx + 1, "testing")
                        break
        
        # Ensure deployment comes last if present
        if "deployment" in tasks and tasks[-1] != "deployment":
            tasks.remove("deployment")
            tasks.append("deployment")
        
        return tasks
    
    def estimate_cost(self, tasks: List[str], complexity: int = 5) -> float:
        """Estimate total cost for a list of tasks.
        
        Args:
            tasks: List of task types to estimate
            complexity: Complexity score 1-10
            
        Returns:
            Estimated total cost in USD
        """
        total_cost = 0.0
        for task in tasks:
            total_cost += self.estimate_task_cost(task, complexity)
        return total_cost
    
    def estimate_duration(self, tasks: List[str], complexity: int = 5) -> int:
        """Estimate total duration for a list of tasks.
        
        Args:
            tasks: List of task types to estimate
            complexity: Complexity score 1-10
            
        Returns:
            Estimated duration in minutes
        """
        # Base duration per task type (in minutes)
        durations = {
            "planning": 15,
            "implementation": 30,
            "testing": 20,
            "fixing": 15,
            "improvement": 25,
            "documentation": 10,
            "review": 12,
            "deployment": 8
        }
        
        total_duration = 0
        complexity_multiplier = 1.0 + (complexity - 5) * 0.2  # Scale based on complexity
        
        for task in tasks:
            base_duration = durations.get(task, 20)  # Default 20 minutes
            total_duration += int(base_duration * complexity_multiplier)
        
        return total_duration

    def estimate_task_cost(self, task: str, complexity: int) -> float:
        """Estimate cost for a specific task based on complexity.
        
        Args:
            task: The task type
            complexity: Complexity score (1-10)
            
        Returns:
            Estimated cost in USD
        """
        # Base costs per task (average)
        base_costs = {
            "planning": 8.0,
            "implementation": 12.0,
            "testing": 6.0,
            "review": 4.0,
            "fixing": 8.0,
            "improvement": 10.0,
            "documentation": 5.0,
            "deployment": 3.0
        }
        
        base_cost = base_costs.get(task, 5.0)
        
        # Adjust for complexity (0.5x to 1.5x)
        complexity_multiplier = 0.5 + (complexity / 10)
        
        return round(base_cost * complexity_multiplier, 2)