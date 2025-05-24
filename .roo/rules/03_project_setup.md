---
description: "Installation, configuration, and environment setup for automagik-agents"
globs:
  - "**/scripts/**"
  - "**/setup.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/uv.lock"
  - "**/scripts/install/**"
  - "**/docker/**"
  - "**/docker-compose.yml"
  - "**/.env*"
  - "**/Dockerfile"
alwaysApply: false
priority: 3
---

# Automagik Agents Project Setup

This guide covers everything needed to set up and configure the Automagik Agents project for development or production use.

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.10-3.12
- **PostgreSQL**: 12+ (required)
- **Neo4j**: 4.4+ (optional, for knowledge graph features)
- **Docker**: Latest (optional, for containerized deployment)

### One-Command Setup
```bash
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents
bash scripts/install/setup.sh
```

## 📋 Installation Options

The setup script provides multiple installation modes:

### Interactive Installation (Recommended)
```bash
bash scripts/install/setup.sh
```
- Guided menu-driven setup
- Choose between local or Docker deployment
- Configure API keys interactively

### Local Development Setup
```bash
bash scripts/install/setup.sh --mode local
```
- Python virtual environment
- Local PostgreSQL connection
- Development server with auto-reload

### Docker Production Setup
```bash
bash scripts/install/setup.sh --mode docker
```
- Containerized deployment
- Production-ready configuration
- Automatic service management

### Non-Interactive Setup
```bash
bash scripts/install/setup.sh \
  --mode local \
  --openai-key sk-your-openai-key \
  --non-interactive \
  --install-service
```

## 🔧 Configuration

### Environment Variables
Create `.env` file in project root:

```bash
# Required: LLM Provider (choose at least one)
OPENAI_API_KEY=sk-your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Database Configuration (PostgreSQL required)
DATABASE_URL=postgresql://user:password@localhost:5432/automagik_agents
DB_HOST=localhost
DB_PORT=5432
DB_NAME=automagik_agents
DB_USER=automagik_user
DB_PASSWORD=your_secure_password

# Optional: Neo4j for Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Application Settings
AM_HOST=0.0.0.0
AM_PORT=8000
AM_ENV=development
AM_API_KEY=your-api-key-for-client-access

# Optional: External Integrations
DISCORD_BOT_TOKEN=your-discord-bot-token
NOTION_TOKEN=your-notion-integration-token
GMAIL_CREDENTIALS_PATH=path/to/gmail/credentials.json

# Optional: Agent Configuration
AM_AGENTS_NAMES=simple_agent,sofia_agent  # Leave empty to load all
GRAPHITI_QUEUE_ENABLED=true
```

### Database Setup

#### PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Create database and user
sudo -u postgres createuser --interactive automagik_user
sudo -u postgres createdb automagik_agents --owner automagik_user
sudo -u postgres psql -c "ALTER USER automagik_user PASSWORD 'your_secure_password';"
```

#### Database Initialization
The setup script automatically initializes the database:
```bash
# Manual initialization if needed
python -m src.cli.db --init
```

### Neo4j Setup (Optional)
```bash
# Docker
docker run --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_neo4j_password \
  neo4j:latest

# Or install locally
# Follow Neo4j installation guide for your OS
```

## 🛠️ Development Setup

### Python Environment
```bash
# Using uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
cd automagik-agents
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
uv pip install -e .

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### IDE Configuration

#### VS Code
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": true,
      "source.organizeImports.ruff": true
    }
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

#### PyCharm
1. Open project directory
2. Configure Python interpreter: `.venv/bin/python`
3. Enable Ruff for formatting and linting
4. Set run configuration: `python -m src`

### Development Commands
After setup, use these commands for development:

```bash
# Start development server
agent dev                    # With auto-reload
python -m src --reload      # Manual alternative

# Service management
agent start                 # Start service
agent stop                  # Stop service
agent restart               # Restart service
agent status                # Show status
agent logs                  # View logs
agent health                # Health check

# Development tools
ruff check                  # Code quality check
ruff format                 # Format code
pytest                      # Run tests
pytest -v --html=report.html # Detailed test report
```

## 🐳 Docker Setup

### Docker Compose
```yaml
# docker-compose.yml (generated by setup)
version: '3.8'

services:
  automagik-agents:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/automagik_agents
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=automagik_agents
      - POSTGRES_USER=automagik_user
      - POSTGRES_PASSWORD=your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  neo4j:
    image: neo4j:latest
    environment:
      - NEO4J_AUTH=neo4j/your_neo4j_password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

volumes:
  postgres_data:
  neo4j_data:
```

### Docker Commands
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f automagik-agents

# Rebuild after changes
docker-compose build automagik-agents
docker-compose up -d automagik-agents

# Stop services
docker-compose down
```

## 🔐 Security Configuration

### API Key Management
```bash
# Generate secure API keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to database (after server start)
curl -X POST http://localhost:8000/api/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "development", "key": "your-generated-key"}'
```

### Database Security
```bash
# PostgreSQL security hardening
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: listen_addresses = 'localhost'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Configure authentication methods

sudo systemctl restart postgresql
```

### Production Security Checklist
- [ ] Use strong, unique passwords
- [ ] Configure firewall rules
- [ ] Enable SSL/TLS certificates
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Implement rate limiting

## 🧪 Testing Setup

### Test Database
```bash
# Create test database
sudo -u postgres createdb automagik_agents_test --owner automagik_user

# Set test environment
export TEST_DATABASE_URL=postgresql://automagik_user:password@localhost:5432/automagik_agents_test
```

### Test Configuration
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --html=tests/reports/report.html
    --self-contained-html
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### Running Tests
```bash
pytest                          # All tests
pytest tests/test_agents/       # Agent tests only
pytest -m "not slow"           # Skip slow tests
pytest --cov=src              # With coverage
```

## 📊 Monitoring & Logging

### Log Configuration
```python
# src/utils/logging.py configuration
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("logs/automagik.log")
    ]
)
```

### Health Monitoring
```bash
# Health check endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/graphiti-queue

# Service status
agent status                    # Detailed status
agent health                   # Quick health check
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U automagik_user -d automagik_agents

# Check environment variables
echo $DATABASE_URL
```

#### Agent Not Loading
```bash
# Check logs
agent logs

# Verify agent structure
ls src/agents/simple/your_agent/

# Test import
python -c "from src.agents.simple.your_agent.agent import YourAgent"
```

#### API Key Authentication Failing
```bash
# Check API key in database
psql -d automagik_agents -c "SELECT * FROM api_keys;"

# Test with curl
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/agents
```

#### Memory/Performance Issues
```bash
# Monitor resource usage
htop

# Check database connections
psql -d automagik_agents -c "SELECT * FROM pg_stat_activity;"

# Optimize PostgreSQL
sudo nano /etc/postgresql/14/main/postgresql.conf
# Adjust shared_buffers, work_mem, etc.
```

### Debug Mode
```bash
# Enable debug logging
export AM_LOG_LEVEL=DEBUG
python -m src --reload

# Or modify .env
echo "AM_LOG_LEVEL=DEBUG" >> .env
```

### Getting Help
- **Documentation**: Check `/api/v1/docs` when server is running
- **Logs**: Use `agent logs` for real-time debugging
- **Database**: Use PostgreSQL logs for database issues
- **GitHub Issues**: Report bugs and feature requests

## 🔄 Updates & Maintenance

### Updating Code
```bash
git pull origin main
agent update                   # Quick update
agent rebuild                  # Full rebuild

# Manual update
pip install -e . --upgrade
agent restart
```

### Database Migrations
```bash
# Check for pending migrations
python -m src.cli.db --check

# Run migrations
python -m src.cli.db --migrate

# Backup before major updates
pg_dump automagik_agents > backup_$(date +%Y%m%d).sql
```

### Cleanup
```bash
# Clean logs
rm -rf logs/*.log

# Clean Docker volumes
docker-compose down -v

# Clean Python cache
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

---

**Remember**: The setup script handles most configuration automatically. Use manual setup only when you need custom configurations or the automated setup doesn't work for your environment.
