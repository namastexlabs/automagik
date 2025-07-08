#!/bin/bash
# Local test script to verify GitHub Actions will pass

set -e  # Exit on error

echo "🧪 Running local tests to verify GitHub Actions will pass"
echo "=================================================="

# Check Python version
echo "📌 Checking Python version..."
python3 --version
if ! python3 -c "import sys; exit(0 if sys.version_info[:2] == (3, 12) else 1)"; then
    echo "❌ Error: Python 3.12 is required"
    exit 1
fi
echo "✅ Python 3.12 confirmed"

# Install dependencies
echo -e "\n📦 Installing dependencies..."
pip install -e ".[dev]"

# Run linting
echo -e "\n🔍 Running linting..."
ruff check automagik tests
ruff format --check automagik tests
echo "✅ Linting passed"

# Set test environment variables
export DATABASE_URL="sqlite:///test.db"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}"

# Run unit tests
echo -e "\n🧪 Running unit tests..."
pytest tests/agents/simple/test_simple_agent.py \
       tests/agents/sofia/test_sofia_agent.py \
       tests/agents/claude_code/test_agent.py \
       tests/agents/claude_code/test_models.py \
       tests/api/test_agent_routes.py \
       tests/api/test_system_endpoints.py \
       -v --cov=automagik --cov-report=xml --cov-report=term

# Run integration tests (optional)
echo -e "\n🔗 Running integration tests (may fail, that's OK)..."
pytest tests/integration/test_agent_parity.py \
       tests/agents/claude_code/test_integration.py \
       -v -m "not slow" || echo "⚠️  Integration tests failed (expected)"

echo -e "\n✅ Local test run complete!"
echo "If all unit tests passed, the GitHub Actions should pass too."