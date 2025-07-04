# Automagik API Commands Guide

With the new CLI structure, users can now use intuitive commands to manage the API server.

## API Commands

### Start the API Server

```bash
# Basic start
automagik api start

# With custom host and port
automagik api start --host 0.0.0.0 --port 8080

# With auto-reload for development
automagik api start --reload

# Specify external agents directory
automagik api start --external-dir ./my_agents

# With multiple workers (production)
automagik api start --workers 4
```

### Stop the API Server

```bash
automagik api stop
```

### Check API Status

```bash
# Basic status check
automagik api status

# Check specific host/port
automagik api status --host localhost --port 8080
```

### View API Logs

```bash
# Show last 100 lines
automagik api logs

# Show last 50 lines
automagik api logs --lines 50

# Follow logs in real-time
automagik api logs --follow
```

### Test the API

```bash
# Test with default agent
automagik api test

# Test specific agent
automagik api test --agent flashinho_pro_external

# Test on different host/port
automagik api test --host localhost --port 8080
```

## External Agent Auto-Discovery

The API server automatically discovers external agents in these ways:

1. **Environment Variable** (highest priority):
   ```bash
   export AUTOMAGIK_EXTERNAL_AGENTS_DIR=/path/to/agents
   automagik api start
   ```

2. **Command Line** (overrides environment):
   ```bash
   automagik api start --external-dir ./agents_examples
   ```

3. **Auto-Detection** (if not specified):
   - `./agents_examples` (current directory)
   - `./external_agents` (current directory)
   - `~/.automagik/agents` (user home)

## Complete Workflow Example

```bash
# 1. Set up environment
export OPENAI_API_KEY=your-key-here
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=./agents_examples

# 2. Start the API server
automagik api start

# 3. In another terminal, check status
automagik api status

# 4. Test an external agent
automagik api test --agent flashinho_pro_external

# 5. View logs
automagik api logs

# 6. Stop when done
automagik api stop
```

## For Pip Install Users

After installing with pip:

```bash
pip install automagik-agents
```

Users can immediately start using the API:

```bash
# Start with external agents from current directory
automagik api start --external-dir ./my_agents

# Or set environment variable for persistent configuration
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=~/my_automagik_agents
automagik api start
```

## Output Examples

### Starting the API
```
🚀 Starting Automagik API server on 0.0.0.0:8000
📁 Auto-detected external agents: /home/user/agents_examples
✅ API server starting...
📍 API endpoints: http://0.0.0.0:8000/api/v1/
📚 Documentation: http://0.0.0.0:8000/docs
🔑 Default API key: namastex888

Press CTRL+C to stop the server
```

### Status Check
```
✅ API server is running
📍 URL: http://localhost:8000
🤖 Available agents: 12
📦 External agents: 4
```

### Test Output
```
🧪 Testing API with agent: flashinho_pro_external
📍 URL: http://localhost:8000/api/v1/agent/flashinho_pro_external/run
✅ Test successful!

💬 Response: Hello! I'm Flashinho Pro, your educational assistant...

📊 Usage: {'model': 'google:gemini-2.5-pro', 'total_tokens': 156}
```

## Troubleshooting

If `automagik api start` doesn't work:

1. **Check installation**:
   ```bash
   pip show automagik-agents
   ```

2. **Use development mode**:
   ```bash
   automagik agents dev
   ```

3. **Direct Python execution**:
   ```bash
   python -m automagik.api
   ```

4. **Check environment**:
   ```bash
   which automagik
   echo $AUTOMAGIK_EXTERNAL_AGENTS_DIR
   ```