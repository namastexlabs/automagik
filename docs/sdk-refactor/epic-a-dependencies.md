# Epic A - Dependency & Build Plumbing

## Owner: @core-squad
## Branch: feature/sdk-migration
## Priority: FIRST - No dependencies

## Objective
Add the official `claude-code-sdk` Python package to the project dependencies and ensure it's properly installed and importable.

## Detailed Implementation Steps

### 1. Update pyproject.toml
```toml
# In the [project] dependencies section, add:
"claude-code-sdk>=0.0.10",  # No upper pin yet to allow patch updates
```

### 2. Verify Installation
```bash
# Run from project root
pip install -e .[dev]

# Test import in Python
python -c "import claude_code; print(claude_code.__version__)"
```

### 3. Update Development Dependencies (if needed)
Check if any dev dependencies conflict with the SDK requirements. The SDK requires:
- `anyio>=3.0.0`
- `pydantic>=2.0.0`

### 4. CI/CD Pipeline Updates
- Ensure GitHub Actions workflow installs the new dependency
- Update any Docker images or deployment scripts
- Verify poetry.lock or requirements.txt regeneration (if used)

## Success Criteria
- [ ] `claude-code-sdk>=0.0.10` added to pyproject.toml
- [ ] `pip install -e .[dev]` completes without errors
- [ ] `import claude_code` works in Python REPL
- [ ] CI pipeline passes with new dependency
- [ ] No version conflicts with existing dependencies

## Testing Commands
```bash
# Local verification
pytest tests/test_imports.py -v -k "test_claude_code_import"

# Full test suite still passes
pytest -n auto
```

## Notes
- This is the foundation for all other epics
- Must be merged before any other SDK work begins
- Keep the version constraint flexible for now
- Document any discovered incompatibilities

## Rollback Plan
If issues arise:
1. Remove the dependency from pyproject.toml
2. Run `pip install -e .[dev]` again
3. Revert the commit

## Files to Modify
- `/pyproject.toml`
- `/.github/workflows/tests.yml` (if needed)
- `/requirements-dev.txt` (if exists)