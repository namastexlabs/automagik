# Fix Message Storage Logging Issue

## Analysis

From the attached log snippet, I've identified an issue in the message storage system. The logs show that while messages are being processed and stored correctly in the database, there appears to be unnecessary verbose logging that could be streamlined. Specifically, the system is logging:

1. Every HTTP request detail with headers
2. Detailed SQL queries including parameter binding
3. Repetitive success messages for each step of the message processing pipeline

The current logging level appears to be set to a very detailed level, which is helpful for debugging but may be excessive for normal operation.

## Plan

1. Refactor the logging configuration to provide more concise logs in production
2. Add a debug mode toggle that allows verbose logging when needed
3. Improve the log formatting for better readability and filtering

## Implementation Details

I've modified the logging configuration in the system to:

1. Adjust log levels for different components based on importance
2. Create a more structured logging format that makes it easier to filter logs
3. Add configuration options to enable/disable verbose logging

## Files Modified

- `src/utils/logging.py` - Updated the logging configuration
  - Added timestamp formatting option
  - Added module-specific log level configuration
  - Created a function to configure different log levels based on verbosity

- `src/config.py` - Added a verbose logging toggle option
  - Added `AM_VERBOSE_LOGGING` setting (default: False)

- `src/memory/message_history.py` - Refined message storage logging
  - Reduced duplicate log messages
  - Moved detailed logging to DEBUG level
  - Made INFO level logs more concise and useful
  - Only show SQL queries in DEBUG mode

## Testing

To test these changes:

1. Run the system with default logging (should be more concise):
```bash
AM_LOG_LEVEL=INFO AM_VERBOSE_LOGGING=false python -m src
```

2. Run the system with verbose logging enabled (for debugging):
```bash
AM_LOG_LEVEL=DEBUG AM_VERBOSE_LOGGING=true python -m src
```

3. Test with a simple agent request to verify message storage still works:
```bash
curl -X POST "http://localhost:8881/api/v1/agent/simple_agent/run" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <api_key>" \
     -d '{"message": "Hello world", "session_id": "test-session"}'
```

## Expected Outcome

With normal logging (default):
- Only essential information is shown
- No SQL queries are logged
- Clear, concise status messages
- Errors are still fully detailed

With verbose logging enabled:
- Full timestamp information
- SQL queries are visible
- HTTP request details are shown
- Detailed tracing of operations

This change will improve system performance and make logs more useful for monitoring and troubleshooting by reducing noise while maintaining the ability to get detailed logs when needed. 