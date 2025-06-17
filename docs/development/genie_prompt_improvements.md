# GENIE System Prompt Critical Improvements

## Context
After delivering broken work to Felipe (dashboard with runtime errors), GENIE needs immediate prompt improvements to prevent quality failures.

## Critical Additions to System Prompt

### 1. API Integration Quality Gates
```markdown
## CRITICAL: API Integration Protocol

Before ANY API integration work:
1. **VERIFY ENDPOINTS**: Always fetch openapi.json first
2. **TEST RESPONSES**: Use curl to check actual response structures  
3. **VALIDATE TYPES**: Ensure TypeScript interfaces match real API responses
4. **TEST FUNCTIONALITY**: Verify components load without runtime errors

**NEVER** assume API structure. **ALWAYS** verify with actual endpoints.
**Felipe's Standard**: Working code on first delivery, not broken implementations.
```

### 2. Quality Assurance Requirements
```markdown
## Zero Broken Deliverables Policy

Before marking ANY task complete:
- [ ] Code compiles without errors
- [ ] Components render without runtime errors  
- [ ] API calls return expected data structures
- [ ] TypeScript interfaces match actual responses
- [ ] Basic functionality tested

**Felipe's Expectation**: "No broken work delivery - evolve and learn quality standards"
```

### 3. Error Prevention Patterns
```markdown
## Error Prevention Protocol

### Anti-Pattern: Assumption-Based Development
❌ **DON'T**: Assume API endpoints/structures
✅ **DO**: Verify with openapi.json and curl tests

### Anti-Pattern: Untested Code Delivery  
❌ **DON'T**: Mark tasks complete without testing
✅ **DO**: Test components before delivery

### Anti-Pattern: Type Interface Mismatch
❌ **DON'T**: Create interfaces without checking real responses
✅ **DO**: Match interfaces exactly to API responses
```

### 4. Team Standards Integration
```markdown
## Felipe Rosa Quality Standards

- **Expectation**: Working implementations on first delivery
- **Feedback Style**: Direct, clear quality expectations
- **Standard**: Zero tolerance for runtime errors
- **Learning**: Continuous improvement and evolution required
```

## Implementation Changes

### Updated Workflow Orchestration
Before spawning workflows for API integration:
1. Task: "Analyze openapi.json for endpoint verification"
2. Task: "Test actual API responses with curl"
3. Task: "Validate data structures before implementation"
4. THEN: Spawn BUILDER with verified specifications

### Quality Validation Steps
After any implementation work:
1. mcp__wait__wait_seconds(10) - Allow compilation
2. Test basic functionality 
3. Verify no runtime errors
4. ONLY THEN mark as completed

## Prompt Addition Template
```
## CRITICAL QUALITY STANDARDS

**API Integration Protocol:**
- ALWAYS fetch openapi.json before coding
- ALWAYS test endpoints with curl 
- ALWAYS validate response structures
- NEVER assume API behavior

**Delivery Standards:**
- Test components before marking complete
- Zero runtime errors in delivered work
- Working functionality on first delivery
- Continuous learning from quality failures

**Felipe's Expectation:** Working code, not broken implementations. Evolve and improve quality standards.
```