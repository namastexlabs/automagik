import logging
from datetime import datetime
import asyncio
import traceback
import signal
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from automagik.config import settings
from automagik.utils.logging import configure_logging
from automagik.utils.version import SERVICE_INFO
from automagik.auth import APIKeyMiddleware
from automagik.api.models import HealthResponse
from automagik.api.routes import main_router as api_router
from automagik.agents.models.agent_factory import AgentFactory
from automagik.cli.db import db_init


# Configure logging
configure_logging()

# Get our module's logger
logger = logging.getLogger(__name__)


async def initialize_all_agents():
    """Initialize agents at startup.
    
    If AUTOMAGIK_AGENT_NAMES environment variable is set, activate only those specific agents
    and deactivate all others. Otherwise, all agents remain in their current active state.
    
    This ensures that agents are created and registered in the database
    before any API requests are made, rather than waiting for the first
    run request.
    """
    try:
        # Discover all available agents
        AgentFactory.discover_agents()
        
        # Get the list of available agents
        discovered_agents = AgentFactory.list_available_agents()
        
        # Filter out error agents - these are placeholder agents created during failed imports
        # They should not be registered in the database or exposed via API
        available_agents = [agent for agent in discovered_agents if not agent.endswith('_error')]
        
        logger.info(f"Discovered {len(discovered_agents)} agents, filtered to {len(available_agents)} valid agents: {', '.join(available_agents)}")
        if len(discovered_agents) > len(available_agents):
            error_agents = [agent for agent in discovered_agents if agent.endswith('_error')]
            logger.warning(f"Filtered out {len(error_agents)} error agents: {', '.join(error_agents)}")
        
        # Import database functions
        from automagik.db.repository.agent import create_agent, get_agent_by_name, list_agents, update_agent
        from automagik.db.models import Agent
        
        # Register discovered agents in database if they don't exist
        registered_count = 0
        for agent_name in available_agents:
            existing_agent = get_agent_by_name(agent_name)
            if not existing_agent:
                # Get agent class to read DEFAULT_MODEL and DEFAULT_CONFIG
                try:
                    agent_class = AgentFactory.get_agent_class(agent_name)
                    if agent_class and hasattr(agent_class, 'DEFAULT_MODEL'):
                        model = agent_class.DEFAULT_MODEL
                        default_config = getattr(agent_class, 'DEFAULT_CONFIG', {})
                    else:
                        # Fall back to creating temporary instance to get model
                        temp_agent = AgentFactory.create_agent(agent_name, {})
                        model = getattr(temp_agent.config, 'model', 'openai:gpt-4o-mini')
                        default_config = {}
                except Exception as e:
                    logger.warning(f"Could not get model for {agent_name}: {e}")
                    model = "openai:gpt-4o-mini"  # Sensible default
                    default_config = {}
                
                # Create new agent in database
                from automagik.agents.models.framework_types import FrameworkType
                new_agent = Agent(
                    name=agent_name,
                    type=FrameworkType.default().value,  # Use enum for consistency
                    model=model,  # Use agent's declared model
                    config={**default_config, "created_by": "auto_discovery"},
                    description=f"Auto-discovered {agent_name} agent",
                    active=True  # Default to active
                )
                create_agent(new_agent)
                registered_count += 1
                logger.info(f"📝 Registered new agent in database: {agent_name} with model {model}")
        
        if registered_count > 0:
            logger.info(f"✅ Registered {registered_count} new agents in database")
        
        # Handle AUTOMAGIK_AGENT_NAMES to update active status in database
        if settings.AUTOMAGIK_AGENT_NAMES:
            # Parse comma-separated list of agent names
            specified_agents = [name.strip() for name in settings.AUTOMAGIK_AGENT_NAMES.split(',')]
            logger.info(f"🔧 AUTOMAGIK_AGENT_NAMES environment variable specified: {', '.join(specified_agents)}")
            
            
            # First, deactivate all agents
            all_db_agents = list_agents(active_only=False)
            deactivated_count = 0
            for db_agent in all_db_agents:
                if db_agent.active:
                    db_agent.active = False
                    if update_agent(db_agent):
                        deactivated_count += 1
                        logger.debug(f"Deactivated agent: {db_agent.name}")
            
            if deactivated_count > 0:
                logger.info(f"📌 Deactivated {deactivated_count} agents")
            
            # Activate only the specified agents
            activated_count = 0
            for agent_name in specified_agents:
                # Try exact name first
                db_agent = get_agent_by_name(agent_name)
                
                # If not found, try with _agent suffix
                if not db_agent and f"{agent_name}_agent" in available_agents:
                    db_agent = get_agent_by_name(f"{agent_name}_agent")
                
                if db_agent:
                    if not db_agent.active:
                        db_agent.active = True
                        if update_agent(db_agent):
                            activated_count += 1
                            logger.info(f"✅ Activated agent: {db_agent.name}")
                else:
                    logger.warning(f"⚠️ Agent '{agent_name}' not found in database")
            
            logger.info(f"✅ Activated {activated_count} agents based on AUTOMAGIK_AGENT_NAMES")
        else:
            # AUTOMAGIK_AGENT_NAMES is not set - activate all available agents
            logger.info("🔧 AUTOMAGIK_AGENT_NAMES not specified - activating all available agents")
            
            all_db_agents = list_agents(active_only=False)
            activated_count = 0
            for db_agent in all_db_agents:
                # Only activate agents that are in the available_agents list (discovered)
                if db_agent.name in available_agents and not db_agent.active:
                    db_agent.active = True
                    if update_agent(db_agent):
                        activated_count += 1
                        logger.info(f"✅ Activated agent: {db_agent.name}")
            
            if activated_count > 0:
                logger.info(f"✅ Activated {activated_count} agents (all available agents)")
            else:
                logger.info("📌 All discovered agents are already active")
        
        # Get only active agents from database for initialization
        from automagik.db.repository.agent import list_agents
        active_db_agents = list_agents(active_only=True)
        agents_to_initialize = [agent.name for agent in active_db_agents if agent.name in available_agents]
        
        logger.info(f"🔧 Initializing {len(agents_to_initialize)} active agents...")
        
        # List to collect all initialized agents
        initialized_agents = []
        
        # Initialize each agent
        for agent_name in agents_to_initialize:
            try:
                logger.debug(f"Initializing agent: {agent_name}")
                # This will create and register the agent
                agent = AgentFactory.get_agent(agent_name)
                initialized_agents.append((agent_name, agent))
                logger.debug(f"✅ Agent {agent_name} initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize agent {agent_name}: {str(e)}")
        
        # Now initialize prompts and Graphiti for all agents
        prompt_init_tasks = []
        graphiti_init_tasks = []
        
        for agent_name, agent in initialized_agents:
            # Initialize prompts
            logger.debug(f"Registering prompts for agent: {agent_name}")
            prompt_task = asyncio.create_task(agent.initialize_prompts())
            prompt_init_tasks.append((agent_name, prompt_task))
            
        
        # Wait for all prompt initialization tasks to complete
        for agent_name, task in prompt_init_tasks:
            try:
                success = await task
                if success:
                    logger.debug(f"✅ Prompts for {agent_name} initialized successfully")
                else:
                    logger.warning(f"⚠️ Prompts for {agent_name} could not be fully initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing prompts for {agent_name}: {str(e)}")
        
        
        logger.info(f"✅ Agent initialization completed. {len(initialized_agents)} agents initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agents: {str(e)}")
        logger.error(f"Detailed error: {traceback.format_exc()}")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Get our module's logger
    logger = logging.getLogger(__name__)
    
    # Configure API documentation
    title = SERVICE_INFO["name"]
    description = SERVICE_INFO["description"]
    version = SERVICE_INFO["version"]
    
    # Set up lifespan context manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize database if needed
        # The database needs to be available first before any agent operations
        try:
            logger.info("🏗️ Initializing database for application startup...")
            # Check which database provider we're using
            from automagik.db.providers.factory import get_database_provider
            provider = get_database_provider()
            db_type = provider.get_database_type()
            
            logger.info(f"Using {db_type} database provider")
            
            # For PostgreSQL, try to create database if it doesn't exist
            if db_type == "postgresql":
                config = provider._get_db_config()
                database_name = config.get('database', 'automagik_agents')
                
                logger.info(f"Ensuring PostgreSQL database '{database_name}' exists...")
                
                # Try to create database if it doesn't exist
                if hasattr(provider, 'create_database_if_not_exists'):
                    created = provider.create_database_if_not_exists(database_name)
                    if not created:
                        logger.warning(f"⚠️ Could not create database '{database_name}' - will try to connect anyway")
            
            # Apply migrations to ensure all tables exist
            db_init(force=False)
            
            # Critical: Verify essential tables exist before continuing
            essential_tables = ['users', 'agents', 'sessions', 'messages', 'memories']
            missing_tables = []
            
            for table in essential_tables:
                if not provider.table_exists(table):
                    missing_tables.append(table)
            
            if missing_tables:
                logger.error(f"❌ Critical: Essential database tables are missing: {missing_tables}")
                logger.error("❌ Cannot start application without required database schema")
                logger.error("❌ Please run 'make db-init' or check database migration logs")
                raise Exception(f"Missing essential database tables: {missing_tables}")
            
            logger.info(f"✅ Database initialization completed - verified essential tables exist")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            logger.error(f"❌ Detailed error: {traceback.format_exc()}")
            # For fresh databases, we cannot continue without proper schema
            logger.error("❌ Application startup aborted due to database initialization failure")
            raise e
        
        
        # Initialize tracing system
        try:
            logger.info("📊 Initializing tracing system...")
            from automagik.tracing import get_tracing_manager
            tracing = get_tracing_manager()
            if tracing:
                logger.info(f"✅ Tracing system initialized - Telemetry: {tracing.telemetry is not None}, Observability: {tracing.observability is not None}")
            else:
                logger.info("📊 Tracing system disabled or not configured")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize tracing system: {e}")
        
        # Initialize agents after core services are ready
        await initialize_all_agents()
        
        # Initialize MCP manager after database and agents are ready
        try:
            logger.info("🚀 Initializing MCP manager...")
            from automagik.mcp.client import get_mcp_manager
            await get_mcp_manager()
            logger.info("✅ MCP manager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing MCP manager: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Initialize tools (discover and sync to database)
        try:
            logger.info("🔧 Initializing tool discovery and management...")
            from automagik.services.startup import startup_initialization
            await startup_initialization()
            logger.info("✅ Tool system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing tool system: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        
        # Initialize workflows (discover and sync to database like agents)
        try:
            logger.info("⚙️ Initializing workflow discovery and management...")
            from automagik.agents.claude_code.workflow_discovery import WorkflowDiscovery
            success = WorkflowDiscovery.initialize_workflows()
            if success:
                logger.info("✅ Workflow system initialized successfully")
            else:
                logger.warning("⚠️ Workflow system initialized with some errors")
        except Exception as e:
            logger.error(f"❌ Error initializing workflow system: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        
        # Claude Code workflow services removed - process tracking handled in sdk_executor
        
        yield
        
        # Cleanup shared resources
        try:
            # Shutdown MCP manager
            logger.info("🛑 Shutting down MCP manager...")
            from automagik.mcp.client import shutdown_mcp_manager
            await shutdown_mcp_manager()
            logger.info("✅ MCP manager shutdown successfully")
        except Exception as e:
            logger.error(f"❌ Error shutting down MCP manager: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Claude Code workflow services removed - process tracking handled in sdk_executor
        
    
    # Create the FastAPI app
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        docs_url=None,  # Disable default docs url
        redoc_url=None,  # Disable default redoc url
        openapi_url=None,  # Disable default openapi url
        openapi_tags=[
            {
                "name": "System",
                "description": "System endpoints for status and health checking",
                "order": 1,
            },
            {
                "name": "Agents",
                "description": "Endpoints for listing available agents and running agent tasks",
                "order": 2,
            },
            {
                "name": "Sessions",
                "description": "Endpoints to manage and retrieve agent conversation sessions",
                "order": 3,
            },
        ],
        debug=True  # NEW: enable debug mode per Phase 2 instructions
    )
    
    # Setup API routes
    setup_routes(app)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    # Add request logging middleware
    try:
        from automagik.api.middleware import RequestLoggingMiddleware
        app.add_middleware(RequestLoggingMiddleware)
        logger.info("✅ Added request logging middleware")
    except Exception as e:
        logger.warning(f"⚠️ Failed to add request logging middleware: {str(e)}")

    # Add JSON parsing middleware to fix malformed JSON
    try:
        from automagik.api.middleware import JSONParsingMiddleware
        app.add_middleware(JSONParsingMiddleware)
        logger.info("✅ Added JSON parsing middleware")
    except Exception as e:
        logger.warning(f"⚠️ Failed to add JSON parsing middleware: {str(e)}")

    # Add authentication middleware
    app.add_middleware(APIKeyMiddleware)
    
    # Add tracing middleware if available
    try:
        from automagik.tracing.middleware import TracingMiddleware
        app.add_middleware(TracingMiddleware)
        logger.info("✅ Added tracing middleware")
    except ImportError:
        logger.debug("Tracing middleware not available, skipping")
    
    # Set up database message store regardless of environment
    try:
        logger.info("🔧 Initializing database connection for message storage")
        
        # Get database provider for connection testing
        from automagik.db.providers.factory import get_database_provider
        provider = get_database_provider()
        
        # Test the connection with provider-specific logic
        if provider.get_database_type() == "sqlite":
            # SQLite-specific connection test
            with provider.get_connection() as conn:
                conn.execute("SELECT 1")
                logger.info("✅ SQLite database connection test successful")
                
                # Check if required tables exist - but only log, don't fail startup
                # Tables will be created during initialization phase
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                sessions_table_exists = cursor.fetchone() is not None
                
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
                messages_table_exists = cursor.fetchone() is not None
                
                logger.info(f"Database tables check - Sessions: {sessions_table_exists}, Messages: {messages_table_exists}")
                
                if not (sessions_table_exists and messages_table_exists):
                    logger.warning("⚠️ Some database tables are missing - they will be created during initialization")
                else:
                    logger.info("✅ Core database tables found")
        else:
            # PostgreSQL connection test using provider method (with auto-creation, skip health check)
            # Create connection pool without health check to avoid premature migration error messages
            pool = provider.get_connection_pool(skip_health_check=True)
            
            # Test the connection with a simple query
            with pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    logger.info(f"✅ Database connection test successful: {version}")
                    
                    # Check if required tables exist - but only log, don't fail startup
                    # Tables will be created during initialization phase
                    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sessions')")
                    sessions_table_exists = cur.fetchone()[0]
                    
                    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'messages')")
                    messages_table_exists = cur.fetchone()[0]
                    
                    logger.info(f"Database tables check - Sessions: {sessions_table_exists}, Messages: {messages_table_exists}")
                    
                    if not (sessions_table_exists and messages_table_exists):
                        logger.warning("⚠️ Some database tables are missing - they will be created during initialization")
                    else:
                        logger.info("✅ Core database tables found")
                pool.putconn(conn)
            
        logger.info("✅ Database connection pool initialized successfully")
        
        # Skip database read/write verification during early connection setup
        # This will be properly verified after migrations are applied in the startup lifespan
        logger.info("⚠️ Skipping database verification during early setup - will be verified after migration")
        
        # Log success
        logger.info("✅ Database message storage initialized successfully")
        
        # Configure MessageHistory to use database by default
        logger.info("✅ MessageHistory configured to use database storage")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database connection for message storage: {str(e)}")
        logger.error("⚠️ Application will fall back to in-memory message store")
        # Include traceback for debugging
        logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Create an in-memory message history as fallback
        # Don't reference the non-existent message_store module
        logger.warning("⚠️ Using in-memory storage as fallback - MESSAGES WILL NOT BE PERSISTED!")
    
    # ---------------------------------------------------------------------
    # Phase 2A/B/D Middleware for improved stability and visibility
    # ---------------------------------------------------------------------

    # Catch-all exception handler so that all 500s are logged with traceback
    @app.middleware("http")
    async def catch_all_exceptions_middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Handle client disconnects gracefully without logging as errors
            from starlette.requests import ClientDisconnect
            if isinstance(exc, ClientDisconnect):
                logger.debug(f"Client disconnected from {request.url}")
                # Return a basic response that won't be sent anyway since client disconnected
                return JSONResponse(status_code=499, content={"detail": "Client disconnected"})
            
            # Log the error with traceback so we can diagnose pre-router failures
            logger.error(f"❌ Unhandled exception in request {request.url}: {exc}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(exc)}"},
            )

    # Bounded semaphore to limit the number of concurrent in-process requests
    _request_semaphore = asyncio.BoundedSemaphore(
        getattr(settings, "AUTOMAGIK_UVICORN_LIMIT_CONCURRENCY", 10)
    )

    @app.middleware("http")
    async def limit_concurrent_requests(request: Request, call_next):
        async with _request_semaphore:
            return await call_next(request)

    # ---------------------------------------------------------------------
    # Existing setup logic continues below
    # ---------------------------------------------------------------------

    return app

def setup_routes(app: FastAPI):
    """Set up API routes for the application."""
    # Root and health endpoints (no auth required)
    @app.get("/", tags=["System"], summary="Root Endpoint", description="Returns service information and status")
    async def root():
        # Get base URL from settings
        base_url = f"http://{settings.AUTOMAGIK_API_HOST}:{settings.AUTOMAGIK_API_PORT}"
        return {
            "status": "online",
            "docs": f"{base_url}/api/v1/docs",
            **SERVICE_INFO
        }

    @app.get("/health", tags=["System"], summary="Health Check", description="Returns health status of the service")
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=SERVICE_INFO["version"],
            environment=settings.ENVIRONMENT
        )

    
    @app.get("/health/workflow-services", tags=["System"], summary="Workflow Services Health", description="Returns Claude Code workflow services status")
    async def workflow_services_health():
        """Get Claude Code workflow services status"""
        try:
            from automagik.agents.claude_code.startup import get_workflow_services_status
            return get_workflow_services_status()
        except Exception as e:
            logger.error(f"❌ Error getting workflow services status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    # Include API router (with versioned prefix)
    app.include_router(api_router, prefix="/api/v1")

# Create the app instance
app = create_app()

# Include Documentation router after app is created (to avoid circular imports)
from automagik.api.docs import router as docs_router
app.include_router(docs_router)

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Run the Sofia application server")
    parser.add_argument(
        "--reload", 
        action="store_true", 
        default=False,
        help="Enable auto-reload for development (default: False)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default=settings.AUTOMAGIK_API_HOST,
        help=f"Host to bind the server to (default: {settings.AUTOMAGIK_API_HOST})"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=int(settings.AUTOMAGIK_API_PORT),
        help=f"Port to bind the server to (default: {settings.AUTOMAGIK_API_PORT})"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Signal handlers removed - uvicorn handles signals natively
    
    # Log the configuration
    logger.info("Starting server with configuration:")
    logger.info(f"├── Host: {args.host}")
    logger.info(f"├── Port: {args.port}")
    logger.info(f"└── Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    
    # Run the server
    uvicorn.run(
        "automagik.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        timeout_graceful_shutdown=5
    )
