# Documentation Reference Guide for Epics

This guide helps architects reference existing documentation properly instead of duplicating content.

## Core Documentation Structure

```
docs/
├── architecture/           # System architecture & design
│   ├── database.md        # Database design patterns
│   ├── decisions.md       # Architectural decisions
│   ├── memory.md          # Memory system architecture  
│   ├── mcp-refactor.md    # MCP system architecture
│   └── overview.md        # High-level system overview
├── development/           # Epic documentation & guides
│   ├── README.md          # Epic index and guidelines
│   ├── epic-template.md   # Template for new epics
│   ├── agents-overview.md # Agent development guide
│   └── [epic-id]/         # Individual epic directories
├── integrations/          # External system integrations
│   ├── mcp.md            # MCP integration guide
│   ├── mcp-config-spec.md # MCP configuration specification
│   ├── multimodal.md     # Multimodal integration
│   ├── slack.md          # Slack integration
│   └── whatsapp.md       # WhatsApp integration
├── operations/           # Deployment & operations
│   ├── BREAKING_CHANGES.md # Breaking changes log
│   ├── docker.md         # Docker deployment
│   ├── environment.md    # Environment setup
│   └── makefile-reference.md # Make commands
├── getting-started/      # User guides
│   ├── migration-guide.md # Migration instructions
│   ├── running.md        # How to run the system
│   └── setup.md          # Initial setup guide
└── testing/              # Testing strategies & reports
    ├── benchmarking.md   # Performance benchmarking
    ├── stress-testing.md # Load testing guide
    └── reports/          # Test reports archive
```

## How to Reference Existing Documentation

### ✅ Correct: Reference with Relative Links

```markdown
# Epic Architecture

This epic builds on the existing MCP system. For details on MCP architecture, 
see [MCP Integration Guide](../../integrations/mcp.md).

The database changes follow patterns described in 
[Database Architecture](../../architecture/database.md).

For deployment considerations, refer to 
[Operations Guide](../../operations/docker.md).
```

### ❌ Incorrect: Duplicate Content

```markdown
# Epic Architecture

## MCP System Overview
[Duplicated content from existing MCP docs...]

## Database Patterns  
[Duplicated content from database docs...]
```

## Reference Templates by Topic

### MCP-Related Epics
```markdown
## MCP Integration

This epic extends the MCP system described in:
- [MCP Architecture](../../architecture/mcp-refactor.md) - Core system design
- [MCP Integration Guide](../../integrations/mcp.md) - Integration patterns
- [MCP Configuration](../../integrations/mcp-config-spec.md) - Configuration format

## Implementation Notes
[Epic-specific implementation details only]
```

### Agent Development Epics
```markdown
## Agent Framework

This epic builds on the agent framework documented in:
- [Agent Overview](../agents-overview.md) - Agent development guide
- [System Architecture](../../architecture/overview.md) - Overall system design

## New Agent Requirements
[Epic-specific agent requirements only]
```

### Database Schema Epics
```markdown
## Database Changes

This epic modifies the database schema following patterns in:
- [Database Architecture](../../architecture/database.md) - Schema design patterns
- [Migration Guide](../../getting-started/migration-guide.md) - Migration procedures

## Schema Modifications
[Epic-specific database changes only]
```

### API Development Epics
```markdown
## API Integration

This epic extends the API following established patterns:
- [System Overview](../../architecture/overview.md) - API architecture
- [Integration Patterns](../../integrations/) - External integration guides

## New API Endpoints
[Epic-specific API changes only]
```

## Quick Reference Links

### Architecture & Design
- [System Overview](../architecture/overview.md)
- [Architectural Decisions](../architecture/decisions.md)
- [Database Design](../architecture/database.md)
- [Memory System](../architecture/memory.md)
- [MCP Refactor](../architecture/mcp-refactor.md)

### Integrations
- [MCP Integration](../integrations/mcp.md)
- [MCP Configuration](../integrations/mcp-config-spec.md)
- [Slack Integration](../integrations/slack.md)
- [WhatsApp Integration](../integrations/whatsapp.md)
- [Multimodal Support](../integrations/multimodal.md)

### Operations
- [Breaking Changes](../operations/BREAKING_CHANGES.md)
- [Docker Deployment](../operations/docker.md)
- [Environment Setup](../operations/environment.md)
- [Makefile Commands](../operations/makefile-reference.md)

### Development
- [Agent Development](./agents-overview.md)
- [Implementation Roadmap](./IMPLEMENTATION_ROADMAP.md)
- [Epic Template](./epic-template.md)

### Testing
- [Benchmarking](../testing/benchmarking.md)
- [Stress Testing](../testing/stress-testing.md)
- [Test Reports](../testing/reports/)

## Documentation Maintenance

### When to Reference vs. Create New Content

**Reference Existing** when:
- Core system architecture is already documented
- Integration patterns are established
- Operational procedures exist
- Testing strategies are defined

**Create New Content** when:
- Epic introduces truly new concepts
- Specific implementation details unique to epic
- Epic-specific requirements or constraints
- New integration patterns not covered elsewhere

### Link Validation

Always verify links work by checking:
1. File exists at referenced path
2. Relative path is correct from epic directory
3. Referenced section exists in target document

### Content Synchronization

If epic implementation reveals issues with existing docs:
1. Note discrepancies in epic documentation
2. Create follow-up task to update existing docs
3. Don't duplicate content - reference and note updates needed

---

**Last Updated**: 2025-06-11  
**Maintained By**: Architect workflow

This guide ensures consistent documentation practices and prevents content duplication across epics.