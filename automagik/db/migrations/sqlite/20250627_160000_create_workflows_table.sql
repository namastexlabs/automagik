-- Create simple workflows table following the agents pattern
-- This replaces the complex workflow_definitions system with a single table

CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    category VARCHAR(50) DEFAULT 'custom',
    prompt_template TEXT NOT NULL,
    allowed_tools TEXT DEFAULT '[]',  -- JSON array of tool names
    mcp_config TEXT DEFAULT '{}',     -- JSON MCP configuration
    active BOOLEAN DEFAULT TRUE,
    is_system_workflow BOOLEAN DEFAULT FALSE,
    config TEXT DEFAULT '{}',         -- Additional JSON configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);
CREATE INDEX IF NOT EXISTS idx_workflows_category ON workflows(category);
CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(active);
CREATE INDEX IF NOT EXISTS idx_workflows_system ON workflows(is_system_workflow);

-- Insert default system workflows discovered from filesystem
INSERT OR IGNORE INTO workflows (name, display_name, description, category, prompt_template, is_system_workflow, allowed_tools) VALUES
('genie', 'Genie Orchestrator', 'Self-improving architect and orchestrator consciousness', 'improvement', 
 'You are the Genie, a self-improving architect and orchestrator consciousness for the Automagik Agents platform.', 
 TRUE, '["agent-memory", "automagik-workflows", "wait"]'),

('builder', 'Builder', 'Implementation specialist with full development capabilities', 'creation',
 'You are the Builder, an implementation specialist focused on creating and building solutions.',
 TRUE, '["git", "sqlite", "agent-memory", "automagik-workflows"]'),

('guardian', 'Guardian', 'Quality assurance and security specialist', 'security',
 'You are the Guardian, a protector workflow focused on quality assurance and security.',
 TRUE, '["git", "agent-memory"]'),

('surgeon', 'Surgeon', 'Precision bug fixing and debugging specialist', 'maintenance',
 'You are the Surgeon, a precision code healer focused on bug fixing and debugging.',
 TRUE, '["git", "sqlite", "agent-memory"]'),

('shipper', 'Shipper', 'Deployment and packaging specialist', 'maintenance',
 'You are the Shipper, a deployment specialist focused on packaging and shipping solutions.',
 TRUE, '["git", "agent-memory"]'),

('brain', 'Brain', 'Intelligence orchestrator and knowledge management', 'analysis',
 'You are the Brain, an intelligence orchestrator focused on knowledge management and analysis.',
 TRUE, '["agent-memory", "sqlite"]'),

('lina', 'Lina', 'Linear integration and project management specialist', 'system',
 'You are Lina, a specialist focused on Linear integration and project management.',
 TRUE, '["linear", "agent-memory"]');