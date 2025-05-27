#!/bin/bash
#===========================================
# Automagik Shell Helper Functions
#===========================================
# Convenient shortcuts for managing Automagik services

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
  echo "[WARN] AM_PORT is not defined in a discoverable .env file. Using default port 8881." >&2
  _AM_EFFECTIVE_PORT_VALUE="8881"
fi
AM_EFFECTIVE_PORT=${_AM_EFFECTIVE_PORT_VALUE}

# Automagik Agents Management - Now calls proper CLI commands
am-agents() {
    case "$1" in
        "start")
            echo "🚀 Starting automagik agents..."
            automagik agents start
            ;;
        "stop")
            echo "🛑 Stopping automagik agents..."
            automagik agents stop
            ;;
        "restart")
            echo "🔄 Restarting automagik agents..."
            automagik agents restart
            ;;
        "status")
            echo "📊 Checking automagik agents status..."
            automagik agents status
            ;;
        "logs")
            echo "📋 Showing automagik agents logs..."
            automagik agents logs
            ;;
        "dev")
            echo "🔧 Starting automagik agents in development mode..."
            automagik agents dev
            ;;
        "health")
            echo "🔍 Checking automagik agents health..."
            if curl -s http://localhost:${AM_EFFECTIVE_PORT}/health > /dev/null 2>&1; then
                echo "✅ API is healthy and responding"
                echo "📡 Available endpoints:"
                echo "  • API: http://localhost:${AM_EFFECTIVE_PORT}"
                echo "  • Docs: http://localhost:${AM_EFFECTIVE_PORT}/docs"
                echo "  • Health: http://localhost:${AM_EFFECTIVE_PORT}/health"
            else
                echo "❌ API is not responding"
                echo "💡 Try: am-agents start"
            fi
            ;;
        "help"|"--help"|"-h"|"")
            echo "🤖 Automagik Agents Management Commands (Helper Shortcuts):"
            echo
            echo "  am-agents start   - Start automagik agents"
            echo "  am-agents stop    - Stop automagik agents"
            echo "  am-agents restart - Restart automagik agents"
            echo "  am-agents status  - Show service status"
            echo "  am-agents logs    - Show live logs"
            echo "  am-agents health  - Check API health"
            echo "  am-agents dev     - Start in development mode"
            echo "  am-agents help    - Show this help message"
            echo
            echo "📡 Service URLs:"
            echo "  • API: http://localhost:${AM_EFFECTIVE_PORT}"
            echo "  • Documentation: http://localhost:${AM_EFFECTIVE_PORT}/docs"
            echo "  • Health Check: http://localhost:${AM_EFFECTIVE_PORT}/health"
            echo
            echo "💡 These are shortcuts to 'automagik agents <command>'"
            echo "💡 For full CLI functionality, use: automagik agents --help"
            ;;
        *)
            echo "❌ Unknown command: $1"
            echo "💡 Use 'am-agents help' to see available commands"
            echo "💡 Or use the full CLI: automagik agents --help"
            ;;
    esac
}

# Backward compatibility alias (but warn about conflict)
agent() {
    echo "⚠️  WARNING: 'agent' command conflicts with automagik CLI structure"
    echo "💡 Please use 'am-agents' instead, or the full 'automagik agents' command"
    echo "🔄 Redirecting to am-agents..."
    echo
    am-agents "$@"
}

# General automagik management
automagik-status() {
    echo "📊 Automagik Bundle Status:"
    echo
    echo "🤖 Agents:"
    if curl -s http://localhost:${AM_EFFECTIVE_PORT}/health > /dev/null 2>&1; then
        echo "  ✅ Running - API responding on port ${AM_EFFECTIVE_PORT}"
    else
        echo "  ❌ Stopped or not responding"
    fi
    echo
    echo "🌐 Omni: ⏳ Coming Soon"
    echo "🔧 Langflow: ⏳ Coming Soon"
}

# Export functions to make them available
export -f am-agents agent automagik-status

echo "🎯 Automagik helper functions loaded!"
echo "💡 Use 'am-agents help' for agent management commands"
echo "💡 Use 'automagik agents --help' for full CLI functionality"
echo "⚠️  Note: 'agent' command is deprecated - use 'am-agents' instead" 