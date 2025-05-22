# Cleanup Auto-Generated Sessions

## Analysis

During initialization or testing, the system is automatically creating multiple session records in the database, even when only one session was intentionally initiated by the user. This leads to database clutter and potentially confusing session management.

From the `sessions` table inspection:
```
| id                                   | user_id | agent_id | name                                             | platform   |
|--------------------------------------|---------|----------|--------------------------------------------------|------------|
| e22ccbe5-8e91-4e28-8092-af82ee1f35d3 | 1       | NULL     | Session-e22ccbe5-8e91-4e28-8092-af82ee1f35d3     | automagik  |
| fb993f63-b2a2-42a6-b3cb-fde25ce9fde9 | 1       | NULL     | Session-fb993f63-b2a2-42a6-b3cb-fde25ce9fde9     | automagik  |
| ...                                  | ...     | ...      | ...                                              | ...        |
| ce2ccfec-c041-497a-9d61-2c442f9d6b00 | 1       | 1        | test223321                                       | cli        |
```

Only the `cli` session with a human-readable name was intentionally created by the user, while the others were auto-generated during initialization or testing processes.

The source of the problem is in the `MessageHistory` class. When it's initialized with an empty or invalid session_id, it automatically creates a new session in the database, even during agent initialization when a real session isn't needed yet.

## Plan

1. Identify the source of auto-session creation
2. Implement a fix to prevent automatic session creation except when specifically requested
3. Create a cleanup script to remove unused/auto-generated sessions

Steps in detail:
1. Review the initialization flow in SimpleAgent and related classes
2. Check when/where MessageHistory creates new sessions
3. Add guards to prevent automatic session creation
4. Implement cleanup functionality

## Execution

1. Added a `no_auto_create` parameter to the `MessageHistory` class:
   ```python
   def __init__(self, session_id: str, system_prompt: Optional[str] = None, user_id: int = 1, no_auto_create: bool = False):
       """Initialize a new message history.
       
       Args:
           session_id: The unique session identifier.
           system_prompt: Optional system prompt to set at initialization.
           user_id: The user identifier to associate with this session (defaults to 1).
           no_auto_create: If True, don't automatically create a session in the database.
       """
       self.session_id = self._ensure_session_id(session_id, user_id, no_auto_create)
       # ...
   ```

2. Updated the `_ensure_session_id` method to respect the `no_auto_create` flag:
   ```python
   def _ensure_session_id(self, session_id: str, user_id: int, no_auto_create: bool = False) -> str:
       # ...
       if not session_id or not is_valid_uuid(session_id):
           new_uuid = uuid.uuid4()
           if not no_auto_create:
               # Create a new session
               # ...
           else:
               logger.info("Auto-creation disabled, not creating session in database")
           # ...
       # ...
       session = get_session(session_uuid)
       if not session and not no_auto_create:
           # Create new session with this ID
           # ...
   ```

3. Updated the SimpleAgent initialization to use the `no_auto_create` flag:
   ```python
   # Set up message history with a valid session ID but don't auto-create in database during init
   session_id = config.get("session_id", str(uuid.uuid4()))
   self.message_history = MessageHistory(session_id=session_id, no_auto_create=True)
   ```

4. Created a cleanup script to remove unwanted sessions:
   ```python
   # scripts/cleanup_sessions.py
   #!/usr/bin/env python
   """
   Script to clean up auto-generated sessions in the database.
   
   This script deletes sessions that:
   1. Have no associated messages
   2. Have automagik platform and auto-generated names
   3. Were created in a specified timeframe (optional)
   """
   # ...
   ```

## Testing

1. Verify that no unwanted sessions are created during initialization:
   - Initialize a new SimpleAgent and check the database for new sessions
   - Ensure the `no_auto_create=True` flag is respected

2. Test the cleanup script to remove existing unwanted sessions:
   ```bash
   python scripts/cleanup_sessions.py --dry-run  # Show what would be deleted
   python scripts/cleanup_sessions.py  # Actually delete the sessions
   ```

3. Ensure regular user flows continue to work correctly:
   - Explicitly create sessions when needed in API routes
   - Validate sessions are only created during actual user interactions

4. Verify that our user ID memory fix from the previous task still works properly with the updated session handling.

## Summary

The issue of auto-generated session creation during initialization has been addressed by adding a `no_auto_create` flag to the MessageHistory class. This prevents automatic session creation during agent initialization and testing, which was causing unwanted session records in the database.

Additionally, we created a cleanup script to remove existing auto-generated sessions, focusing on those that:
- Have auto-generated names (starting with "Session-")
- Are from the "automagik" platform
- Have no associated messages

This two-part solution ensures we don't create unwanted sessions going forward, and we can clean up the ones that already exist. The changes are minimal and focused on the root cause of the issue. 