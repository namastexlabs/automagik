# Message Injection Code Cleanup Plan

## Overview
This cleanup plan removes all unnecessary message injection code before implementing the simpler stream-json input approach. The injection system was overengineering since Claude Code already supports `--input-format stream-json`.

## Cleanup Order (Follow Sequentially)

### Phase 1: Remove Test Files First (Prevents Breaking Tests)
1. **Delete entire test files:**
   ```bash
   rm test_message_injection.py
   ```

2. **Remove test methods from `test_workflows_comprehensive.py`:**
   - Lines 206-261: `test_message_injection()` method
   - Lines 263-317: `test_multiple_message_injection()` method
   - Lines 434-488: `test_rapid_message_injection()` method
   - Lines 528-529: Test execution calls
   - Line 543: Rapid injection test call

### Phase 2: Remove Core Implementation Files
3. **Delete the entire message injection module:**
   ```bash
   rm automagik/agents/claude_code/sdk_message_injection.py
   ```

### Phase 3: Clean SDK Execution Strategies
4. **Edit `automagik/agents/claude_code/sdk_execution_strategies.py`:**
   - **Remove import:** Line 28
     ```python
     from .sdk_message_injection import SDKMessageInjector  # DELETE THIS LINE
     ```
   
   - **Remove instance creation:** Line 70
     ```python
     self.message_injector = SDKMessageInjector()  # DELETE THIS LINE
     ```
   
   - **Remove methods:** Lines 76-93
     ```python
     async def _check_and_process_pending_messages(...)  # DELETE ENTIRE METHOD
     async def _build_enhanced_prompt_with_injected_messages(...)  # DELETE ENTIRE METHOD
     ```
   
   - **Remove injection logic:** Lines 248-301
     - Delete the entire block checking for and processing injected messages
     - Remove calls to `_check_and_process_pending_messages`
     - Remove calls to `_build_enhanced_prompt_with_injected_messages`
   
   - **Remove duplicate method:** Lines 843-889
     ```python
     async def _build_enhanced_prompt_with_injected_messages(...)  # DELETE DUPLICATE
     ```

### Phase 4: Remove API Endpoint
5. **Edit `automagik/api/routes/claude_code_routes.py`:**
   - **Remove class:** Lines 903-913
     ```python
     class InjectMessageRequest(BaseModel):  # DELETE ENTIRE CLASS
     ```
   
   - **Remove endpoint:** Lines 914-1103
     ```python
     @router.post("/run/{run_id}/inject-message")  # DELETE ENTIRE FUNCTION
     async def inject_message_to_running_workflow(...):
     ```

### Phase 5: Update Documentation
6. **Update `FRONTEND_INTEGRATION.md`:**
   - Remove all sections mentioning message injection
   - Replace with references to stream-json input

7. **Keep `streaminput.md`:**
   - This documents why we removed injection and how to use stream-json

### Phase 6: Clean Up Test Reports (Optional)
8. **Reset test report files:**
   ```bash
   # These contain old test results, can be regenerated
   rm test_report*.json
   ```

## Verification Checklist

After cleanup, verify:
- [ ] No imports of `SDKMessageInjector` remain
- [ ] No references to `.pending_messages.json` exist
- [ ] No `/inject-message` endpoint in API routes
- [ ] No message injection tests remain
- [ ] Code still compiles without errors
- [ ] Existing workflows still function

## Git Commands for Cleanup

```bash
# Create cleanup branch
git checkout -b cleanup-message-injection

# After making all changes
git add -A
git commit -m "refactor: remove message injection code in favor of stream-json input

- Removed SDKMessageInjector class and module
- Removed /inject-message API endpoint  
- Removed message injection tests
- Cleaned up sdk_execution_strategies.py
- Updated documentation

Message injection was overengineering since Claude Code already supports
--input-format stream-json for real-time input."
```

## Files Summary

**Files to Delete:**
- `automagik/agents/claude_code/sdk_message_injection.py` (entire file)
- `test_message_injection.py` (entire file)

**Files to Edit:**
- `automagik/agents/claude_code/sdk_execution_strategies.py` (remove imports and methods)
- `automagik/api/routes/claude_code_routes.py` (remove endpoint and class)
- `test_workflows_comprehensive.py` (remove test methods)
- `FRONTEND_INTEGRATION.md` (update docs)

**Total Lines to Remove:** ~800 lines of code

## Why This Cleanup Matters

1. **Reduces Complexity:** Removes ~800 lines of unnecessary code
2. **Eliminates Tech Debt:** Prevents confusion about which approach to use
3. **Simplifies Maintenance:** One less system to maintain and debug
4. **Improves Performance:** No file polling or queue management overhead
5. **Follows KISS Principle:** Uses existing CLI functionality instead of custom solution

## Next Steps After Cleanup

Once cleanup is complete:
1. Implement simple stdin monitoring in `sdk_execution_strategies.py`
2. Test with `--input-format stream-json` flag
3. Document usage examples
4. Consider simple HTTP wrapper if needed