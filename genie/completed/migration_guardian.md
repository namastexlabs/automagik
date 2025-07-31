# GUARDIAN Task Card - Migration Verification & Safety

## Epic Context  
- **Epic**: Repository Migration automagik → namastexlabs/automagik
- **Branch**: migration/namastex-automagik-sync
- **Session**: migration_guardian_1

## Primary Objective
Provide comprehensive verification and safety measures for the repository migration process.

## Requirements Checklist
- [ ] Verify backup state before migration starts
- [ ] Monitor BUILDER reference updates for completeness
- [ ] Verify no broken imports or module references after updates
- [ ] Validate PM2 service configuration still functional
- [ ] Check Makefile commands work with new service names
- [ ] Verify target repository accessibility and permissions
- [ ] Monitor SURGEON git operations for errors
- [ ] Validate tag preservation and integrity
- [ ] Perform post-migration functionality verification
- [ ] Document any issues or rollback procedures needed

## Technical Specifications
- **Verification Scope**: Complete codebase functionality
- **Critical Services**: PM2 (automagik service), Makefile commands
- **Import Validation**: Python module imports, path references
- **Tag Integrity**: All 26 tags present and pointing to correct commits
- **Security**: Repository access, authentication, force push safety

## Success Criteria
- [ ] All reference updates verified without breaking functionality
- [ ] PM2 service "automagik" can start/stop/restart properly
- [ ] Makefile commands execute without errors
- [ ] Python imports and path references remain functional
- [ ] Target repository migration completed without data loss
- [ ] All tags transferred with correct commit associations
- [ ] No security or access issues detected

## Resources
- Architecture: /genie/current/repo-migration-epic.md
- Task Dependencies: migration_builder.md, migration_surgeon.md
- Verification Tools: grep, make commands, PM2 status checks

## Status Updates
- **Created**: Ready for verification duties
- **Started**: [ ]
- **Completed**: [ ]

## Notes
<!-- GUARDIAN updates this section during execution -->
Focus on preventing data loss and ensuring rollback capability. Monitor other workflows for any issues and provide safety checkpoints.