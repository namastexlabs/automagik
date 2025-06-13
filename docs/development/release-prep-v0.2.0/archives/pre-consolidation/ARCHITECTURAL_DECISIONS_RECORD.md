# Architectural Decisions Record
## Epic: release-prep-v0.2.0 - Claude Code Local-Only Architecture

### ADR-001: Local-Only Execution Architecture

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
Claude Code currently supports dual execution modes (Docker and local) with incomplete Docker implementation. The Docker mode adds significant complexity without providing immediate value, complicating development, testing, and maintenance.

#### Decision
Transform Claude Code to support **local execution only**, removing all Docker/container-related code and infrastructure.

#### Rationale
1. **Incomplete Implementation**: Docker mode is not fully functional and requires significant additional development
2. **Complexity Reduction**: Dual-mode architecture adds unnecessary complexity to codebase
3. **Development Velocity**: Local-only focus accelerates development and simplifies debugging
4. **Maintenance Overhead**: Maintaining two execution paths increases technical debt
5. **Testing Simplicity**: Single execution mode enables more focused and comprehensive testing

#### Consequences
**Positive**:
- Simplified architecture with clear execution path
- Reduced codebase size (~1,000+ lines removed)
- Faster development and testing cycles
- Lower maintenance overhead
- Clearer documentation and onboarding

**Negative**:
- Loss of potential future containerization benefits
- Need to re-implement Docker support if required later
- Some users may expect containerized execution

**Neutral**:
- Local execution capabilities remain unchanged
- All existing workflows continue to function

#### Implementation Impact
- Remove `container.py`, `docker_executor.py`, and `docker/` directory
- Simplify `agent.py` initialization logic
- Consolidate test suite to focus on local execution
- Update documentation to reflect local-only architecture

---

### ADR-002: Executor Factory Simplification

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
`ExecutorFactory` currently implements a factory pattern to choose between Docker and local executors. With local-only architecture, this factory becomes unnecessary complexity.

#### Decision
**Remove ExecutorFactory entirely** and use direct `LocalExecutor` instantiation in `ClaudeCodeAgent`.

#### Rationale
1. **Over-Engineering**: Factory pattern unnecessary for single implementation
2. **Direct Instantiation**: Simpler and more transparent
3. **Reduced Indirection**: Easier to debug and understand
4. **YAGNI Principle**: Current needs don't justify factory complexity

#### Alternative Considered
Keep simplified factory for potential future extensibility, but rejected due to YAGNI principle and current simplicity needs.

#### Consequences
**Positive**:
- Simplified code path from agent to executor
- Easier debugging and testing
- Reduced abstraction layers
- Clear dependency relationships

**Negative**:
- Future executor types require more refactoring
- Loss of factory pattern benefits

#### Implementation Impact
- Replace factory calls with direct `LocalExecutor` instantiation
- Remove `executor_factory.py` or simplify to utility functions
- Update related tests to test direct instantiation

---

### ADR-003: Test Suite Consolidation Strategy

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
Current test suite contains mixed concerns with Docker and local execution tests intermingled, creating confusion and maintenance overhead.

#### Decision
**Consolidate test suite** to focus exclusively on local execution with enhanced coverage of local-specific scenarios.

#### Rationale
1. **Test Clarity**: Single execution mode enables focused test scenarios
2. **Faster Execution**: No Docker setup/teardown overhead
3. **Better Coverage**: More thorough testing of actual execution path
4. **Simplified CI/CD**: No Docker dependencies in test environment

#### Implementation Strategy
1. **Remove**: All Docker-specific test files and test methods
2. **Consolidate**: Merge overlapping local execution tests
3. **Enhance**: Add comprehensive local execution edge cases
4. **Optimize**: Improve test performance and reliability

#### Consequences
**Positive**:
- Faster test execution (estimated 20%+ improvement)
- Clearer test intent and organization
- Better coverage of actual execution paths
- Simplified test environment setup

**Negative**:
- Temporary reduction in overall test count
- Need to rebuild Docker tests if containerization returns

#### Quality Gates
- Maintain minimum 85% code coverage
- All existing local functionality must remain tested
- Test execution time must improve or maintain current performance

---

### ADR-004: Project Rename from "automagik-agents" to "automagik"

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Product Team  
**Epic**: release-prep-v0.2.0  

#### Context
Current project name "automagik-agents" is verbose and the "-agents" suffix may limit perception of the platform's capabilities beyond just agents.

#### Decision
Rename project from **"automagik-agents"** to **"automagik"** for the 0.2 release.

#### Rationale
1. **Simplicity**: Shorter, more memorable name
2. **Brand Clarity**: "Automagik" better represents the platform vision
3. **Flexibility**: Allows for expansion beyond agents into broader automation
4. **Marketing**: More appealing and professional brand name

#### Scope of Changes
- Package name in `pyproject.toml`
- Repository references and URLs
- Documentation and README
- Installation instructions
- Import statements (if any hardcoded references exist)

#### Consequences
**Positive**:
- Better brand recognition and memorability
- More flexible platform positioning
- Professional project naming

**Negative**:
- Potential confusion during transition period
- Need to update external references and documentation
- Package name conflicts (need to verify availability)

**Neutral**:
- No functional impact on codebase
- Backward compatibility maintained through aliases if needed

#### Migration Strategy
1. Update `pyproject.toml` package metadata
2. Search and replace hardcoded references
3. Update documentation and README
4. Maintain compatibility during transition period

---

### ADR-005: Environment Variable Deprecation Strategy

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
`CLAUDE_CODE_MODE` environment variable becomes obsolete with local-only architecture, but immediate removal might break existing configurations.

#### Decision
**Mark `CLAUDE_CODE_MODE` as deprecated** with graceful handling and warning messages, but maintain backward compatibility.

#### Rationale
1. **Backward Compatibility**: Avoid breaking existing user configurations
2. **Graceful Migration**: Provide clear migration path and timeline
3. **User Experience**: Informative warnings rather than hard failures
4. **Future Cleanup**: Clear deprecation timeline for eventual removal

#### Implementation Approach
```python
# Deprecation handling in agent initialization
if os.environ.get("CLAUDE_CODE_MODE") == "docker":
    logger.warning(
        "CLAUDE_CODE_MODE=docker is deprecated. "
        "Claude Code now runs in local mode only. "
        "This variable will be ignored. "
        "Support will be removed in v0.3.0"
    )
```

#### Consequences
**Positive**:
- Smooth transition for existing users
- Clear communication about changes
- Maintains functionality during migration period

**Negative**:
- Additional code complexity for deprecation handling
- Need to maintain deprecation logic until v0.3.0

#### Timeline
- v0.2.0: Deprecation warnings introduced
- v0.3.0: Environment variable support removed entirely

---

### ADR-006: Documentation Architecture for Local-Only Focus

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
Current documentation includes extensive Docker setup and configuration instructions that become obsolete with local-only architecture.

#### Decision
**Restructure documentation** to focus exclusively on local execution with simplified setup and configuration guidance.

#### Rationale
1. **User Experience**: Simpler setup instructions improve onboarding
2. **Maintenance**: Single execution mode reduces documentation complexity
3. **Clarity**: Clear focus prevents confusion about execution options
4. **Accuracy**: Documentation matches actual implementation capabilities

#### Documentation Changes Required
1. **Remove**: All Docker setup and configuration sections
2. **Simplify**: Installation and setup instructions
3. **Enhance**: Local execution troubleshooting and optimization
4. **Update**: Architecture diagrams and component descriptions

#### Consequences
**Positive**:
- Clearer, more focused documentation
- Simplified user onboarding experience
- Reduced documentation maintenance overhead
- Better alignment between docs and implementation

**Negative**:
- Loss of Docker documentation for future reference
- Need to rebuild Docker docs if containerization returns

#### Quality Standards
- All documentation must reflect actual implementation
- Setup instructions must be testable and verified
- Troubleshooting guides must cover common local execution issues

---

### ADR-007: Breaking Changes Management for 0.2 Release

**Status**: Proposed  
**Date**: 2025-01-13  
**Deciders**: Architecture Team  
**Epic**: release-prep-v0.2.0  

#### Context
Local-only transformation introduces potential breaking changes that need careful management to minimize user impact.

#### Decision
**Minimize breaking changes** through backward compatibility measures and clear migration guidance.

#### Breaking Changes Assessment

**API Level**: NO BREAKING CHANGES
- Local execution API remains unchanged
- Workflow configurations unchanged
- Environment variables for local mode unchanged

**Configuration Level**: MINIMAL BREAKING CHANGES
- `CLAUDE_CODE_MODE=docker` will be ignored (with warning)
- All local configuration options remain functional

**Deployment Level**: MINIMAL BREAKING CHANGES
- Docker deployment options removed
- Local deployment requirements unchanged

#### Mitigation Strategies
1. **Deprecation Warnings**: Clear messaging about removed features
2. **Migration Guide**: Comprehensive guide for affected users
3. **Backward Compatibility**: Maintain compatibility where possible
4. **Version Communication**: Clear release notes about changes

#### Consequences
**Positive**:
- Minimal disruption to existing users
- Clear communication about changes
- Smooth transition path provided

**Negative**:
- Some users may need to adjust deployment strategies
- Docker users will need alternative solutions

#### Release Communication Plan
1. Pre-release communication about upcoming changes
2. Detailed release notes with migration guidance
3. Support documentation for transition period
4. Community support for migration questions

---

### Implementation Priority Matrix

| ADR | Priority | Dependencies | Risk Level | Effort |
|-----|----------|--------------|------------|--------|
| ADR-001 | P0 | None | Medium | High |
| ADR-002 | P0 | ADR-001 | Low | Medium |
| ADR-003 | P1 | ADR-001, ADR-002 | Medium | High |
| ADR-004 | P1 | None | Low | Low |
| ADR-005 | P2 | ADR-001 | Low | Low |
| ADR-006 | P2 | ADR-001 | Low | Medium |
| ADR-007 | P0 | All ADRs | Medium | Medium |

### Review and Approval Process

**Technical Review Required**:
- ADR-001: Local-only architecture decision
- ADR-002: Factory pattern removal
- ADR-003: Test suite consolidation approach

**Product Review Required**:
- ADR-004: Project rename decision
- ADR-007: Breaking changes management

**Stakeholder Review Required**:
- ADR-005: Environment variable deprecation timeline
- ADR-006: Documentation restructuring scope

These architectural decisions provide the foundation for implementing the Claude Code local-only transformation while maintaining system stability and user experience.