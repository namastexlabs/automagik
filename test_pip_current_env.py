#!/usr/bin/env python3
"""Test pip installation in current environment."""

import subprocess
import sys
import os
import tempfile
import time
import requests
import shutil
from pathlib import Path

def test_cli_commands():
    """Test CLI commands."""
    print("🧪 Testing CLI commands...")
    
    # Test help
    print("\n1️⃣ Testing: automagik --help")
    result = subprocess.run(["automagik", "--help"], capture_output=True, text=True)
    print("✅ Help command" if result.returncode == 0 else f"❌ Help command: {result.stderr}")
    
    # Test agent list
    print("\n2️⃣ Testing: automagik agents list")
    result = subprocess.run(["automagik", "agents", "list"], capture_output=True, text=True)
    print("✅ Agent list" if result.returncode == 0 else f"❌ Agent list: {result.stderr}")
    if result.returncode == 0:
        print(result.stdout)
    
    # Test server help
    print("\n3️⃣ Testing: automagik-server --help")
    result = subprocess.run(["automagik-server", "--help"], capture_output=True, text=True)
    print("✅ Server help" if result.returncode == 0 else f"❌ Server help: {result.stderr}")

def test_external_agents():
    """Test external agent loading."""
    print("\n🧪 Testing external agent loading...")
    
    # Create test agent directory
    test_dir = Path.cwd() / "test_external_agents"
    test_dir.mkdir(exist_ok=True)
    
    agent_dir = test_dir / "hello_agent"
    agent_dir.mkdir(exist_ok=True)
    
    # Create test agent
    agent_code = '''"""Test external agent."""
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

def create_agent(config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    return HelloAgent(config or {})

class HelloAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self._code_prompt_text = "You are a hello agent. Say hello!"
        self.dependencies = AutomagikAgentsDependencies(
            model_name="openai:gpt-4o-mini",
            model_settings={},
            api_keys={},
            tool_config={}
        )
        self.tool_registry.register_default_tools(self.context)
    
    @property
    def model_name(self) -> str:
        return "openai:gpt-4o-mini"
'''
    
    (agent_dir / "agent.py").write_text(agent_code)
    (agent_dir / "__init__.py").touch()
    
    # Test with external agents directory
    env = os.environ.copy()
    env["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = str(test_dir)
    
    print(f"📁 Created test agent in: {test_dir}")
    
    # List agents with external directory
    result = subprocess.run(
        ["automagik", "agents", "list"],
        capture_output=True,
        text=True,
        env=env
    )
    
    if result.returncode == 0 and "hello_agent" in result.stdout:
        print("✅ External agent detected!")
    else:
        print("❌ External agent not detected")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
    
    # Cleanup
    shutil.rmtree(test_dir)
    
def test_server_startup():
    """Test server startup with timeout."""
    print("\n🧪 Testing server startup...")
    
    port = 38881
    env = os.environ.copy()
    env["AUTOMAGIK_API_PORT"] = str(port)
    env["AUTOMAGIK_DATABASE_TYPE"] = "sqlite"
    env["AUTOMAGIK_SQLITE_DATABASE_PATH"] = "test_pip.db"
    
    print(f"🚀 Starting server on port {port}...")
    
    # Start server
    server_process = subprocess.Popen(
        ["automagik-server", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for startup with timeout
    start_time = time.time()
    timeout = 20  # 20 seconds
    
    while time.time() - start_time < timeout:
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server exited early")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
            return False
        
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                
                # Test API endpoint
                headers = {"X-API-Key": env.get("AUTOMAGIK_API_KEY", "test-key")}
                response = requests.get(f"http://localhost:{port}/api/v1/agents", headers=headers, timeout=5)
                print(f"📋 Agents API: {'✅' if response.status_code == 200 else '❌'}")
                
                # Stop server
                server_process.terminate()
                server_process.wait(timeout=5)
                return True
        except:
            pass
        
        time.sleep(0.5)
    
    print("❌ Server startup timeout")
    server_process.terminate()
    server_process.wait(timeout=5)
    return False

def main():
    """Run tests."""
    print("=" * 60)
    print("🧪 Automagik Pip Installation Test (Current Environment)")
    print("=" * 60)
    
    # Check if automagik is installed
    try:
        import automagik
        print(f"✅ Automagik installed: v{automagik.__version__}")
    except ImportError:
        print("❌ Automagik not installed in current environment")
        print("Run: pip install -e .")
        return
    
    # Run tests
    test_cli_commands()
    test_external_agents()
    test_server_startup()
    
    print("\n✅ Tests completed!")

if __name__ == "__main__":
    main()