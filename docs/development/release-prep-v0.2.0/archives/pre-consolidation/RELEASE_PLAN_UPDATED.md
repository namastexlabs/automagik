# Automagik Agents v0.2.0 Release Plan (Updated)

## Executive Summary

Based on human feedback, this updated plan addresses the requirements for:
- **Version Target**: v0.1.4 → v0.2.0 (minor release)
- **MCP Refactor Inclusion**: All changes in main branch will be included
- **Architecture Enhancement**: Improved document organization with epic-based folder structure
- **Workflow Improvements**: Updated prompts for proper document placement

## Key Changes from Previous Plan

### 1. Version Strategy Adjustment
- **Previous**: v0.1.4 → v1.0.0 (major release)
- **Updated**: v0.1.4 → v0.2.0 (minor release with MCP refactor)
- **Rationale**: Include modern MCP architecture while maintaining semantic versioning

### 2. MCP Refactor Status
✅ **CONFIRMED**: MCP refactor migrations are already present and functional:
- Migration file: `20250610_230000_create_mcp_configs_table.sql`
- **PostgreSQL Support**: Full support with JSONB, constraints, and triggers
- **SQLite Compatibility**: Uses JSON text storage, maintains functionality
- **Automatic Migration**: Applied during `automagik agents db init`

### 3. Architecture System Improvements

#### Document Organization Enhancement
**Problem Identified**: Architecture documents created in project root
**Solution Implemented**: Epic-based folder structure

```bash
# New Standard Structure
docs/development/{epic_id}/
├── ARCHITECTURE.md           # System overview
├── TECHNICAL_DECISIONS.md    # Decision records  
├── IMPLEMENTATION_ROADMAP.md # Implementation plan
├── INTEGRATION_SPECS.md      # Interface specs
└── BREAKING_CHANGES.md       # Migration guides
```

#### Workflow Prompt Updates
✅ **COMPLETED**: Updated ARCHITECT workflow prompt to:
- Enforce epic-based document organization
- Prevent root-level document creation  
- Provide clear document creation templates
- Include mandatory folder structure requirements

## Migration Status Assessment

### Database Migrations ✅ READY
**Current MCP Migration**: `20250610_230000_create_mcp_configs_table.sql`

**PostgreSQL Features**:
- ✅ JSONB storage with GIN indexes
- ✅ UUID primary keys with `gen_random_uuid()`
- ✅ Timestamp defaults with `NOW()`
- ✅ JSON validation constraints
- ✅ Automatic trigger for updated_at

**SQLite Compatibility**:
- ✅ JSON text storage (compatible equivalent)
- ✅ String UUID storage
- ✅ ISO timestamp storage
- ✅ All constraints preserved
- ✅ Provider abstraction handles differences

**Migration Safety**:
- ✅ Creates backup tables before migration
- ✅ Uses `IF NOT EXISTS` for idempotency
- ✅ Includes rollback documentation
- ✅ Comprehensive validation and indexing

### API Changes Assessment
**MCP API Simplification**:
- **Removed**: 15+ complex endpoints
- **Added**: 4 simplified CRUD endpoints
- **Status**: ✅ Already implemented in codebase
- **Breaking Changes**: Yes, but manageable for v0.2.0

## Updated Release Timeline

### Phase 1: Quality & Stability (Week 1)
**Focus**: Fix critical issues and prepare foundation

#### Day 1-2: Critical Fixes
```bash
# Priority 1: Fix undefined names (BLOCKING)
uv run ruff check src/ --select F821 --no-fix
# Manual fix required for 12 undefined names

# Priority 2: Auto-fix what's possible
uv run ruff check src/ --fix
uv run ruff format src/
```

#### Day 3-4: Test Stabilization  
```bash
# Ensure all 892 tests pass consistently
uv run pytest tests/ -v --tb=short

# Validate database migrations work for both providers
uv run pytest tests/db/test_mcp_migration.py -v
```

#### Day 5: Documentation Audit
- ✅ Update architecture documents organization
- ✅ Document MCP refactor changes
- ✅ Create v0.2.0 migration guide

### Phase 2: MCP System Validation (Week 2)
**Focus**: Ensure MCP refactor is production-ready

#### MCP System Testing
```bash
# Test MCP configs table creation
automagik agents db init --force

# Test both SQLite and PostgreSQL
DATABASE_TYPE=sqlite automagik agents db init
DATABASE_TYPE=postgresql automagik agents db init

# Validate MCP API endpoints
uv run pytest tests/api/test_mcp_routes_new.py -v
```

#### Integration Testing
- ✅ Agent creation with MCP configs
- ✅ Tool discovery and filtering
- ✅ Multi-database compatibility
- ✅ Performance benchmarking

### Phase 3: Release Preparation (Week 3)
**Focus**: Finalize and package release

#### Version Update
```bash
# Update version in src/version.py
__version__ = "0.2.0"

# Update pyproject.toml metadata
# Update documentation references
# Create release notes
```

#### Final Testing
```bash
# Full test suite multiple runs
for i in {1..3}; do
    uv run pytest tests/ -v --tb=short || break
done

# Performance regression testing
uv run python scripts/benchmarks/comprehensive_benchmark.py
```

#### Release Artifacts
- 📦 PyPI package build and test
- 🐳 Docker images for multiple architectures
- 📚 Documentation site update
- 📋 Release notes with migration guide

## Success Criteria for v0.2.0

### Code Quality ✅/❌
- [ ] **0 Ruff errors** (down from 182)
- [ ] **0 undefined names** (down from 12) - CRITICAL
- [ ] **100% test pass rate** (892/892 tests)
- [ ] **>85% code coverage** maintained

### MCP System ✅/❌
- [ ] **Database migrations work** for both SQLite and PostgreSQL
- [ ] **API endpoints functional** with new simplified structure
- [ ] **Agent integration working** with new MCP configs
- [ ] **Performance benchmarks** meet or exceed previous version

### Architecture ✅/❌
- [ ] **Epic-based document structure** implemented
- [ ] **Workflow prompts updated** to prevent root-level documents
- [ ] **Existing documents** moved to proper locations
- [ ] **Architecture system enhanced** and documented

### Release Readiness ✅/❌
- [ ] **Version bumped** to 0.2.0
- [ ] **Release notes** comprehensive with migration guide
- [ ] **Documentation updated** with new MCP system
- [ ] **Docker images** built and tested

## Breaking Changes Management

### MCP Refactor Impact
**Database Changes**:
- ✅ Migration handles old → new system automatically
- ✅ Backup tables created for safety
- ✅ Rollback procedures documented

**API Changes**:
- ⚠️ 15+ endpoints removed, 4 new endpoints added
- ✅ Migration guide for API consumers
- ✅ Version clearly indicates breaking changes (0.1.4 → 0.2.0)

**Client Impact**:
- **Internal tools**: Update to new MCP API endpoints
- **External integrations**: Provide migration timeline and support
- **Documentation**: Comprehensive change documentation

## Risk Assessment

### High Risk: Code Quality Issues
- **Risk**: 12 undefined names could cause runtime failures
- **Mitigation**: Priority focus on fixing critical Ruff errors
- **Timeline**: 2-3 days intensive work

### Medium Risk: MCP System Changes
- **Risk**: Breaking changes affect existing users
- **Mitigation**: Clear migration guide, version communication
- **Timeline**: Manageable with proper documentation

### Low Risk: Document Organization
- **Risk**: Developer confusion about where to find documents
- **Mitigation**: Clear structure, updated prompts, examples
- **Timeline**: Already implemented

## Cost Estimation

### Development Time
- **Week 1**: Code quality fixes - 30-40 hours
- **Week 2**: MCP validation and testing - 20-30 hours  
- **Week 3**: Release preparation - 15-20 hours
- **Total**: 65-90 hours over 3 weeks

### Infrastructure Costs
- **Testing environments**: ~$20
- **CI/CD pipeline runs**: ~$10
- **Documentation hosting**: ~$5
- **Total**: ~$35

## Post-Release Plan

### Monitoring
- **Error rates**: Target <1% increase from v0.1.4
- **Performance**: No degradation in key metrics
- **Adoption**: Community feedback tracking
- **Support**: Migration assistance for breaking changes

### Future Roadmap
- **v0.2.1**: Patch releases for any critical issues
- **v0.3.0**: Next feature release with additional enhancements
- **v1.0.0**: Major stable release after community validation

---

## Immediate Next Steps

1. **Fix Critical Code Quality Issues**
   - Focus on 12 undefined names (F821 errors)
   - Run comprehensive Ruff fixes
   - Ensure clean codebase

2. **Validate MCP System**
   - Test database migrations thoroughly
   - Verify API endpoint functionality
   - Confirm agent integration works

3. **Update Version and Documentation**
   - Bump to v0.2.0 in all relevant files
   - Create comprehensive release notes
   - Document migration procedures

4. **Release Package**
   - Build and test PyPI package
   - Create GitHub release
   - Update documentation sites

**Estimated Timeline**: 3 weeks to high-quality v0.2.0 release
**Key Success Factor**: All critical code quality issues resolved first