<p align="center">
  <img src=".github/images/automagik_logo.png" alt="AutoMagik Logo" width="600"/>
</p>

## 🚀 From Ideas to Production in Minutes

Automagik Agents is a powerful deployment layer over Pydantic AI that accelerates your AI agent development from concept to production. Born from our daily work at Namastex Labs, it provides a reliable, tested foundation for rapidly building, deploying, and managing AI agents with advanced capabilities like persistent memory and tool integration.

We built Automagik because we needed to save time while creating high-quality, production-ready agents. By focusing on standardized patterns, best practices, and reusable components, Automagik lets you create sophisticated AI assistants in minutes instead of days.

## 🌟 Features

- **Extensible Agent System**
  - Template-based agent creation
  - Built-in templates: Simple Agent, Sofia Agent, Notion Agent, and Discord Agent
  - Easy-to-use CLI for creating new agents
  - Automatic tool registration and management

- **Powerful API Integration**
  - FastAPI-based RESTful endpoints
  - Session management with conversation history
  - Structured request/response models
  - Built-in authentication and CORS support
  - Health monitoring and version tracking

- **Advanced Memory System**
  - Persistent conversation history
  - Session-based memory management
  - Tool call and output tracking
  - Structured message storage
  - Agent-specific memories with customizable access controls
  - Dynamic memory injection via {{variable}} templating
  - Memory creation, reading, and updating tools

- **Built-in Templates**
  - **Simple Agent**: Basic chat functionality with memory tools
  - **Sofia Agent**: Memory-enhanced agent with comprehensive knowledge management and dynamic prompt templating
  - **Notion Agent**: Full Notion integration with database management
  - **Discord Agent**: Discord integration for managing servers, channels, and messages

## 🚀 Quick Start

1. **Installation**
   ```bash
   git clone https://github.com/namastexlabs/automagik-agents
   cd automagik-agents
   ```
   Create and manage a virtual environment using [uv](https://docs.astral.sh/uv/):
   ```bash
   uv venv
   ```
   ```bash
   # On Linux environments/WSL
   source .venv/bin/activate
   ```
   ```bash
   # On Windows
   .venv/Scripts/activate
   ```
   Install all the dependencies
   ```bash
   uv pip install -e .
   ```

2. **Environment Setup**
   ```bash
   # Copy example environment file
   cp .env-example .env

   # Configure required variables
   AM_API_KEY=your_api_key_here
   AM_HOST=0.0.0.0
   AM_PORT=8881
   OPENAI_API_KEY=your_openai_key_here
   OPENAI_MODEL=openai:gpt-4o-mini  # or your preferred model
   
   # For Notion agent (optional)
   NOTION_TOKEN=your_notion_token
   
   # For Discord agent (optional)
   DISCORD_BOT_TOKEN=your_discord_token
   ```
   Make sure you have access to a PosgreSQL 15 database by:
   a. Setting up a local instance via docker-compose:
   1. (Optional) Override the default .env variables
   ```bash
   POSTGRES_DB=
   POSTGRES_USER=
   POSTGRES_PASSWORD=
   POSTGRES_PORT=

   DATABASE_URL="your_custom_url"
   ```
   2. Create the Postgres container:
   ```bash
   cd docker/
   # Initialize the container using the .env on root
   docker-compose --env-file ../.env up
   ```
   **or**
   b. Connecting to a existing database by overriding the DATABASE_URL .env variable:
   ```bash
   DATABASE_URL="your_database_url"
   ```
3. **Initialize automagik's database structure:**
   ```bash
   automagik-agents db init
   ```

4. **Start the API Server**
   ```bash
   automagik-agents api start --reload # Initialize the API with hot-reloading
   ```
5. **Hello world!**
  To make sure your setup is running correctly, do a API health check:
   ```bash
   curl http://localhost:8881/health
   ```
   Start you first conversation session with a simple, template, agent:
   ```bash
   automagik-agents agent chat start --agent simple
   ```

=======
# AutoMagik Agents

A powerful toolkit for quickly building and deploying AI agents using the Pydantic AI framework. Create custom agents from templates, expose them through a RESTful API, and manage conversations with built-in memory and tool support. Perfect for teams looking to rapidly prototype and deploy AI agents with standardized patterns and best practices.

## 🌟 Features

### Extensible Agent System
- **Template-Based Development**: Create new agents from pre-built templates
- **Ready-to-Use Templates**: Start with Simple Agent or Notion Agent
- **Intuitive CLI**: Generate agents with simple commands
- **Automatic Tool Registration**: Register and manage tools effortlessly

### Powerful API Integration
- **FastAPI Backend**: High-performance RESTful endpoints
- **Sophisticated Session Management**: Track conversation history
- **Structured Data Models**: Clear request/response patterns
- **Security**: Built-in authentication and CORS support
- **Monitoring**: Health checks and version tracking

### Advanced Memory System
- **Persistent Conversation History**: Maintain context across sessions
- **Session-Based Organization**: Efficient memory management
- **Tool Interaction Tracking**: Record tool calls and outputs
- **Structured Storage**: Organized message repository

### Built-in Templates
- **Simple Agent**: Basic chat functionality with datetime tools
- **Notion Agent**: Full Notion integration with database management

## 🚀 Quick Start

### Installation

```bash
pip install automagik-agents
```

### Environment Setup

```bash
# Copy example environment file
cp .env-example .env

# Configure required variables
AM_API_KEY=your_api_key_here
AM_HOST=0.0.0.0
AM_PORT=8000
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=openai:gpt-4o-mini  # or your preferred model

# For Notion agent (optional)
NOTION_TOKEN=your_notion_token
```

### Creating Your First Agent

```bash
# Create from simple template
automagik-agents create-agent -n my_agent -t simple_agent

# Create from Notion template
automagik-agents create-agent -n my_notion_agent -t notion_agent
```

### Starting the API Server

```bash
automagik-agents api start --reload
```

## 💡 Usage Examples

### CLI Commands

1. **Interactive Chat** - Useful when developing / debugging without an UI.
   ```bash
   # Start a chat session with an agent
   automagik-agents agent chat start --agent my_agent
   
   # List available agents for chat
   automagik-agents agent chat list
   ```

2. **Agent Mode** - We made this so that we can provide another agent with tools to test the new agents under development.
   ```bash
   # Run a single message through an agent
   automagik-agents agent run message --agent my_agent --message "What time is it?"
   
   # Run with session continuity
   automagik-agents agent run message --agent my_agent --session my_session --message "Remember this information"
   automagik-agents agent run message --agent my_agent --session my_session --message "What did I ask you to remember?"
   ```

3. **Debug Mode**
   ```bash
   # Enable debug mode for detailed output
   automagik-agents --debug agent run message --agent my_agent --message "Debug information"
   ```

### API Endpoints

1. **Health Check**
   ```bash
   curl http://localhost:8881/health
   ```

2. **Run an Agent**
   ```bash
   # Simple agent
   curl -X POST http://localhost:8881/api/v1/agent/simple_agent/run \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "message_content": "What time is it?",
       "session_name": "optional_session_name"
     }'
   ```

3. **Memory Management**
   ```bash
   # Create a memory
   curl -X POST http://localhost:8881/api/v1/memories \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "user_preference",
       "description": "User color preference",
       "content": "The user prefers blue",
       "agent_id": 1,
       "read_mode": "tool_calling",
       "access": "write"
     }'
     
   # Get a memory
   curl http://localhost:8881/api/v1/memories/{memory_id} \
     -H "X-API-Key: your_api_key"
     
   # List memories
   curl http://localhost:8881/api/v1/memories \
     -H "X-API-Key: your_api_key"
   ```

4. **Session Management**
   ```bash
   # Get session history
   curl http://localhost:8881/api/v1/sessions/{session_id_or_name} \
     -H "X-API-Key: your_api_key"

   # Delete session
   curl -X DELETE http://localhost:8881/api/v1/sessions/{session_id_or_name} \
     -H "X-API-Key: your_api_key"
   ```
=======
#### Health Check

```bash
curl http://localhost:8000/health
```

#### Running Agents

**Simple Agent**
```bash
curl -X POST http://localhost:8000/agent/simple_agent/run \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "message_input": "What time is it?",
    "session_id": "optional_session_id"
  }'
```

**Notion Agent**
```bash
curl -X POST http://localhost:8000/agent/notion_agent/run \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "message_input": "List my databases",
    "session_id": "optional_session_id"
  }'
```

#### Session Management

**Retrieve Session History**
```bash
curl http://localhost:8000/session/your_session_id \
  -H "X-API-Key: your_api_key"
```

**Clear Session Data**
```bash
curl -X DELETE http://localhost:8000/session/your_session_id \
  -H "X-API-Key: your_api_key"
```

### Dynamic Memory System

Automagik features a powerful dynamic memory system that can inject variable content into agent prompts:

1. **Template Variables in Prompts**
   ```python
   # Example prompt with template variables
   AGENT_PROMPT = (
     """
     You are an AI assistant with the following traits:
     - Name: {{assistant_name}}
     - Personality: {{personality}}
     - Knowledge areas: {{knowledge_areas}}
     
     Current user preferences: {{user_preferences}}
     """
   )
   ```

2. **Creating Memories for Template Variables**
   ```bash
   # Create memories that will be injected into prompts
   curl -X POST http://localhost:8881/api/v1/memories \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "personality",
       "description": "Agent personality traits",
       "content": "friendly, helpful, knowledgeable",
       "agent_id": 3,
       "read_mode": "system_prompt",
       "access": "read"
     }'
   ```

3. **How It Works**
   - Template variables using `{{variable_name}}` syntax are identified in prompts
   - The system automatically fetches memory values with matching names
   - Values are injected into the prompt at runtime
   - Special variables like `{{run_id}}` are handled automatically
   - Memory values can be updated via API or agent tools
   - This allows for dynamic agent personality and knowledge without redeployment

### Creating Custom Agents

1. **Create Agent Using CLI**
   ```bash
   automagik-agents agent create agent --name custom_agent --template simple_agent
   ```

2. **Customize Agent Files**
   - Edit `src/agents/simple/custom_agent/prompts/prompt.py` for system prompts
   - Add template variables with `{{variable_name}}` syntax for dynamic content
   - Modify `src/agents/simple/custom_agent/agent.py` for behavior and tool registration
   - Update `src/agents/simple/custom_agent/__init__.py` for configuration

3. **Register Tools**
   ```python
   def register_tools(self):
       """Register custom tools with the agent."""
       # Register built-in memory tools
       from src.tools.memory_tools import read_memory, create_memory, update_memory
       self.agent.tool(read_memory)
       self.agent.tool(create_memory)
       self.agent.tool(update_memory)
       
       # Register custom tools
       self.agent.tool(your_custom_tool)
   ```
=======
#### 1. Create Agent Template

```bash
automagik-agents create-agent -n custom -t simple_agent
```

#### 2. Customize Agent Files

- Edit `src/agents/custom_agent/prompts.py` for system prompts
- Modify `src/agents/custom_agent/agent.py` for agent behavior
- Update `src/agents/custom_agent/__init__.py` for configuration

#### 3. Register Custom Tools

```python
def register_tools(self):
    """Register custom tools with the agent."""
    # Register built-in tools
    self.agent.tool(self.get_current_time)
    
    # Register custom tools
    self.agent.tool(your_custom_tool)
    
def your_custom_tool(self, param1: str) -> str:
    """Custom tool description.
    
    Args:
        param1: Description of parameter
        
    Returns:
        Description of return value
    """
    # Tool implementation
    return f"Processed: {param1}"
```

### Testing

Run all tests including memory, API, and CLI tests:
```bash
python tests/run_all_tests.py
```

Run specific test categories:
```bash
# Run only memory tests
python tests/run_all_tests.py --memory --no-api --no-cli

# Run with verbose output
python tests/run_all_tests.py --verbose
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 API Documentation

Explore the complete API documentation at `/api/v1/docs` when running the server.

## 🗺️ Roadmap

- **Graph Agents**: Advanced agent orchestration and workflows
- **Seamless Deployment**: Built-in deployment solutions in namastex/automagik for agent automation
- **Heartbeat Mode**: Our proprietary method to keep agents alive 24hrs doing tasks
- **MCP Integration**: Model Context Protocol for easier tool reusing
- **Support for Other Agent Frameworks**: Expand compatibility across the ecosystem
- **Smart Context Management**: Optimal handling of large context windows

Automagik Agents is and will always be open source. Since this is our daily work tool, we provide high priority maintenance and updates.
=======
---

<p align="center">
  <b>Part of the AutoMagik Ecosystem</b><br>
  <a href="https://github.com/namastexlabs/automagik">AutoMagik</a> |
  <a href="https://github.com/namastexlabs/automagik-agents">AutoMagik Agents</a> |
  <a href="https://github.com/namastexlabs/automagik-ui">AutoMagik UI</a>
</p>
