#!/usr/bin/env python3
"""Minimal test to verify environment and dependencies."""

import sys
import subprocess
import os

def check_python_version():
    """Check Python version is 3.12."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version[:2] != (3, 12):
        print("❌ ERROR: Python 3.12 is required")
        return False
    print("✅ Python 3.12 confirmed")
    return True

def check_dependencies():
    """Check if all required dependencies can be imported."""
    dependencies = [
        "pytest",
        "pytest_cov",
        "ruff",
        "automagik",
        "pydantic_ai",
        "fastapi",
        "claude_code_sdk",
    ]
    
    failed = []
    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {dep}: {e}")
            failed.append(dep)
    
    return len(failed) == 0

def run_single_test():
    """Run a single test to verify pytest works."""
    print("\n🧪 Running a single test...")
    result = subprocess.run(
        ["pytest", "tests/api/test_system_endpoints.py::test_health_endpoint", "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Test passed!")
        return True
    else:
        print(f"❌ Test failed!")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        return False

def check_linting():
    """Run ruff check on a small file."""
    print("\n🔍 Checking linting setup...")
    result = subprocess.run(
        ["ruff", "check", "automagik/__init__.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Linting check passed")
        return True
    else:
        print(f"❌ Linting failed: {result.stdout}")
        return False

def main():
    """Run all checks."""
    print("🚀 Running minimal test suite")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Linting", check_linting),
        ("Single Test", run_single_test),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        try:
            results.append(check_func())
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    for i, (name, _) in enumerate(checks):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"  {name}: {status}")
    
    if all(results):
        print("\n✅ All checks passed! GitHub Actions should work.")
        return 0
    else:
        print("\n❌ Some checks failed. Fix these before pushing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())