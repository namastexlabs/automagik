// ===================================================================
// 🎭 AM-Agents-Labs - Development PM2 Configuration
// ===================================================================
// Hot reload development instance for testing and development

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
      name: 'automagik-dev',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/python',
      args: '-m automagik',
      interpreter: 'none',
      version: extractVersionFromPyproject(PROJECT_ROOT),
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        AUTOMAGIK_API_PORT: '9991', // Development port
        AUTOMAGIK_API_HOST: envVars.AUTOMAGIK_API_HOST || '0.0.0.0',
        AUTOMAGIK_API_KEY: envVars.AUTOMAGIK_API_KEY || "namastex888",
        AUTOMAGIK_ENV: 'development', // Force development mode
        AUTOMAGIK_LOG_LEVEL: 'DEBUG', // Enable debug logging
        NODE_ENV: 'development',
        PYTHONUNBUFFERED: '1' // Ensure Python logs are flushed immediately
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: ['automagik'], // Enable hot reload for automagik directory
      watch_delay: 1000,
      ignore_watch: [
        'node_modules',
        'logs',
        '.git',
        '*.log',
        '__pycache__',
        '*.pyc',
        '.venv'
      ],
      max_memory_restart: '1G',
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 1000,
      kill_timeout: 5000,
      error_file: path.join(PROJECT_ROOT, 'logs/dev-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/dev-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/dev-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};