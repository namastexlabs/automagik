#!/usr/bin/env python3
"""Test script for pip installation with better control and debugging."""

import subprocess
import sys
import time
import os
import tempfile
import shutil
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple

class PipInstallTester:
    """Test automagik pip installation in isolated environment."""
    
    def __init__(self, test_dir: Optional[str] = None):
        self.test_dir = Path(test_dir) if test_dir else Path(tempfile.mkdtemp(prefix="automagik_test_"))
        self.venv_path = self.test_dir / "venv"
        self.agents_dir = self.test_dir / "my_agents"
        self.env_file = self.test_dir / ".env"
        self.port = 38881
        self.base_url = f"http://localhost:{self.port}"
        
    def setup_test_environment(self) -> bool:
        """Set up isolated test environment."""
        print(f"📁 Setting up test environment in: {self.test_dir}")
        
        try:
            # Create virtual environment
            print("🐍 Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
            
            # Get pip path
            self.pip_path = self.venv_path / "bin" / "pip" if os.name != 'nt' else self.venv_path / "Scripts" / "pip.exe"
            self.python_path = self.venv_path / "bin" / "python" if os.name != 'nt' else self.venv_path / "Scripts" / "python.exe"
            
            # Create .env file
            print("📝 Creating .env file...")
            env_content = f"""# Test configuration
AUTOMAGIK_API_PORT={self.port}
AUTOMAGIK_API_HOST=0.0.0.0
AUTOMAGIK_API_KEY=test-api-key
AUTOMAGIK_DATABASE_TYPE=sqlite
AUTOMAGIK_SQLITE_DATABASE_PATH=test_automagik.db
OPENAI_API_KEY=sk-test-key-not-real
AUTOMAGIK_EXTERNAL_AGENTS_DIR=./my_agents
SKIP_DB_INIT=true
AM_LOG_LEVEL=DEBUG
"""
            self.env_file.write_text(env_content)
            
            # Create test agent
            print("🤖 Creating test agent...")
            self.agents_dir.mkdir(parents=True, exist_ok=True)
            test_agent_dir = self.agents_dir / "test_agent"
            test_agent_dir.mkdir(exist_ok=True)
            
            agent_code = '''"""Test agent for pip installation verification."""
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies


AGENT_PROMPT = """You are a test agent created to verify pip installation.
When asked, respond with: 'Hello from the test agent! Pip installation is working correctly.'"""


def create_agent(config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    """Factory function to create the test agent."""
    return TestAgent(config or {})


class TestAgent(AutomagikAgent):
    """Test agent implementation."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model", "openai:gpt-4o-mini"),
            model_settings={},
            api_keys={},
            tool_config={}
        )
        self.tool_registry.register_default_tools(self.context)
    
    @property
    def model_name(self) -> str:
        return self.dependencies.model_name or "openai:gpt-4o-mini"
'''
            (test_agent_dir / "agent.py").write_text(agent_code)
            (test_agent_dir / "__init__.py").touch()
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def install_automagik(self, editable: bool = True) -> bool:
        """Install automagik package."""
        print("\n📦 Installing automagik...")
        
        try:
            # Get the path to the main automagik directory
            automagik_path = Path(__file__).parent
            
            cmd = [str(self.pip_path), "install"]
            if editable:
                cmd.append("-e")
            cmd.append(str(automagik_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Installation failed: {result.stderr}")
                return False
            
            print("✅ Automagik installed successfully")
            
            # Verify installation
            print("\n🔍 Verifying installation...")
            verify_cmd = [str(self.python_path), "-c", "import automagik; print(f'Version: {automagik.__version__}')"]
            result = subprocess.run(verify_cmd, capture_output=True, text=True, cwd=str(self.test_dir))
            
            if result.returncode == 0:
                print(f"✅ {result.stdout.strip()}")
                return True
            else:
                print(f"❌ Import failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    
    def test_cli_commands(self) -> Dict[str, bool]:
        """Test various CLI commands."""
        print("\n🧪 Testing CLI commands...")
        
        results = {}
        
        # Test help command
        print("  Testing: automagik --help")
        result = subprocess.run(
            [str(self.python_path), "-m", "automagik", "--help"],
            capture_output=True, text=True, cwd=str(self.test_dir)
        )
        results["help"] = result.returncode == 0
        print(f"  {'✅' if results['help'] else '❌'} Help command")
        
        # Test agent list
        print("  Testing: automagik agents list")
        result = subprocess.run(
            [str(self.python_path), "-m", "automagik", "agents", "list"],
            capture_output=True, text=True, cwd=str(self.test_dir),
            env={**os.environ, **self._load_env_vars()}
        )
        results["agents_list"] = result.returncode == 0
        print(f"  {'✅' if results['agents_list'] else '❌'} Agent list command")
        if not results["agents_list"]:
            print(f"     Error: {result.stderr}")
        
        return results
    
    def start_server_subprocess(self) -> Optional[subprocess.Popen]:
        """Start server as subprocess with timeout."""
        print(f"\n🚀 Starting server on port {self.port}...")
        
        env = {**os.environ, **self._load_env_vars()}
        
        # Use subprocess with non-blocking IO
        server_process = subprocess.Popen(
            [str(self.python_path), "-m", "automagik.cli.commands.server"],
            cwd=str(self.test_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start (with timeout)
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        while time.time() - start_time < timeout:
            # Check if process is still running
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                print(f"❌ Server exited with code: {server_process.returncode}")
                print(f"Stdout: {stdout}")
                print(f"Stderr: {stderr}")
                return None
            
            # Try to connect
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    return server_process
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(0.5)
        
        # Timeout reached
        print("❌ Server startup timeout")
        server_process.terminate()
        server_process.wait(timeout=5)
        return None
    
    def test_api_endpoints(self, server_process: subprocess.Popen) -> Dict[str, bool]:
        """Test API endpoints."""
        print("\n🧪 Testing API endpoints...")
        
        results = {}
        headers = {"X-API-Key": "test-api-key"}
        
        # Test health endpoint
        print("  Testing: GET /health")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            results["health"] = response.status_code == 200
            print(f"  {'✅' if results['health'] else '❌'} Health check")
        except Exception as e:
            results["health"] = False
            print(f"  ❌ Health check failed: {e}")
        
        # Test agents list
        print("  Testing: GET /api/v1/agents")
        try:
            response = requests.get(f"{self.base_url}/api/v1/agents", headers=headers, timeout=5)
            results["agents_api"] = response.status_code == 200
            print(f"  {'✅' if results['agents_api'] else '❌'} Agents API")
            
            if results["agents_api"]:
                agents = response.json()
                print(f"     Found {len(agents)} agents")
                for agent in agents:
                    print(f"     - {agent.get('name', 'Unknown')}")
        except Exception as e:
            results["agents_api"] = False
            print(f"  ❌ Agents API failed: {e}")
        
        return results
    
    def _load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if self.env_file.exists():
            for line in self.env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
        return env_vars
    
    def run_tests(self) -> Tuple[bool, Dict[str, any]]:
        """Run all tests."""
        print("=" * 60)
        print("🧪 Automagik Pip Installation Test Suite")
        print("=" * 60)
        
        all_results = {
            "setup": False,
            "installation": False,
            "cli_commands": {},
            "server_startup": False,
            "api_endpoints": {}
        }
        
        # Setup environment
        if not self.setup_test_environment():
            return False, all_results
        all_results["setup"] = True
        
        # Install package
        if not self.install_automagik():
            return False, all_results
        all_results["installation"] = True
        
        # Test CLI commands
        cli_results = self.test_cli_commands()
        all_results["cli_commands"] = cli_results
        
        # Start server
        server_process = self.start_server_subprocess()
        if server_process:
            all_results["server_startup"] = True
            
            # Test API endpoints
            api_results = self.test_api_endpoints(server_process)
            all_results["api_endpoints"] = api_results
            
            # Cleanup server
            print("\n🛑 Stopping server...")
            server_process.terminate()
            server_process.wait(timeout=5)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"Setup: {'✅' if all_results['setup'] else '❌'}")
        print(f"Installation: {'✅' if all_results['installation'] else '❌'}")
        print(f"CLI Commands: {sum(1 for v in cli_results.values() if v)}/{len(cli_results)}")
        print(f"Server Startup: {'✅' if all_results['server_startup'] else '❌'}")
        if all_results["api_endpoints"]:
            print(f"API Endpoints: {sum(1 for v in api_results.values() if v)}/{len(api_results)}")
        
        # Overall success
        success = (
            all_results["setup"] and 
            all_results["installation"] and 
            all(cli_results.values()) and
            all_results["server_startup"] and
            all(api_results.values() if api_results else [True])
        )
        
        return success, all_results
    
    def cleanup(self):
        """Clean up test environment."""
        print(f"\n🧹 Cleaning up {self.test_dir}")
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")


def main():
    """Run the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test automagik pip installation")
    parser.add_argument("--test-dir", help="Test directory (default: temp dir)")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up test directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    tester = PipInstallTester(args.test_dir)
    
    try:
        success, results = tester.run_tests()
        
        if args.json:
            print(json.dumps(results, indent=2))
        
        if not args.no_cleanup:
            tester.cleanup()
        else:
            print(f"\n📁 Test directory preserved: {tester.test_dir}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Test interrupted")
        if not args.no_cleanup:
            tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        if not args.no_cleanup:
            tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()