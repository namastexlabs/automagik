# Epic Documentation Template

## Instructions for Architect Workflow

**MANDATORY**: All epic documentation MUST be created in `docs/development/[epic-id]/` directory. 
**NEVER** create .md files in the project root directory.

## Epic Directory Structure

For each epic, create the following standardized structure:

```
docs/development/[epic-id]/
├── README.md                  # Epic overview (use this template)
├── architecture.md            # Technical architecture decisions
├── decisions.md              # Key technical decisions with rationale
├── implementation-plan.md     # Phased implementation roadmap
└── requirements.md           # Functional and non-functional requirements
```

## Epic README Template

Use this template for `docs/development/[epic-id]/README.md`:

```markdown
# Epic: [EPIC-ID] - [Epic Title]

**Status**: [PLANNED|IN_PROGRESS|COMPLETED|BLOCKED]  
**Priority**: [HIGH|MEDIUM|LOW]  
**Estimated Effort**: [Small|Medium|Large|XL]  
**Target Completion**: [Date]  

## Overview

[Brief description of the epic's purpose and goals]

## Business Value

[Why this epic matters and what value it delivers]

## Technical Scope

[High-level technical boundaries and components involved]

## Success Criteria

- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2] 
- [ ] [Measurable outcome 3]

## Documentation Structure

- **Architecture**: [`architecture.md`](./architecture.md) - Technical design decisions
- **Decisions**: [`decisions.md`](./decisions.md) - Key technical choices with rationale
- **Implementation**: [`implementation-plan.md`](./implementation-plan.md) - Phased delivery plan
- **Requirements**: [`requirements.md`](./requirements.md) - Functional/non-functional requirements

## Dependencies

### Upstream Dependencies
- [Dependency 1]: [Description and impact]
- [Dependency 2]: [Description and impact]

### Downstream Impact
- [System/Epic 1]: [How this epic affects it]
- [System/Epic 2]: [How this epic affects it]

## Risk Assessment

### High-Risk Areas
- [Risk 1]: [Description and mitigation strategy]
- [Risk 2]: [Description and mitigation strategy]

### Breaking Changes
- [ ] **None** - No breaking changes expected
- [ ] **Database Schema** - [Description]
- [ ] **API Contracts** - [Description]
- [ ] **Dependencies** - [Description]

## Linear Integration

**Linear Epic**: [Link to Linear epic]  
**Component Tasks**: [Links to Linear tasks]

## Related Epics

- [Related Epic 1]: [Relationship description]
- [Related Epic 2]: [Relationship description]

## Implementation Status

### Phase 1: [Phase Name]
- [ ] [Task 1]
- [ ] [Task 2]

### Phase 2: [Phase Name]  
- [ ] [Task 1]
- [ ] [Task 2]

### Phase 3: [Phase Name]
- [ ] [Task 1] 
- [ ] [Task 2]

## Testing Strategy

[Overview of testing approach and validation criteria]

## Deployment Plan

[How this epic will be deployed and rolled out]

## Monitoring & Metrics

[How success will be measured post-deployment]

---

**Last Updated**: [Date]  
**Document Owner**: [Workflow/Person]
```

## Architecture Document Template

Use this template for `docs/development/[epic-id]/architecture.md`:

```markdown
# [EPIC-ID] Architecture

## System Overview

[High-level architecture diagram and description]

## Component Design

### Component 1: [Name]
- **Purpose**: [What it does]
- **Interface**: [How it's accessed]
- **Dependencies**: [What it relies on]
- **Data Flow**: [How data moves through it]

### Component 2: [Name]
- **Purpose**: [What it does]
- **Interface**: [How it's accessed]
- **Dependencies**: [What it relies on] 
- **Data Flow**: [How data moves through it]

## Integration Points

### External Systems
- [System 1]: [Integration approach]
- [System 2]: [Integration approach]

### Internal Systems
- [Component 1]: [Integration approach]
- [Component 2]: [Integration approach]

## Data Architecture

### Database Changes
- [Table/Collection 1]: [Changes and rationale]
- [Table/Collection 2]: [Changes and rationale]

### API Changes
- [Endpoint 1]: [Changes and rationale]
- [Endpoint 2]: [Changes and rationale]

## Security Considerations

- [Security Aspect 1]: [Approach and controls]
- [Security Aspect 2]: [Approach and controls]

## Performance Considerations

- [Performance Aspect 1]: [Expected impact and optimizations]
- [Performance Aspect 2]: [Expected impact and optimizations]

## Scalability Plan

[How the system will handle growth and scale]

---

**Last Updated**: [Date]  
**Review Status**: [DRAFT|REVIEW|APPROVED]
```

## Key Rules for Architect Workflow

### ✅ DO:
1. **Create epic directory first**: `mkdir -p docs/development/[epic-id]`
2. **Use standardized templates**: Copy templates and customize
3. **Reference existing docs**: Link to `docs/architecture/`, `docs/integrations/`, etc.
4. **Consolidate related content**: Don't create multiple small files
5. **Update index files**: Ensure epic is listed in `docs/development/README.md`

### ❌ DON'T:
1. **Create root .md files**: Never create documentation in project root
2. **Scatter documentation**: Keep all epic docs in one directory
3. **Duplicate existing content**: Reference existing architecture docs instead
4. **Create temporary files**: Use proper epic structure from the start
5. **Ignore templates**: Always use standardized structure

## Template Usage Instructions

1. **Create Epic Directory**:
   ```bash
   mkdir -p docs/development/[epic-id]
   ```

2. **Copy Templates**:
   ```bash
   cp docs/development/epic-template.md docs/development/[epic-id]/README.md
   # Edit and customize the template
   ```

3. **Create Architecture Docs**:
   ```bash
   # Create other required files using templates above
   touch docs/development/[epic-id]/architecture.md
   touch docs/development/[epic-id]/decisions.md
   touch docs/development/[epic-id]/implementation-plan.md
   touch docs/development/[epic-id]/requirements.md
   ```

4. **Reference Existing Docs**:
   ```markdown
   # Good: Reference existing documentation
   See [MCP Integration Guide](../../integrations/mcp.md) for details.
   
   # Bad: Duplicate existing content
   ## MCP Integration
   [Duplicate content here...]
   ```

## Epic Documentation Index

This template ensures all epics follow the same structure and can be easily found in `docs/development/README.md`.