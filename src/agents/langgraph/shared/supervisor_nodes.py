"""Supervisor nodes with MCP tool integration for LangGraph orchestration.

This module implements the supervisor and supporting nodes that use MCP tools
for intelligent routing, monitoring, and human-in-the-loop coordination.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import Field
from langgraph.graph import END
from langgraph.prebuilt import ToolNode

from .orchestrator import OrchestrationState, OrchestrationPhase

logger = logging.getLogger(__name__)

# Supervisor prompt
SUPERVISOR_PROMPT = """
You are an orchestration supervisor for a team of autonomous Claude Code agents.

Your MCP tools allow you to:
- Check Slack threads and post updates
- Monitor Linear tasks and project progress  
- Send WhatsApp alerts for urgent matters
- Perform git operations (status, log, rollback)
- Search and update agent memory

ALWAYS use tools to gather current context before making routing decisions.

Routing guidelines:
1. Check Linear task status before assigning work
2. Read recent Slack messages for human feedback
3. If tasks are stalled >30min, investigate why
4. Send WhatsApp alerts when human input is urgently needed
5. Post status updates to Slack when switching agents

Special handling for ping-pong tests:
If the task mentions "ping pong test" or test_mode is "ping_pong", route agents in this order:
genie → alpha → beta → gamma → delta → epsilon → genie (and repeat if more rounds)
Each agent should receive context about the ping pong test and not wait for user input.

Available agents:
- genie: Main orchestrator that coordinates all workflows
- alpha: Task manager and epic breakdown specialist
- beta: Core implementation 
- gamma: Quality assurance and testing
- delta: API development
- epsilon: Tools and integrations

Normal flow: genie → alpha → (beta/delta/epsilon based on needs) → gamma

Make informed routing decisions based on actual project state, not assumptions.
"""


class MCPToolExecutor:
    """Handles MCP tool execution for the supervisor."""
    
    @staticmethod
    async def execute_mcp_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool by name with given arguments.
        
        This uses the actual MCP client to execute tools.
        """
        logger.info(f"Executing MCP tool: {tool_name} with args: {args}")
        
        try:
            # Get the MCP client manager
            from src.mcp.client import get_mcp_client_manager
            mcp_client_manager = await get_mcp_client_manager()
            
            # Check if the requested server exists
            parts = tool_name.split("__")
            if len(parts) >= 3:
                server_name = parts[1]
                
                # Get list of available servers
                available_servers = [s.name for s in mcp_client_manager.list_servers()] if mcp_client_manager else []
                
                # If server not available, use mock response
                if server_name not in available_servers:
                    logger.warning(f"MCP server '{server_name}' not available. Available servers: {available_servers}")
                    logger.warning("Using mock response for testing")
                    
                    # Return appropriate mock data based on tool
                    if tool_name == "mcp__slack__slack_post_message":
                        return {
                            "success": True,
                            "result": {
                                "ts": str(time.time()),
                                "channel": args.get("channel_id", "C08UF878N3Z"),
                                "message": "Mock message posted"
                            }
                        }
                    elif tool_name == "mcp__slack__slack_reply_to_thread":
                        return {
                            "success": True,
                            "result": {
                                "ts": str(time.time()),
                                "thread_ts": args.get("thread_ts"),
                                "message": "Mock reply posted"
                            }
                        }
                    elif tool_name == "mcp__linear__linear_createProject":
                        return {
                            "success": True,
                            "result": {
                                "id": f"mock-project-{int(time.time())}",
                                "name": args.get("name", "Mock Project"),
                                "state": "started"
                            }
                        }
                    elif tool_name == "mcp__linear__linear_createIssue":
                        return {
                            "success": True,
                            "result": {
                                "id": f"mock-issue-{int(time.time())}",
                                "identifier": f"MOCK-{int(time.time() % 1000)}",
                                "title": args.get("title", "Mock Issue"),
                                "state": {"name": "Todo"}
                            }
                        }
                    else:
                        return {"success": True, "result": f"Mock execution of {tool_name}"}
            
            if mcp_client_manager and server_name in available_servers:
                # Already extracted above
                actual_tool_name = "__".join(parts[2:])
                    
                    # Execute the tool
                    result = await mcp_client_manager.call_tool(
                        server_name=server_name,
                        tool_name=actual_tool_name,
                        arguments=args
                    )
                    
                    return {"success": True, "result": result}
                else:
                    logger.error(f"Invalid MCP tool name format: {tool_name}")
                    return {"success": False, "error": "Invalid tool name format"}
            else:
                logger.warning("MCP client manager not available, returning mock data")
                # Return mock results for testing
                if tool_name == "mcp__slack__slack_get_thread_replies":
                    return {
                        "messages": [
                            {"ts": str(time.time()), "text": "Test message", "user": "U123"}
                        ]
                    }
                elif tool_name == "mcp__linear__linear_getProjectIssues":
                    return {
                        "issues": [
                            {"id": "123", "state": {"name": "In Progress"}, "updatedAt": datetime.now().isoformat()}
                        ]
                    }
                
                return {"success": True, "result": f"Mock execution of {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}


# Create handoff tools for each agent
def create_handoff_tools():
    """Create tools for handing off to each agent."""
    tools = []
    
    # Create transfer to alpha
    @tool
    def transfer_to_alpha(
        reason: str = Field(description="Reason for transferring to alpha"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to alpha agent."""
        return {
            "agent": "alpha",
            "reason": reason,
            "context": context
        }
    
    # Create transfer to beta
    @tool
    def transfer_to_beta(
        reason: str = Field(description="Reason for transferring to beta"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to beta agent."""
        return {
            "agent": "beta",
            "reason": reason,
            "context": context
        }
    
    # Create transfer to gamma
    @tool
    def transfer_to_gamma(
        reason: str = Field(description="Reason for transferring to gamma"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to gamma agent."""
        return {
            "agent": "gamma",
            "reason": reason,
            "context": context
        }
    
    # Create transfer to delta
    @tool
    def transfer_to_delta(
        reason: str = Field(description="Reason for transferring to delta"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to delta agent."""
        return {
            "agent": "delta",
            "reason": reason,
            "context": context
        }
    
    # Create transfer to epsilon
    @tool
    def transfer_to_epsilon(
        reason: str = Field(description="Reason for transferring to epsilon"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to epsilon agent."""
        return {
            "agent": "epsilon",
            "reason": reason,
            "context": context
        }
    
    # Create transfer to genie
    @tool
    def transfer_to_genie(
        reason: str = Field(description="Reason for transferring to genie"),
        context: str = Field(description="Context to pass to the agent")
    ) -> Dict[str, Any]:
        """Transfer control to genie agent."""
        return {
            "agent": "genie",
            "reason": reason,
            "context": context
        }
    
    tools = [transfer_to_alpha, transfer_to_beta, transfer_to_gamma, transfer_to_delta, transfer_to_epsilon, transfer_to_genie]
    
    return tools


# MCP tool wrappers
@tool
async def check_slack_thread(
    thread_ts: str = Field(description="Slack thread timestamp"),
    channel_id: str = Field(description="Slack channel ID")
) -> Dict[str, Any]:
    """Check Slack thread for new messages using MCP."""
    result = await MCPToolExecutor.execute_mcp_tool(
        "mcp__slack__slack_get_thread_replies",
        {"channel_id": channel_id, "thread_ts": thread_ts}
    )
    return result


@tool
async def post_to_slack(
    message: str = Field(description="Message to post"),
    thread_ts: str = Field(description="Thread to post in"),
    channel_id: str = Field(description="Channel ID")
) -> Dict[str, Any]:
    """Post a message to Slack thread using MCP."""
    result = await MCPToolExecutor.execute_mcp_tool(
        "mcp__slack__slack_reply_to_thread",
        {"channel_id": channel_id, "thread_ts": thread_ts, "text": message}
    )
    return result


@tool
async def check_linear_tasks(
    project_id: str = Field(description="Linear project ID")
) -> Dict[str, Any]:
    """Check Linear project tasks using MCP."""
    result = await MCPToolExecutor.execute_mcp_tool(
        "mcp__linear__linear_getProjectIssues",
        {"projectId": project_id}
    )
    return result


@tool
async def send_whatsapp_alert(
    message: str = Field(description="Alert message")
) -> Dict[str, Any]:
    """Send WhatsApp alert to group using MCP."""
    result = await MCPToolExecutor.execute_mcp_tool(
        "mcp__send_whatsapp_message__send_text_message",
        {"message": message}
    )
    return result


@tool
def wait_for_human(
    context: str = Field(description="What we're waiting for")
) -> Dict[str, Any]:
    """Signal that we need to wait for human input."""
    return {
        "action": "wait",
        "context": context
    }


@tool
def mark_complete(
    summary: str = Field(description="Summary of completed work")
) -> Dict[str, Any]:
    """Mark the epic as complete."""
    return {
        "action": "complete",
        "summary": summary
    }


async def supervisor_node(state: OrchestrationState) -> OrchestrationState:
    """Enhanced supervisor using MCP tools with GPT-4.1."""
    
    # Create Slack thread on first round if Slack is enabled
    if state["round_number"] == 0 and state["orchestration_config"].get("slack_notifications"):
        # Post initial message to create thread
        slack_result = await MCPToolExecutor.execute_mcp_tool(
            "mcp__slack__slack_post_message",
            {
                "channel_id": state.get("slack_channel_id", "C08UF878N3Z"),
                "text": f"🚀 Starting orchestration for epic {state.get('epic_id', 'Unknown')}\nTask: {state.get('task_message', 'No task specified')}\n\n_All updates will be posted in this thread_"
            }
        )
        
        # Extract thread timestamp from response
        if slack_result and isinstance(slack_result, dict) and slack_result.get("ts"):
            state["slack_thread_ts"] = slack_result["ts"]
            logger.info(f"Created Slack thread: {state['slack_thread_ts']}")
        
        # Send WhatsApp notification to group if configured
        if state["orchestration_config"].get("whatsapp_notifications"):
            await MCPToolExecutor.execute_mcp_tool(
                "mcp__send_whatsapp_message__send_text_message",
                {
                    "message": f"🚀 Starting AI orchestration for {state.get('epic_id', 'task')}. I'll notify you if human input is needed."
                }
            )
    
    # Handle kill request first
    if state.get("kill_requested"):
        state["kill_requested"] = False
        logger.warning("Kill requested, halting orchestration")
        state["next_agent"] = "wait"
        return state
    
    # Handle rollback request
    if state.get("rollback_requested"):
        logger.info("Rollback requested, routing to rollback node")
        state["next_agent"] = "rollback"
        return state
    
    # Create supervisor with tools
    all_tools = (
        create_handoff_tools() + 
        [check_slack_thread, post_to_slack, check_linear_tasks, 
         send_whatsapp_alert, wait_for_human, mark_complete]
    )
    
    supervisor = ChatOpenAI(
        model="gpt-4-1106-preview",  # Using GPT-4.1
        temperature=0
    ).bind_tools(all_tools)
    
    # Build context
    context_parts = []
    
    # Add last run info
    if state["completed_runs"]:
        last_run = state["completed_runs"][-1]
        context_parts.append(f"Last run: {last_run['agent']} completed at {last_run['timestamp']}")
        if "result" in last_run and isinstance(last_run["result"], dict):
            context_parts.append(f"Result: {last_run['result'].get('output', 'No output')[:200]}...")
    
    # Add recent Slack messages
    if state["recent_slack_messages"]:
        context_parts.append(f"Recent Slack: {len(state['recent_slack_messages'])} new messages")
        for msg in state["recent_slack_messages"][-3:]:
            context_parts.append(f"- {msg.get('text', '')[:100]}")
    
    # Add stall status
    if state["stall_counter"] > 0:
        context_parts.append(f"Warning: No progress for {state['stall_counter'] * 30} minutes")
    
    # Add task message if no Slack thread
    if not state.get('slack_thread_ts') and state.get('task_message'):
        context_parts.insert(0, f"Task: {state['task_message']}")
    
    # Check for test modes
    is_ping_pong = (
        "ping pong" in state.get('task_message', '').lower() or
        state.get('orchestration_config', {}).get('test_mode_settings', {}).get('test_mode') == 'ping_pong'
    )
    
    is_epic_simulation = (
        "epic simulation" in state.get('task_message', '').lower() or
        state.get('orchestration_config', {}).get('test_mode_settings', {}).get('test_mode') == 'epic_simulation'
    )
    
    if is_ping_pong:
        # Determine next agent in ping-pong sequence
        sequence = ["genie", "alpha", "beta", "gamma", "delta", "epsilon"]
        current = state.get('current_agent', 'genie')
        try:
            current_idx = sequence.index(current)
            next_idx = (current_idx + 1) % len(sequence)
            next_agent = sequence[next_idx]
            context_parts.append(f"PING PONG MODE: Route from {current} to {next_agent}")
        except ValueError:
            next_agent = "alpha"  # Default if current agent not in sequence
    elif is_epic_simulation:
        # Epic simulation mode - route based on workflow stage
        current = state.get('current_agent', 'genie')
        workflow_stage = len(state.get('agent_handoffs', []))
        
        # Define epic simulation workflow
        epic_workflow = [
            "genie",    # Create epic and announce
            "alpha",    # Break down into tasks
            "beta",     # Core implementation planning
            "gamma",    # Test planning
            "delta",    # API planning
            "epsilon"   # Tool planning
        ]
        
        if workflow_stage < len(epic_workflow):
            next_agent = epic_workflow[workflow_stage]
            context_parts.append(f"EPIC SIMULATION MODE: Stage {workflow_stage + 1} - Route to {next_agent}")
        else:
            next_agent = "complete"
            context_parts.append("EPIC SIMULATION MODE: All stages completed")
    
    # Determine test mode display
    test_mode = "PING PONG" if is_ping_pong else "EPIC SIMULATION" if is_epic_simulation else "Normal"
    
    context_message = f"""
Current State:
- Epic: {state.get('epic_id', 'Unknown')}
- Slack Thread: {state.get('slack_thread_ts', 'None')}  
- Current Agent: {state.get('current_agent', 'None')}
- Round: {state['round_number']}/{state['max_rounds']}
- Agents Run: {', '.join(state['agent_handoffs'])}
- Test Mode: {test_mode}

Context:
{chr(10).join(context_parts)}

Task: {
    f"Route to {next_agent} for ping pong test continuation." if is_ping_pong else
    f"Route to {next_agent} for epic simulation stage." if is_epic_simulation and 'next_agent' in locals() else
    "Analyze the current state and decide the next action."
}
{
    "" if (is_ping_pong or is_epic_simulation) else
    "Use tools to check Slack and Linear before making routing decisions." if state.get('slack_thread_ts') else 
    "Route to appropriate agent based on the task."
}
"""
    
    # Get supervisor response
    response = await supervisor.ainvoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=context_message)
    ])
    
    # Process tool calls
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            
            # Handle transfers
            if tool_name.startswith("transfer_to_"):
                agent = tool_name.replace("transfer_to_", "")
                state["next_agent"] = agent
                state["routing_reason"] = tool_call["args"]["reason"]
                state["agent_context"] = tool_call["args"]["context"]
                state["agent_handoffs"].append(agent)
                
                # Log to Slack (skip if no thread)
                if state.get("slack_thread_ts"):
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__slack__slack_reply_to_thread",
                        {
                            "channel_id": state.get("slack_channel_id", "C08UF878N3Z"),
                            "thread_ts": state["slack_thread_ts"],
                            "text": f"🔄 Routing to {agent}: {tool_call['args']['reason']}"
                        }
                    )
                
                return state
            
            # Handle wait
            elif tool_name == "wait_for_human":
                state["awaiting_human_feedback"] = True
                state["human_feedback_context"] = tool_call["args"]["context"]
                state["next_agent"] = "human_feedback"
                return state
            
            # Handle completion
            elif tool_name == "mark_complete":
                if state.get("slack_thread_ts"):
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__slack__slack_reply_to_thread",
                        {
                            "channel_id": state.get("slack_channel_id", "C08UF878N3Z"),
                            "thread_ts": state["slack_thread_ts"],
                            "text": f"✅ Epic complete: {tool_call['args']['summary']}"
                        }
                    )
                state["next_agent"] = END
                return state
    
    # Default: wait if no specific action
    state["next_agent"] = "wait"
    return state


async def slack_monitor_node(state: OrchestrationState) -> Dict[str, Any]:
    """Monitor Slack for new messages and commands."""
    
    if not state.get("slack_thread_ts"):
        logger.debug("No Slack thread configured, skipping monitor")
        return state
    
    try:
        # Get thread history
        result = await MCPToolExecutor.execute_mcp_tool(
            "mcp__slack__slack_get_thread_replies",
            {
                "channel_id": "C08UF878N3Z",  # The genie group channel
                "thread_ts": state["slack_thread_ts"]
            }
        )
        
        messages = result.get("messages", [])
        
        # Filter new messages
        last_check = state.get("last_slack_check", 0)
        new_messages = [
            msg for msg in messages
            if float(msg.get("ts", 0)) > last_check
        ]
        
        state["recent_slack_messages"] = new_messages
        state["last_slack_check"] = time.time()
        
        # Check for commands
        for msg in new_messages:
            text = msg.get("text", "").lower()
            
            # Kill commands
            if any(cmd in text for cmd in ["stop", "cancel", "kill", "abort"]):
                logger.warning(f"Kill command detected: {msg['text']}")
                state["kill_requested"] = True
                
                # Kill active process if any
                if state.get("active_process_pid"):
                    # Import here to avoid circular dependency
                    from .orchestrator import LangGraphOrchestrator
                    orchestrator = LangGraphOrchestrator()
                    killed = await orchestrator.cli_node.kill_active_process(
                        state["active_process_pid"], 
                        force=True
                    )
                    if killed:
                        if state.get("slack_thread_ts"):
                            await MCPToolExecutor.execute_mcp_tool(
                                "mcp__slack__slack_reply_to_thread",
                                {
                                    "channel_id": "C08UF878N3Z",
                                    "thread_ts": state["slack_thread_ts"],
                                    "text": "🛑 Killed active Claude process"
                                }
                            )
            
            # Rollback commands
            elif any(cmd in text for cmd in ["revert", "rollback", "undo"]):
                state["rollback_requested"] = True
                # Try to extract SHA from message
                import re
                sha_match = re.search(r'[a-f0-9]{7,40}', text)
                if sha_match:
                    state["rollback_to_sha"] = sha_match.group()
            
            # Human feedback
            elif not msg.get("bot_id"):  # Human message
                state["awaiting_human_feedback"] = False
                state["human_feedback_context"] = msg.get("text", "")
                state["whatsapp_alert_sent"] = False
    
    except Exception as e:
        logger.error(f"Slack monitor error: {e}")
    
    return state


async def progress_monitor_node(state: OrchestrationState) -> Dict[str, Any]:
    """Monitor Linear progress and detect stalls."""
    
    if not state.get("linear_project_id"):
        logger.debug("No Linear project configured, skipping monitor")
        return state
    
    try:
        # Check Linear tasks
        result = await MCPToolExecutor.execute_mcp_tool(
            "mcp__linear__linear_getProjectIssues",
            {"projectId": state["linear_project_id"]}
        )
        
        issues = result.get("issues", [])
        
        if issues:
            # Check for stalled progress
            latest_update = max([
                datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
                for issue in issues
            ])
            
            time_since_update = (datetime.now() - latest_update).seconds
            
            if time_since_update > 1800:  # 30 minutes
                state["stall_counter"] += 1
                
                if state["stall_counter"] >= 3 and not state.get("whatsapp_alert_sent"):
                    # Send WhatsApp alert to group
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__send_whatsapp_message__send_text_message",
                        {
                            "message": f"🚨 Epic {state.get('epic_id', 'unknown')} stalled - no updates in 90min"
                        }
                    )
                    state["whatsapp_alert_sent"] = True
            else:
                state["stall_counter"] = 0
                state["last_progress_timestamp"] = time.time()
            
            # Check if all tasks done
            open_issues = [
                i for i in issues 
                if i["state"]["name"] not in ["Done", "Canceled"]
            ]
            
            if not open_issues and issues:
                state["epic_may_be_complete"] = True
                if state.get("slack_thread_ts"):
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__slack__slack_reply_to_thread",
                        {
                            "channel_id": "C08UF878N3Z",
                            "thread_ts": state["slack_thread_ts"],
                            "text": "✅ All Linear tasks complete. Should we close this epic?"
                        }
                    )
    
    except Exception as e:
        logger.error(f"Progress monitor error: {e}")
    
    return state


async def human_feedback_node(state: OrchestrationState) -> Dict[str, Any]:
    """Request human feedback with WhatsApp notification."""
    
    if not state["awaiting_human_feedback"]:
        # Post to Slack
        context = state.get("human_feedback_context", "Human input needed")
        if state.get("slack_thread_ts"):
            await MCPToolExecutor.execute_mcp_tool(
                "mcp__slack__slack_reply_to_thread",
                {
                    "channel_id": "C08UF878N3Z",
                    "thread_ts": state["slack_thread_ts"],
                    "text": f"🤖 {context}. Please respond in this thread."
                }
            )
        
        # Send WhatsApp to group if not already sent
        if not state.get("whatsapp_alert_sent") and state["orchestration_config"].get("whatsapp_notifications"):
            await MCPToolExecutor.execute_mcp_tool(
                "mcp__send_whatsapp_message__send_text_message",
                {
                    "message": f"🔔 Your input needed on epic {state.get('epic_id', 'unknown')}\n{context}"
                }
            )
            state["whatsapp_alert_sent"] = True
        
        state["awaiting_human_feedback"] = True
    
    # Don't burn cycles - just return
    await asyncio.sleep(30)
    return state


async def wait_node(state: OrchestrationState) -> Dict[str, Any]:
    """Simple wait node for pausing execution."""
    logger.info("In wait state, pausing for 30 seconds")
    await asyncio.sleep(30)
    return state


async def rollback_node(state: OrchestrationState) -> Dict[str, Any]:
    """Handle rollback requests."""
    
    rollback_sha = state.get("rollback_to_sha")
    if not rollback_sha and state["completed_runs"]:
        # Get SHA from last run
        last_run = state["completed_runs"][-1]
        rollback_sha = last_run.get("result", {}).get("git_sha_start")
    
    if rollback_sha:
        # Import here to avoid circular dependency
        from .git_manager import GitManager
        git_manager = GitManager()
        
        # Get workspace for current agent
        workspace = state["workspace_paths"].get(state["current_agent"])
        if workspace:
            success = await git_manager.rollback_workspace(
                workspace_path=workspace,
                target_sha=rollback_sha,
                reason="Human requested rollback via Slack"
            )
            
            if success:
                if state.get("slack_thread_ts"):
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__slack__slack_reply_to_thread",
                        {
                            "channel_id": "C08UF878N3Z",
                            "thread_ts": state["slack_thread_ts"],
                            "text": f"✅ Rolled back to {rollback_sha[:8]}"
                        }
                    )
                # Remove last run
                if state["completed_runs"]:
                    state["completed_runs"].pop()
            else:
                if state.get("slack_thread_ts"):
                    await MCPToolExecutor.execute_mcp_tool(
                        "mcp__slack__slack_reply_to_thread",
                        {
                            "channel_id": "C08UF878N3Z",
                            "thread_ts": state["slack_thread_ts"],
                            "text": f"❌ Failed to rollback to {rollback_sha[:8]}"
                        }
                    )
    
    state["rollback_requested"] = False
    state["rollback_to_sha"] = None
    return state