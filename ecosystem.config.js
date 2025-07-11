// ===================================================================
// 🎭 AM-Agents-Labs - Standalone PM2 Configuration
// ===================================================================
// This file enables am-agents-labs to run independently
// It extracts the same configuration from the central ecosystem

const path = require('path');
const fs = require('fs');

// Get the current directory (am-agents-labs)
const PROJECT_ROOT = __dirname;

/**
 * Extract version from pyproject.toml file using standardized approach
 * @param {string} projectPath - Path to the project directory
 * @returns {string} Version string or 'unknown'
 */
function extractVersionFromPyproject(projectPath) {
  const pyprojectPath = path.join(projectPath, 'pyproject.toml');
  
  if (!fs.existsSync(pyprojectPath)) {
    return 'unknown';
  }
  
  try {
    const content = fs.readFileSync(pyprojectPath, 'utf8');
    
    // Standard approach: Static version in [project] section
    const projectVersionMatch = content.match(/\[project\][\s\S]*?version\s*=\s*["']([^"']+)["']/);
    if (projectVersionMatch) {
      return projectVersionMatch[1];
    }
    
    // Fallback: Simple version = "..." pattern anywhere in file
    const simpleVersionMatch = content.match(/^version\s*=\s*["']([^"']+)["']/m);
    if (simpleVersionMatch) {
      return simpleVersionMatch[1];
    }
    
    return 'unknown';
  } catch (error) {
    console.warn(`Failed to read version from ${pyprojectPath}:`, error.message);
    return 'unknown';
  }
}

// Load environment variables from .env file if it exists
const envPath = path.join(PROJECT_ROOT, '.env');
let envVars = {};
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const [key, value] = line.split('=');
    if (key && value) {
      envVars[key.trim()] = value.trim().replace(/^["']|["']$/g, '');
    }
  });
}

module.exports = {
  apps: [
    {
      name: 'am-agents-labs',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/python',
      args: '-m automagik',
      interpreter: 'none',
      version: extractVersionFromPyproject(PROJECT_ROOT),
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        AUTOMAGIK_API_PORT: envVars.AUTOMAGIK_API_PORT || '8881',
        AUTOMAGIK_API_HOST: envVars.AUTOMAGIK_API_HOST || '0.0.0.0',
        AUTOMAGIK_API_KEY: envVars.AUTOMAGIK_API_KEY || "namastex888",
	AUTOMAGIK_ENV: envVars.AUTOMAGIK_ENV || 'production',
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1', // Ensure Python logs are flushed immediately
        // Add NVM Node.js paths to ensure Claude CLI is available
        PATH: `/home/cezar/.nvm/versions/node/v22.16.0/bin:${process.env.PATH || '/usr/local/bin:/usr/bin:/bin'}`
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 1000,
      kill_timeout: 5000,
      error_file: path.join(PROJECT_ROOT, 'logs/err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
