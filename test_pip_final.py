#!/usr/bin/env python3
"""Final pip installation test with correct commands and better debugging."""

import subprocess
import time
import requests
import os
from pathlib import Path

def test_installation_status():
    """Test current installation status."""
    print("🧪 Testing Installation Status")
    print("=" * 60)
    
    # Check package installation
    result = subprocess.run(
        ["pip", "show", "automagik"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Package installed:")
        for line in result.stdout.strip().split('\n'):
            if line.startswith(('Name:', 'Version:', 'Location:')):
                print(f"   {line}")
    else:
        print("❌ Package not installed")
        return False
    
    # Check entry points
    print("\n📋 Checking entry points...")
    for cmd in ["automagik", "automagik-server"]:
        result = subprocess.run(["which", cmd], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {cmd}: {result.stdout.strip()}")
        else:
            print(f"❌ {cmd}: not found")
    
    return True

def test_cli_structure():
    """Test CLI command structure."""
    print("\n🧪 Testing CLI Structure")
    print("=" * 60)
    
    commands = [
        (["automagik", "--help"], "Main help"),
        (["automagik", "agents", "--help"], "Agents help"),
        (["automagik", "agents", "status"], "Server status"),
        (["automagik-server", "--help"], "Server help")
    ]
    
    for cmd, desc in commands:
        print(f"\n📌 {desc}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Command successful")
            # Show first few lines of output
            lines = result.stdout.strip().split('\n')[:5]
            for line in lines:
                print(f"   {line}")
        else:
            print(f"❌ Command failed: {result.stderr.strip()[:100]}")

def test_external_agents():
    """Test external agent loading mechanism."""
    print("\n🧪 Testing External Agent Loading")
    print("=" * 60)
    
    # Create test directory
    test_dir = Path("/tmp/test_external_agents")
    test_dir.mkdir(exist_ok=True)
    
    # Create test agent
    agent_dir = test_dir / "test_external_agent"
    agent_dir.mkdir(exist_ok=True)
    
    agent_code = '''"""Test external agent."""
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

def create_agent(config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    """Factory function for external agent."""
    return TestExternalAgent(config or {})

class TestExternalAgent(AutomagikAgent):
    """External test agent."""
    
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self._code_prompt_text = "I am an external test agent!"
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
    
    print(f"✅ Created test agent in: {agent_dir}")
    
    # Test discovery with environment variable
    env = os.environ.copy()
    env["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = str(test_dir)
    
    # Try to check if agent factory can discover it
    test_script = f"""
import os
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = '{test_dir}'
os.environ['AUTOMAGIK_DATABASE_TYPE'] = 'sqlite'
os.environ['AUTOMAGIK_SQLITE_DATABASE_PATH'] = ':memory:'

from automagik.agents.models.agent_factory import AgentFactory
AgentFactory._discover_external_agents()

if 'test_external_agent' in AgentFactory._available_agents:
    print("✅ External agent discovered!")
else:
    print("❌ External agent not found")
    print(f"Available agents: {{list(AgentFactory._available_agents.keys())}}")
"""
    
    result = subprocess.run(
        ["python", "-c", test_script],
        capture_output=True,
        text=True,
        env=env
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Stderr: {result.stderr}")
    
    return "External agent discovered!" in result.stdout

def test_server_on_custom_port():
    """Test server startup on custom port."""
    print("\n🧪 Testing Server on Custom Port")
    print("=" * 60)
    
    port = 38881
    env = os.environ.copy()
    env["AUTOMAGIK_API_PORT"] = str(port)
    env["AUTOMAGIK_DATABASE_TYPE"] = "sqlite"
    env["AUTOMAGIK_SQLITE_DATABASE_PATH"] = "/tmp/test_automagik.db"
    env["SKIP_DB_INIT"] = "true"
    
    print(f"🚀 Starting server on port {port}...")
    
    # Start server process
    server_process = subprocess.Popen(
        ["automagik-server", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Monitor startup
    start_time = time.time()
    timeout = 30
    server_started = False
    
    while time.time() - start_time < timeout:
        # Check if process is still running
        if server_process.poll() is not None:
            output = server_process.stdout.read()
            print(f"❌ Server exited early")
            print("Output:")
            print(output)
            return False
        
        # Try to connect
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                server_started = True
                break
        except:
            pass
        
        time.sleep(0.5)
    
    if server_started:
        # Test endpoints
        print("\n📋 Testing endpoints...")
        
        # Health check
        try:
            response = requests.get(f"http://localhost:{port}/health")
            print(f"  /health: {'✅' if response.status_code == 200 else '❌'} ({response.status_code})")
        except Exception as e:
            print(f"  /health: ❌ {e}")
        
        # API agents (with auth)
        try:
            headers = {"X-API-Key": env.get("AUTOMAGIK_API_KEY", "test-key")}
            response = requests.get(f"http://localhost:{port}/api/v1/agents", headers=headers)
            print(f"  /api/v1/agents: {'✅' if response.status_code == 200 else '❌'} ({response.status_code})")
            if response.status_code == 200:
                agents = response.json()
                print(f"    Found {len(agents)} agents")
        except Exception as e:
            print(f"  /api/v1/agents: ❌ {e}")
    else:
        print("❌ Server startup timeout")
    
    # Cleanup
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()
    
    return server_started

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Automagik Pip Installation Final Test")
    print("=" * 60)
    
    tests = [
        ("Installation Status", test_installation_status),
        ("CLI Structure", test_cli_structure),
        ("External Agents", test_external_agents),
        ("Server Custom Port", test_server_on_custom_port)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    overall = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if overall else '❌ SOME TESTS FAILED'}")
    
    # Recommendations
    if not overall:
        print("\n💡 Recommendations:")
        if not results.get("Installation Status"):
            print("  - Run: pip install -e .")
        if not results.get("External Agents"):
            print("  - Check AUTOMAGIK_EXTERNAL_AGENTS_DIR configuration")
        if not results.get("Server Custom Port"):
            print("  - Check if port 38881 is available")
            print("  - Verify database configuration")

if __name__ == "__main__":
    main()