#!/bin/bash
#===========================================
# Automagik System Detection & Dependencies
#===========================================
# Functions for OS detection and system dependency installation

# Source common utilities if not already loaded
if [ -z "$COMMON_LOADED" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
    COMMON_LOADED=true
fi

# OS Detection Variables
export OS=""
export OS_DISTRO=""
export PACKAGE_MANAGER=""
export IS_WSL=false

# Detect operating system
detect_os() {
    log "INFO" "Detecting operating system..."
    
    # Check for WSL
    if grep -qEi "(Microsoft|WSL)" /proc/version 2>/dev/null; then
        IS_WSL=true
        log "INFO" "WSL environment detected"
    fi
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        
        # Detect Linux distribution
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS_DISTRO="$ID"
            
            case "$OS_DISTRO" in
                ubuntu|debian)
                    PACKAGE_MANAGER="apt"
                    ;;
                fedora|rhel|centos)
                    PACKAGE_MANAGER="dnf"
                    # Fallback to yum if dnf not available
                    if ! check_command dnf; then
                        PACKAGE_MANAGER="yum"
                    fi
                    ;;
                arch|manjaro)
                    PACKAGE_MANAGER="pacman"
                    ;;
                opensuse*)
                    PACKAGE_MANAGER="zypper"
                    ;;
                *)
                    PACKAGE_MANAGER="unknown"
                    ;;
            esac
        else
            OS_DISTRO="unknown"
            PACKAGE_MANAGER="unknown"
        fi
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_DISTRO="macos"
        PACKAGE_MANAGER="brew"
        
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        OS_DISTRO="windows"
        PACKAGE_MANAGER="choco"
        
    else
        OS="unknown"
        OS_DISTRO="unknown"
        PACKAGE_MANAGER="unknown"
    fi
    
    log "INFO" "Detected: OS=$OS, Distro=$OS_DISTRO, Package Manager=$PACKAGE_MANAGER"
    
    # Export for use in other scripts
    export OS OS_DISTRO PACKAGE_MANAGER IS_WSL
}

# Check if running with sudo/admin privileges
check_privileges() {
    if [[ "$OS" == "windows" ]]; then
        # Windows privilege check
        net session &>/dev/null
        return $?
    else
        # Unix-like systems
        if [ "$EUID" -eq 0 ]; then
            return 0
        else
            return 1
        fi
    fi
}

# Install system package
install_package() {
    local package="$1"
    
    log "INFO" "Installing package: $package"
    
    case "$PACKAGE_MANAGER" in
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y "$package"
            ;;
        dnf|yum)
            sudo $PACKAGE_MANAGER install -y "$package"
            ;;
        pacman)
            sudo pacman -S --noconfirm "$package"
            ;;
        zypper)
            sudo zypper install -y "$package"
            ;;
        brew)
            brew install "$package"
            ;;
        choco)
            choco install -y "$package"
            ;;
        *)
            log "ERROR" "Unknown package manager: $PACKAGE_MANAGER"
            return 1
            ;;
    esac
}

# Install Python and related tools
install_python() {
    log "INFO" "Checking Python installation..."
    
    local python_cmd=""
    local pip_cmd=""
    
    # Check for Python 3
    if check_command python3; then
        python_cmd="python3"
        pip_cmd="pip3"
    elif check_command python; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            python_cmd="python"
            pip_cmd="pip"
        fi
    fi
    
    if [ -z "$python_cmd" ]; then
        log "INFO" "Python 3 not found, installing..."
        
        case "$OS" in
            linux)
                case "$OS_DISTRO" in
                    ubuntu|debian)
                        install_package "python3"
                        install_package "python3-pip"
                        install_package "python3-venv"
                        install_package "python3-dev"
                        ;;
                    fedora|rhel|centos)
                        install_package "python3"
                        install_package "python3-pip"
                        install_package "python3-devel"
                        ;;
                    arch|manjaro)
                        install_package "python"
                        install_package "python-pip"
                        ;;
                esac
                ;;
            macos)
                install_package "python@3.11"
                ;;
            windows)
                install_package "python3"
                ;;
        esac
    else
        log "SUCCESS" "Python 3 already installed: $($python_cmd --version)"
    fi
    
    # Export Python commands
    export PYTHON_CMD="${python_cmd:-python3}"
    export PIP_CMD="${pip_cmd:-pip3}"
}

# Install development tools
install_dev_tools() {
    log "INFO" "Installing development tools..."
    
    local tools=()
    
    case "$OS" in
        linux)
            tools+=(curl wget git build-essential)
            
            # PostgreSQL client libraries
            case "$OS_DISTRO" in
                ubuntu|debian)
                    tools+=(libpq-dev postgresql-client)
                    ;;
                fedora|rhel|centos)
                    tools+=(postgresql-devel postgresql)
                    ;;
                arch|manjaro)
                    tools+=(postgresql-libs postgresql)
                    ;;
            esac
            ;;
        macos)
            tools+=(curl wget git postgresql)
            ;;
        windows)
            tools+=(curl wget git)
            ;;
    esac
    
    # Install each tool
    for tool in "${tools[@]}"; do
        if ! check_command "$tool"; then
            install_package "$tool"
        else
            log "SUCCESS" "$tool already installed"
        fi
    done
    
    # Install optional tools
    install_optional_tools
}

# Install optional but useful tools
install_optional_tools() {
    log "INFO" "Checking optional tools..."
    
    # ccze for colored logs
    if ! check_command ccze; then
        log "INFO" "Installing ccze for colored log output..."
        case "$OS" in
            linux)
                if [[ "$OS_DISTRO" =~ ^(ubuntu|debian)$ ]]; then
                    install_package "ccze" || log "WARN" "ccze installation failed (optional)"
                fi
                ;;
            macos)
                install_package "ccze" || log "WARN" "ccze installation failed (optional)"
                ;;
        esac
    fi
    
    # htop for process monitoring
    if ! check_command htop; then
        log "INFO" "Installing htop for process monitoring..."
        install_package "htop" || log "WARN" "htop installation failed (optional)"
    fi
}

# Install Docker
install_docker() {
    log "INFO" "Checking Docker installation..."
    
    if check_command docker; then
        log "SUCCESS" "Docker already installed: $(docker --version)"
        return 0
    fi
    
    log "INFO" "Installing Docker..."
    
    case "$OS" in
        linux)
            case "$OS_DISTRO" in
                ubuntu|debian)
                    # Official Docker installation script
                    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
                    sudo sh /tmp/get-docker.sh
                    rm /tmp/get-docker.sh
                    
                    # Add user to docker group
                    sudo usermod -aG docker "$USER"
                    log "WARN" "You may need to log out and back in for Docker group permissions"
                    ;;
                fedora|rhel|centos)
                    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                    sudo dnf install -y docker-ce docker-ce-cli containerd.io
                    sudo systemctl start docker
                    sudo systemctl enable docker
                    sudo usermod -aG docker "$USER"
                    ;;
                arch|manjaro)
                    install_package "docker"
                    sudo systemctl start docker
                    sudo systemctl enable docker
                    sudo usermod -aG docker "$USER"
                    ;;
            esac
            ;;
        macos)
            if check_command brew; then
                brew install --cask docker
                log "WARN" "Please start Docker Desktop manually after installation"
            else
                log "ERROR" "Homebrew required to install Docker on macOS"
                return 1
            fi
            ;;
        windows)
            if [ "$IS_WSL" = true ]; then
                log "WARN" "In WSL, Docker Desktop should be installed on Windows host"
                log "INFO" "Please install Docker Desktop for Windows and enable WSL integration"
            else
                install_package "docker-desktop"
            fi
            ;;
    esac
    
    # Install Docker Compose
    install_docker_compose
}

# Install Docker Compose
install_docker_compose() {
    log "INFO" "Checking Docker Compose installation..."
    
    # Check for docker compose plugin (v2)
    if docker compose version &>/dev/null; then
        log "SUCCESS" "Docker Compose plugin already installed"
        return 0
    fi
    
    # Check for standalone docker-compose (v1)
    if check_command docker-compose; then
        log "SUCCESS" "Docker Compose standalone already installed"
        return 0
    fi
    
    log "INFO" "Installing Docker Compose..."
    
    case "$OS" in
        linux)
            # Install Docker Compose plugin
            case "$OS_DISTRO" in
                ubuntu|debian)
                    sudo apt-get update
                    sudo apt-get install -y docker-compose-plugin
                    ;;
                fedora|rhel|centos)
                    sudo dnf install -y docker-compose-plugin
                    ;;
                arch|manjaro)
                    install_package "docker-compose"
                    ;;
                *)
                    # Fallback to manual installation
                    local compose_version="v2.23.0"
                    local compose_url="https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-$(uname -s)-$(uname -m)"
                    sudo curl -L "$compose_url" -o /usr/local/bin/docker-compose
                    sudo chmod +x /usr/local/bin/docker-compose
                    ;;
            esac
            ;;
        macos)
            # Docker Desktop includes Compose
            log "INFO" "Docker Compose included with Docker Desktop"
            ;;
        windows)
            # Docker Desktop includes Compose
            log "INFO" "Docker Compose included with Docker Desktop"
            ;;
    esac
}

# Install all system dependencies
install_system_dependencies() {
    print_header "Installing System Dependencies"
    
    # Detect OS first
    detect_os
    
    # Install based on user preferences
    local install_python="${1:-true}"
    local install_docker="${2:-true}"
    local install_dev="${3:-true}"
    
    if [ "$install_python" = true ]; then
        install_python
    fi
    
    if [ "$install_dev" = true ]; then
        install_dev_tools
    fi
    
    if [ "$install_docker" = true ]; then
        install_docker
    fi
    
    log "SUCCESS" "System dependencies installation completed"
}

# Check all prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local issues=()
    
    # Check Python version
    if check_command python3; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        if ! check_version "$python_version" "3.10.0"; then
            issues+=("Python 3.10+ required (found $python_version)")
        fi
    else
        issues+=("Python 3 not found")
    fi
    
    # Check Git
    if ! check_command git; then
        issues+=("Git not found")
    fi
    
    # Check curl or wget
    if ! check_command curl && ! check_command wget; then
        issues+=("Neither curl nor wget found")
    fi
    
    # Report issues
    if [ ${#issues[@]} -gt 0 ]; then
        log "ERROR" "Prerequisites check failed:"
        for issue in "${issues[@]}"; do
            log "ERROR" "  - $issue"
        done
        return 1
    else
        log "SUCCESS" "All prerequisites satisfied"
        return 0
    fi
}

# Export functions
export -f detect_os check_privileges install_package install_python
export -f install_dev_tools install_docker install_docker_compose
export -f install_system_dependencies check_prerequisites 