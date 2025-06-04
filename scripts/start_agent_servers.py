#!/usr/bin/env python3
"""Start multiple agent servers with unique ports and Slack integration.

This script manages the startup of multiple automagik agent servers,
each running on its own port with Slack group chat capabilities.
"""

import os
import sys
import asyncio
import argparse
import subprocess
import signal
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Legacy LangGraph implementation removed as part of NMSTX-230 cleanup
# Port management and Slack integration now handled by PydanticAI Genie implementation

# Agent configuration
AGENT_CONFIGS = {
    "alpha": {
        "name": "Alpha Orchestrator",
        "workspace": "/root/workspace/am-agents-labs",
        "role": "orchestrator"
    },
    "beta": {
        "name": "Beta Core Builder", 
        "workspace": "/root/workspace/am-agents-core",
        "role": "core"
    },
    "delta": {
        "name": "Delta API Builder",
        "workspace": "/root/workspace/am-agents-api", 
        "role": "api"
    },
    "epsilon": {
        "name": "Epsilon Tool Builder",
        "workspace": "/root/workspace/am-agents-tools",
        "role": "tools"
    },
    "gamma": {
        "name": "Gamma Quality Engineer",
        "workspace": "/root/workspace/am-agents-tests",
        "role": "quality"
    }
}


class AgentServerManager:
    """Manages multiple agent server instances."""
    
    def __init__(self, base_env_path: str = "/root/workspace/.env"):
        self.base_env_path = base_env_path
        self.processes: Dict[str, subprocess.Popen] = {}
        self.ports: Dict[str, int] = {}
        self.slack_thread_ts: Optional[str] = None
        
    def start_agent_server(self, agent_name: str, epic_name: str = "", epic_id: str = "") -> bool:
        """Start a single agent server.
        
        Args:
            agent_name: Name of the agent
            epic_name: Epic name for context
            epic_id: Epic ID for context
            
        Returns:
            True if successful
        """
        if agent_name not in AGENT_CONFIGS:
            print(f"❌ Unknown agent: {agent_name}")
            return False
            
        if agent_name in self.processes:
            print(f"⚠️  Agent {agent_name} is already running")
            return True
        
        try:
            # Simple port allocation (placeholder until NMSTX-230)
            base_port = 8000
            port_offset = {"alpha": 0, "beta": 1, "gamma": 2, "delta": 3, "epsilon": 4}.get(agent_name, 5)
            port = base_port + port_offset
            
            self.ports[agent_name] = port
            
            # Create simple agent-specific env file (placeholder)
            env_file = f"/tmp/{agent_name}_env"
            with open(env_file, 'w') as f:
                f.write(f"AM_PORT={port}\n")
                f.write(f"AM_AGENT_NAME={agent_name}\n")
            
            # Add Slack thread to env if available
            if self.slack_thread_ts:
                with open(env_file, 'a') as f:
                    f.write(f"\n# Slack Integration\n")
                    f.write(f"SLACK_THREAD_TS={self.slack_thread_ts}\n")
                    f.write(f"EPIC_NAME={epic_name}\n")
                    f.write(f"EPIC_ID={epic_id}\n")
            
            # Get agent config
            config = AGENT_CONFIGS[agent_name]
            workspace = config["workspace"]
            
            # Build command
            cmd = [
                sys.executable, "-m", "src",
                "--port", str(port),
                "--reload"
            ]
            
            # Set environment
            env = os.environ.copy()
            
            # Load agent-specific env vars
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip()
            
            # Start process
            print(f"🚀 Starting {config['name']} on port {port}...")
            process = subprocess.Popen(
                cmd,
                cwd="/root/prod/am-agents-labs",  # Always run from main project
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[agent_name] = process
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if still running
            if process.poll() is None:
                print(f"✅ {config['name']} started successfully on port {port}")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ {config['name']} failed to start")
                print(f"Stdout: {stdout}")
                print(f"Stderr: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting {agent_name}: {str(e)}")
            return False
    
    def stop_agent_server(self, agent_name: str) -> bool:
        """Stop a single agent server.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if successful
        """
        if agent_name not in self.processes:
            print(f"⚠️  Agent {agent_name} is not running")
            return True
        
        try:
            process = self.processes[agent_name]
            
            # Try graceful shutdown first
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                process.kill()
                process.wait()
            
            del self.processes[agent_name]
            
            # Release port (placeholder - no-op until NMSTX-230)
            if agent_name in self.ports:
                del self.ports[agent_name]
            
            print(f"✅ Stopped {AGENT_CONFIGS[agent_name]['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping {agent_name}: {str(e)}")
            return False
    
    def stop_all_servers(self):
        """Stop all running agent servers."""
        print("\n🛑 Stopping all agent servers...")
        agents = list(self.processes.keys())
        for agent in agents:
            self.stop_agent_server(agent)
    
    def get_status(self) -> Dict[str, Dict]:
        """Get status of all agents.
        
        Returns:
            Dictionary with agent status information
        """
        status = {}
        
        for agent_name, config in AGENT_CONFIGS.items():
            agent_status = {
                "name": config["name"],
                "running": agent_name in self.processes,
                "port": self.ports.get(agent_name),
                "workspace": config["workspace"]
            }
            
            if agent_name in self.processes:
                process = self.processes[agent_name]
                agent_status["pid"] = process.pid
                agent_status["alive"] = process.poll() is None
            
            status[agent_name] = agent_status
        
        return status
    
    def print_status(self):
        """Print formatted status of all agents."""
        print("\n📊 Agent Server Status:")
        print("=" * 60)
        
        status = self.get_status()
        
        for agent_name, info in status.items():
            emoji = "🟢" if info["running"] and info.get("alive", False) else "🔴"
            port_str = f":{info['port']}" if info.get("port") else ""
            pid_str = f" (PID: {info.get('pid', 'N/A')})" if info["running"] else ""
            
            print(f"{emoji} {info['name']:<25} {port_str:<7} {pid_str}")
        
        print("=" * 60)
        
        if self.slack_thread_ts:
            print(f"💬 Slack Thread: {self.slack_thread_ts}")
        
        print()
    
    async def create_slack_thread(self, epic_name: str, epic_id: str, agents: List[str]) -> bool:
        """Create a Slack thread for agent communication.
        
        Args:
            epic_name: Name of the epic
            epic_id: Epic ID
            agents: List of agent names
            
        Returns:
            True if successful
        """
        try:
            # Slack integration disabled pending NMSTX-230 implementation
            print("⚠️  Slack integration disabled - awaiting NMSTX-230 PydanticAI implementation")
            self.slack_thread_ts = None
            return False
                
        except Exception as e:
            print(f"❌ Error creating Slack thread: {str(e)}")
            return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start automagik agent servers")
    parser.add_argument("agents", nargs="*", help="Agents to start (default: all)")
    parser.add_argument("--epic-name", default="Development", help="Epic name")
    parser.add_argument("--epic-id", default="DEV-001", help="Epic ID")
    parser.add_argument("--no-slack", action="store_true", help="Disable Slack integration")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    
    args = parser.parse_args()
    
    # Determine which agents to start
    agents_to_start = args.agents if args.agents else list(AGENT_CONFIGS.keys())
    
    # Create manager
    manager = AgentServerManager()
    
    # Handle SIGINT/SIGTERM
    def signal_handler(signum, frame):
        print("\n\n🛑 Received shutdown signal...")
        manager.stop_all_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show status if requested
    if args.status:
        manager.print_status()
        return
    
    # Create Slack thread if not disabled
    if not args.no_slack:
        print("🔄 Setting up Slack integration...")
        success = await manager.create_slack_thread(
            epic_name=args.epic_name,
            epic_id=args.epic_id,
            agents=agents_to_start
        )
        if not success:
            print("⚠️  Continuing without Slack integration")
    
    # Start agents
    print(f"\n🚀 Starting {len(agents_to_start)} agent servers...")
    
    success_count = 0
    for agent in agents_to_start:
        if manager.start_agent_server(agent, args.epic_name, args.epic_id):
            success_count += 1
        time.sleep(1)  # Stagger startups
    
    print(f"\n✅ Started {success_count}/{len(agents_to_start)} agents successfully")
    
    # Show status
    manager.print_status()
    
    # Instructions
    print("\n📖 Instructions:")
    print("- Agents are now running on separate ports")
    if manager.slack_thread_ts:
        print(f"- Monitor Slack thread: {manager.slack_thread_ts}")
    print("- Press Ctrl+C to stop all agents")
    print("- Run with --status to check agent status")
    
    print("\n🔍 Monitoring agent output...")
    
    try:
        # Keep running until interrupted
        while True:
            # Check if any processes have died
            for agent_name, process in list(manager.processes.items()):
                if process.poll() is not None:
                    print(f"\n⚠️  {AGENT_CONFIGS[agent_name]['name']} has stopped")
                    del manager.processes[agent_name]
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())