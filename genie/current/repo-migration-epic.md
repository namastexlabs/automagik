# Epic: Repository Migration - am-agents-labs → namastexlabs/automagik

## 🎯 Epic Objective
Migrate the current am-agents-labs repository to namastexlabs/automagik with complete reference updates, tag preservation, and forced synchronization.

## 🏗️ Architecture Overview
The migration involves three parallel tracks:
1. **Reference Updates** - Update all am-agents-labs references to automagik
2. **Git Operations** - Handle branch creation, origin changes, and pushing
3. **Verification** - Ensure all changes are complete and functional

## 📊 Current Analysis Results
- **Origin**: `https://github.com/namastexlabs/am-agents-labs.git`
- **Tags**: 26 release tags (v0.4.0 to v0.6.19) 
- **References**: 442+ occurrences of "am-agents-labs" to update
- **Target**: `https://github.com/namastexlabs/automagik.git`

## 🔄 Workflow Strategy
1. **BUILDER** - Handle bulk reference updates across all files
2. **SURGEON** - Precise git operations and repository management  
3. **GUARDIAN** - Verification and rollback safety

## ✅ Success Criteria
- [ ] All am-agents-labs references updated to automagik
- [ ] New origin set to namastexlabs/automagik
- [ ] All 26 tags successfully pushed
- [ ] Repository force-pushed with complete history
- [ ] Core services (PM2, Makefile) functional with new names
- [ ] No broken references or missing dependencies

## 🚨 Risk Mitigation
- Migration branch created for isolation
- Backup verification before force push
- Tag preservation explicitly handled
- Service name consistency maintained

## 🎯 Linear Integration
This epic represents a complete infrastructure migration requiring coordination across multiple systems and careful verification at each step.