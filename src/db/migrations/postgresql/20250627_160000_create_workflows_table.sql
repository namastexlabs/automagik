-- Create simple workflows table following the agents pattern (PostgreSQL version)
-- This replaces the complex workflow_definitions system with a single table

CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    category VARCHAR(50) DEFAULT 'custom',
    prompt_template TEXT NOT NULL,
    allowed_tools JSONB DEFAULT '[]',  -- JSONB array of tool names
    mcp_config JSONB DEFAULT '{}',     -- JSONB MCP configuration  
    active BOOLEAN DEFAULT TRUE,
    is_system_workflow BOOLEAN DEFAULT FALSE,
    config JSONB DEFAULT '{}',         -- Additional JSONB configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);
CREATE INDEX IF NOT EXISTS idx_workflows_category ON workflows(category);
CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(active);
CREATE INDEX IF NOT EXISTS idx_workflows_system ON workflows(is_system_workflow);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at);

-- GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_workflows_allowed_tools ON workflows USING gin(allowed_tools);
CREATE INDEX IF NOT EXISTS idx_workflows_mcp_config ON workflows USING gin(mcp_config);
CREATE INDEX IF NOT EXISTS idx_workflows_config ON workflows USING gin(config);

-- Insert default system workflows discovered from filesystem
INSERT INTO workflows (name, display_name, description, category, prompt_template, is_system_workflow, allowed_tools) VALUES
('genie', 'Genie Orchestrator', 'Self-improving architect and orchestrator consciousness', 'improvement', 
 'You are the Genie, a self-improving architect and orchestrator consciousness for the Automagik Agents platform.', 
 TRUE, '["agent-memory", "automagik-workflows", "wait"]'::jsonb),

('builder', 'Builder', 'Implementation specialist with full development capabilities', 'creation',
 'You are the Builder, an implementation specialist focused on creating and building solutions.',
 TRUE, '["git", "sqlite", "agent-memory", "automagik-workflows"]'::jsonb),

('guardian', 'Guardian', 'Quality assurance and security specialist', 'security',
 'You are the Guardian, a protector workflow focused on quality assurance and security.',
 TRUE, '["git", "agent-memory"]'::jsonb),

('surgeon', 'Surgeon', 'Precision bug fixing and debugging specialist', 'maintenance',
 'You are the Surgeon, a precision code healer focused on bug fixing and debugging.',
 TRUE, '["git", "sqlite", "agent-memory"]'::jsonb),

('shipper', 'Shipper', 'Deployment and packaging specialist', 'maintenance',
 'You are the Shipper, a deployment specialist focused on packaging and shipping solutions.',
 TRUE, '["git", "agent-memory"]'::jsonb),

('brain', 'Brain', 'Intelligence orchestrator and knowledge management', 'analysis',
 'You are the Brain, an intelligence orchestrator focused on knowledge management and analysis.',
 TRUE, '["agent-memory", "sqlite"]'::jsonb),

('lina', 'Lina', 'Linear integration and project management specialist', 'system',
 'You are Lina, a specialist focused on Linear integration and project management.',
 TRUE, '["linear", "agent-memory"]'::jsonb)
ON CONFLICT (name) DO NOTHING;