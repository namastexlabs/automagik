#!/usr/bin/env python3
"""Minimal test to isolate pip installation issues."""

import subprocess
import sys
import os
import tempfile
from pathlib import Path

def test_basic_import():
    """Test if we can import automagik modules."""
    print("🧪 Testing basic imports...")
    
    test_script = """
import sys
print(f"Python: {sys.version}")

try:
    import automagik
    print(f"✅ automagik imported: {automagik.__version__}")
except Exception as e:
    print(f"❌ automagik import failed: {e}")
    sys.exit(1)

try:
    from automagik.agents.models.agent_factory import AgentFactory
    print("✅ AgentFactory imported")
except Exception as e:
    print(f"❌ AgentFactory import failed: {e}")
    sys.exit(1)

try:
    from automagik.cli import app
    print("✅ CLI app imported")
except Exception as e:
    print(f"❌ CLI import failed: {e}")
    sys.exit(1)

print("\\n📋 Checking entry points...")
try:
    import pkg_resources
    dist = pkg_resources.get_distribution('automagik')
    for ep in dist.get_entry_map().get('console_scripts', {}).values():
        print(f"  - {ep.name}: {ep.module_name}:{ep.attrs[0]}")
except Exception as e:
    print(f"❌ Entry points check failed: {e}")

print("\\n✅ All basic imports successful!")
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        # Run in current environment
        print("\n1️⃣ Testing in current environment:")
        result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        # Test in isolated venv
        print("\n2️⃣ Testing in isolated environment:")
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            
            # Create venv
            print("   Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            
            # Get paths
            if os.name == 'nt':
                pip_path = venv_path / "Scripts" / "pip.exe"
                python_path = venv_path / "Scripts" / "python.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
                python_path = venv_path / "bin" / "python"
            
            # Install automagik
            print("   Installing automagik...")
            automagik_path = Path(__file__).parent
            result = subprocess.run(
                [str(pip_path), "install", "-e", str(automagik_path)],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Installation failed: {result.stderr}")
                return False
            
            print("   Running import test...")
            result = subprocess.run(
                [str(python_path), temp_script],
                capture_output=True, text=True
            )
            print(result.stdout)
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            
            return result.returncode == 0
            
    finally:
        os.unlink(temp_script)

def test_agent_factory():
    """Test agent factory functionality."""
    print("\n🧪 Testing agent factory...")
    
    test_script = """
import os
os.environ['AUTOMAGIK_DATABASE_TYPE'] = 'sqlite'
os.environ['AUTOMAGIK_SQLITE_DATABASE_PATH'] = ':memory:'

try:
    from automagik.agents.models.agent_factory import AgentFactory
    
    # List available agents
    agents = AgentFactory.list_available_agents()
    print(f"✅ Found {len(agents)} built-in agents:")
    for agent in agents:
        print(f"   - {agent}")
    
    # Test external agent discovery
    os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = './test_agents'
    print("\\n🔍 Testing external agent discovery...")
    AgentFactory._discover_external_agents()
    
except Exception as e:
    import traceback
    print(f"❌ Agent factory test failed: {e}")
    traceback.print_exc()
    exit(1)

print("\\n✅ Agent factory tests passed!")
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return result.returncode == 0
    finally:
        os.unlink(temp_script)

def test_database_minimal():
    """Test minimal database functionality."""
    print("\n🧪 Testing database providers...")
    
    test_script = """
import os
os.environ['AUTOMAGIK_DATABASE_TYPE'] = 'sqlite'
os.environ['AUTOMAGIK_SQLITE_DATABASE_PATH'] = ':memory:'
os.environ['SKIP_DB_INIT'] = 'true'

try:
    from automagik.db.providers.factory import get_database_provider, get_database_type
    
    # Get provider
    provider = get_database_provider()
    db_type = get_database_type()
    print(f"✅ Database provider created: {db_type}")
    
    # Test connection
    with provider.get_connection() as conn:
        print("✅ Database connection successful")
    
except Exception as e:
    import traceback
    print(f"❌ Database test failed: {e}")
    traceback.print_exc()
    exit(1)

print("\\n✅ Database tests passed!")
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return result.returncode == 0
    finally:
        os.unlink(temp_script)

def main():
    """Run minimal tests."""
    print("=" * 60)
    print("🧪 Minimal Pip Installation Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Imports", test_basic_import),
        ("Agent Factory", test_agent_factory),
        ("Database Provider", test_database_minimal)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print('=' * 60)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        print(f"{test_name}: {'✅ PASSED' if passed else '❌ FAILED'}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()