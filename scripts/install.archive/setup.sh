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
INSTALL_COMPONENT="agents"
INSTALL_MODE=""
INSTALL_PYTHON=true
INSTALL_DOCKER=true
INSTALL_DEV=true
VERBOSE=false
NON_INTERACTIVE=false
INSTALL_AS_SERVICE=false

# API key parameters for non-interactive installs
OPENAI_API_KEY_PARAM=""
DISCORD_BOT_TOKEN_PARAM=""
AM_API_KEY_PARAM=""

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--component)
                INSTALL_COMPONENT="$2"
                shift 2
                ;;
            -m|--mode)
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
                INSTALL_DEV=false
                shift
                ;;
            -v|--verbose)
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
    -m, --mode MODE        Installation mode (local, docker, docker-prod, quick-update)
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

Installation Modes:
    local          Local installation with Python virtual environment
    docker         Docker installation for development/testing (standard ports)
    docker-prod    Docker production deployment (non-standard ports, external DBs)
    quick-update   Quick Docker rebuild only

Examples:
    # Interactive installation
    $0

    # Install agents with Docker for development
    $0 --component agents --mode docker

    # Install agents with Docker for production
    $0 --component agents --mode docker-prod

    # Non-interactive production install with API keys
    $0 --component agents --mode docker-prod --non-interactive \\
       --openai-key sk-your-openai-key \\
       --discord-token your-discord-token

    # Local install with service
    $0 --component agents --mode local --install-service

    # Quick update for agents
    $0 --component agents --mode quick-update

Production Docker Mode (docker-prod):
    • Uses non-standard ports (18881 for agents, 18000 for graphiti)
    • Requires external PostgreSQL database (configure DATABASE_URL)
    • Requires external Neo4j database for Graphiti (configure NEO4J_URI)
    • Optimized for production deployment
    • Uses docker-compose-prod.yml configuration

After installation, use these CLI commands:
    automagik agents start     # Start the automagik-agents service
    automagik agents stop      # Stop the service
    automagik agents logs      # View colored logs
    automagik agents status    # Full service status
    automagik agents --help    # Show all available commands
    automagik install-alias    # Install 'agent' alias for convenience

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
    echo "2) 🐳 Docker Installation (Development/Testing)"
    echo "3) 🏭 Docker Production (Optimized for production)"
    echo "4) 🔄 Quick Update (Docker rebuild only)"
    echo "5) ❌ Cancel"
    echo
    read -p "Choose installation mode (1-5): " mode_choice
    
    case $mode_choice in
        1) INSTALL_MODE="local" ;;
        2) INSTALL_MODE="docker" ;;
        3) INSTALL_MODE="docker-prod" ;;
        4) INSTALL_MODE="quick-update" ;;
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