-- Create comprehensive workflow management tables for database-driven workflows (PostgreSQL version)
-- This migration enables dynamic workflow creation and management

-- Main workflow definitions table
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    category VARCHAR(50) DEFAULT 'custom',
    version INTEGER DEFAULT 1,
    prompt_template TEXT NOT NULL,
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_system_workflow BOOLEAN DEFAULT FALSE,
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (category IN ('system', 'custom', 'security', 'maintenance', 'analysis', 'creation', 'improvement')),
    CHECK (version > 0)
);

-- Workflow tools configuration table
CREATE TABLE IF NOT EXISTS workflow_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    tool_name VARCHAR(200) NOT NULL,
    tool_type VARCHAR(50) NOT NULL DEFAULT 'allowed',
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (tool_type IN ('allowed', 'disallowed', 'required')),
    UNIQUE(workflow_id, tool_name)
);

-- Workflow MCP configurations table
CREATE TABLE IF NOT EXISTS workflow_mcp_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    mcp_server_name VARCHAR(200) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workflow_id, mcp_server_name)
);

-- Workflow versions table for change tracking
CREATE TABLE IF NOT EXISTS workflow_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    prompt_template TEXT NOT NULL,
    tool_configuration JSONB NOT NULL DEFAULT '{}',
    mcp_configuration JSONB DEFAULT '{}',
    change_description TEXT,
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (version_number > 0),
    UNIQUE(workflow_id, version_number)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_name ON workflow_definitions(name);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_category ON workflow_definitions(category);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_active ON workflow_definitions(is_active);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_system ON workflow_definitions(is_system_workflow);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_created_at ON workflow_definitions(created_at);

CREATE INDEX IF NOT EXISTS idx_workflow_tools_workflow_id ON workflow_tools(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_tools_tool_name ON workflow_tools(tool_name);
CREATE INDEX IF NOT EXISTS idx_workflow_tools_tool_type ON workflow_tools(tool_type);

CREATE INDEX IF NOT EXISTS idx_workflow_mcp_configs_workflow_id ON workflow_mcp_configs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_mcp_configs_server_name ON workflow_mcp_configs(mcp_server_name);
CREATE INDEX IF NOT EXISTS idx_workflow_mcp_configs_active ON workflow_mcp_configs(is_active);

CREATE INDEX IF NOT EXISTS idx_workflow_versions_workflow_id ON workflow_versions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_versions_version_number ON workflow_versions(version_number);
CREATE INDEX IF NOT EXISTS idx_workflow_versions_created_at ON workflow_versions(created_at);

-- Insert default system workflows from existing file-based definitions
-- These serve as the foundation for the database-driven system

INSERT INTO workflow_definitions (name, display_name, description, category, prompt_template, is_system_workflow) VALUES
('genie', 'Genie Orchestrator', 'Self-improving architect and orchestrator consciousness', 'improvement', 
 'You are the Genie, a self-improving architect and orchestrator consciousness for the Automagik Agents platform.', TRUE),

('builder', 'Builder', 'Implementation specialist with full development capabilities', 'creation', 
 'You are the Builder, an implementation specialist focused on creating and building solutions.', TRUE),

('guardian', 'Guardian', 'Quality assurance and security specialist', 'security', 
 'You are the Guardian, a protector workflow focused on quality assurance and security.', TRUE),

('surgeon', 'Surgeon', 'Precision bug fixing and debugging specialist', 'maintenance', 
 'You are the Surgeon, a precision code healer focused on bug fixing and debugging.', TRUE),

('shipper', 'Shipper', 'Deployment and packaging specialist', 'maintenance', 
 'You are the Shipper, a deployment specialist focused on packaging and shipping solutions.', TRUE),

('brain', 'Brain', 'Intelligence orchestrator and knowledge management', 'analysis', 
 'You are the Brain, an intelligence orchestrator focused on knowledge management and analysis.', TRUE),

('lina', 'Lina', 'Linear integration and project management specialist', 'system', 
 'You are Lina, a specialist focused on Linear integration and project management.', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Insert default tool configurations for system workflows
-- These reflect the current allowed_tools.json configurations

-- Get workflow IDs for tool assignments
WITH workflow_ids AS (
    SELECT id, name FROM workflow_definitions WHERE is_system_workflow = TRUE
)

-- Genie tools (read-only, orchestration focused)
INSERT INTO workflow_tools (workflow_id, tool_name, tool_type)
SELECT id, 'agent-memory', 'allowed' FROM workflow_ids WHERE name = 'genie'
UNION ALL
SELECT id, 'automagik-workflows', 'allowed' FROM workflow_ids WHERE name = 'genie'
UNION ALL
SELECT id, 'wait', 'allowed' FROM workflow_ids WHERE name = 'genie'

-- Builder tools (full development stack)
UNION ALL
SELECT id, 'git', 'allowed' FROM workflow_ids WHERE name = 'builder'
UNION ALL
SELECT id, 'sqlite', 'allowed' FROM workflow_ids WHERE name = 'builder'
UNION ALL
SELECT id, 'agent-memory', 'allowed' FROM workflow_ids WHERE name = 'builder'
UNION ALL
SELECT id, 'automagik-workflows', 'allowed' FROM workflow_ids WHERE name = 'builder'

-- Guardian tools (testing and validation)
UNION ALL
SELECT id, 'git', 'allowed' FROM workflow_ids WHERE name = 'guardian'
UNION ALL
SELECT id, 'agent-memory', 'allowed' FROM workflow_ids WHERE name = 'guardian'

-- Surgeon tools (debugging and analysis)
UNION ALL
SELECT id, 'git', 'allowed' FROM workflow_ids WHERE name = 'surgeon'
UNION ALL
SELECT id, 'sqlite', 'allowed' FROM workflow_ids WHERE name = 'surgeon'
UNION ALL
SELECT id, 'agent-memory', 'allowed' FROM workflow_ids WHERE name = 'surgeon'

-- Brain tools (analysis and memory)
UNION ALL
SELECT id, 'agent-memory', 'required' FROM workflow_ids WHERE name = 'brain'
UNION ALL
SELECT id, 'sqlite', 'allowed' FROM workflow_ids WHERE name = 'brain'

-- Lina tools (Linear integration)
UNION ALL
SELECT id, 'linear', 'required' FROM workflow_ids WHERE name = 'lina'
UNION ALL
SELECT id, 'agent-memory', 'allowed' FROM workflow_ids WHERE name = 'lina'

ON CONFLICT (workflow_id, tool_name) DO NOTHING;