# SURGEON Task Card - Git Repository Operations

## Epic Context
- **Epic**: Repository Migration automagik → namastexlabs/automagik
- **Branch**: migration/namastex-automagik-sync  
- **Session**: migration_surgeon_1

## Primary Objective
Execute precise git operations to migrate repository to namastexlabs/automagik with complete history and tag preservation.

## Requirements Checklist
- [ ] Create migration branch: migration/namastex-automagik-sync
- [ ] Verify current repository state and clean working directory
- [ ] Add new remote origin: https://github.com/namastexlabs/automagik.git
- [ ] Remove old origin or rename to backup
- [ ] Prepare for force push (verify target repository readiness)
- [ ] Push complete history with --force to overwrite target
- [ ] Push all 26 release tags (v0.4.0 through v0.6.19) 
- [ ] Verify successful migration and branch HEAD reference
- [ ] Update local repository configuration

## Technical Specifications
- **Migration Branch**: migration/namastex-automagik-sync
- **Target Origin**: https://github.com/namastexlabs/automagik.git
- **Tag Count**: 26 tags to preserve (NMSTX-36-complete, v0.4.0-v0.6.19)
- **Force Strategy**: Complete repository replacement at target
- **History Preservation**: Full commit history maintained

## Success Criteria
- [ ] Migration branch created and active
- [ ] New origin configured and accessible
- [ ] Complete repository pushed with --force (no conflicts)
- [ ] All 26 tags successfully transferred
- [ ] Target repository shows correct commit history
- [ ] Local repository properly configured with new remote
- [ ] No data loss or corruption in migration

## Resources
- Architecture: /genie/current/repo-migration-epic.md
- Current Tags: NMSTX-36-complete, v0.4.0→v0.6.19 (26 total)
- Current Origin: https://github.com/namastexlabs/automagik.git

## Status Updates
- **Created**: Ready for git operations
- **Started**: [ ]
- **Completed**: [ ]

## Notes
<!-- SURGEON updates this section during execution -->
Critical: Ensure all tags are pushed with explicit commands. Verify target repository access before force push operations.