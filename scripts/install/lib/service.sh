#!/bin/bash
#===========================================
# Automagik Service Management Library
#===========================================
# Functions for systemd service creation and management

# Source common utilities if not already loaded
if [ -z "$COMMON_LOADED" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
    COMMON_LOADED=true
fi

# Service-related variables
export SERVICE_NAME="automagik-agents"
export SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
export SERVICE_USER=$(whoami)

# Check if systemd is available
check_systemd_available() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log "INFO" "Systemd service installation is only available on Linux"
        return 1
    fi
    
    if ! command -v systemctl &> /dev/null; then
        log "ERROR" "Systemd is not available on this system"
        return 1
    fi
    
    return 0
}

# Detect application port
detect_application_port() {
    local detected_port=8881
    
    # Check .env file for AM_PORT
    if [ -f "$ROOT_DIR/.env" ]; then
        local env_port=$(grep -E '^AM_PORT=' "$ROOT_DIR/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
        if [ -n "$env_port" ]; then
            detected_port=$env_port
        fi
    fi
    
    # Check for running process on different ports
    for check_port in $detected_port 8881 18881; do
        if curl -s "http://localhost:$check_port/health" > /dev/null 2>&1; then
            echo $check_port
            return
        fi
    done
    
    echo $detected_port
}

# Create systemd service file
create_service_file() {
    local work_dir="$ROOT_DIR"
    local user="$SERVICE_USER"
    local venv_path="$ROOT_DIR/$VENV_NAME"
    
    log "INFO" "Creating systemd service file..."
    
    # Create service file content
    local service_content="[Unit]
Description=AutoMagik Agents API Server
After=network.target
Requires=network.target

[Service]
Type=simple
User=$user
WorkingDirectory=$work_dir
Environment=PATH=$venv_path/bin
ExecStart=$venv_path/bin/python -m src
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=automagik-agents

[Install]
WantedBy=multi-user.target"
    
    # Write service file to temporary location
    echo "$service_content" > "/tmp/$SERVICE_NAME.service"
    
    # Install service file
    if sudo mv "/tmp/$SERVICE_NAME.service" "$SERVICE_FILE"; then
        log "SUCCESS" "Service file installed successfully"
        return 0
    else
        log "ERROR" "Failed to install service file"
        return 1
    fi
}

# Enable and configure service
enable_service() {
    log "INFO" "Enabling systemd service..."
    
    # Reload systemd and enable service
    if ! sudo systemctl daemon-reload; then
        log "ERROR" "Failed to reload systemd daemon"
        return 1
    fi
    
    if ! sudo systemctl enable "$SERVICE_NAME"; then
        log "ERROR" "Failed to enable service"
        return 1
    fi
    
    log "SUCCESS" "Service enabled successfully"
    return 0
}

# Start service
start_service() {
    log "INFO" "Starting service..."
    
    if sudo systemctl start "$SERVICE_NAME"; then
        log "SUCCESS" "Service started successfully"
        
        # Give service time to start
        sleep 5
        
        # Check service status
        if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
            log "SUCCESS" "Service is running and healthy"
            
            # Test API endpoint
            local detected_port=$(detect_application_port)
            if curl -s "http://localhost:$detected_port/health" > /dev/null 2>&1; then
                log "SUCCESS" "API is responding at http://localhost:$detected_port"
            else
                log "WARN" "Service is running but API might still be starting up"
                log "INFO" "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
            fi
        else
            log "ERROR" "Service failed to start properly"
            log "INFO" "Check logs with: sudo journalctl -u $SERVICE_NAME"
            return 1
        fi
    else
        log "ERROR" "Failed to start service"
        return 1
    fi
    
    return 0
}

# Show service management commands
show_service_commands() {
    local detected_port=$(detect_application_port)
    
    echo
    echo -e "${PURPLE}🔧 Service Management Commands:${NC}"
    echo -e "  Start:   ${GREEN}sudo systemctl start $SERVICE_NAME${NC}"
    echo -e "  Stop:    ${GREEN}sudo systemctl stop $SERVICE_NAME${NC}"
    echo -e "  Restart: ${GREEN}sudo systemctl restart $SERVICE_NAME${NC}"
    echo -e "  Status:  ${GREEN}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "  Logs:    ${GREEN}sudo journalctl -u $SERVICE_NAME -f${NC}"
    echo -e "  Disable: ${GREEN}sudo systemctl disable $SERVICE_NAME${NC}"
    echo
    echo -e "${CYAN}📡 Service Endpoints:${NC}"
    echo -e "  API Server: ${GREEN}http://localhost:$detected_port${NC}"
    echo -e "  Health Check: ${GREEN}http://localhost:$detected_port/health${NC}"
    echo -e "  API Documentation: ${GREEN}http://localhost:$detected_port/docs${NC}"
    echo
}

# Install service with user confirmation
install_service() {
    local auto_start="${1:-false}"
    
    # Check if systemd is available
    if ! check_systemd_available; then
        return 1
    fi
    
    print_header "Service Installation"
    
    # Create service file
    if ! create_service_file; then
        log "ERROR" "Failed to create service file"
        return 1
    fi
    
    # Enable service
    if ! enable_service; then
        log "ERROR" "Failed to enable service"
        return 1
    fi
    
    log "SUCCESS" "Service installed and enabled successfully!"
    
    # Ask if user wants to start the service now
    echo
    local should_start="$auto_start"
    if [ "$auto_start" != "true" ]; then
        should_start=$(confirm_action "Would you like to start the service now?" "y" && echo "true" || echo "false")
    fi
    
    if [ "$should_start" = "true" ]; then
        if start_service; then
            log "SUCCESS" "✅ Service started successfully!"
        else
            log "ERROR" "❌ Failed to start service"
            return 1
        fi
    else
        log "INFO" "Service created but not started. Use 'sudo systemctl start $SERVICE_NAME' to start it later."
    fi
    
    return 0
}

# Check if service is installed
is_service_installed() {
    [ -f "$SERVICE_FILE" ]
}

# Check if service is running
is_service_running() {
    if ! check_systemd_available; then
        return 1
    fi
    
    sudo systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null
}

# Get service status
get_service_status() {
    if ! check_systemd_available; then
        echo "systemd not available"
        return 1
    fi
    
    if ! is_service_installed; then
        echo "not installed"
        return 1
    fi
    
    if is_service_running; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Uninstall service
uninstall_service() {
    if ! check_systemd_available; then
        return 1
    fi
    
    if ! is_service_installed; then
        log "INFO" "Service is not installed"
        return 0
    fi
    
    log "INFO" "Uninstalling service..."
    
    # Stop service if running
    if is_service_running; then
        log "INFO" "Stopping service..."
        sudo systemctl stop "$SERVICE_NAME" || true
    fi
    
    # Disable service
    log "INFO" "Disabling service..."
    sudo systemctl disable "$SERVICE_NAME" || true
    
    # Remove service file
    log "INFO" "Removing service file..."
    sudo rm -f "$SERVICE_FILE"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    log "SUCCESS" "Service uninstalled successfully"
    return 0
}

# Show service status and information
show_service_status() {
    if ! check_systemd_available; then
        log "INFO" "Systemd service management is not available on this system"
        return 0
    fi
    
    local status=$(get_service_status)
    
    echo
    echo -e "${CYAN}🔧 Service Status:${NC}"
    echo -e "  Name: ${GREEN}$SERVICE_NAME${NC}"
    echo -e "  Status: ${GREEN}$status${NC}"
    
    if [ "$status" = "running" ]; then
        local detected_port=$(detect_application_port)
        echo -e "  Port: ${GREEN}$detected_port${NC}"
        
        # Test API health
        if curl -s "http://localhost:$detected_port/health" > /dev/null 2>&1; then
            echo -e "  Health: ${GREEN}✅ API responding${NC}"
        else
            echo -e "  Health: ${YELLOW}⚠️  API not responding${NC}"
        fi
    fi
    
    if is_service_installed; then
        show_service_commands
    fi
    
    return 0
}

# Export functions
export -f check_systemd_available detect_application_port create_service_file
export -f enable_service start_service show_service_commands install_service
export -f is_service_installed is_service_running get_service_status
export -f uninstall_service show_service_status 