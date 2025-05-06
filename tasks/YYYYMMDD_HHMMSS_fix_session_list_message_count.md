# Task: Fix Message Count in List Sessions Endpoint

**ID**: {YYYYMMDD_HHMMSS}
**Status**: Open
**Priority**: High
**Assignee**: Unassigned
**Reporter**: User
**Created Date**: {YYYY-MM-DD}
**Last Updated**: {YYYY-MM-DD}

## Description

The API endpoint for listing all sessions (likely `/api/v1/sessions` or `/api/v1/chats`) consistently returns `message_count: 0` for every session in the response. This is incorrect as sessions often contain messages. This bug prevents clients from accurately determining the number of messages in a session without fetching the full session details.

**Example of Incorrect Output:**
```json
{
  "sessions": [
    {
      "session_id": "3af18207-6319-4684-a80f-b545b69ad8d3",
      "user_id": "14daad45-c83c-489d-bfa9-6fafab7c0b28",
      "agent_id": 1,
      "session_name": "manychat-14daad45-c83c-489d-bfa9-6fafab7c0b28",
      "created_at": "2025-04-28T19:30:17.262908Z",
      "last_updated": "2025-04-28T19:30:17.262908Z",
      "message_count": 0, // Incorrectly 0
      "agent_name": null,
      "session_origin": null
    },
    // ... other sessions with message_count: 0
  ],
  "total": 187,
  "page": 1,
  "page_size": 50,
  "total_pages": 4
}
```

## Root Cause Analysis

Based on investigation:
1.  The `get_sessions` function in `src/api/controllers/session_controller.py` hardcodes `message_count=0` when creating `SessionInfo` objects.
    ```python
    # src/api/controllers/session_controller.py
    session_infos.append(SessionInfo(
        # ... other fields
        message_count=0,  # BUG: Hardcoded to 0
        # ... other fields
    ))
    ```
2.  The underlying repository function `list_sessions` in `src/db/repository/session.py` only queries the `sessions` table (`SELECT * FROM sessions`) and does not perform a join or subquery to count messages for each session.

## Proposed Solution

1.  **Modify `src/db/repository/session.py` -> `list_sessions` function:**
    *   Change the SQL query to perform a `LEFT JOIN` with the `messages` table.
    *   Use `COUNT(m.id) AS message_count` (or a similar aggregate on the messages table) to get the message count for each session.
    *   Ensure the `GROUP BY` clause includes all selected columns from the `sessions` table to make the `COUNT` aggregate work correctly per session.
    *   The modified function should return `Session` objects that now include or can be adapted to include this `message_count`.

2.  **Modify `src/api/controllers/session_controller.py` -> `get_sessions` function:**
    *   When iterating through the `Session` objects returned by the modified `list_sessions` function, correctly access the `message_count`.
    *   Update the instantiation of `SessionInfo` to use the actual message count:
        ```python
        message_count=session.message_count, // Or session.get('message_count', 0)
        ```

## Files to Modify

*   `am-agents-labs/src/db/repository/session.py`
*   `am-agents-labs/src/api/controllers/session_controller.py`

## Acceptance Criteria

*   The `/api/v1/sessions` (or equivalent) endpoint must return the correct `message_count` for each session.
*   The count should accurately reflect the number of messages stored in the `messages` table for that `session_id`.
*   Sessions with no messages should correctly show `message_count: 0`.
*   Pagination and filtering for the list sessions endpoint should continue to function correctly.

## Impact / Risk

*   **Low Risk**: The change primarily involves modifying SQL queries and data mapping. Care should be taken to ensure the SQL query is performant, especially with a large number of sessions or messages.
*   **Positive Impact**: Clients will receive accurate message counts, improving UI/UX and data consistency.

## Test Plan

1.  Create several test sessions with varying numbers of messages (0, 1, 5, many).
2.  Call the "list all sessions" API endpoint.
3.  Verify that the `message_count` for each test session in the JSON response is correct.
4.  Verify that pagination still works as expected.
5.  Verify that filtering (if any) still works as expected alongside the message count.

## Dependencies

*   None explicitly identified, but relies on the existing database schema for `sessions` and `messages` tables.

## Notes

*   Consider the performance implications of the JOIN operation if the `messages` table is very large. An alternative, though potentially less efficient for a list view, would be to make a separate count query per session (N+1 problem). 