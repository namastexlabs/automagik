# BUILDER Task Card - Repository Reference Updates

## Epic Context
- **Epic**: Repository Migration automagik → namastexlabs/automagik
- **Branch**: migration/namastex-automagik-sync
- **Session**: migration_builder_1

## Primary Objective
Update ALL references from "automagik" to "automagik" across the entire codebase for consistent naming.

## Requirements Checklist
- [ ] Update package.json project name from "automagik" to "automagik"
- [ ] Update ecosystem.config.js PM2 service name references
- [ ] Update all Makefile service management commands
- [ ] Update repository URLs in payloads/full_test.json and other config files
- [ ] Update all documentation files (INSTALLATION_GUIDE.md, README.md, etc.)
- [ ] Update all test files with hardcoded paths (/root/workspace/automagik → /root/workspace/automagik)
- [ ] Update all .cursor/rules/ development configuration files
- [ ] Update all scripts/ automation with new repository name
- [ ] Verify no remaining "automagik" references exist in codebase

## Technical Specifications
- **Target Pattern**: Replace "automagik" with "automagik" 
- **Scope**: ~442 file references identified via grep analysis
- **Critical Files**: package.json, ecosystem.config.js, Makefile, documentation
- **Path Updates**: /root/workspace/automagik → /root/workspace/automagik
- **Service Names**: PM2 service "automagik" → "automagik"

## Success Criteria
- [ ] Zero occurrences of "automagik" remain in codebase (verified by grep)
- [ ] All PM2 service references updated consistently
- [ ] All documentation references point to automagik
- [ ] All test paths and scripts use new naming
- [ ] Package.json name field updated to "automagik"

## Resources
- Architecture: /genie/current/repo-migration-epic.md
- Grep Analysis: 442+ occurrences identified across multiple file types
- Critical Files: Focus on package.json, ecosystem.config.js, Makefile first

## Status Updates
- **Created**: Ready for implementation
- **Started**: [ ]
- **Completed**: [ ]

## Notes
<!-- BUILDER updates this section during execution -->
Focus on systematic replacement while preserving functionality. Ensure PM2 service names remain consistent throughout all configuration files.