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

from src.config import settings
from src.utils.logging import configure_logging
from src.version import SERVICE_INFO
from src.auth import APIKeyMiddleware
from src.api.models import HealthResponse
from src.api.routes import main_router as api_router
from src.agents.models.agent_factory import AgentFactory
from src.cli.db import db_init

# Configure Neo4j logging to reduce verbosity
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neo4j.io").setLevel(logging.ERROR)
logging.getLogger("neo4j.bolt").setLevel(logging.ERROR)

# Configure logging
configure_logging()

# Get our module's logger
logger = logging.getLogger(__name__)

# Global shutdown flag for graceful shutdown handling
_shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    
    # Log with signal name for better debugging
    signal_names = {2: "SIGINT (Ctrl+C)", 15: "SIGTERM"}
    signal_name = signal_names.get(signum, f"Signal {signum}")
    logger.info(f"📝 Received {signal_name}, initiating graceful shutdown...")
    
    # AGGRESSIVE: Try to cancel all pending tasks immediately
    try:
        # Get the current event loop if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # Cancel all pending tasks
            pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending_tasks:
                logger.info(f"📝 Cancelling {len(pending_tasks)} pending tasks...")
                for task in pending_tasks:
                    task.cancel()
        except RuntimeError:
            # No event loop running, which is fine for sync contexts
            pass
    except Exception as e:
        logger.warning(f"Error during task cancellation: {e}")
    
    # Force exit after a very short timeout to prevent hanging
    import threading
    def force_exit():
        import time
        time.sleep(2.0)  # Give 2 seconds for graceful shutdown
        logger.warning("📝 Force exiting due to shutdown timeout...")
        os._exit(1)
    
    # Start force exit timer in background
    force_exit_thread = threading.Thread(target=force_exit, daemon=True)
    force_exit_thread.start()

def register_signal_handlers():
    """Register signal handlers for graceful shutdown.
    
    This function should only be called when running as the main application,
    not during imports or tests.
    """
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

async def initialize_all_agents():
    """Initialize agents at startup.
    
    If AM_AGENTS_NAMES environment variable is set, activate only those specific agents
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
        from src.db.repository.agent import create_agent, get_agent_by_name, list_agents, update_agent
        from src.db.models import Agent
        
        # Register discovered agents in database if they don't exist
        registered_count = 0
        for agent_name in available_agents:
            existing_agent = get_agent_by_name(agent_name)
            if not existing_agent:
                # Create new agent in database
                from src.agents.models.framework_types import FrameworkType
                new_agent = Agent(
                    name=agent_name,
                    type=FrameworkType.default().value,  # Use enum for consistency
                    model="openai:gpt-4.1",  # Default model
                    config={"created_by": "auto_discovery"},
                    description=f"Auto-discovered {agent_name} agent",
                    active=True  # Default to active
                )
                create_agent(new_agent)
                registered_count += 1
                logger.info(f"📝 Registered new agent in database: {agent_name}")
        
        if registered_count > 0:
            logger.info(f"✅ Registered {registered_count} new agents in database")
        
        # Handle AM_AGENTS_NAMES to update active status in database
        if settings.AM_AGENTS_NAMES:
            # Parse comma-separated list of agent names
            specified_agents = [name.strip() for name in settings.AM_AGENTS_NAMES.split(',')]
            logger.info(f"🔧 AM_AGENTS_NAMES environment variable specified: {', '.join(specified_agents)}")
            
            
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
            
            logger.info(f"✅ Activated {activated_count} agents based on AM_AGENTS_NAMES")
        
        # Get only active agents from database for initialization
        from src.db.repository.agent import list_agents
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
            
            # Initialize Graphiti
            if hasattr(agent, 'initialize_graphiti'):
                logger.debug(f"Initializing Graphiti for agent: {agent_name}")
                graphiti_task = asyncio.create_task(agent.initialize_graphiti())
                graphiti_init_tasks.append((agent_name, graphiti_task))
        
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
        
        # Wait for all Graphiti initialization tasks to complete
        for agent_name, task in graphiti_init_tasks:
            try:
                success = await task
                if success:
                    logger.debug(f"✅ Graphiti for {agent_name} initialized successfully")
                else:
                    logger.debug(f"ℹ️ Graphiti for {agent_name} not enabled or could not be initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing Graphiti for {agent_name}: {str(e)}")
        
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
        # The database needs to be available first
        try:
            logger.info("🏗️ Initializing database for application startup...")
            # Check which database provider we're using
            provider = get_database_provider()
            db_type = provider.get_database_type()
            
            # All database types should use the proper migration system
            logger.info(f"Using {db_type} database provider")
            db_init(force=False)
            logger.info("✅ Database initialization completed")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            # Continue startup even if database init fails for development
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Initialize Graphiti indices and constraints if Neo4j is configured
        if settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD:
            try:
                logger.info("🚀 Initializing Graphiti indices and constraints...")
                # Import the client asynchronously with retry logic
                try:
                    from src.utils.graphiti_queue import get_graphiti_client_async
                    
                    # Initialize the shared client with retry logic - faster for development
                    # Use shorter delays in development to make interruption more responsive
                    client = await get_graphiti_client_async(max_retries=3, retry_delay=1.0)
                    
                    if client:
                        # The build_indices_and_constraints should have already been called
                        # during client initialization, but let's log that it's ready
                        logger.info("✅ Graphiti client initialized and indices built successfully")
                    else:
                        logger.warning("⚠️ Failed to initialize shared Graphiti client")
                        
                except ImportError:
                    logger.warning("⚠️ graphiti-core package not found, skipping Graphiti initialization")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Graphiti indices and constraints: {str(e)}")
                logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Initialize agents after core services are ready
        await initialize_all_agents()
        
        # Initialize MCP client manager after database and agents are ready
        try:
            logger.info("🚀 Initializing MCP client manager...")
            from src.mcp.client import get_mcp_client_manager
            await get_mcp_client_manager()
            logger.info("✅ MCP client manager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing MCP client manager: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Initialize tools (discover and sync to database)
        try:
            logger.info("🔧 Initializing tool discovery and management...")
            from src.services.startup import startup_initialization
            await startup_initialization()
            logger.info("✅ Tool system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing tool system: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Start Graphiti queue
        try:
            logger.info("🚀 Starting Graphiti queue...")
            from src.utils.graphiti_queue import get_graphiti_queue
            queue_manager = get_graphiti_queue()
            await queue_manager.start()
            logger.info("✅ Graphiti queue started successfully")
        except Exception as e:
            logger.error(f"❌ Error starting Graphiti queue: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        yield
        
        # Cleanup shared resources
        try:
            # Shutdown MCP client manager
            logger.info("🛑 Shutting down MCP client manager...")
            from src.mcp.client import shutdown_mcp_client_manager
            await shutdown_mcp_client_manager()
            logger.info("✅ MCP client manager shutdown successfully")
        except Exception as e:
            logger.error(f"❌ Error shutting down MCP client manager: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        try:
            # Stop Graphiti queue
            logger.info("🛑 Stopping Graphiti queue...")
            from src.utils.graphiti_queue import shutdown_graphiti_queue
            await shutdown_graphiti_queue()
            logger.info("✅ Graphiti queue stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error stopping Graphiti queue: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
        
        # Graphiti client cleanup is handled automatically by the queue shutdown above
        logger.debug("🛑 Graphiti client cleanup completed via queue shutdown")
    
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

    # Add JSON parsing middleware to fix malformed JSON
    try:
        from src.api.middleware import JSONParsingMiddleware
        app.add_middleware(JSONParsingMiddleware)
        logger.info("✅ Added JSON parsing middleware")
    except Exception as e:
        logger.warning(f"⚠️ Failed to add JSON parsing middleware: {str(e)}")

    # Add authentication middleware
    app.add_middleware(APIKeyMiddleware)
    
    # Set up database message store regardless of environment
    try:
        logger.info("🔧 Initializing database connection for message storage")
        
        # Get database provider for connection testing
        from src.db.providers.factory import get_database_provider
        provider = get_database_provider()
        
        # Test the connection with provider-specific logic
        if provider.get_database_type() == "sqlite":
            # SQLite-specific connection test
            with provider.get_connection() as conn:
                conn.execute("SELECT 1")
                logger.info("✅ SQLite database connection test successful")
                
                # Check if required tables exist
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                sessions_table_exists = cursor.fetchone() is not None
                
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
                messages_table_exists = cursor.fetchone() is not None
                
                logger.info(f"Database tables check - Sessions: {sessions_table_exists}, Messages: {messages_table_exists}")
                
                if not (sessions_table_exists and messages_table_exists):
                    logger.error("❌ Required database tables are missing - sessions or messages tables not found")
                    raise ValueError("Required database tables not found")
        else:
            # PostgreSQL connection test using legacy method
            from src.db.connection import get_connection_pool
            pool = get_connection_pool()
            
            # Test the connection with a simple query
            with pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    logger.info(f"✅ Database connection test successful: {version}")
                    
                    # Check if required tables exist
                    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sessions')")
                    sessions_table_exists = cur.fetchone()[0]
                    
                    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'messages')")
                    messages_table_exists = cur.fetchone()[0]
                    
                    logger.info(f"Database tables check - Sessions: {sessions_table_exists}, Messages: {messages_table_exists}")
                    
                    if not (sessions_table_exists and messages_table_exists):
                        logger.error("❌ Required database tables are missing - sessions or messages tables not found")
                        raise ValueError("Required database tables not found")
                pool.putconn(conn)
            
        logger.info("✅ Database connection pool initialized successfully")
        
        # Verify database read/write functionality using the dedicated function
        from src.db.connection import verify_db_read_write
        verify_db_read_write()
        
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
            # Log the error with traceback so we can diagnose pre-router failures
            logger.error(f"❌ Unhandled exception in request {request.url}: {exc}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(exc)}"},
            )

    # Bounded semaphore to limit the number of concurrent in-process requests
    _request_semaphore = asyncio.BoundedSemaphore(
        getattr(settings, "UVICORN_LIMIT_CONCURRENCY", 10)
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
        base_url = f"http://{settings.AM_HOST}:{settings.AM_PORT}"
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
            environment=settings.AM_ENV
        )

    @app.get("/health/graphiti-queue", tags=["System"], summary="Graphiti Queue Health", description="Returns Graphiti queue status and statistics")
    async def graphiti_queue_health():
        """Get Graphiti queue status and statistics"""
        try:
            # Quick check if queue is disabled
            if not settings.GRAPHITI_QUEUE_ENABLED:
                return {
                    "status": "disabled",
                    "enabled": False,
                    "message": "Graphiti queue is disabled by configuration"
                }
            
            from src.utils.graphiti_queue import get_graphiti_queue
            queue_manager = get_graphiti_queue()
            return queue_manager.get_queue_status()
        except Exception as e:
            logger.error(f"❌ Error getting Graphiti queue status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "enabled": settings.GRAPHITI_QUEUE_ENABLED
            }

    # Include API router (with versioned prefix)
    app.include_router(api_router, prefix="/api/v1")

# Create the app instance
app = create_app()

# Include Documentation router after app is created (to avoid circular imports)
from src.api.docs import router as docs_router
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
        default=settings.AM_HOST,
        help=f"Host to bind the server to (default: {settings.AM_HOST})"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=int(settings.AM_PORT),
        help=f"Port to bind the server to (default: {settings.AM_PORT})"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Register signal handlers only when running as main application
    register_signal_handlers()
    
    # Log the configuration
    logger.info("Starting server with configuration:")
    logger.info(f"├── Host: {args.host}")
    logger.info(f"├── Port: {args.port}")
    logger.info(f"└── Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    
    # Run the server
    uvicorn.run(
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
