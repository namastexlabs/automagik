---
description: "Package management, versioning strategies, and dependency maintenance"
globs: 
alwaysApply: false
---

# Dependencies & Package Management

This guide covers all aspects of dependency management, package installation, and environment setup for the Automagik Agents framework.

## Package Management Philosophy

### Core Principles

1. **Reproducible builds** across all environments
2. **Security-first** dependency management
3. **Fast installation** with uv package manager
4. **Pinned versions** for stability
5. **Regular updates** with security scanning

### Tools & Standards

- **Primary**: `uv` package manager (10x faster than pip)
- **Lock file**: `uv.lock` (auto-generated, never edit manually)
- **Configuration**: `pyproject.toml` (single source of truth)
- **Security**: `pip-audit` for vulnerability scanning
- **CI/CD**: Automated dependency updates via Dependabot

## Environment Setup

### Development Environment

```bash
# 2. Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install project dependencies
uv pip install -e .

# 4. Install development dependencies
uv pip install -e ".[dev,test]"

# 5. Verify installation
python -c "import src; print('Installation successful')"
```

### Production Environment

```bash
# 1. Install from lock file (exact versions)
uv pip install -r uv.lock

# 2. Install only production dependencies
uv pip install -e . --no-dev

# 3. Verify critical imports
python -c "from src.agents.models import AutomagikAgent; print('Production ready')"
```

### Docker Environment

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install -r uv.lock --system

# Copy application code
COPY src/ ./src/

# Install application
RUN uv pip install -e . --system
```

## Dependency Management

### Adding New Dependencies

#### Production Dependencies

```bash
# 1. Add to pyproject.toml
uv pip install package-name==1.2.3

# 2. Update lock file
uv pip compile

# 3. Commit both files
git add pyproject.toml uv.lock
git commit -m "Add package-name for feature X"
```

#### Development Dependencies

```bash
# 1. Add to dev group
uv pip install --group dev pytest-asyncio==0.21.0

# 2. Or add to pyproject.toml manually
[project.optional-dependencies]
dev = [
    "pytest-asyncio==0.21.0",
    # ... other dev dependencies
]

# 3. Install and update lock
uv pip install -e ".[dev]"
```

#### Optional Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
discord = ["discord.py>=2.0.0"]
whatsapp = ["evolution-api-client>=1.0.0"]
all = ["automagik-agents[discord,whatsapp]"]
```

### Updating Dependencies

#### Regular Updates (Monthly)

```bash
# 1. Update all dependencies
uv pip install --upgrade-package "*"

# 2. Test thoroughly
pytest
python -m src.main --health-check

# 3. Review changes
git diff uv.lock

# 4. Commit if tests pass
git add uv.lock
git commit -m "Update dependencies - $(date +%Y-%m-%d)"
```

#### Security Updates (Immediate)

```bash
# 1. Check for vulnerabilities
pip-audit -r uv.lock

# 2. Update specific vulnerable package
uv pip install package-name==safe-version

# 3. Verify fix
pip-audit -r uv.lock

# 4. Emergency deployment if critical
```

#### Selective Updates

```bash
# Update specific package
uv pip install --upgrade-package "pydantic"

# Update package group
uv pip install --upgrade-package "pytest*"

# Update with constraints
uv pip install "pydantic>=2.0,<3.0" --upgrade
```

### Removing Dependencies

```bash
# 1. Remove from code first
grep -r "import package_name" src/  # Ensure no usage

# 2. Uninstall package
uv pip uninstall package-name

# 3. Remove from pyproject.toml
# Edit [project.dependencies] or [project.optional-dependencies]

# 4. Update lock file
uv pip compile

# 5. Commit changes
git add pyproject.toml uv.lock
git commit -m "Remove unused package-name"
```

## Package Configuration

### pyproject.toml Structure

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "automagik-agents"
version = "0.1.0"
description = "Production-grade AI agent framework"
authors = [{name = "Automagik Team", email = "team@automagik.dev"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.10"

dependencies = [
    # Core framework
    "pydantic>=2.5.0,<3.0",
    "pydantic-ai>=0.0.13",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    
    # Database
    "psycopg2-binary>=2.9.0",
    "alembic>=1.12.0",
    
    # HTTP clients
    "httpx>=0.25.0",
    "aiofiles>=23.0.0",
    
    # Configuration
    "python-dotenv>=1.0.0",
    "typer>=0.9.0",
    
    # Logging
    "structlog>=23.0.0",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-httpx>=0.22.0",
    "pytest-mock>=3.11.0",
    
    # Code quality
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
    "pre-commit>=3.5.0",
    
    # Security
    "pip-audit>=2.6.0",
    "bandit>=1.7.0",
    "safety>=2.3.0",
]

test = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "coverage>=7.3.0",
]

docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.4.0",
    "mkdocstrings[python]>=0.23.0",
]

[project.scripts]
automagik-agents = "src.cli:main"
agent = "src.cli:agent_command"

[project.urls]
Homepage = "https://github.com/namastexlabs/automagik-agents-labs"
Documentation = "https://docs.automagik.dev"
Repository = "https://github.com/namastexlabs/automagik-agents-labs"
Issues = "https://github.com/namastexlabs/automagik-agents-labs/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.setuptools.package-data]
"*" = ["*.txt", "*.md", "*.yml", "*.yaml", "*.json"]
```

### Version Pinning Strategy

#### Production Dependencies
```toml
# ✅ GOOD: Pin major and minor versions
"pydantic>=2.5.0,<3.0"
"fastapi>=0.104.0,<1.0"

# ✅ GOOD: Exact pins for critical packages
"psycopg2-binary==2.9.7"

# ❌ BAD: Unpinned versions
"requests"
"numpy>=1.0"
```

#### Development Dependencies
```toml
# ✅ GOOD: More flexible for dev tools
"pytest>=7.4.0"
"black>=23.0.0"

# ✅ GOOD: Exact pins for reproducible CI
"mypy==1.6.1"
"ruff==0.1.5"
```

## Security & Vulnerability Management

### Security Scanning

#### Automated Scanning (CI)

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install uv
        run: pip install uv
        
      - name: Install dependencies
        run: uv pip install -r uv.lock
        
      - name: Run pip-audit
        run: pip-audit -r uv.lock --desc --format=json
        
      - name: Run bandit
        run: bandit -r src/ -f json
        
      - name: Run safety
        run: safety check --json
```

#### Manual Security Checks

```bash
# Check for known vulnerabilities
pip-audit -r uv.lock

# Scan for security issues in code
bandit -r src/

# Check dependency safety
safety check

# Generate security report
pip-audit -r uv.lock --format=json --output=security-report.json
```

### Vulnerability Response

#### Critical Vulnerabilities (CVSS ≥ 7.0)

1. **Immediate Response** (within 24 hours)
   ```bash
   # Check affected package
   pip-audit -r uv.lock --desc
   
   # Update to safe version
   uv pip install package-name==safe-version
   
   # Test thoroughly
   pytest
   
   # Emergency deployment
   ```

2. **Documentation**
   ```bash
   # Document in commit message
   git commit -m "SECURITY: Update package-name to fix CVE-2024-XXXX
   
   - Updated from vulnerable version X.Y.Z to safe version A.B.C
   - Addresses [CVE-2024-XXXX](mdc:link-to-cve)
   - Tested: all tests pass, no breaking changes"
   ```

#### Medium Vulnerabilities (CVSS 4.0-6.9)

1. **Planned Response** (within 1 week)
2. **Include in regular update cycle**
3. **Monitor for exploitation in the wild**

### Dependency Policies

#### Allowed Dependencies

- **Well-maintained** packages with active development
- **Security-conscious** maintainers with good track record
- **Compatible licenses** (MIT, Apache 2.0, BSD)
- **Stable APIs** with semantic versioning

#### Restricted Dependencies

- **GPL-licensed** packages (licensing conflicts)
- **Unmaintained** packages (>1 year without updates)
- **Pre-release** versions in production
- **Packages with known security issues**

#### Approval Process

```bash
# 1. Research new dependency
pip show package-name
pip-audit package-name
bandit -r $(python -c "import package_name; print(package_name.__file__)")

# 2. Add with justification
git commit -m "Add package-name for feature X

Justification:
- Actively maintained (last update: YYYY-MM-DD)
- No known security vulnerabilities
- MIT licensed
- Used by major projects: [list examples]
- Alternatives considered: [list and explain why rejected]"
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
AM_ENV=development
AM_LOG_LEVEL=DEBUG

# Install with development dependencies
uv pip install -e ".[dev,test]"

# Enable pre-commit hooks
pre-commit install
```

### Testing Environment

```bash
# .env.test
AM_ENV=test
AM_LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/automagik_test

# Install with test dependencies only
uv pip install -e ".[test]"
```

### Production Environment

```bash
# .env.production
AM_ENV=production
AM_LOG_LEVEL=INFO

# Install production dependencies only
uv pip install -r uv.lock --no-dev
```

### CI/CD Environment

```yaml
# Install exact versions from lock file
- name: Install dependencies
  run: |
    pip install uv
    uv pip install -r uv.lock
    
# Cache dependencies for faster builds
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
```

## Performance Optimization

### Installation Speed

```bash
# Use uv for 10x faster installs
uv pip install -r uv.lock

# Parallel installation
uv pip install -r uv.lock --no-deps --parallel

# Use local cache
export UV_CACHE_DIR=~/.cache/uv
```

### Build Optimization

```dockerfile
# Multi-stage Docker build
FROM python:3.11-slim as builder

# Install uv
RUN pip install uv

# Install dependencies in separate layer
COPY pyproject.toml uv.lock ./
RUN uv pip install -r uv.lock --target=/app/deps

FROM python:3.11-slim as runtime

# Copy dependencies
COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages/

# Copy application
COPY src/ ./src/
```

### Dependency Analysis

```bash
# Analyze dependency tree
uv pip show --verbose package-name

# Find dependency conflicts
uv pip check

# Analyze package sizes
pip-autoremove --list

# Generate dependency graph
pipdeptree --graph-output png > deps.png
```

## Troubleshooting

### Common Issues

#### Lock File Conflicts

```bash
# Resolve lock file conflicts
git checkout --theirs uv.lock
uv pip compile
git add uv.lock
```

#### Version Conflicts

```bash
# Check for conflicts
uv pip check

# Resolve with constraints
echo "problematic-package==1.2.3" > constraints.txt
uv pip install -c constraints.txt -r uv.lock
```

#### Cache Issues

```bash
# Clear uv cache
uv cache clean

# Clear pip cache
pip cache purge

# Reinstall from scratch
rm -rf .venv
uv venv
uv pip install -e ".[dev]"
```

#### Import Errors

```bash
# Check installed packages
uv pip list

# Verify package installation
python -c "import package_name; print(package_name.__version__)"

# Reinstall specific package
uv pip uninstall package-name
uv pip install package-name
```

## Integration with Task Management

Always use the Task Management System when working with dependencies:

```bash
# Plan dependency work
task-master next

# Document dependency changes
task-master update-subtask --id=X.Y --prompt="Updated package X to version Y for security fix..."

# Mark dependency update complete
task-master set-status --id=X.Y --status=done
```

## Best Practices Summary

1. **Always use uv** instead of pip for faster installs
2. **Pin versions** for reproducible builds
3. **Regular security scans** with pip-audit
4. **Test thoroughly** after dependency updates
5. **Document security fixes** in commit messages
6. **Use lock files** for exact version control
7. **Separate dev/prod** dependencies appropriately
8. **Monitor vulnerabilities** continuously
9. **Cache dependencies** in CI for speed
10. **Review changelogs** before major updates

This comprehensive dependency guide ensures secure, fast, and reliable package management across all environments.
