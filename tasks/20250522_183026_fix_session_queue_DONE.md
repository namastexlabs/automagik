# Task: Fix Session Queue Cancellation and Merging
**Status**: Completed

## Analysis
- [x] Requirements
  - [x] When two messages arrive for same session quickly, first should be cancelled
  - [x] Only one processor call should happen with merged messages
  - [x] First caller should receive CancelledError
- [x] Challenges
  - [x] Race condition between worker loop and cancellation logic
  - [x] Worker doesn't properly handle future cancellation
  - [x] Message merging logic has timing issues
- [x] Dependencies
  - [x] Test: test_session_queue_cancels_prior_and_merges

## Plan
- [x] Step 1: Fix worker loop cancellation handling
  - [x] Make worker check if current future is cancelled before processing
  - [x] Properly handle CancelledError in worker
- [x] Step 2: Fix message merging logic
  - [x] Ensure atomic message replacement in queue
  - [x] Handle race conditions properly
- [x] Step 3: Test the fix
  - [x] Run the failing test to verify it passes

## Execution
- [x] Implementation 1: Fix session queue logic
  - [x] Files modified: src/utils/session_queue.py

## Summary
- [x] Files modified: `src/utils/session_queue.py` (lines 1-241)
- [x] Dependencies added/changed: None
- [x] Edge cases considered: Race conditions, timing issues
- [x] Known limitations: None
- [x] Future impact points: All session-based processing 