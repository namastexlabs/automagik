# Development Documentation

This directory contains development-related documentation including epic specifications, implementation guides, and agent development resources.

## Epic Documentation

All epics must follow the standardized structure defined in [`epic-template.md`](./epic-template.md).

### Active Epics

| Epic ID | Title | Status | Priority | Documentation |
|---------|-------|---------|----------|---------------|
| NMSTX-258 | MCP Refactor Testing Validation | COMPLETED | HIGH | [`nmstx-258/`](./nmstx-258/) |

### Epic Documentation Structure

Each epic should have its own directory with the following structure:

```
docs/development/[epic-id]/
├── README.md                  # Epic overview
├── architecture.md            # Technical architecture 
├── decisions.md              # Key technical decisions
├── implementation-plan.md     # Phased implementation roadmap
└── requirements.md           # Functional/non-functional requirements
```

## Creating New Epic Documentation

1. **Use the Template**: Start with [`epic-template.md`](./epic-template.md)
2. **Create Epic Directory**: `mkdir -p docs/development/[epic-id]`
3. **Follow Standard Structure**: Use the templates provided
4. **Update This Index**: Add your epic to the table above

## Development Resources

### Agent Development
- [`agents-overview.md`](./agents-overview.md) - Guide to creating and managing agents

### Implementation Guides
- [`IMPLEMENTATION_ROADMAP.md`](./IMPLEMENTATION_ROADMAP.md) - Overall project implementation roadmap

## Documentation Rules for Architects

### ✅ DO:
- Create all epic documentation in `docs/development/[epic-id]/`
- Use standardized templates and structure
- Reference existing documentation instead of duplicating
- Update this index when adding new epics
- Consolidate related content in epic directories

### ❌ DON'T:
- Create .md files in the project root directory
- Scatter documentation across multiple locations
- Duplicate existing architectural documentation
- Create temporary or ad-hoc documentation files
- Ignore the standardized epic structure

## Epic Lifecycle

1. **Planning**: Create epic directory with README.md using template
2. **Architecture**: Complete architecture.md with technical design
3. **Implementation**: Track progress in implementation-plan.md
4. **Completion**: Update status in epic README and this index
5. **Archive**: Completed epics remain in development docs for reference

---

**Last Updated**: 2025-06-11  
**Maintained By**: Architect workflow

For questions about epic documentation standards, refer to [`epic-template.md`](./epic-template.md).