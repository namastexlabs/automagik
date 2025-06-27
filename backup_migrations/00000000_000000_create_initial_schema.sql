-- Migration: Create initial database schema
-- Description: Creates base tables for users, agents, sessions, messages, and memories
-- Created at: Initial SQLite schema

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    phone_number TEXT,
    user_data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    model TEXT NOT NULL,
    description TEXT,
    version TEXT,
    config TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    run_id INTEGER DEFAULT 0,
    system_prompt TEXT,
    active_default_prompt_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    agent_id INTEGER,
    agent_name TEXT,
    name TEXT,
    platform TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    run_finished_at TEXT,
    message_count INTEGER DEFAULT 0
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    user_id TEXT,
    agent_id INTEGER,
    role TEXT NOT NULL,
    text_content TEXT,
    media_url TEXT,
    mime_type TEXT,
    message_type TEXT,
    raw_payload TEXT DEFAULT '{}',
    tool_calls TEXT DEFAULT '{}',
    tool_outputs TEXT DEFAULT '{}',
    system_prompt TEXT,
    user_feedback TEXT,
    flagged TEXT,
    context TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    content TEXT,
    session_id TEXT,
    user_id TEXT,
    agent_id INTEGER,
    read_mode TEXT,
    access TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

