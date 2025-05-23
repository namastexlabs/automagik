#!/bin/bash
#===========================================
# Automagik Shell Helper Functions
#===========================================
# Convenient commands for managing Automagik services

# Determine ROOT_DIR and ENV_FILE to find AM_PORT
# This helper script might be sourced from anywhere, so make a best guess.
# It's typically installed at $HOME/.automagik/shell-helpers.sh
# The project root is assumed to be $HOME/workspace/am-agents-labs or similar.

_SHELL_HELPERS_AM_PORT_FROM_ENV=""
# Try to find the .env file based on common project locations relative to $HOME
_PROJECT_ROOT_CANDIDATES=(
    "$HOME/workspace/am-agents-labs"
    "$HOME/projects/am-agents-labs"
    "$(pwd)" # If sourced from within the project
)

for r_candidate in "${_PROJECT_ROOT_CANDIDATES[@]}"; do
    if [ -f "$r_candidate/.env" ]; then
        _SHELL_HELPERS_ENV_FILE="$r_candidate/.env"
        if grep -q "^AM_PORT=" "$_SHELL_HELPERS_ENV_FILE" 2>/dev/null; then
            _SHELL_HELPERS_AM_PORT_FROM_ENV=$(grep "^AM_PORT=" "$_SHELL_HELPERS_ENV_FILE" | cut -d'=' -f2- | sed 's/^["\x27]//' | sed 's/["\x27]$//')
            break
        fi
    fi
done

# If not found, try to locate it via this script's path if it was installed by the installer
if [ -z "$_SHELL_HELPERS_AM_PORT_FROM_ENV" ] && [[ "${BASH_SOURCE[0]}" == *"/.automagik/shell-helpers.sh"* ]]; then
    _INSTALLED_HELPERS_PATH="${BASH_SOURCE[0]}"
    _AUTOMAGIK_DIR="$(dirname "$_INSTALLED_HELPERS_PATH")"
    _POSSIBLE_ROOT_FROM_INSTALLER_PATH="$(dirname "$_AUTOMAGIK_DIR")" # Assumes $HOME/.automagik, so parent is $HOME
    # This is still a guess; a robust solution would require the ROOT_DIR to be passed or set globally
    # For now, we fall back to common locations check or the default.
fi 

_AM_EFFECTIVE_PORT_VALUE=${_SHELL_HELPERS_AM_PORT_FROM_ENV}
if [ -z "$_AM_EFFECTIVE_PORT_VALUE" ]; then
  echo "[ERROR] AM_PORT is not defined in a discoverable .env file. Helper commands may not work correctly." >&2
  # Not exiting because this script is sourced. Commands will fail if port is needed and empty.
fi
AM_EFFECTIVE_PORT=${_AM_EFFECTIVE_PORT_VALUE}

# Automagik Agents Management
agent() {
    case "$1" in
        "start")
            # Check current status
            local service_available=false
            local container_available=false
            local service_running=false
            local container_running=false
            
            # Check if service is available and running
            if systemctl list-unit-files | grep -q automagik-agents 2>/dev/null; then
                service_available=true
                if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                    service_running=true
                fi
            fi
            
            # Check if container is available and running
            if docker ps -a | grep -q automagik_agents 2>/dev/null; then
                container_available=true
                if docker ps | grep -q automagik_agents 2>/dev/null; then
                    container_running=true
                fi
            fi
            
            # If both are running, show status
            if [ "$service_running" = true ] && [ "$container_running" = true ]; then
                echo "⚠️  Both service AND container are running!"
                echo "   Service: ✅ Running"
                echo "   Container: ✅ Running"
                echo "💡 Use 'agent status' for detailed information"
                return 0
            fi
            
            # If one is running, show which one
            if [ "$service_running" = true ]; then
                echo "✅ automagik-agents service is already running"
                return 0
            fi
            
            if [ "$container_running" = true ]; then
                echo "✅ automagik-agents container is already running"
                return 0
            fi
            
            # Nothing is running, decide what to start
            if [ "$service_available" = true ] && [ "$container_available" = true ]; then
                # Both are available, ask user
                echo "🔧 Both systemd service and Docker container are available."
                echo "Which would you like to start?"
                echo "1) Systemd service"
                echo "2) Docker container"
                read -p "Choose option (1-2): " start_choice
                
                case $start_choice in
                    1)
                        echo "🔧 Starting automagik-agents service..."
                        sudo systemctl start automagik-agents
                        sleep 2
                        if systemctl is-active --quiet automagik-agents; then
                            echo "✅ automagik-agents service started successfully"
                            echo "📡 API available at: http://localhost:${AM_EFFECTIVE_PORT}"
                        else
                            echo "❌ Failed to start automagik-agents service"
                            echo "📋 Check logs with: agent logs"
                        fi
                        ;;
                    2)
                        echo "🔧 Starting automagik-agents container..."
                        docker start automagik_agents
                        sleep 2
                        if docker ps | grep -q automagik_agents; then
                            echo "✅ automagik-agents container started successfully"
                            echo "📡 API available at: http://localhost:${AM_EFFECTIVE_PORT}"
                        else
                            echo "❌ Failed to start automagik-agents container"
                            echo "📋 Check logs with: agent logs"
                        fi
                        ;;
                    *)
                        echo "❌ Invalid choice. Operation cancelled."
                        ;;
                esac
                
            elif [ "$service_available" = true ]; then
                # Only service available
                echo "🔧 Starting automagik-agents service..."
                sudo systemctl start automagik-agents
                sleep 2
                if systemctl is-active --quiet automagik-agents; then
                    echo "✅ automagik-agents service started successfully"
                    echo "📡 API available at: http://localhost:${AM_EFFECTIVE_PORT}"
                else
                    echo "❌ Failed to start automagik-agents service"
                    echo "📋 Check logs with: agent logs"
                fi
                
            elif [ "$container_available" = true ]; then
                # Only container available
                echo "🔧 Starting automagik-agents container..."
                docker start automagik_agents
                sleep 2
                if docker ps | grep -q automagik_agents; then
                    echo "✅ automagik-agents container started successfully"
                    echo "📡 API available at: http://localhost:${AM_EFFECTIVE_PORT}"
                else
                    echo "❌ Failed to start automagik-agents container"
                    echo "📋 Check logs with: agent logs"
                fi
                
            else
                echo "❌ No automagik-agents service or container found"
                echo "💡 Run the installer first"
            fi
            ;;
        "stop")
            local service_running=false
            local container_running=false
            local stopped_something=false
            
            # Check what's running
            if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                service_running=true
            fi
            
            if docker ps | grep -q automagik_agents 2>/dev/null; then
                container_running=true
            fi
            
            # If both are running, ask what to stop
            if [ "$service_running" = true ] && [ "$container_running" = true ]; then
                echo "⚠️  Both service AND container are running!"
                echo "Which would you like to stop?"
                echo "1) Systemd service only"
                echo "2) Docker container only"
                echo "3) Both service and container"
                read -p "Choose option (1-3): " stop_choice
                
                case $stop_choice in
                    1)
                        echo "🛑 Stopping automagik-agents service..."
                        sudo systemctl stop automagik-agents
                        echo "✅ automagik-agents service stopped"
                        stopped_something=true
                        ;;
                    2)
                        echo "🛑 Stopping automagik-agents container..."
                        docker stop automagik_agents
                        echo "✅ automagik-agents container stopped"
                        stopped_something=true
                        ;;
                    3)
                        echo "🛑 Stopping both service and container..."
                        sudo systemctl stop automagik-agents
                        docker stop automagik_agents
                        echo "✅ Both automagik-agents service and container stopped"
                        stopped_something=true
                        ;;
                    *)
                        echo "❌ Invalid choice. Operation cancelled."
                        ;;
                esac
                
            else
                # Stop whatever is running
                if [ "$service_running" = true ]; then
                    echo "🛑 Stopping automagik-agents service..."
                    sudo systemctl stop automagik-agents
                    echo "✅ automagik-agents service stopped"
                    stopped_something=true
                fi
                
                if [ "$container_running" = true ]; then
                    echo "🛑 Stopping automagik-agents container..."
                    docker stop automagik_agents
                    echo "✅ automagik-agents container stopped"
                    stopped_something=true
                fi
            fi
            
            if [ "$stopped_something" = false ]; then
                echo "ℹ️  automagik-agents is not running"
            fi
            ;;
        "restart")
            # Check what's currently running
            local service_running=false
            local container_running=false
            
            if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                service_running=true
            fi
            
            if docker ps | grep -q automagik_agents 2>/dev/null; then
                container_running=true
            fi
            
            if [ "$service_running" = false ] && [ "$container_running" = false ]; then
                echo "ℹ️  Nothing is currently running. Use 'agent start' to start."
                return 0
            fi
            
            # If both are running, ask what to restart
            if [ "$service_running" = true ] && [ "$container_running" = true ]; then
                echo "⚠️  Both service AND container are running!"
                echo "Which would you like to restart?"
                echo "1) Systemd service only"
                echo "2) Docker container only"
                echo "3) Both service and container"
                read -p "Choose option (1-3): " restart_choice
                
                case $restart_choice in
                    1)
                        echo "🔄 Restarting automagik-agents service..."
                        sudo systemctl restart automagik-agents
                        sleep 2
                        if systemctl is-active --quiet automagik-agents; then
                            echo "✅ automagik-agents service restarted successfully"
                        else
                            echo "❌ Failed to restart automagik-agents service"
                        fi
                        ;;
                    2)
                        echo "🔄 Restarting automagik-agents container..."
                        docker restart automagik_agents
                        sleep 2
                        if docker ps | grep -q automagik_agents; then
                            echo "✅ automagik-agents container restarted successfully"
                        else
                            echo "❌ Failed to restart automagik-agents container"
                        fi
                        ;;
                    3)
                        echo "🔄 Restarting both service and container..."
                        sudo systemctl restart automagik-agents
                        docker restart automagik_agents
                        sleep 2
                        echo "✅ Both automagik-agents service and container restarted"
                        ;;
                    *)
                        echo "❌ Invalid choice. Operation cancelled."
                        ;;
                esac
                
            else
                # Restart whatever is running
                if [ "$service_running" = true ]; then
                    echo "🔄 Restarting automagik-agents service..."
                    sudo systemctl restart automagik-agents
                    sleep 2
                    if systemctl is-active --quiet automagik-agents; then
                        echo "✅ automagik-agents service restarted successfully"
                    else
                        echo "❌ Failed to restart automagik-agents service"
                    fi
                fi
                
                if [ "$container_running" = true ]; then
                    echo "🔄 Restarting automagik-agents container..."
                    docker restart automagik_agents
                    sleep 2
                    if docker ps | grep -q automagik_agents; then
                        echo "✅ automagik-agents container restarted successfully"
                    else
                        echo "❌ Failed to restart automagik-agents container"
                    fi
                fi
            fi
            ;;
        "status")
            echo "📊 Automagik Agents Status:"
            echo
            
            # Check systemd service
            if command -v systemctl &> /dev/null && systemctl list-unit-files | grep -q automagik-agents; then
                echo "🔧 Service Status:"
                sudo systemctl status automagik-agents --no-pager --lines=3
                echo
            fi
            
            # Check Docker container
            if command -v docker &> /dev/null && docker ps -a | grep -q automagik_agents; then
                echo "🐳 Container Status:"
                docker ps -a | grep automagik_agents
                echo
                
                # Check health if running
                if docker ps | grep -q automagik_agents; then
                    local health=$(docker inspect automagik_agents --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
                    echo "🔗 Container Health: $health"
                fi
            fi
            
            # Quick API health check
            echo "🔗 API Health Check:"
            if curl -s http://localhost:${AM_EFFECTIVE_PORT}/health > /dev/null 2>&1; then
                echo "✅ API is responding at http://localhost:${AM_EFFECTIVE_PORT}"
            else
                echo "❌ API is not responding"
            fi
            ;;
        "logs")
            if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                # Service logs
                if command -v ccze &> /dev/null; then
                    echo "📋 Showing automagik-agents service logs (press Ctrl+C to exit)..."
                    sudo journalctl -u automagik-agents.service -f | ccze -A
                else
                    echo "📋 Showing automagik-agents service logs (press Ctrl+C to exit)..."
                    sudo journalctl -u automagik-agents.service -f
                fi
            elif docker ps | grep -q automagik_agents 2>/dev/null; then
                # Container logs
                echo "📋 Showing automagik-agents container logs (press Ctrl+C to exit)..."
                docker logs automagik_agents -f
            else
                echo "❌ No running automagik-agents service or container found"
                echo "💡 Try: agent start"
            fi
            ;;
        "dev")
            echo "🔧 Starting automagik-agents in development mode..."
            echo "📂 Make sure you're in the project directory and virtual environment is activated"
            echo "💡 Tip: Use 'source .venv/bin/activate' to activate the virtual environment"
            echo
            read -p "Continue? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                python -m src --reload
            else
                echo "❌ Development mode cancelled"
            fi
            ;;
        "health")
            echo "🔍 Checking automagik-agents health..."
            if curl -s http://localhost:${AM_EFFECTIVE_PORT}/health > /dev/null 2>&1; then
                echo "✅ API is healthy and responding"
                echo "📡 Available endpoints:"
                echo "  • API: http://localhost:${AM_EFFECTIVE_PORT}"
                echo "  • Docs: http://localhost:${AM_EFFECTIVE_PORT}/docs"
                echo "  • Health: http://localhost:${AM_EFFECTIVE_PORT}/health"
            else
                echo "❌ API is not responding"
                
                # Check what's running
                if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                    echo "ℹ️  Service is running but API might be starting up"
                    echo "💡 Try: agent logs"
                elif docker ps | grep -q automagik_agents 2>/dev/null; then
                    echo "ℹ️  Container is running but API might be starting up"
                    echo "💡 Try: agent logs"
                else
                    echo "ℹ️  Neither service nor container is running"
                    echo "💡 Try: agent start"
                fi
            fi
            ;;
        "update"|"quick-update")
            echo "⚡ Running quick update to deploy code changes..."
            echo "🔧 This will detect what's changed and rebuild only what's needed"
            echo
            
            # Find the installer script
            local installer_script=""
            
            # Try to find the installer script
            for search_path in \
                "$(pwd)/scripts/install/setup.sh" \
                "$HOME/workspace/am-agents-labs/scripts/install/setup.sh" \
                "/home/*/workspace/am-agents-labs/scripts/install/setup.sh" \
                "$(find /home -name setup.sh -path "*/am-agents-labs/scripts/install/*" 2>/dev/null | head -1)"; do
                
                if [ -f "$search_path" ]; then
                    installer_script="$search_path"
                    break
                fi
            done
            
            if [ -n "$installer_script" ]; then
                echo "📍 Found installer at: $installer_script"
                echo "🚀 Starting quick update..."
                "$installer_script" --component agents --mode quick-update
            else
                echo "❌ Could not find the installer script"
                echo "💡 Please run from the project directory:"
                echo "    ./scripts/install/setup.sh --component agents --mode quick-update"
            fi
            ;;
        "rebuild")
            echo "🔄 Smart Rebuild: Rebuilding with optimizations based on changes..."
            echo "🔧 This uses the 'smart' quick update mode"
            echo
            
            # Find the installer script
            local installer_script=""
            
            # Try to find the installer script
            for search_path in \
                "$(pwd)/scripts/install/setup.sh" \
                "$HOME/workspace/am-agents-labs/scripts/install/setup.sh" \
                "/home/*/workspace/am-agents-labs/scripts/install/setup.sh" \
                "$(find /home -name setup.sh -path "*/am-agents-labs/scripts/install/*" 2>/dev/null | head -1)"; do
                
                if [ -f "$search_path" ]; then
                    installer_script="$search_path"
                    break
                fi
            done
            
            if [ -n "$installer_script" ]; then
                echo "📍 Found installer at: $installer_script"
                echo "🚀 Starting smart rebuild..."
                # Pass --non-interactive to avoid update mode prompt
                "$installer_script" --component agents --mode quick-update --non-interactive
            else
                echo "❌ Could not find the installer script"
                echo "💡 Please run from the project directory:"
                echo "    ./scripts/install/setup.sh --component agents --mode quick-update"
            fi
            ;;
        "help"|"--help"|"-h"|"")
            echo "🤖 Automagik Agents Management Commands:"
            echo
            echo "  agent start     - Start the service or container"
            echo "  agent stop      - Stop the service or container"
            echo "  agent restart   - Restart the service or container"
            echo "  agent status    - Show service/container status"
            echo "  agent logs      - Show live logs (with colors if ccze available)"
            echo "  agent health    - Check API health and endpoints"
            echo "  agent update    - Quick update to deploy code changes (interactive)"
            echo "  agent rebuild   - Smart rebuild with optimizations (non-interactive)"
            echo "  agent dev       - Start in development mode (manual)"
            echo "  agent help      - Show this help message"
            echo
            echo "📡 Service URLs:"
            echo "  • API: http://localhost:${AM_EFFECTIVE_PORT}"
            echo "  • Documentation: http://localhost:${AM_EFFECTIVE_PORT}/docs"
            echo "  • Health Check: http://localhost:${AM_EFFECTIVE_PORT}/health"
            echo
            echo "💡 Works with both systemd services and Docker containers"
            ;;
        *)
            echo "❌ Unknown command: $1"
            echo "💡 Use 'agent help' to see available commands"
            ;;
    esac
}

# Omni Management (placeholder for future implementation)
omni() {
    case "$1" in
        "start"|"stop"|"restart"|"status"|"logs"|"health")
            echo "🌐 Omni commands coming soon!"
            echo "ℹ️  Omni installation will be available in future updates"
            ;;
        "help"|"--help"|"-h"|"")
            echo "🌐 Omni Management Commands (Coming Soon):"
            echo
            echo "  omni start     - Start the omni service"
            echo "  omni stop      - Stop the omni service"
            echo "  omni restart   - Restart the omni service"
            echo "  omni status    - Show omni status"
            echo "  omni logs      - Show omni logs"
            echo "  omni health    - Check omni health"
            echo "  omni help      - Show this help message"
            ;;
        *)
            echo "❌ Unknown omni command: $1"
            echo "💡 Use 'omni help' to see available commands"
            ;;
    esac
}

# Langflow Management (placeholder for future implementation)
langflow() {
    case "$1" in
        "start"|"stop"|"restart"|"status"|"logs"|"health")
            echo "🔧 Langflow commands coming soon!"
            echo "ℹ️  Langflow installation will be available in future updates"
            ;;
        "help"|"--help"|"-h"|"")
            echo "🔧 Langflow Management Commands (Coming Soon):"
            echo
            echo "  langflow start     - Start the langflow service"
            echo "  langflow stop      - Stop the langflow service"
            echo "  langflow restart   - Restart the langflow service"
            echo "  langflow status    - Show langflow status"
            echo "  langflow logs      - Show langflow logs"
            echo "  langflow health    - Check langflow health"
            echo "  langflow help      - Show this help message"
            ;;
        *)
            echo "❌ Unknown langflow command: $1"
            echo "💡 Use 'langflow help' to see available commands"
            ;;
    esac
}

# General automagik management
automagik() {
    case "$1" in
        "status")
            echo "📊 Automagik Bundle Status:"
            echo
            echo "🤖 Agents:"
            if systemctl is-active --quiet automagik-agents 2>/dev/null; then
                echo "  ✅ Running"
            else
                echo "  ❌ Stopped"
            fi
            echo
            echo "🌐 Omni: ⏳ Coming Soon"
            echo "🔧 Langflow: ⏳ Coming Soon"
            ;;
        "help"|"--help"|"-h"|"")
            echo "🎯 Automagik Bundle Management:"
            echo
            echo "  automagik status  - Show status of all components"
            echo "  automagik help    - Show this help message"
            echo
            echo "Component-specific commands:"
            echo "  agent <command>     - Manage Automagik Agents"
            echo "  omni <command>      - Manage Omni (coming soon)"
            echo "  langflow <command>  - Manage Langflow (coming soon)"
            echo
            echo "💡 Use '<component> help' for component-specific commands"
            ;;
        *)
            echo "❌ Unknown automagik command: $1"
            echo "💡 Use 'automagik help' to see available commands"
            ;;
    esac
}

# Export functions to make them available
export -f agent omni langflow automagik

echo "🎯 Automagik helper functions loaded!"
echo "💡 Use 'agent help', 'omni help', 'langflow help', or 'automagik help' for available commands" 