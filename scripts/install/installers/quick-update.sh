#!/bin/bash
#===========================================
# Automagik Quick Update Installer
#===========================================
# Fast deployment of code changes without full rebuilds

# Source required libraries
INSTALLER_DIR="$(dirname "${BASH_SOURCE[0]}")"
LIB_DIR="$(dirname "$INSTALLER_DIR")/lib"

source "$LIB_DIR/common.sh"
source "$LIB_DIR/system.sh"

# Quick update variables
export UPDATE_MODE="smart"  # smart, force, or minimal
export PRESERVE_DATA=true
export USE_CACHE=true

# Detect what's currently running
detect_current_deployment() {
    print_header "Detecting current deployment"
    
    local has_service=false
    local has_containers=false
    local service_running=false
    local containers_running=false
    
    # Check systemd service
    if systemctl list-unit-files | grep -q automagik-agents 2>/dev/null; then
        has_service=true
        if systemctl is-active --quiet automagik-agents 2>/dev/null; then
            service_running=true
        fi
    fi
    
    # Check Docker containers
    if docker ps -a | grep -q automagik 2>/dev/null; then
        has_containers=true
        if docker ps | grep -q automagik 2>/dev/null; then
            containers_running=true
        fi
    fi
    
    log "INFO" "Current Deployment Status:"
    echo "  📋 Systemd Service: $([ "$has_service" = true ] && echo "✅ Installed" || echo "❌ Not found") $([ "$service_running" = true ] && echo "(Running)" || echo "(Stopped)")"
    echo "  🐳 Docker Containers: $([ "$has_containers" = true ] && echo "✅ Found" || echo "❌ Not found") $([ "$containers_running" = true ] && echo "(Running)" || echo "(Stopped)")"
    
    # Set deployment mode
    if [ "$has_containers" = true ]; then
        DEPLOYMENT_MODE="docker"
        log "SUCCESS" "Docker deployment detected - will perform container quick update"
    elif [ "$has_service" = true ]; then
        DEPLOYMENT_MODE="service" 
        log "SUCCESS" "Service deployment detected - will perform service quick restart"
    else
        log "ERROR" "No existing deployment found. Run full installation first."
        return 1
    fi
    
    return 0
}

# Show quick update options
show_quick_update_options() {
    echo
    echo -e "${CYAN}Quick Update Options:${NC}"
    echo
    echo -e "${YELLOW}Update Strategy:${NC}"
    echo "1) 🧠 Smart Update (recommended) - Only rebuild what changed"
    echo "2) ⚡ Force Update - Rebuild everything with optimizations"
    echo "3) 🚀 Minimal Update - Just restart without rebuild"
    read -p "Choose update strategy (1-3): " update_choice
    
    case $update_choice in
        1) UPDATE_MODE="smart" ;;
        2) UPDATE_MODE="force" ;;
        3) UPDATE_MODE="minimal" ;;
        *) 
            log "WARN" "Invalid choice, using smart update"
            UPDATE_MODE="smart"
            ;;
    esac
    
    echo
    echo -e "${YELLOW}Selected: ${GREEN}${UPDATE_MODE} update${NC}"
    case $UPDATE_MODE in
        "smart") echo "  • Analyzes changes and rebuilds only what's needed" ;;
        "force") echo "  • Forces rebuild with optimized caching" ;;
        "minimal") echo "  • Just restarts services/containers" ;;
    esac
}

# Analyze what needs updating
analyze_changes() {
    print_header "Analyzing changes"
    
    local needs_rebuild=false
    local src_changed=false
    local deps_changed=false
    
    if [ "$DEPLOYMENT_MODE" = "docker" ]; then
        # Check source code changes
        if [ -d "$ROOT_DIR/src" ]; then
            log "INFO" "Checking source code changes..."
            # Check if any Python files have changed more recently than the container
            if docker inspect automagik_agents &>/dev/null; then
                local container_time=$(docker inspect automagik_agents --format='{{.Created}}' | xargs -I {} date -d {} +%s 2>/dev/null || echo 0)
                local src_time=$(find "$ROOT_DIR/src" -name "*.py" -type f -newer <(date -d "@$container_time" +%Y%m%d%H%M.%S) 2>/dev/null | wc -l)
                
                if [ "$src_time" -gt 0 ]; then
                    src_changed=true
                    needs_rebuild=true
                    log "INFO" "📝 Source code changes detected"
                else
                    log "SUCCESS" "📝 No source code changes detected"
                fi
            else
                src_changed=true
                needs_rebuild=true
                log "INFO" "📝 Container not found - full rebuild needed"
            fi
        fi
        
        # Check dependency changes
        if [ -f "$ROOT_DIR/pyproject.toml" ] || [ -f "$ROOT_DIR/requirements.txt" ]; then
            log "INFO" "Checking dependency changes..."
            if docker inspect automagik_agents &>/dev/null; then
                local container_time=$(docker inspect automagik_agents --format='{{.Created}}' | xargs -I {} date -d {} +%s 2>/dev/null || echo 0)
                local deps_time=0
                
                [ -f "$ROOT_DIR/pyproject.toml" ] && deps_time=$(stat -c %Y "$ROOT_DIR/pyproject.toml" 2>/dev/null || echo 0)
                [ -f "$ROOT_DIR/requirements.txt" ] && deps_time=$(( deps_time > $(stat -c %Y "$ROOT_DIR/requirements.txt" 2>/dev/null || echo 0) ? deps_time : $(stat -c %Y "$ROOT_DIR/requirements.txt" 2>/dev/null || echo 0) ))
                
                if [ "$deps_time" -gt "$container_time" ]; then
                    deps_changed=true
                    needs_rebuild=true
                    log "INFO" "📦 Dependency changes detected"
                else
                    log "SUCCESS" "📦 No dependency changes detected"
                fi
            fi
        fi
    fi
    
    # Report analysis
    echo
    echo -e "${CYAN}📊 Change Analysis:${NC}"
    echo "  Source Code: $([ "$src_changed" = true ] && echo -e "${YELLOW}⚡ Changed${NC}" || echo -e "${GREEN}✅ Unchanged${NC}")"
    echo "  Dependencies: $([ "$deps_changed" = true ] && echo -e "${YELLOW}⚡ Changed${NC}" || echo -e "${GREEN}✅ Unchanged${NC}")"
    echo "  Rebuild Needed: $([ "$needs_rebuild" = true ] && echo -e "${YELLOW}⚡ Yes${NC}" || echo -e "${GREEN}✅ No${NC}")"
    
    # Override analysis based on update mode
    case $UPDATE_MODE in
        "force")
            needs_rebuild=true
            log "INFO" "🔧 Force mode: rebuilding regardless of changes"
            ;;
        "minimal")
            needs_rebuild=false
            log "INFO" "🚀 Minimal mode: skipping rebuild, restart only"
            ;;
    esac
    
    export NEEDS_REBUILD=$needs_rebuild
    export SRC_CHANGED=$src_changed
    export DEPS_CHANGED=$deps_changed
    
    return 0
}

# Quick update Docker containers
quick_update_docker() {
    print_header "Quick Docker Update"
    
    cd "$ROOT_DIR/docker"
    
    # Determine Docker Compose command
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # Enable optimizations
    export DOCKER_BUILDKIT=1
    
    if [ "$NEEDS_REBUILD" = true ]; then
        log "INFO" "🔧 Rebuilding containers with optimizations..."
        
        # Graceful stop to preserve data
        log "INFO" "Gracefully stopping automagik-agents container..."
        $DOCKER_COMPOSE stop automagik-agents 2>/dev/null || true
        
        # Build with cache optimizations
        local build_args="--build-arg BUILDKIT_INLINE_CACHE=1"
        
        if [ "$UPDATE_MODE" = "force" ] || [ "$DEPS_CHANGED" = true ]; then
            log "INFO" "Dependencies changed - using fresh build layers"
            build_args="$build_args --no-cache"
        else
            log "INFO" "Using cached dependency layers - faster build"
        fi
        
        # Build the container
        if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" build $build_args automagik-agents; then
            log "ERROR" "Failed to rebuild automagik-agents container"
            return 1
        fi
        
        log "SUCCESS" "Container rebuilt with optimizations"
    else
        log "INFO" "🚀 No rebuild needed - restarting existing container"
    fi
    
    # Start the container
    log "INFO" "Starting automagik-agents container..."
    if ! $DOCKER_COMPOSE --env-file "$ROOT_DIR/.env" up -d automagik-agents; then
        log "ERROR" "Failed to start automagik-agents container"
        return 1
    fi
    
    cd "$ROOT_DIR"
    log "SUCCESS" "Quick Docker update completed"
    return 0
}

# Quick update systemd service
quick_update_service() {
    print_header "Quick Service Update"
    
    if [ "$NEEDS_REBUILD" = true ]; then
        log "INFO" "🔧 Updating Python environment..."
        
        # Activate virtual environment
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            source "$ROOT_DIR/.venv/Scripts/activate"
        else
            source "$ROOT_DIR/.venv/bin/activate"
        fi
        
        # Update dependencies if needed
        if [ "$DEPS_CHANGED" = true ]; then
            log "INFO" "Updating dependencies..."
            uv sync
        fi
        
        # Install in editable mode to reflect code changes
        log "INFO" "Updating code installation..."
        uv pip install -e .
        
        log "SUCCESS" "Python environment updated"
    fi
    
    # Restart the service
    log "INFO" "Restarting automagik-agents service..."
    sudo systemctl restart automagik-agents
    
    # Wait and check
    sleep 3
    if systemctl is-active --quiet automagik-agents; then
        log "SUCCESS" "Service restarted successfully"
    else
        log "ERROR" "Service failed to restart"
        return 1
    fi
    
    log "SUCCESS" "Quick service update completed"
    return 0
}

# Run quick health check
quick_health_check() {
    print_header "Quick Health Check"
    
    local port=18881
    local max_retries=10
    local retry_count=0
    
    log "INFO" "Waiting for API to be ready..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            log "SUCCESS" "✅ API is healthy at http://localhost:$port"
            return 0
        fi
        
        echo -n "."
        sleep 2
        retry_count=$((retry_count + 1))
    done
    echo ""
    
    log "WARN" "API health check timed out, but update completed"
    log "INFO" "Check manually: curl http://localhost:$port/health"
    return 1
}

# Print quick update summary
print_quick_update_summary() {
    print_header "🚀 Quick Update Complete!"
    
    local update_time=$(date +"%H:%M:%S")
    
    echo -e "${GREEN}Update Summary (${update_time}):${NC}"
    echo "✅ Mode: $UPDATE_MODE update"
    echo "✅ Deployment: $DEPLOYMENT_MODE"
    echo "✅ Rebuilt: $([ "$NEEDS_REBUILD" = true ] && echo "Yes (optimized)" || echo "No (restart only)")"
    echo "✅ Data: Preserved"
    
    echo
    echo -e "${YELLOW}🎯 Quick Commands:${NC}"
    echo "• agent status  - Check current status"
    echo "• agent logs    - View live logs"
    echo "• agent health  - Test API health"
    
    echo
    echo -e "${CYAN}📡 Endpoints:${NC}"
    echo "• API: http://localhost:18881"
    echo "• Health: http://localhost:18881/health"
    echo "• Docs: http://localhost:18881/docs"
    
    echo
    echo -e "${PURPLE}💡 Development Workflow:${NC}"
    echo "• Make code changes"
    echo "• Run: ./scripts/install/setup.sh --component agents --mode quick-update"
    echo "• Or: Quick update via agent command (coming soon)"
}

# Main quick update function
quick_update_agents() {
    print_header "Automagik Quick Update"
    
    # Initialize logging
    init_logging
    
    # Detect current deployment
    if ! detect_current_deployment; then
        exit 1
    fi
    
    # Show options if interactive
    if [ "$NON_INTERACTIVE" != "true" ]; then
        show_quick_update_options
    else
        # Default to smart update in non-interactive mode
        UPDATE_MODE="smart"
        log "INFO" "Non-interactive mode: Using smart update strategy"
    fi
    
    # Analyze what needs updating
    if ! analyze_changes; then
        log "ERROR" "Change analysis failed"
        exit 1
    fi
    
    # Perform the appropriate update
    case $DEPLOYMENT_MODE in
        "docker")
            if ! quick_update_docker; then
                log "ERROR" "Docker quick update failed"
                exit 1
            fi
            ;;
        "service")
            if ! quick_update_service; then
                log "ERROR" "Service quick update failed" 
                exit 1
            fi
            ;;
    esac
    
    # Quick health check
    if ! quick_health_check; then
        log "WARN" "Health check failed, but update may still be successful"
    fi
    
    # Show summary
    print_quick_update_summary
    
    log "SUCCESS" "Quick update completed successfully! ⚡"
    return 0
}

# Export functions
export -f detect_current_deployment show_quick_update_options analyze_changes
export -f quick_update_docker quick_update_service quick_health_check
export -f print_quick_update_summary quick_update_agents 