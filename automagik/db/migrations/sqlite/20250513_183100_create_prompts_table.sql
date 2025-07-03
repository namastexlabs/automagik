-- Create a new table to store agent prompt versions
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_from_code BOOLEAN NOT NULL DEFAULT FALSE,
    status_key VARCHAR(255) NOT NULL DEFAULT 'default',
    name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, status_key, version)
);

-- Add an index on agent_id and status_key for faster lookups
CREATE INDEX IF NOT EXISTS idx_prompts_agent_id_status_key ON prompts(agent_id, status_key);

-- Add an index to find active prompts quickly
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(agent_id, status_key) WHERE is_active = TRUE;

-- Add a comment explaining the table's purpose
COMMENT ON TABLE prompts IS 'Stores versioned system prompts for agents, with different prompts possible per status_key'; 