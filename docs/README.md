# Automagik Agents Documentation

Welcome to the comprehensive documentation for Automagik Agents - a production-ready AI agent framework with multi-agent orchestration, persistent memory, and extensive integrations.

## 📁 Documentation Structure

### 🚀 [Getting Started](./getting-started/)
Everything you need to get up and running quickly.

- **[Setup](./getting-started/setup.md)** - Installation and initial configuration
- **[Configuration](./getting-started/configuration.md)** - Environment variables and settings
- **[Running](./getting-started/running.md)** - Starting and managing the application
- **[Migration Guide](./getting-started/migration-guide.md)** - Upgrading from older versions

### 🏗️ [Architecture](./architecture/)
Deep dive into system design, patterns, and decision-making.

- **[Overview](./architecture/overview.md)** - System architecture and components
- **[Orchestration](./architecture/orchestration.md)** - Multi-agent coordination patterns
- **[Decision Framework](./architecture/decision-framework.md)** - Architecture decision records (ADR) process
- **[Database](./architecture/database.md)** - PostgreSQL schema and data models
- **[Memory](./architecture/memory.md)** - Agent memory and knowledge graph systems

### 🛠️ [Development](./development/)
Guides for building and extending the agent system.

- **[Development Guide](./development/README.md)** - Epic development standards and guidelines
- **[Agents Overview](./development/agents-overview.md)** - Agent system architecture and patterns
- **[Epic Template](./development/epic-template.md)** - Standardized epic documentation template
- **[Documentation Reference](./development/docs-reference-guide.md)** - How to reference existing docs
- **[Implementation Roadmap](./development/IMPLEMENTATION_ROADMAP.md)** - Project implementation roadmap

### 🔌 [Integrations](./integrations/)
External services and protocol integrations.

- **[MCP Integration](./integrations/mcp.md)** - Model Context Protocol server integration
- **[MCP Configuration](./integrations/mcp-config-spec.md)** - MCP configuration specification
- **[Slack](./integrations/slack.md)** - Complete Slack bot integration (if available)
- **[WhatsApp](./integrations/whatsapp.md)** - Evolution API WhatsApp integration
- **[Multimodal](./integrations/multimodal.md)** - Image and vision processing capabilities

### ⚙️ [Operations](./operations/)
DevOps, deployment, and operational procedures.

- **[Breaking Changes](./operations/BREAKING_CHANGES.md)** - Breaking changes log and migration notes
- **[Docker](./operations/docker.md)** - Container best practices and standardization  
- **[Makefile Reference](./operations/makefile-reference.md)** - Complete guide to make commands
- **[Environment](./operations/environment.md)** - Environment variable management

### 🧪 [Testing](./testing/)
Testing frameworks, performance evaluation, and quality assurance.

- **[Benchmarking](./testing/benchmarking.md)** - Performance testing and optimization
- **[Stress Testing](./testing/stress-testing.md)** - Load testing and reliability validation
- **[Test Reports](./testing/reports/)** - Historical test reports and analysis

## 🗺️ Quick Navigation

### For New Users
1. **[Setup](./getting-started/setup.md)** → **[Configuration](./getting-started/configuration.md)** → **[Running](./getting-started/running.md)**
2. **[Agents Overview](./development/agents-overview.md)** → **[Architecture Overview](./architecture/overview.md)**

### For Developers
1. **[Architecture Overview](./architecture/overview.md)** → **[Orchestration](./architecture/orchestration.md)**
2. **[Agent Development](./development/agents-overview.md)** → **[API Reference](./development/api.md)**
3. **[Agent Mocking](./development/agent-mocking.md)** → **[Testing](./testing/)**

### For DevOps Engineers
1. **[Docker](./operations/docker.md)** → **[Makefile Reference](./operations/makefile-reference.md)**
2. **[Environment Management](./operations/environment.md)** → **[Configuration](./getting-started/configuration.md)**

### For Architects
1. **[Architecture Overview](./architecture/overview.md)** → **[Decision Framework](./architecture/decision-framework.md)**
2. **[Orchestration Patterns](./architecture/orchestration.md)** → **[Memory Systems](./architecture/memory.md)**

## 🎯 Common Use Cases

### Building Your First Agent
```bash
# Quick start sequence
make install-dev
automagik agents create -n my_agent -t simple
automagik agents chat -a my_agent
```
**Documentation**: [Setup](./getting-started/setup.md) → [Agents Overview](./development/agents-overview.md)

### Multi-Agent Orchestration  
**Documentation**: [Orchestration](./architecture/orchestration.md) → [Slack Integration](./integrations/slack.md)

### Production Deployment
**Documentation**: [Docker](./operations/docker.md) → [Environment](./operations/environment.md) → [Makefile Reference](./operations/makefile-reference.md)

### External Integrations
**Documentation**: [MCP](./integrations/mcp.md) → [Slack](./integrations/slack.md) → [WhatsApp](./integrations/whatsapp.md)

## 📚 Additional Resources

### Project Files
- **[Main README](../README.md)** - Project overview and quick start
- **[Architecture Document](../ARCHITECTURE.MD)** - High-level technical architecture
- **[Claude Guidelines](../CLAUDE.md)** - Development guidelines for Claude Code

### Live Resources
- **API Documentation**: http://localhost:8881/api/v1/docs (when running)
- **Code Examples**: `/src/agents/pydanticai/` directory
- **Test Examples**: `/tests/` directory

## 🔍 Finding Information

### Search Strategy
1. **Use this README** for high-level navigation
2. **Check section READMEs** for detailed topic guidance
3. **Search by keyword** across the docs folder
4. **Review code examples** in `/src/` and `/tests/`

### Documentation Standards
- **Consistent naming**: All files use kebab-case naming
- **Logical organization**: Related content grouped in folders
- **Cross-references**: Links between related documentation
- **Code examples**: Practical examples with explanations
- **Regular updates**: Documentation kept current with codebase

## 📝 Contributing to Documentation

When adding or updating documentation:

1. **Follow the folder structure** - Place files in appropriate categories
2. **Use kebab-case naming** - `my-feature.md` not `my_feature.md`
3. **Update this README** - Add new files to the appropriate section
4. **Cross-reference related docs** - Link to relevant documentation
5. **Include code examples** - Show practical usage where applicable
6. **Test all links** - Ensure internal links work correctly

## 🚧 Documentation Status

**Last Major Reorganization**: January 2025  
**Current Version**: Aligned with codebase v0.1.4+  
**Maintenance**: Actively maintained ✅

### Recent Updates
- ✅ **Complete reorganization** - Logical folder structure and consistent naming
- ✅ **Consolidated duplicates** - Removed redundant and outdated content
- ✅ **Updated architecture** - Added orchestration patterns and decision frameworks
- ✅ **Enhanced integrations** - Comprehensive integration guides
- ✅ **Improved navigation** - Clear paths for different user types

---

**Need help?** Can't find what you're looking for? Check the [main project README](../README.md) or explore the source code in `/src/` for implementation details.