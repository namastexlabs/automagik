# Agent Self-Improvement: Critical Execution Patterns

## 🚨 Critical Agent Behavior Gaps Identified

Based on workflow kill system implementation, two critical patterns need improvement:

### 1. BUILDER Commit Gap ❌
**Issue**: BUILDER implemented emergency kill functionality but didn't commit
**Impact**: User had to manually request commit, breaking workflow autonomy
**Required Fix**: All implementation agents must commit their work

### 2. GUARDIAN Execution Pattern Gap ❌  
**Issue**: GUARDIAN attempting direct Python execution instead of `uv run`
**Repository Rule**: This repo NEVER runs Python directly - always `uv run`
**Required Fix**: All agents must use `uv run python` pattern

---

## 🔧 Required Agent Behavior Updates

### Git Workflow Completion (BUILDER, SURGEON, etc.)
```bash
# REQUIRED PATTERN - No exceptions:
1. Implement changes
2. Run validation/tests  
3. git add .
4. git commit -m "feat: descriptive message following team standards"
5. Report completion with commit hash
```

### Python Execution Standard (ALL AGENTS)
```bash
# ❌ WRONG - Never use:
python script.py
python -m module
pytest
mypy

# ✅ CORRECT - Always use:
uv run python script.py  
uv run python -m module
uv run pytest
uv run mypy
```

---

## 📝 Updated Dispatch Text Requirements

### For Implementation Agents (BUILDER, SURGEON, etc.)
Add these requirements to all dispatch texts:

```markdown
## CRITICAL EXECUTION REQUIREMENTS

### Git Workflow Completion (MANDATORY)
After implementing changes, you MUST:
1. Run validation: `uv run pytest` or appropriate tests
2. Stage changes: `git add .`  
3. Commit work: `git commit -m "feat: descriptive message"`
4. Report commit hash in completion summary

### Python Execution Pattern (MANDATORY)
This repository NEVER runs Python directly. Always use:
- `uv run python script.py` (not `python script.py`)
- `uv run python -m module` (not `python -m module`)  
- `uv run pytest` (not `pytest`)
- `uv run mypy` (not `mypy`)

FAILURE TO FOLLOW THESE PATTERNS WILL CAUSE WORKFLOW FAILURES.
```

### For Validation Agents (GUARDIAN, etc.)
```markdown
## VALIDATION REQUIREMENTS

### Verify Implementation Completion
- Confirm implementation agent committed their work
- Validate commit message follows team standards
- Check that all changes are properly staged and committed

### Use Repository Execution Patterns
- All Python execution must use `uv run python`
- All tool execution must use `uv run <tool>`
- Never run Python tools directly without `uv run`
```

---

## 🎯 GUARDIAN Recovery Guidance

Since GUARDIAN is currently running, here's immediate recovery guidance:

### If GUARDIAN Encounters Python Execution Issues:
```markdown
GUARDIAN - EXECUTION PATTERN CORRECTION:

If you encounter command failures, ensure you're using repository execution patterns:

✅ CORRECT USAGE:
```bash
uv run python test_script.py
uv run python -m pytest tests/
uv run python -m mypy src/
uv run python -c "import sys; print(sys.version)"
```

❌ INCORRECT USAGE (will fail):
```bash
python test_script.py
pytest tests/
mypy src/
python -c "import sys; print(sys.version)"
```

This repository requires `uv run` for ALL Python operations.
```

---

## 🧠 Self-Improvement Integration

### GENIE Orchestration Updates Needed
1. **Dispatch Text Enhancement**: Add execution patterns to all agent dispatch texts
2. **Completion Verification**: Validate agents completed git workflow
3. **Pattern Enforcement**: Flag agents that don't follow repository standards

### Future Agent Training
1. **Repository Onboarding**: Include execution patterns in agent context
2. **Validation Chains**: Subsequent agents verify previous agent completion
3. **Error Recovery**: Provide correction guidance for common pattern violations

### Team Standards Applied
- **Felipe's Security**: Proper git workflow ensures audit trail and validation
- **Cezar's Architecture**: Consistent execution patterns maintain system reliability
- **Repository Standards**: `uv run` pattern is non-negotiable for environment consistency

---

## 📊 Implementation Priority

### Immediate (Current GUARDIAN)
- Provide execution pattern correction if GUARDIAN encounters failures
- Ensure GUARDIAN validates BUILDER's work was committed properly

### Short-term (Next Orchestrations)
- Update all dispatch texts with execution pattern requirements
- Add completion verification steps to workflow sequences

### Long-term (Systematic Improvement)
- Integrate execution patterns into agent training/context
- Build automatic validation of agent completion patterns
- Create repository-specific agent behavior guidelines

This self-improvement cycle ensures agents become more autonomous and reliable while following established repository standards consistently.