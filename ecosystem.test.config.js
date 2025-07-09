module.exports = {
  apps: [
    {
      name: 'am-agents-test',
      cwd: '/home/cezar/automagik-dev/automagik-dev-1',
      script: '.venv/bin/python',
      args: '-m automagik',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/cezar/automagik-dev/automagik-dev-1',
        AUTOMAGIK_API_PORT: '48881',
        AUTOMAGIK_API_HOST: '0.0.0.0',
        AUTOMAGIK_API_KEY: 'namastex888',
        AUTOMAGIK_ENV: 'test',
        NODE_ENV: 'test',
        PYTHONUNBUFFERED: '1'
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
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};