-- Create comprehensive workflow management tables for database-driven workflows (SQLite version)
-- This migration enables dynamic workflow creation and management

-- Main workflow definitions table
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    description TEXT,
    category TEXT DEFAULT 'custom',
    version INTEGER DEFAULT 1,
    prompt_template TEXT NOT NULL,
    system_prompt TEXT,
    is_active INTEGER DEFAULT 1,
    is_system_workflow INTEGER DEFAULT 0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CHECK (category IN ('system', 'custom', 'security', 'maintenance', 'analysis', 'creation', 'improvement')),
    CHECK (version > 0)
);

-- Workflow tools configuration table
CREATE TABLE IF NOT EXISTS workflow_tools (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL DEFAULT 'allowed',
    configuration TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CHECK (tool_type IN ('allowed', 'disallowed', 'required')),
    UNIQUE(workflow_id, tool_name)
);

-- Workflow MCP configurations table
CREATE TABLE IF NOT EXISTS workflow_mcp_configs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    mcp_server_name TEXT NOT NULL,
    configuration TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workflow_id, mcp_server_name)
);

-- Workflow versions table for change tracking
CREATE TABLE IF NOT EXISTS workflow_versions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    prompt_template TEXT NOT NULL,
    tool_configuration TEXT NOT NULL DEFAULT '{}',
    mcp_configuration TEXT DEFAULT '{}',
    change_description TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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

INSERT OR IGNORE INTO workflow_definitions (id, name, display_name, description, category, prompt_template, is_system_workflow) VALUES
('wf_genie', 'genie', 'Genie Orchestrator', 'Self-improving architect and orchestrator consciousness', 'improvement', 
 'You are the Genie, a self-improving architect and orchestrator consciousness for the Automagik Agents platform.', 1),

('wf_builder', 'builder', 'Builder', 'Implementation specialist with full development capabilities', 'creation', 
 'You are the Builder, an implementation specialist focused on creating and building solutions.', 1),

('wf_guardian', 'guardian', 'Guardian', 'Quality assurance and security specialist', 'security', 
 'You are the Guardian, a protector workflow focused on quality assurance and security.', 1),

('wf_surgeon', 'surgeon', 'Surgeon', 'Precision bug fixing and debugging specialist', 'maintenance', 
 'You are the Surgeon, a precision code healer focused on bug fixing and debugging.', 1),

('wf_shipper', 'shipper', 'Shipper', 'Deployment and packaging specialist', 'maintenance', 
 'You are the Shipper, a deployment specialist focused on packaging and shipping solutions.', 1),

('wf_brain', 'brain', 'Brain', 'Intelligence orchestrator and knowledge management', 'analysis', 
 'You are the Brain, an intelligence orchestrator focused on knowledge management and analysis.', 1),

('wf_lina', 'lina', 'Lina', 'Linear integration and project management specialist', 'system', 
 'You are Lina, a specialist focused on Linear integration and project management.', 1);

-- Insert default tool configurations for system workflows
-- These reflect the current allowed_tools.json configurations

-- Genie tools (read-only, orchestration focused)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_genie_memory', 'wf_genie', 'agent-memory', 'allowed'),
('wt_genie_workflow', 'wf_genie', 'automagik-workflows', 'allowed'),
('wt_genie_wait', 'wf_genie', 'wait', 'allowed');

-- Builder tools (full development stack)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_builder_git', 'wf_builder', 'git', 'allowed'),
('wt_builder_sqlite', 'wf_builder', 'sqlite', 'allowed'),
('wt_builder_memory', 'wf_builder', 'agent-memory', 'allowed'),
('wt_builder_workflow', 'wf_builder', 'automagik-workflows', 'allowed');

-- Guardian tools (testing and validation)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_guardian_git', 'wf_guardian', 'git', 'allowed'),
('wt_guardian_memory', 'wf_guardian', 'agent-memory', 'allowed');

-- Surgeon tools (debugging and analysis)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_surgeon_git', 'wf_surgeon', 'git', 'allowed'),
('wt_surgeon_sqlite', 'wf_surgeon', 'sqlite', 'allowed'),
('wt_surgeon_memory', 'wf_surgeon', 'agent-memory', 'allowed');

-- Brain tools (analysis and memory)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_brain_memory', 'wf_brain', 'agent-memory', 'required'),
('wt_brain_sqlite', 'wf_brain', 'sqlite', 'allowed');

-- Lina tools (Linear integration)
INSERT OR IGNORE INTO workflow_tools (id, workflow_id, tool_name, tool_type) VALUES
('wt_lina_linear', 'wf_lina', 'linear', 'required'),
('wt_lina_memory', 'wf_lina', 'agent-memory', 'allowed');