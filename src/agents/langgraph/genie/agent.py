"""Genie orchestrator agent - coordinates other agents using LangGraph.

This agent acts as an orchestrator that can delegate tasks to other agents
(alpha, beta, gamma, delta, epsilon) and coordinate their work.
"""

import logging
from typing import Dict, Optional, Any
from pydantic_ai import Agent
from pydantic_ai.models import Model

from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from .prompts.prompt import GENIE_PROMPT

logger = logging.getLogger(__name__)


class Genie(AutomagikAgent):
    """Genie orchestrator that coordinates other agents."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = GENIE_PROMPT
        self.name = config.get("agent_name", "genie")
        
        # Initialize dependencies with orchestration context
        self.dependencies = AutomagikAgentsDependencies(
            user_name=config.get("user_name", "User"),
            session_id=config.get("session_id", ""),
            code_prompt_text=self._code_prompt_text,
            context=self.context,
            orchestrator=True  # Mark as orchestrator
        )
        
        # No direct tools for genie - it orchestrates via API
        logger.info(f"Genie orchestrator initialized: {self.name}")
    
    def _create_agent(self, deps: AutomagikAgentsDependencies, model: Optional[Model] = None) -> Agent:
        """Create the Pydantic AI agent with orchestration capabilities."""
        agent = super()._create_agent(deps, model)
        
        # Add orchestration-specific system prompt
        orchestration_context = """
You are Genie, the orchestrator agent. Your role is to:
1. Understand the user's request
2. Break it down into tasks
3. Delegate tasks to the appropriate specialist agents:
   - Alpha: Project management and coordination
   - Beta: Core implementation and development
   - Gamma: Quality assurance and testing
   - Delta: API development and integration
   - Epsilon: Tools and utilities

You coordinate their work and ensure tasks are completed efficiently.
For the ping pong test, you should demonstrate agent coordination by having agents pass messages back and forth.
"""
        
        # Update system prompt with orchestration context
        if hasattr(agent, '_system_prompt'):
            agent._system_prompt = orchestration_context + "\n\n" + agent._system_prompt
        
        return agent
    
    async def process_request(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process orchestration request and coordinate agents.
        
        For now, this returns instructions on how to orchestrate.
        Actual orchestration happens through the LangGraph workflow.
        """
        # Parse the request to determine orchestration strategy
        request_lower = message.lower()
        
        if "ping pong" in request_lower:
            return self._create_ping_pong_plan()
        elif "test" in request_lower and "orchestration" in request_lower:
            return self._create_test_orchestration_plan()
        else:
            return self._create_general_orchestration_plan(message)
    
    def _create_ping_pong_plan(self) -> str:
        """Create a ping pong test plan."""
        return """🎾 Ping Pong Orchestration Test Plan:

1. **Round 1**: Alpha → Beta
   - Alpha: "Ping! Starting orchestration test."
   - Beta: "Pong! Ready to implement."

2. **Round 2**: Beta → Gamma  
   - Beta: "Ping! Implementation complete."
   - Gamma: "Pong! Starting quality checks."

3. **Round 3**: Gamma → Delta
   - Gamma: "Ping! Tests passing."
   - Delta: "Pong! API endpoints ready."

4. **Round 4**: Delta → Epsilon
   - Delta: "Ping! Integration complete."
   - Epsilon: "Pong! Tools configured."

5. **Round 5**: Epsilon → Alpha
   - Epsilon: "Ping! All systems go."
   - Alpha: "Pong! Orchestration test complete!"

This demonstrates multi-agent coordination with message passing."""
    
    def _create_test_orchestration_plan(self) -> str:
        """Create a test orchestration plan."""
        return """🧪 Test Orchestration Plan:

1. **Initialization**: 
   - Create test session
   - Initialize all agents
   - Set up communication channels

2. **Execution**:
   - Alpha: Coordinate the test
   - Beta: Execute test logic
   - Gamma: Validate results
   - Delta: Check API responses
   - Epsilon: Monitor performance

3. **Completion**:
   - Collect results from all agents
   - Generate summary report
   - Clean up resources"""
    
    def _create_general_orchestration_plan(self, request: str) -> str:
        """Create a general orchestration plan based on the request."""
        return f"""📋 Orchestration Plan for: "{request}"

1. **Analysis Phase**:
   - Understanding the request
   - Identifying required agents
   - Planning task distribution

2. **Delegation Phase**:
   - Alpha: Project oversight
   - Beta: Core development
   - Gamma: Quality assurance
   - Delta: API work
   - Epsilon: Tooling support

3. **Coordination Phase**:
   - Monitor progress
   - Handle inter-agent communication
   - Resolve blockers

4. **Completion Phase**:
   - Gather results
   - Verify completion
   - Report back to user

Ready to orchestrate this request through the LangGraph workflow."""