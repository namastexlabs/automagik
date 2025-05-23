#!/bin/bash
#===========================================
# Automagik Bundle Setup Script
#===========================================
# Main orchestrator for the modular setup system

set -e  # Exit on any error

# Correctly define ROOT_DIR based on setup.sh's location
# This script (setup.sh) is in scripts/install/, so ROOT_DIR is two levels up.
export ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"

# INSTALL_DIR is where the install scripts themselves live (e.g., scripts/install)
export INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# VENV_NAME and VENV_PATH are now consistently defined relative to the true ROOT_DIR
export VENV_NAME=".venv"
export VENV_PATH="$ROOT_DIR/$VENV_NAME"

# Source libraries (they will now inherit the correct ROOT_DIR and VENV_PATH)
source "$INSTALL_DIR/lib/common.sh"
source "$INSTALL_DIR/lib/system.sh"
source "$INSTALL_DIR/lib/python.sh"
source "$INSTALL_DIR/lib/config.sh"
source "$INSTALL_DIR/lib/service.sh"

# Mark libraries as loaded (optional, for clarity if scripts check this)
COMMON_LOADED=true
SYSTEM_LOADED=true
PYTHON_LOADED=true
CONFIG_LOADED=true
SERVICE_LOADED=true

# Default values
INSTALL_COMPONENT="agents"  # Default to agents
INSTALL_MODE=""            # Interactive by default
INSTALL_PYTHON=true
INSTALL_DOCKER=true
INSTALL_DEV_TOOLS=true
INSTALL_HELPERS=true
VERBOSE=false

# API key parameters for non-interactive installs
OPENAI_API_KEY_PARAM=""
DISCORD_BOT_TOKEN_PARAM=""
AM_API_KEY_PARAM=""

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --component|-c)
                INSTALL_COMPONENT="$2"
                shift 2
                ;;
            --mode|-m)
                INSTALL_MODE="$2"
                shift 2
                ;;
            --openai-key)
                OPENAI_API_KEY_PARAM="$2"
                shift 2
                ;;
            --discord-token)
                DISCORD_BOT_TOKEN_PARAM="$2"
                shift 2
                ;;
            --am-api-key)
                AM_API_KEY_PARAM="$2"
                shift 2
                ;;
            --no-python)
                INSTALL_PYTHON=false
                shift
                ;;
            --no-docker)
                INSTALL_DOCKER=false
                shift
                ;;
            --no-dev)
                INSTALL_DEV_TOOLS=false
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --install-service)
                INSTALL_AS_SERVICE=true
                shift
                ;;
            --no-helpers)
                INSTALL_HELPERS=false
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    cat << EOF
Automagik Bundle Setup Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -c, --component NAME    Component to install (agents, omni, langflow, bundle)
                           Default: agents
    -m, --mode MODE        Installation mode (local, docker, quick-update)
                           Default: interactive menu
    --openai-key KEY       OpenAI API key for non-interactive installs
    --discord-token TOKEN  Discord bot token for non-interactive installs
    --am-api-key KEY       Automagik API key (auto-generated if not provided)
    --no-python            Skip Python installation
    --no-docker            Skip Docker installation  
    --no-dev               Skip development tools installation
    -v, --verbose          Enable verbose output
    --non-interactive      Skip interactive prompts and use defaults
    --install-service      Install as systemd service (Linux only)
    --no-helpers           Skip helper functions installation

Examples:
    # Interactive installation
    $0

    # Install agents with Docker
    $0 --component agents --mode docker

    # Non-interactive local install with API keys
    $0 --component agents --mode local --non-interactive \\
       --openai-key sk-your-openai-key \\
       --discord-token your-discord-token

    # Quick update for agents
    $0 --component agents --mode quick-update

    # Install without Docker
    $0 --no-docker

    # Install as service with helper commands
    $0 --component agents --mode local --install-service

After installation, use these convenient commands:
    agent start     # Start the automagik-agents service
    agent stop      # Stop the service
    agent logs      # View colored logs
    agent status    # Full service status
    agent health    # Quick API health check
    agent help      # Show all available commands

EOF
}

# Main interactive menu
show_main_menu() {
    clear
    print_banner
    
    echo -e "${CYAN}Welcome to the Automagik Bundle Installer!${NC}"
    echo
    echo "This modular installer can set up various Automagik components."
    echo
    echo -e "${YELLOW}Available Components:${NC}"
    echo "1) 🤖 Automagik Agents - AI agent framework"
    echo "2) 🌐 Omni - Unified interface (Coming Soon)"
    echo "3) 🔧 Langflow - Visual workflow builder (Coming Soon)"
    echo "4) 📦 Full Bundle - All components (Coming Soon)"
    echo "5) ❌ Exit"
    echo
    read -p "Choose component to install (1-5): " component_choice
    
    case $component_choice in
        1) INSTALL_COMPONENT="agents" ;;
        2) 
            print_warning "Omni installation coming soon!"
            exit 0
            ;;
        3)
            print_warning "Langflow installation coming soon!"
            exit 0
            ;;
        4)
            print_warning "Full bundle installation coming soon!"
            exit 0
            ;;
        5)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Show installation mode menu
show_mode_menu() {
    echo
    echo -e "${YELLOW}Installation Mode:${NC}"
    echo "1) 🏠 Local Installation (Python virtual environment)"
    echo "2) 🐳 Docker Installation (Containerized deployment)"
    echo "3) 🔄 Quick Update (Docker rebuild only)"
    echo "4) ❌ Cancel"
    echo
    read -p "Choose installation mode (1-4): " mode_choice
    
    case $mode_choice in
        1) INSTALL_MODE="local" ;;
        2) INSTALL_MODE="docker" ;;
        3) INSTALL_MODE="quick-update" ;;
        4)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Install component
install_component() {
    local component="$1"
    local mode="$2"
    
    print_header "Installing $component in $mode mode"
    
    # Export installation options
    export_installation_options "$mode"
    
    # Check if installer exists
    local installer="$INSTALL_DIR/installers/${component}.sh"
    if [ -f "$installer" ]; then
        # Run the component installer
        source "$installer"
        install_"$component" "$mode"
    else
        print_error "Installer for $component not found at $installer"
        exit 1
    fi
}

# Export installation options to agents installer
export_installation_options() {
    export INSTALL_DEPENDENCIES="$INSTALL_PYTHON"
    export INSTALL_MODE="$1"
    
    # Export flags (defaults to false if not set)
    export NON_INTERACTIVE="${NON_INTERACTIVE:-false}"
    export INSTALL_AS_SERVICE="${INSTALL_AS_SERVICE:-false}"
    export INSTALL_HELPERS="${INSTALL_HELPERS:-true}"
    
    # Export API key parameters for configuration
    export OPENAI_API_KEY_PARAM="$OPENAI_API_KEY_PARAM"
    export DISCORD_BOT_TOKEN_PARAM="$DISCORD_BOT_TOKEN_PARAM"
    export AM_API_KEY_PARAM="$AM_API_KEY_PARAM"
}

# Main execution
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    # Show main menu if no component specified
    if [ -z "$INSTALL_COMPONENT" ] || [ "$INSTALL_COMPONENT" = "agents" -a -z "$INSTALL_MODE" ]; then
        show_main_menu
    fi
    
    # Show mode menu if not specified
    if [ -z "$INSTALL_MODE" ]; then
        show_mode_menu
    fi
    
    # Install the component
    install_component "$INSTALL_COMPONENT" "$INSTALL_MODE"
}

# Run main function
main "$@" 