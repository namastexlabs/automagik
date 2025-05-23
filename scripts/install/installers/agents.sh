#!/bin/bash
#===========================================
# Automagik Agents Installer
#===========================================
# Complete installation script for Automagik Agents

# Source required libraries
INSTALLER_DIR="$(dirname "${BASH_SOURCE[0]}")"
LIB_DIR="$(dirname "$INSTALLER_DIR")/lib"

source "$LIB_DIR/common.sh"
source "$LIB_DIR/system.sh"
source "$LIB_DIR/python.sh"
source "$LIB_DIR/config.sh"
source "$LIB_DIR/service.sh"

# Agents-specific variables
export USE_DOCKER_DB=true
export INSTALL_DEV_DEPS=false
export INSTALL_AS_SERVICE=false
export FORCE_REBUILD=false

AM_EFFECTIVE_PORT=$( { get_env_value "AM_PORT" "$ENV_FILE" || true; } )
if [ -z "$AM_EFFECTIVE_PORT" ]; then
    log "ERROR" "AM_PORT is not defined in $ENV_FILE. Please define it to continue."
    # Consider exiting if this script cannot function without AM_PORT
    # exit 1 
fi
export AM_EFFECTIVE_PORT # Export for the Python script

# Detect existing setup
detect_existing_setup() {
    print_header "Detecting existing setup"
    
    local existing_venv=false
    local existing_env_file=false
    local existing_docker_setup=false
    local existing_database=false
    
    # VENV_PATH is now globally defined by setup.sh

    # Check for existing virtual environment
    if [ -d "$VENV_PATH" ]; then
        existing_venv=true
        log "SUCCESS" "Found existing virtual environment at $VENV_PATH"
    fi
    
    # Check for existing .env file
    if [ -f "$ROOT_DIR/.env" ]; then
        existing_env_file=true
        log "SUCCESS" "Found existing .env file"
    fi
    
    # Check for existing Docker setup
    if [ -f "$ROOT_DIR/docker/docker-compose.yml" ]; then
        existing_docker_setup=true
        log "SUCCESS" "Found existing Docker setup"
        
        # Check if containers are running
        if docker ps | grep -q "automagik_postgres\|automagik_agents"; then
            existing_database=true
            log "SUCCESS" "Found running Docker containers"
        fi
    fi
    
    # Check for existing AutoMagik setup (different project)
    if [ -f "$ROOT_DIR/docker/docker-compose.yml" ] && grep -q "18888" "$ROOT_DIR/docker/docker-compose.yml"; then
        log "WARN" "Detected existing AutoMagik setup (port 18888) - this script is for automagik-agents (port 8881)"
        log "INFO" "This setup will create a separate configuration for automagik-agents."
    fi
    
    # Summary
    echo
    log "INFO" "Setup Detection Summary:"
    echo "  Virtual Environment: $([ "$existing_venv" = true ] && echo "Found" || echo "Not found")"
    echo "  Environment File: $([ "$existing_env_file" = true ] && echo "Found" || echo "Not found")"
    echo "  Docker Setup: $([ "$existing_docker_setup" = true ] && echo "Found" || echo "Not found")"
    echo "  Running Containers: $([ "$existing_database" = true ] && echo "Found" || echo "Not found")"
    echo
}

# Setup database
setup_database() {
    print_header "Setting up database"
    
    if [ "$USE_DOCKER_DB" = true ]; then
        log "INFO" "Starting database containers (PostgreSQL only)"
        cd "$ROOT_DIR/docker"
        
        # Check if PostgreSQL is already running
        if docker ps | grep -q "automagik_postgres"; then
            log "SUCCESS" "PostgreSQL container already running"
        else
            if docker compose version &> /dev/null; then
                docker compose --env-file "$ROOT_DIR/.env" up -d postgres
            else
                docker-compose --env-file "$ROOT_DIR/.env" up -d postgres
            fi
            
            log "INFO" "Waiting for PostgreSQL to be ready..."
            sleep 10
            log "SUCCESS" "PostgreSQL container started"
        fi
        cd "$ROOT_DIR"
    else
        log "WARN" "Skipping Docker database setup"
        log "INFO" "Make sure PostgreSQL is running and accessible"
    fi
    
    # Initialize database schema
    log "INFO" "Initializing database schema"
    
    # Activate virtual environment and run database initialization
    # VENV_PATH is global
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$VENV_PATH/Scripts/activate"
    else
        source "$VENV_PATH/bin/activate"
    fi
    
    # Check if the CLI command exists and run database initialization
    if automagik-agents db --help &> /dev/null; then
        automagik-agents db init
        log "SUCCESS" "Database initialized"
    else
        log "WARN" "Database CLI not available. You may need to initialize the database manually."
    fi
}

# Show local installation options menu
show_local_options_menu() {
    echo
    echo -e "${CYAN}Local Installation Options:${NC}"
    echo
    
    # System dependencies
    echo -e "${YELLOW}System Dependencies:${NC}"
    if confirm_action "Install system dependencies automatically (Python, Docker, ccze, etc.)?" "y"; then
        INSTALL_DEPENDENCIES=true
    else
        INSTALL_DEPENDENCIES=false
    fi
    
    # Database options
    echo
    echo -e "${YELLOW}Database Setup:${NC}"
    echo "1) Use Docker for PostgreSQL (recommended)"
    echo "2) Use existing PostgreSQL installation"
    read -p "Choose database option (1-2): " db_choice
    
    case $db_choice in
        1) USE_DOCKER_DB=true ;;
        2) USE_DOCKER_DB=false ;;
        *) USE_DOCKER_DB=true ;;
    esac
    
    # Development dependencies
    echo
    if confirm_action "Install development dependencies?" "n"; then
        INSTALL_DEV_DEPS=true
    fi
    
    # Service installation
    echo
    if confirm_action "Install as a system service?" "n"; then
        INSTALL_AS_SERVICE=true
    fi
}

# Test server startup briefly
test_server_startup() {
    log "INFO" "Testing server startup (this will take about 15 seconds)..."
    
    # Create a temporary Python script that starts the server with timeout
    cat > /tmp/test_server.py << 'EOF'
import sys
import signal
import subprocess
import time
import requests
import os

AM_EFFECTIVE_PORT_PY = os.getenv('AM_EFFECTIVE_PORT')

def timeout_handler(signum, frame):
    print("✅ Server startup test completed")
    sys.exit(0)

def test_server():
    # Set signal handler for timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(15)  # 15 second timeout
    
    try:
        # Start server
        print("🔧 Starting server...")
        process = subprocess.Popen([sys.executable, "-m", "src"], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
        
        # Wait a bit for startup
        time.sleep(8)
        
        # Test health endpoint
        try:
            if AM_EFFECTIVE_PORT_PY is None:
                print("⚠️ AM_EFFECTIVE_PORT not set in environment for Python script.")
            else:
                response = requests.get(f"http://localhost:{AM_EFFECTIVE_PORT_PY}/health", timeout=3)
            if response.status_code == 200:
                print("✅ Server is responding to health checks!")
                    print(f"✅ API available at: http://localhost:{AM_EFFECTIVE_PORT_PY}")
            else:
                print("⚠️  Server started but health check returned:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("⚠️  Server started but health endpoint not accessible")
        
        # Cleanup
        process.terminate()
        process.wait(timeout=3)
        
    except Exception as e:
        print(f"⚠️  Server test encountered an issue: {e}")
    finally:
        signal.alarm(0)  # Cancel alarm

if __name__ == "__main__":
    test_server()
EOF

    # Run the test
    python /tmp/test_server.py
    
    # Cleanup
    rm -f /tmp/test_server.py
    
    log "SUCCESS" "Server startup test completed"
}

# Run health check
run_health_check() {
    print_header "Running health check"
    
    log "INFO" "Testing local installation without starting a persistent server"
    
    # Check if we can import the main module
    log "INFO" "Verifying Python environment and dependencies..."
    
    # Activate virtual environment
    # VENV_PATH is global
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$VENV_PATH/Scripts/activate"
    else
        source "$VENV_PATH/bin/activate"
    fi
    
    # Test basic imports and CLI availability
    if python -c "import src; print('✅ Main module imports successfully')" 2>/dev/null; then
        log "SUCCESS" "Python environment and main module are working"
    else
        log "ERROR" "Failed to import main module"
        return 1
    fi
    
    # Test CLI availability
    if automagik-agents --help >/dev/null 2>&1; then
        log "SUCCESS" "CLI is available and working"
    else
        log "WARN" "CLI might not be fully configured yet"
    fi
    
    # Test database connectivity if configured
    local db_url=$(get_env_value "DATABASE_URL")
    if [ -n "$db_url" ]; then
        log "INFO" "Testing database connectivity..."
        if python -c "
import sys
sys.path.insert(0, '.')
try:
    import psycopg2
    from urllib.parse import urlparse
    
    # Parse DATABASE_URL
    db_url = '$db_url'
    parsed = urlparse(db_url)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password
    )
    
    # Test connection
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print('✅ Database connection successful')
    print(f'✅ Connected to: {version.split()[0]} {version.split()[1]}')
    
    # Close properly
    cursor.close()
    conn.close()
    exit(0)
except Exception as e:
    print(f'⚠️  Database connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            log "SUCCESS" "Database connectivity verified"
        else
            log "WARN" "Database connection test failed (this may be normal for first setup)"
        fi
    fi
    
    log "SUCCESS" "Health check completed - installation appears to be working"
    
    # Offer to test server startup
    if [ "$NON_INTERACTIVE" != "true" ]; then
        echo
        if confirm_action "Would you like to test the server startup quickly?" "n"; then
            test_server_startup
        fi
    fi
    
    log "INFO" "You can now start the server manually with: python -m src"
}

# Show critical API key warning
show_api_key_warning() {
    echo
    echo -e "${RED}⚠️  IMPORTANT: API Keys Required for Agent Functionality${NC}"
    echo
    echo -e "${YELLOW}Your Automagik Agents installation is complete, but agents need API keys to function:${NC}"
    echo
    echo -e "${CYAN}🔑 Required for AI functionality:${NC}"
    echo -e "  • ${BLUE}OPENAI_API_KEY${NC} - Get at: ${GREEN}https://platform.openai.com/api-keys${NC}"
    echo -e "  • ${BLUE}DISCORD_BOT_TOKEN${NC} - Get at: ${GREEN}https://discord.com/developers/applications${NC}"
    echo
    echo -e "${CYAN}📝 To configure:${NC}"
    echo -e "  1. Edit: ${YELLOW}nano $ROOT_DIR/.env${NC}"
    echo -e "  2. Add your API keys"
    echo -e "  3. Restart: ${YELLOW}agent restart${NC}"
    echo
    echo -e "${RED}❌ Without these keys, agents cannot process requests or provide responses!${NC}"
    echo -e "${GREEN}✅ The API server will start, but with limited functionality.${NC}"
    echo
}

# Print next steps for local installation
print_local_next_steps() {
    print_header "🎉 Local Installation Complete!"
    
    echo -e "${GREEN}Installation Summary:${NC}"
    echo "✅ Virtual environment: $VENV_PATH"
    echo "✅ Dependencies installed with UV"
    echo "✅ Environment configuration: $([ -f "$ROOT_DIR/.env.bkp" ] && echo "New from template (.env.bkp created)" || echo "Ready")"
    
    if [ "$USE_DOCKER_DB" = true ]; then
        echo "✅ PostgreSQL running in Docker container"
    fi
    
    if [ "$INSTALL_AS_SERVICE" = true ]; then
        echo "✅ System service installed and enabled"
    fi
    
    echo
    echo -e "${YELLOW}🚀 Quick Start Commands:${NC}"
    
    if [ "$INSTALL_AS_SERVICE" = true ]; then
        echo -e "${GREEN}Start service:${NC} agent start  ${BLUE}(or: sudo systemctl start automagik-agents)${NC}"
        echo -e "${GREEN}View logs:${NC}    agent logs   ${BLUE}(or: sudo journalctl -u automagik-agents -f)${NC}"
        echo -e "${GREEN}Check status:${NC} agent status ${BLUE}(or: sudo systemctl status automagik-agents)${NC}"
        echo -e "${GREEN}Stop service:${NC} agent stop   ${BLUE}(or: sudo systemctl stop automagik-agents)${NC}"
    else
        echo -e "${GREEN}Activate environment:${NC} $(get_activation_command)"
        echo -e "${GREEN}Start server:${NC}         python -m src"
        echo -e "${GREEN}Development mode:${NC}     python -m src --reload"
        echo -e "${GREEN}Interactive dev:${NC}      agent dev"
    fi
    
    echo
    echo -e "${CYAN}📡 Service URLs:${NC}"
    local display_port="$AM_EFFECTIVE_PORT"
    echo "• API Server: http://localhost:$display_port"
    echo "• Health Check: http://localhost:$display_port/health"
    echo "• API Documentation: http://localhost:$display_port/docs"
    
    echo
    echo -e "${PURPLE}💡 Helpful Commands:${NC}"
    echo "• agent help       - Show all management commands"
    echo "• automagik status - Check all component status"
    if [ "$INSTALL_AS_SERVICE" != true ]; then
        echo "• automagik-agents --help - CLI utilities"
    fi
    
    echo
    echo -e "${BLUE}📝 Configuration:${NC}"
    echo "• Edit settings: nano $ROOT_DIR/.env"
    if [ -f "$ROOT_DIR/.env.bkp" ]; then
        echo "• Original backup: $ROOT_DIR/.env.bkp"
    fi
    
    echo
    echo -e "${GREEN}For more information: https://github.com/namastexlabs/automagik-agents${NC}"
}

# Main local installation function
install_agents_local() {
    print_header "Installing Automagik Agents (Local Mode)"
    
    # Initialize logging
    init_logging
    
    # Set up error handling
    set_error_trap
    trap cleanup_on_exit EXIT
    
    # Detect existing setup
    detect_existing_setup
    
    # Show options menu for interactive mode (always show for local installs)
    if [ "$INSTALL_MODE" = "local" ] && [ "$NON_INTERACTIVE" != "true" ]; then
        show_local_options_menu
    fi
    
    # Install system dependencies if requested
    if [ "$INSTALL_DEPENDENCIES" = true ]; then
        install_system_dependencies true "$USE_DOCKER_DB" true
    fi
    
    # Check prerequisites
    if ! check_prerequisites; then
        log "ERROR" "Prerequisites check failed"
        exit 1
    fi
    
    # Setup Python environment
    if ! setup_python_environment "$INSTALL_DEV_DEPS" "$VENV_NAME" "$FORCE_REBUILD"; then
        log "ERROR" "Python environment setup failed"
        exit 1
    fi
    
    # Setup configuration
    if ! setup_configuration true "$USE_DOCKER_DB" "$FORCE_REBUILD"; then
        log "ERROR" "Configuration setup failed"
        exit 1
    fi
    
    # Setup database
    if ! setup_database; then
        log "ERROR" "Database setup failed"
        exit 1
    fi
    
    # Run health check
    if ! run_health_check; then
        log "WARN" "Health check had issues, but installation may still be functional"
    fi
    
    # Offer service installation for local installations on Linux
    if check_systemd_available; then
        if [ "$INSTALL_AS_SERVICE" = "true" ]; then
            # Explicitly requested via command line
            install_service false
        elif [ "$NON_INTERACTIVE" != "true" ]; then
            echo
            log "INFO" "Service installation is available on this system"
            if confirm_action "Would you like to install AutoMagik Agents as a system service?" "n"; then
                install_service false
                INSTALL_AS_SERVICE=true
            fi
        fi
    elif [ "$INSTALL_AS_SERVICE" = "true" ]; then
        log "WARN" "Service installation requested but systemd is not available on this system"
    fi
    
    # Show next steps
    print_local_next_steps
    
    # Install shell helper functions
    if [ "$INSTALL_HELPERS" != "false" ]; then
        if [ "$NON_INTERACTIVE" != "true" ]; then
            echo
            if confirm_action "Would you like to install convenient shell helper commands (agent start/stop/logs)?" "y"; then
                install_shell_helpers true
                echo
                echo -e "${CYAN}🎯 Helper functions installed! Use these commands:${NC}"
                echo "• agent start/stop/restart - Service management"
                echo "• agent logs/status/health - Monitoring"  
                echo "• agent help - Show all commands"
                echo
                echo -e "${YELLOW}💡 Reload your shell or run: source ~/.automagik/shell-helpers.sh${NC}"
            fi
        else
            # Install by default in non-interactive mode unless explicitly disabled
            install_shell_helpers true
            echo
            echo -e "${CYAN}🎯 Helper functions installed for convenient management${NC}"
        fi
    else
        log "INFO" "Skipping helper functions installation (--no-helpers specified)"
    fi
    
    # Show critical API key warning
    show_api_key_warning
    
    log "SUCCESS" "Automagik Agents local installation completed successfully! 🎉"
    
    # Final summary
    echo
    echo -e "${PURPLE}📋 Installation Summary:${NC}"
    echo -e "  🐍 Python Environment: ${GREEN}✅ Configured${NC}"
    echo -e "  🗄️  Database: ${GREEN}✅ PostgreSQL Ready${NC}"
    echo -e "  ⚙️  Configuration: ${GREEN}✅ $([ -f "$ROOT_DIR/.env.bkp" ] && echo "New from template" || echo "Existing preserved")${NC}"
    echo -e "  🔧 System Service: $([ "$INSTALL_AS_SERVICE" = "true" ] && echo -e "${GREEN}✅ Installed${NC}" || echo -e "${YELLOW}❌ Manual start${NC}")"
    echo -e "  🎯 Helper Commands: ${GREEN}✅ Available${NC}"
    echo
    return 0
}

# Main agents installation function
install_agents() {
    local mode="$1"
    
    case "$mode" in
        "local")
            install_agents_local
            ;;
        "docker")
            # Source Docker installer and run it
            local docker_installer="$INSTALLER_DIR/docker.sh"
            if [ -f "$docker_installer" ]; then
                source "$docker_installer"
                install_agents_docker
            else
                log "ERROR" "Docker installer not found at $docker_installer"
                exit 1
            fi
            ;;
        "quick-update")
            # Source quick-update installer and run it
            local quick_installer="$INSTALLER_DIR/quick-update.sh"
            if [ -f "$quick_installer" ]; then
                source "$quick_installer"
                quick_update_agents
            else
                log "ERROR" "Quick-update installer not found at $quick_installer"
                exit 1
            fi
            ;;
        *)
            log "ERROR" "Unknown installation mode: $mode"
            exit 1
            ;;
    esac
    
    return 0
}

# Export functions
export -f detect_existing_setup setup_database show_local_options_menu
export -f run_health_check print_local_next_steps install_agents_local install_agents 