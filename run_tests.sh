#!/bin/bash
# Quick test runner for local development

set -e

echo "🚀 Automagik Tests - Quick Local Run"
echo "===================================="

# Activate virtual environment
source .venv/bin/activate

# Export test environment variables
export DATABASE_URL="sqlite:///test.db"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}"

# Option 1: Run minimal checks
if [ "$1" = "minimal" ]; then
    echo "Running minimal checks..."
    python3 test_minimal.py
    exit $?
fi

# Option 2: Run quick smoke tests
if [ "$1" = "smoke" ]; then
    echo "Running smoke tests..."
    pytest tests/api/test_system_endpoints.py -v
    exit $?
fi

# Option 3: Run full test suite (like GitHub Actions)
if [ "$1" = "full" ]; then
    echo "Running full test suite..."
    
    # Linting
    echo -e "\n🔍 Linting..."
    ruff check automagik tests
    ruff format --check automagik tests
    
    # Unit tests
    echo -e "\n🧪 Unit tests..."
    pytest tests/agents/simple/test_simple_agent.py \
           tests/agents/sofia/test_sofia_agent.py \
           tests/agents/claude_code/test_agent.py \
           tests/agents/claude_code/test_models.py \
           tests/api/test_agent_routes.py \
           tests/api/test_system_endpoints.py \
           -v --cov=automagik --cov-report=term
    
    exit $?
fi

# Default: Show usage
echo "Usage: $0 [minimal|smoke|full]"
echo ""
echo "  minimal - Run minimal dependency and setup checks"
echo "  smoke   - Run quick smoke tests (system endpoints)"
echo "  full    - Run full test suite like GitHub Actions"
echo ""
echo "Examples:"
echo "  ./run_tests.sh minimal   # Quick health check"
echo "  ./run_tests.sh smoke     # Fast smoke tests"
echo "  ./run_tests.sh full      # Complete test suite"