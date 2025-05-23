#!/bin/bash
#===========================================
# Automagik Python Management Library
#===========================================
# Functions for Python version checking, UV installation, and virtual environment management

# Source common utilities if not already loaded
if [ -z "$COMMON_LOADED" ]; then
    # LIB_DIR should be defined in common.sh relative to itself if common.sh is sourced directly.
    # If common.sh is sourced by setup.sh, then LIB_DIR from common.sh might be incorrect here.
    # It's safer if python.sh defines its own path to common.sh if needed.
    # However, setup.sh sources common.sh first, so COMMON_LOADED should be true.
    source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
    COMMON_LOADED=true
fi

# Python-related variables (PYTHON_CMD, PIP_CMD are set in check_python_version)
# VENV_NAME and VENV_PATH are now expected to be set by the main setup.sh script

# Check Python version
check_python_version() {
    log "INFO" "Checking Python version..."
    
    if ! check_command python3; then
        log "ERROR" "Python 3 is not installed"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local major=$(echo $python_version | cut -d'.' -f1)
    local minor=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 10 ]); then
        log "ERROR" "Python 3.10 or higher is required (found $python_version)"
        return 1
    fi
    
    if [ "$major" -eq 3 ] && [ "$minor" -gt 12 ]; then
        log "WARN" "Python 3.13+ detected. The project is tested with Python 3.10-3.12"
    fi
    
    log "SUCCESS" "Python $python_version found"
    
    # Set Python commands
    export PYTHON_CMD="python3"
    export PIP_CMD="pip3"
    
    return 0
}

# Install UV package manager
install_uv() {
    if check_command uv; then
        log "SUCCESS" "UV is already installed: $(uv --version)"
        return 0
    fi
    
    log "INFO" "Installing UV package manager..."
    
    # Download and install uv
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        log "ERROR" "Neither curl nor wget found. Please install one of them first."
        return 1
    fi
    
    # Source the profile to make uv available
    if [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if [ -f "$HOME/.cargo/bin/uv" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    if check_command uv; then
        log "SUCCESS" "UV installed successfully: $(uv --version)"
        return 0
    else
        log "ERROR" "UV installation failed"
        return 1
    fi
}

# Setup virtual environment
setup_virtual_environment() {
    # VENV_NAME and VENV_PATH are now global, set by setup.sh
    local force_recreate="${1:-false}" # Renamed internal venv_name param to avoid conflict if any
    
    log "INFO" "Setting up Python virtual environment: $VENV_NAME at $VENV_PATH"
    
    # Check if virtual environment already exists AT THE CORRECT PATH (VENV_PATH)
    if [ -d "$VENV_PATH" ]; then
        if [ "$force_recreate" = false ] && [ "$NON_INTERACTIVE" != "true" ]; then
            log "SUCCESS" "Virtual environment already exists at $VENV_PATH"
            if confirm_action "Do you want to recreate it?" "n"; then
                force_recreate=true
            else
                log "SUCCESS" "Using existing virtual environment"
                return 0
            fi
        elif [ "$force_recreate" = false ] && [ "$NON_INTERACTIVE" = "true" ]; then
             log "INFO" "Non-interactive: Using existing virtual environment at $VENV_PATH if present."
             return 0
        fi
        
        if [ "$force_recreate" = true ]; then
            log "INFO" "Removing existing virtual environment at $VENV_PATH"
            rm -rf "$VENV_PATH"
        fi
    fi
    
    log "INFO" "Creating virtual environment with UV at $VENV_PATH"
    cd "$ROOT_DIR" # Ensure we are in project root to create .venv there
    if ! uv venv "$VENV_NAME"; then # uv venv uses VENV_NAME relative to CWD
        log "ERROR" "Failed to create virtual environment $VENV_NAME in $ROOT_DIR"
        return 1
    fi
    
    log "SUCCESS" "Virtual environment created at $VENV_PATH"
    return 0
}

# Activate virtual environment
activate_virtual_environment() {
    # VENV_PATH is global
    log "INFO" "Activating virtual environment: $VENV_PATH"
    
    if [ ! -d "$VENV_PATH" ]; then
        log "ERROR" "Virtual environment not found at $VENV_PATH"
        return 1
    fi
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$VENV_PATH/Scripts/activate"
    else
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ "$VIRTUAL_ENV" = "$VENV_PATH" ]; then
        log "SUCCESS" "Virtual environment activated"
        return 0
    else
        log "ERROR" "Failed to activate virtual environment. VIRTUAL_ENV is '$VIRTUAL_ENV', expected '$VENV_PATH'."
        return 1
    fi
}

# Install Python dependencies
install_python_dependencies() {
    local install_dev="${1:-false}"
    
    log "INFO" "Installing Python dependencies"
    
    cd "$ROOT_DIR"
    
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        log "WARN" "Not in a virtual environment, activating..."
        if ! activate_virtual_environment; then
            return 1
        fi
    fi
    
    local python_executable="$VENV_PATH/bin/python"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        python_executable="$VENV_PATH/Scripts/python.exe"
    fi

    log "INFO" "Installing project dependencies with UV using Python from $python_executable"
    if ! uv sync --python "$python_executable"; then
        log "ERROR" "Failed to sync dependencies"
        return 1
    fi
    
    log "INFO" "Installing project in editable mode using Python from $python_executable"
    if ! uv pip install -e . --python "$python_executable"; then
        log "ERROR" "Failed to install project in editable mode"
        return 1
    fi
    
    if [ "$install_dev" = true ]; then
        log "INFO" "Installing development dependencies using Python from $python_executable"
        if ! uv pip install --python "$python_executable" pytest pytest-asyncio pytest-html ruff black isort mypy; then
            log "WARN" "Some development dependencies failed to install"
        else
            log "SUCCESS" "Development dependencies installed"
        fi
    fi
    
    log "SUCCESS" "Python dependencies installed successfully"
    return 0
}

# Get activation command for the user
get_activation_command() {
    # VENV_PATH is global
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "$VENV_PATH\\Scripts\\activate"
    else
        echo "source $VENV_PATH/bin/activate"
    fi
}

# Check if UV is available
check_uv_available() {
    if check_command uv; then
        return 0
    fi
    
    # Check if UV is in common paths
    for path in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
        if [ -f "$path" ]; then
            export PATH="$(dirname "$path"):$PATH"
            return 0
        fi
    done
    
    return 1
}

# Setup complete Python environment
setup_python_environment() {
    local install_dev="${1:-false}"
    local venv_name="${2:-$VENV_NAME}"
    local force_recreate="${3:-false}"
    
    print_header "Setting up Python Environment"
    
    # Check Python version
    if ! check_python_version; then
        log "ERROR" "Python version check failed"
        return 1
    fi
    
    # Install UV if not available
    if ! check_uv_available; then
        if ! install_uv; then
            log "ERROR" "UV installation failed"
            return 1
        fi
    fi
    
    # Setup virtual environment
    if ! setup_virtual_environment "$force_recreate"; then
        log "ERROR" "Virtual environment setup failed"
        return 1
    fi
    
    # Activate virtual environment
    if ! activate_virtual_environment; then
        log "ERROR" "Virtual environment activation failed"
        return 1
    fi
    
    # Install dependencies
    if ! install_python_dependencies "$install_dev"; then
        log "ERROR" "Dependency installation failed"
        return 1
    fi
    
    log "SUCCESS" "Python environment setup completed"
    return 0
}

# Export functions
export -f check_python_version install_uv setup_virtual_environment
export -f activate_virtual_environment install_python_dependencies
export -f get_activation_command check_uv_available setup_python_environment 