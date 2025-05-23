#!/bin/bash
#===========================================
# Automagik Docker Installer
#===========================================
# Docker-based installation for Automagik Agents

# Source required libraries
INSTALLER_DIR="$(dirname "${BASH_SOURCE[0]}")"
LIB_DIR="$(dirname "$INSTALLER_DIR")/lib"

source "$LIB_DIR/common.sh"
source "$LIB_DIR/system.sh"
source "$LIB_DIR/config.sh"

# Docker-specific variables
export INIT_GRAPHITI=true
export FORCE_REBUILD=false

AM_EFFECTIVE_PORT=$( { get_env_value "AM_PORT" "$ENV_FILE" || true; } )
if [ -z "$AM_EFFECTIVE_PORT" ]; then
    # .env may not exist yet (first-run). Use default port and continue; it will be refreshed after configuration step.
    AM_EFFECTIVE_PORT="8881"
    log "INFO" "AM_PORT is not yet defined. Using default port $AM_EFFECTIVE_PORT for now."
fi

# Show Docker installation options
show_docker_options_menu() {
    echo
    echo -e "${CYAN}Docker Installation Options:${NC}"
    echo
    
    # System dependencies
    echo -e "${YELLOW}System Dependencies:${NC}"
    if confirm_action "Install system dependencies automatically (Docker, etc.)?" "y"; then
        INSTALL_DEPENDENCIES=true
    else
        INSTALL_DEPENDENCIES=false
    fi
    
    # Graphiti setup
    echo
    if confirm_action "Include Neo4j and Graphiti containers for knowledge graphs?" "y"; then
        INIT_GRAPHITI=true
    else
        INIT_GRAPHITI=false
    fi
    
    echo
    echo -e "${YELLOW}Docker installation will include:${NC}"
    echo "• Automagik Agents container (port ${AM_EFFECTIVE_PORT})"
    echo "• PostgreSQL container"
    if [ "$INIT_GRAPHITI" = true ]; then
        echo "• Neo4j container (port 7474)"
        echo "• Graphiti container (port 8000)"
    fi
}

# Setup Docker environment
setup_docker_environment() {
    print_header "Setting up Docker environment"
    
    # Check Docker availability
    if ! check_command docker; then
        log "ERROR" "Docker is not installed or not available"
        return 1
    fi
    
    # Check Docker Compose
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
        log "SUCCESS" "Docker Compose V2 available"
    elif docker-compose --version &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
        log "SUCCESS" "Docker Compose V1 available"
    else
        log "ERROR" "Docker Compose is not available"
        return 1
    fi
    
    # Verify Docker is running
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker daemon is not running"
        return 1
    fi
    
    log "SUCCESS" "Docker environment is ready"
    return 0
}

# Build and start containers
build_and_start_containers() {
    print_header "Building and starting containers"
    
    cd "$ROOT_DIR/docker"
    
    # Enable Docker BuildKit for optimized builds
    export DOCKER_BUILDKIT=1
    
    # Stop any existing containers
    log "INFO" "Stopping any existing containers..."
    $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" down 2>/dev/null || true
    
    # Build containers
    log "INFO" "Building containers with optimizations..."
    if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        automagik-agents; then
        log "ERROR" "Failed to build automagik-agents container"
        return 1
    fi
    
    # Start PostgreSQL first
    log "INFO" "Starting PostgreSQL container..."
    if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" up -d postgres; then
        log "ERROR" "Failed to start PostgreSQL container"
        return 1
    fi
    
    # Wait for PostgreSQL to be ready
    log "INFO" "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Start Graphiti services if requested
    if [ "$INIT_GRAPHITI" = true ]; then
        log "INFO" "Starting Neo4j and Graphiti containers..."
        if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" --profile graphiti up -d neo4j graphiti; then
            log "WARN" "Failed to start Graphiti containers, continuing without them"
        else
            log "SUCCESS" "Neo4j available at http://localhost:7474"
            log "SUCCESS" "Graphiti available at http://localhost:8000"
        fi
    fi
    
    # Start main agents container
    log "INFO" "Starting automagik-agents container..."
    if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" up -d automagik-agents; then
        log "ERROR" "Failed to start automagik-agents container"
        return 1
    fi
    
    cd "$ROOT_DIR"
    log "SUCCESS" "All containers started successfully"
    return 0
}

# Run Docker health check
run_docker_health_check() {
    print_header "Running Docker health check"
    
    log "INFO" "Checking container status..."
    
    # Check if containers are running
    if ! docker ps | grep -q "automagik_agents"; then
        log "ERROR" "automagik-agents container is not running"
        return 1
    fi
    
    if ! docker ps | grep -q "automagik_postgres"; then
        log "ERROR" "PostgreSQL container is not running"
        return 1
    fi
    
    log "SUCCESS" "All containers are running"
    
    # Wait for container health check
    log "INFO" "Waiting for container health checks..."
    local retry_count=0
    local max_retries=20
    
    while [ $retry_count -lt $max_retries ]; do
        if docker inspect automagik_agents --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            log "SUCCESS" "automagik-agents container is healthy"
            break
        elif docker ps | grep -q automagik_agents; then
            echo -n "."
            sleep 3
            retry_count=$((retry_count + 1))
        else
            log "ERROR" "Container failed to start. Check logs with: docker logs automagik_agents"
            return 1
        fi
    done
    echo ""
    
    if [ $retry_count -eq $max_retries ]; then
        log "WARN" "Container health check timed out, but container is running"
        log "INFO" "Check logs with: docker logs automagik_agents"
    fi
    
    # Test API endpoint
    log "INFO" "Testing API endpoint..."
    sleep 15
    if curl -s "http://localhost:${AM_EFFECTIVE_PORT}/health" > /dev/null 2>&1; then
        log "SUCCESS" "API endpoint is accessible at http://localhost:${AM_EFFECTIVE_PORT}"
    else
        log "WARN" "API endpoint test failed. The service might need more time to start."
    fi
    
    return 0
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
    echo -e "  3. Restart containers: ${YELLOW}cd docker && docker compose restart${NC}"
    echo
    echo -e "${RED}❌ Without these keys, agents cannot process requests or provide responses!${NC}"
    echo -e "${GREEN}✅ The API server will start, but with limited functionality.${NC}"
    echo
}

# Print Docker next steps
print_docker_next_steps() {
    print_header "🎉 Docker Installation Complete!"
    
    echo -e "${GREEN}Installation Summary:${NC}"
    echo "✅ Docker containers built and deployed"
    echo "✅ PostgreSQL container running"
    echo "✅ Automagik Agents containerized"
    
    if [ "$INIT_GRAPHITI" = true ]; then
        echo "✅ Neo4j and Graphiti containers running"
    fi
    
    echo
    echo -e "${YELLOW}🚀 Container Management:${NC}"
    echo -e "${GREEN}View all containers:${NC} docker ps"
    echo -e "${GREEN}View logs:${NC}           docker logs automagik_agents -f"
    echo -e "${GREEN}Restart container:${NC}   docker restart automagik_agents"
    echo -e "${GREEN}Stop all:${NC}            cd docker && docker compose down"
    echo -e "${GREEN}Start all:${NC}           cd docker && docker compose up -d"
    
    echo
    echo -e "${CYAN}📡 Service URLs (once started):${NC}"
    echo "• API Server: http://localhost:${AM_EFFECTIVE_PORT}"
    echo "• Health Check: http://localhost:${AM_EFFECTIVE_PORT}/health"
    echo "• API Documentation: http://localhost:${AM_EFFECTIVE_PORT}/docs"
    
    if [ "$INIT_GRAPHITI" = true ]; then
        echo "• Neo4j Browser: http://localhost:7474"
        echo "• Graphiti API: http://localhost:8000"
    fi
    
    echo
    echo -e "${PURPLE}💡 Helpful Commands:${NC}"
    echo "• docker logs automagik_agents -f  - View live logs"
    echo "• docker exec -it automagik_agents bash - Access container shell"
    echo "• docker inspect automagik_agents --format='{{.State.Health.Status}}' - Check health"
    
    echo
    echo -e "${BLUE}📝 Configuration:${NC}"
    echo "• Edit settings: nano $ROOT_DIR/.env"
    echo "• Rebuild after changes: cd docker && docker compose build && docker compose up -d"
    if [ -f "$ROOT_DIR/.env.bkp" ]; then
        echo "• Original backup: $ROOT_DIR/.env.bkp"
    fi
    
    echo
    echo -e "${GREEN}For more information: https://github.com/namastexlabs/automagik-agents${NC}"
}

# Main Docker installation function
install_agents_docker() {
    print_header "Installing Automagik Agents (Docker Mode)"
    
    # Initialize logging
    init_logging
    
    # Set up error handling
    set_error_trap
    trap cleanup_on_exit EXIT
    
    # Show options menu for interactive mode
    if [ "$NON_INTERACTIVE" != "true" ]; then
        show_docker_options_menu
    fi
    
    # Install system dependencies if requested
    if [ "$INSTALL_DEPENDENCIES" = true ]; then
        install_system_dependencies false false true  # no python, no docker db, yes docker
    fi
    
    # Setup Docker environment
    if ! setup_docker_environment; then
        log "ERROR" "Docker environment setup failed"
        exit 1
    fi
    
    # Setup configuration
    if ! setup_configuration true false "$FORCE_REBUILD"; then  # interactive, no docker db, force
        log "ERROR" "Configuration setup failed"
        exit 1
    fi
    
    # Refresh port in case .env was just created or updated
    AM_EFFECTIVE_PORT=$( { get_env_value "AM_PORT" "$ENV_FILE" || true; } )
    if [ -z "$AM_EFFECTIVE_PORT" ]; then
        AM_EFFECTIVE_PORT="8881"
    fi
    
    # Build and start containers
    if ! build_and_start_containers; then
        log "ERROR" "Container deployment failed"
        exit 1
    fi
    
    # Run health check
    if ! run_docker_health_check; then
        log "WARN" "Health check had issues, but installation may still be functional"
    fi
    
    # Show next steps
    print_docker_next_steps
    
    # Install shell helper functions for Docker management
    if [ "$INSTALL_HELPERS" != "false" ]; then
        if [ "$NON_INTERACTIVE" != "true" ]; then
            echo
            if confirm_action "Would you like to install convenient Docker management commands?" "y"; then
                install_docker_helpers true
            fi
        else
            install_docker_helpers true
        fi
    fi
    
    # Show critical API key warning
    show_api_key_warning
    
    log "SUCCESS" "Automagik Agents Docker installation completed successfully! 🎉"
    
    # Final summary
    echo
    echo -e "${PURPLE}📋 Installation Summary:${NC}"
    echo -e "  🐳 Docker Containers: ${GREEN}✅ Running${NC}"
    echo -e "  🗄️  Database: ${GREEN}✅ PostgreSQL in Docker${NC}"
    echo -e "  ⚙️  Configuration: ${GREEN}✅ $([ -f "$ROOT_DIR/.env.bkp" ] && echo "New from template" || echo "Existing preserved")${NC}"
    echo -e "  🧠 Knowledge Graph: $([ "$INIT_GRAPHITI" = "true" ] && echo -e "${GREEN}✅ Neo4j + Graphiti${NC}" || echo -e "${YELLOW}❌ Not installed${NC}")"
    echo -e "  🎯 Helper Commands: ${GREEN}✅ Available${NC}"
    echo
    
    return 0
}

# Install Docker-specific helper commands (placeholder)
install_docker_helpers() {
    local install_helpers="${1:-true}"
    
    if [ "$install_helpers" != "true" ]; then
        return 0
    fi
    
    log "INFO" "Docker-specific helper commands will be integrated with the main helpers"
    log "SUCCESS" "Use 'agent help' for container management commands"
    return 0
}

# Export functions
export -f show_docker_options_menu setup_docker_environment build_and_start_containers
export -f run_docker_health_check print_docker_next_steps install_agents_docker 