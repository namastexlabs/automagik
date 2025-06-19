# Workflow Runs Database Migration Plan

## Objectives

This document outlines the migration plan for consolidating workflow run data from the legacy `workflow_processes` table to a new, enhanced `workflow_runs` table structure. The migration aims to:

- **Standardize data structure** - Create a unified schema for all workflow run information
- **Improve performance** - Optimize queries and indexing for better database performance  
- **Enable analytics** - Support advanced reporting and analytics capabilities
- **Ensure data integrity** - Maintain all historical data during the migration process
- **Zero downtime** - Execute migration without service interruption

## Current State Analysis

### Existing Schema: `workflow_processes`

```sql
CREATE TABLE workflow_processes (
    id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    message TEXT NOT NULL,
    max_turns INTEGER DEFAULT 30,
    session_name TEXT,
    git_branch TEXT,
    repository_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    execution_time INTEGER,
    total_cost REAL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Data Source Mapping

The following table shows how existing data will be mapped to the new schema:

| Current Field | New Field | Transformation | Notes |
|---------------|-----------|----------------|-------|
| `id` | `run_id` | Direct copy | Primary key |
| `workflow_name` | `workflow_type` | Direct copy | Workflow classification |
| `message` | `description` | Direct copy | Task description |
| `max_turns` | `max_turns` | Direct copy | Turn limit configuration |
| `session_name` | `session_id` | Direct copy | Session identifier |
| `git_branch` | `git_branch` | Direct copy | Git branch reference |
| `repository_url` | `repository_url` | Direct copy | Repository location |
| `created_at` | `created_at` | Direct copy | Creation timestamp |
| `updated_at` | `updated_at` | Direct copy | Last modification timestamp |
| `status` | `status` | Direct copy | Execution status |
| `result` | `result_data` | JSON conversion | Structured result data |
| `error_message` | `error_details` | JSON conversion | Error information |
| `execution_time` | `execution_time_ms` | Direct copy | Execution duration |
| `total_cost` | `total_cost` | Direct copy | Associated costs |
| `started_at` | `started_at` | Direct copy | Execution start time |
| `completed_at` | `completed_at` | Direct copy | Execution completion time |

### Additional Fields

The new schema includes additional fields for enhanced functionality:

| New Field | Purpose | Default Value |
|-----------|---------|---------------|
| `user_id` | User tracking | `NULL` (for system runs) |
| `priority` | Task prioritization | `'normal'` |
| `tags` | Categorization | `'[]'` (empty JSON array) |
| `metadata` | Extended information | `'{}'` (empty JSON object) |
| `progress_data` | Progress tracking | `'{}'` (empty JSON object) |
| `resource_usage` | Performance metrics | `'{}'` (empty JSON object) |

## Target Schema: `workflow_runs`

```sql
CREATE TABLE workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    description TEXT NOT NULL,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT DEFAULT 'normal',
    
    -- Configuration
    max_turns INTEGER DEFAULT 30,
    session_id TEXT,
    git_branch TEXT,
    repository_url TEXT,
    
    -- Timing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Results and Performance
    result_data JSON,
    error_details JSON,
    execution_time_ms INTEGER,
    total_cost DECIMAL(10,4),
    
    -- Enhanced Features  
    tags JSON DEFAULT '[]',
    metadata JSON DEFAULT '{}',
    progress_data JSON DEFAULT '{}',
    resource_usage JSON DEFAULT '{}',
    
    -- Indexes
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Performance Indexes
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX idx_workflow_runs_workflow_type ON workflow_runs(workflow_type);
CREATE INDEX idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX idx_workflow_runs_created_at ON workflow_runs(created_at);
CREATE INDEX idx_workflow_runs_completed_at ON workflow_runs(completed_at);
CREATE INDEX idx_workflow_runs_priority ON workflow_runs(priority);

-- Composite Indexes for Analytics
CREATE INDEX idx_workflow_runs_type_status ON workflow_runs(workflow_type, status);
CREATE INDEX idx_workflow_runs_user_status ON workflow_runs(user_id, status);
CREATE INDEX idx_workflow_runs_date_range ON workflow_runs(created_at, completed_at);
```

## Migration Strategy

### Phase 1: Schema Preparation (Week 1)

1. **Create new table structure**
   - Deploy `workflow_runs` table with all indexes
   - Verify schema integrity and constraints
   - Test basic CRUD operations

2. **Implement dual-write pattern**
   - Update application code to write to both tables
   - Ensure data consistency between old and new tables
   - Add feature flag for gradual rollout

### Phase 2: Data Migration (Week 2)

1. **Historical data migration**
   - Create migration script with batch processing
   - Map existing data according to transformation rules
   - Validate migrated data integrity

2. **Migration script structure**:
   ```sql
   -- Migration in batches to avoid locks
   INSERT INTO workflow_runs (
       run_id, workflow_type, description, status,
       max_turns, session_id, git_branch, repository_url,
       created_at, updated_at, started_at, completed_at,
       result_data, error_details, execution_time_ms, total_cost,
       tags, metadata, progress_data, resource_usage
   )
   SELECT 
       id, workflow_name, message, status,
       max_turns, session_name, git_branch, repository_url,
       created_at, updated_at, started_at, completed_at,
       CASE WHEN result IS NOT NULL THEN json_object('result', result) ELSE '{}' END,
       CASE WHEN error_message IS NOT NULL THEN json_object('error', error_message) ELSE '{}' END,
       execution_time, total_cost,
       '[]', '{}', '{}', '{}'
   FROM workflow_processes
   WHERE id BETWEEN ? AND ?
   AND id NOT IN (SELECT run_id FROM workflow_runs);
   ```

### Phase 3: Application Migration (Week 3)

1. **Update read operations**
   - Modify queries to use `workflow_runs` table
   - Update API endpoints and data models
   - Implement backward compatibility layer

2. **Performance validation**
   - Monitor query performance improvements
   - Validate analytics capabilities
   - Conduct load testing

### Phase 4: Cleanup (Week 4)

1. **Remove dual-write pattern**
   - Update code to write only to `workflow_runs`
   - Remove feature flags and legacy code paths
   - Clean up deprecated functions

2. **Archive legacy table**
   - Rename `workflow_processes` to `workflow_processes_archive`
   - Document archival process for future reference
   - Set up automated cleanup procedures

## Risk Assessment & Mitigation

### High Risk Items

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|-------------------|
| Data loss during migration | Critical | Low | Full backup + rollback plan + batch processing |
| Performance degradation | High | Medium | Thorough testing + index optimization + monitoring |
| Application downtime | High | Low | Dual-write pattern + gradual rollout + feature flags |

### Medium Risk Items

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|-------------------|
| Query compatibility issues | Medium | Medium | Comprehensive testing + backward compatibility layer |
| Storage space constraints | Medium | Low | Disk space monitoring + cleanup procedures |
| Team coordination issues | Medium | Medium | Clear communication plan + documentation |

## Success Criteria

### Performance Metrics
- [ ] Query response time improved by 30%
- [ ] Storage efficiency increased by 20%
- [ ] Zero data loss during migration
- [ ] 99.9% uptime maintained throughout migration

### Functional Requirements
- [ ] All existing functionality preserved
- [ ] New analytics capabilities operational
- [ ] API backward compatibility maintained
- [ ] Enhanced reporting features available

### Quality Assurance
- [ ] Comprehensive test coverage (>95%)
- [ ] Load testing passed for 10x current traffic
- [ ] Security audit completed
- [ ] Documentation updated and reviewed

## Timeline

### Week 1: Foundation
- **Days 1-2**: Schema deployment and testing
- **Days 3-4**: Dual-write implementation
- **Days 5-7**: Integration testing and validation

### Week 2: Migration
- **Days 8-9**: Historical data migration (batched)
- **Days 10-11**: Data validation and integrity checks
- **Days 12-14**: Performance testing and optimization

### Week 3: Transition
- **Days 15-16**: Application code updates
- **Days 17-18**: API endpoint migration
- **Days 19-21**: User acceptance testing

### Week 4: Finalization
- **Days 22-23**: Legacy cleanup and archival
- **Days 24-25**: Documentation and training
- **Days 26-28**: Post-migration monitoring and optimization

## Rollback Plan

### Immediate Rollback (if issues detected in first 24 hours)
1. Switch feature flag to disable new table writes
2. Revert API endpoints to use legacy table
3. Monitor system stability for 2 hours
4. Conduct post-incident review

### Extended Rollback (if issues detected later)
1. Restore database from pre-migration backup
2. Apply any critical updates that occurred post-migration
3. Re-enable legacy code paths
4. Schedule detailed investigation and remediation

## Monitoring & Validation

### Key Metrics to Monitor
- Database query performance (response times, throughput)
- Application error rates and response codes
- Data consistency between tables during dual-write phase
- Storage utilization and growth patterns
- User experience metrics (page load times, feature availability)

### Validation Procedures
- Automated data integrity checks (row counts, checksums)
- Sample data comparison between old and new tables
- End-to-end functionality testing
- Performance benchmark comparisons
- User acceptance testing with key stakeholders

## Communication Plan

### Stakeholders
- **Development Team**: Daily standups during migration weeks
- **DevOps Team**: Real-time monitoring and alert coordination
- **Product Team**: Weekly progress updates and user impact assessment
- **Leadership**: Milestone reports and risk escalation procedures

### Communication Channels
- **Slack**: Real-time updates and issue coordination
- **Email**: Formal milestone notifications and reports
- **Wiki**: Living documentation and reference materials
- **Meetings**: Weekly status reviews and decision points

---

*Document Version: 1.0*  
*Last Updated: 2025-06-19*  
*Next Review: Upon completion of Phase 1*