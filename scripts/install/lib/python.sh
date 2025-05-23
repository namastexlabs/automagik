#!/bin/bash
#===========================================
# Automagik Python Management Library
#===========================================
# Functions for Python version checking, UV installation, and virtual environment management

# Source common utilities if not already loaded
if [ -z "$COMMON_LOADED" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
    COMMON_LOADED=true
fi

# Python-related variables
export PYTHON_CMD=""
export PIP_CMD=""
export VENV_NAME=".venv"
export VENV_PATH=""

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
    local venv_name="${1:-$VENV_NAME}"
    local force_recreate="${2:-false}"
    
    log "INFO" "Setting up Python virtual environment: $venv_name"
    
    cd "$ROOT_DIR"
    
    # Set venv path
    export VENV_PATH="$ROOT_DIR/$venv_name"
    
    # Check if virtual environment already exists
    if [ -d "$VENV_PATH" ]; then
        if [ "$force_recreate" = false ]; then
            log "SUCCESS" "Virtual environment already exists at $VENV_PATH"
            if confirm_action "Do you want to recreate it?" "n"; then
                force_recreate=true
            else
                log "SUCCESS" "Using existing virtual environment"
                return 0
            fi
        fi
        
        if [ "$force_recreate" = true ]; then
            log "INFO" "Removing existing virtual environment"
            rm -rf "$VENV_PATH"
        fi
    fi
    
    log "INFO" "Creating virtual environment with UV"
    if ! uv venv "$venv_name"; then
        log "ERROR" "Failed to create virtual environment"
        return 1
    fi
    
    log "SUCCESS" "Virtual environment created at $VENV_PATH"
    return 0
}

# Activate virtual environment
activate_virtual_environment() {
    local venv_path="${1:-$VENV_PATH}"
    
    if [ -z "$venv_path" ]; then
        venv_path="$ROOT_DIR/$VENV_NAME"
    fi
    
    log "INFO" "Activating virtual environment: $venv_path"
    
    # Check if virtual environment exists
    if [ ! -d "$venv_path" ]; then
        log "ERROR" "Virtual environment not found at $venv_path"
        return 1
    fi
    
    # Activate based on OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$venv_path/Scripts/activate"
    else
        source "$venv_path/bin/activate"
    fi
    
    # Verify activation
    if [ "$VIRTUAL_ENV" = "$venv_path" ]; then
        log "SUCCESS" "Virtual environment activated"
        return 0
    else
        log "ERROR" "Failed to activate virtual environment"
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
    
    log "INFO" "Installing project dependencies with UV"
    if ! uv sync; then
        log "ERROR" "Failed to sync dependencies"
        return 1
    fi
    
    log "INFO" "Installing project in editable mode"
    if ! uv pip install -e .; then
        log "ERROR" "Failed to install project in editable mode"
        return 1
    fi
    
    if [ "$install_dev" = true ]; then
        log "INFO" "Installing development dependencies"
        if ! uv pip install pytest pytest-asyncio pytest-html ruff black isort mypy; then
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
    local venv_path="${1:-$VENV_PATH}"
    
    if [ -z "$venv_path" ]; then
        venv_path="$ROOT_DIR/$VENV_NAME"
    fi
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "$venv_path\\Scripts\\activate"
    else
        echo "source $venv_path/bin/activate"
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
    if ! setup_virtual_environment "$venv_name" "$force_recreate"; then
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