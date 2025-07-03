CREATE TABLE IF NOT EXISTS tool_executions (
    id TEXT PRIMARY KEY,
    tool_id TEXT,
    agent_name TEXT,
    session_id TEXT,
    parameters TEXT,
    context TEXT,
    status TEXT,
    result TEXT,
    error_message TEXT,
    execution_time_ms INTEGER,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_id ON tool_executions(tool_id);

CREATE INDEX IF NOT EXISTS idx_tool_executions_agent_name ON tool_executions(agent_name);

CREATE INDEX IF NOT EXISTS idx_tool_executions_session_id ON tool_executions(session_id);