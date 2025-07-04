"""Main entry point for the application when run as a module.

This allows running the Automagik Agents application with:
    python -m automagik
"""

import sys
import logging
import argparse
import uvicorn
import traceback
import signal
import os

# Import necessary modules for logging configuration
try:
    from automagik.utils.logging import configure_logging
    from automagik.config import settings, Environment
    
    # Configure logging before anything else
    configure_logging()
    
    # Get our module's logger
    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

def create_argument_parser():
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(description="Run the Sofia application server")
    parser.add_argument(
        "--reload", 
        action="store_true", 
        default=None,
        help="Enable auto-reload for development (default: auto-enabled in development mode)"
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
    return parser

def get_server_config(args=None):
    """Get server configuration from args or default settings."""
    if args is None:
        host = settings.AUTOMAGIK_API_HOST
        port = int(settings.AUTOMAGIK_API_PORT)
        reload_flag = None
    else:
        host = args.host
        port = args.port
        reload_flag = args.reload
    
    # Determine if auto-reload should be enabled
    # If --reload flag is explicitly provided, use that value
    # Otherwise, auto-enable in development mode BUT disable for systemd
    if reload_flag is not None:
        should_reload = reload_flag
    elif os.environ.get('INVOCATION_ID'):  # Running under systemd
        should_reload = False  # Disable reload for systemd to fix signal handling
    else:
        should_reload = settings.ENVIRONMENT == Environment.DEVELOPMENT
    
    return host, port, should_reload

def log_server_config(host, port, should_reload):
    """Log the server configuration."""
    reload_status = "Enabled" if should_reload else "Disabled"
    logger.info("Starting server with configuration:")
    logger.info(f"├── Host: {host}")
    logger.info(f"├── Port: {port}")
    logger.info(f"└── Auto-reload: {reload_status}")

# Signal handling removed - let uvicorn handle signals natively
# This prevents conflicts with uvicorn's reloader process

def main():
    """Run the Automagik Agents API."""
    try:
        # Let uvicorn handle signals natively for proper shutdown
        
        # Log startup message
        logger.info("Starting Automagik Agents API")
        
        # Check if application is being run with arguments
        if len(sys.argv) > 1:
            # Parse command line arguments
            parser = create_argument_parser()
            args = parser.parse_args()
            host, port, should_reload = get_server_config(args)
        else:
            # Use default settings
            host, port, should_reload = get_server_config()
        
        # Log configuration
        log_server_config(host, port, should_reload)
        
        # Run the server with proper signal handling
        uvicorn.run(
            "automagik.main:app",
            host=host,
            port=port,
            reload=should_reload,
            # Add signal handlers for graceful shutdown
            access_log=False,  # Reduce log noise
            # Force uvicorn to handle signals properly
            use_colors=False,
            # Add graceful shutdown timeout
            timeout_graceful_shutdown=5
        )
    except Exception as e:
        logger.error(f"Error running application: {str(e)}")
        # Print traceback for easier debugging
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 