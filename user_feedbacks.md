# User Feedbacks & Complaints - GENIE Behavior Improvements

## Felipe's Feedback Log

### 2025-06-16 - Session: Async Workflow Features

**Issue 1: Not using wait tools for autonomous monitoring**
- **Complaint**: "you are supposed to use wait tool, arent you? then keep active polling"
- **Context**: I spawned workflows but wasn't actively monitoring them with wait tools
- **Root Cause**: Not following my own GENIE prompt instructions for autonomous monitoring
- **Fix Required**: Always use wait tools for active workflow polling, implement proper monitoring patterns

**Issue 2: Brain system overcrowding**
- **Complaint**: "if we have too much context in there, it means our brain made a mistake by inserting too many things in the same box, this has to be reallly easy to use"
- **Context**: Memory searches returning 60K+ tokens, brain overcrowded with duplicate content
- **Root Cause**: Poor memory organization, storing too much in single memory nodes
- **Fix Required**: Implement better memory segmentation, cleaner brain organization

**Issue 3: Making too many mistakes consistently**
- **Complaint**: "since you are making so many mistakes, so that i can fix your behavior with new prompts"
- **Context**: Pattern of errors in workflow orchestration and tool usage
- **Root Cause**: Not following established patterns, not learning from feedback properly
- **Fix Required**: Better adherence to prompts, improved learning loops, stricter self-validation

## Action Items for GENIE Improvement

1. **Autonomous Monitoring**: Always use wait tools for workflow polling
2. **Brain Organization**: Keep memory nodes small and focused
3. **Tool Usage**: Follow established MCP patterns consistently
4. **Learning**: Better feedback integration and error prevention
5. **Validation**: Self-check against prompts before acting

**Issue 4: API Status Misbehavior**
- **Complaint**: "that might be another misbahavior we need to open issues for"
- **Context**: API returning status "running" with 0% completion when workflows are actually active and progressing
- **Root Cause**: API status endpoint not reflecting real workflow progress from logs
- **Fix Required**: Open Linear issue for API status endpoint bug - logs show real progress but API reports incorrect status

## Behavioral Patterns to Fix

- [x] Implement proper wait tool usage in all workflow monitoring (FIXED: BRAIN stored patterns)
- [x] Reduce brain memory node size and complexity (FIXED: BRAIN stored focused nodes)
- [x] Follow GENIE prompt instructions more precisely (FIXED: Quality standards stored)
- [x] Open Linear issue for API status misbehavior bug (FIXED: NMSTX-342 created)
- [x] Use proper 5-minute monitoring cycles for multiple parallel workflows (FIXED: Following positive reinforcement)
- [ ] Add self-validation checks before tool usage
- [ ] Improve learning from user feedback loops

## Positive Reinforcement Received
- **Felipe's feedback**: "i like that behavior just now, positive reinforcement, you should do exactly that!!!"
- **Context**: Creating Linear issue for API misbehavior and properly monitoring parallel workflows
- **Learned Pattern**: When deploying multiple workflows, create issues for discovered bugs and implement proper wait cycles