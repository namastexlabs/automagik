#!/bin/bash
#===========================================
# Automagik Common Utilities Library
#===========================================
# Shared functions and utilities used across all setup scripts

# Color codes for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# Global variables (INSTALL_DIR, ROOT_DIR, VENV_NAME, VENV_PATH are now set by the main setup.sh script)
# LIB_DIR is the directory this common.sh script is in.
export LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print functions
print_banner() {
    echo -e "${PURPLE}"
    cat << "EOF"
       ██            ███████████  ████████   ███        ███     █       ▓███████ ░██▓ ███   ████    
       ███   ▓██     ██          ███    ▒██░ ████      ████    ███     ███        ██  ██▒  ███      
      ████    ██     ██   ███   ██        ██ █████    █████   █████   ███  █████  ██  ██  ██▒       
     ▓██ ██   ██     ██   ███   ██   ██▓  ██ ██ ███  ███ ██   ██ ██   ███  █████  ██  █████         
     ██  ███  ██     ██   ███   ███      ░██ ██  ██  ██ ███  ██▒  ██  ███     ██  ██  ███░███       
    ██░   ██  ████▒████   ███    ████  ████  ██   ████      ███   ███  █████ ▓██  ██  █▓   ███░     
   ███    ███   █████     ███      ██████    ██▒   ██      ███░    ███   ▓████████████       ███    

                                 Automagik Bundle Installer
                               Effortless Setup & Deployment
EOF
    echo -e "${NC}"
}

print_header() {
    local header="$1"
    local width=80
    local padding=$(( (width - ${#header} - 2) / 2 ))
    
    echo -e "${BLUE}"
    printf '=%.0s' $(seq 1 $width)
    echo
    printf "%*s%s%*s\n" $padding "" "$header" $padding ""
    printf '=%.0s' $(seq 1 $width)
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${PURPLE}🔧 $1${NC}"
}

print_reuse() {
    echo -e "${CYAN}♻️  $1${NC}"
}

# Utility functions
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

confirm_action() {
    local prompt="${1:-Continue?}"
    local default="${2:-n}"
    
    if [[ "$default" =~ ^[Yy]$ ]]; then
        read -p "$prompt (Y/n): " -n 1 -r
    else
        read -p "$prompt (y/N): " -n 1 -r
    fi
    echo
    
    if [[ "$default" =~ ^[Yy]$ ]]; then
        [[ ! $REPLY =~ ^[Nn]$ ]]
    else
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

# Error handling
set_error_trap() {
    trap 'handle_error $? $LINENO' ERR
}

handle_error() {
    local exit_code=$1
    local line_number=$2
    print_error "Script failed with exit code $exit_code at line $line_number"
    
    # Log error details if log file is set
    if [ -n "$LOG_FILE" ]; then
        echo "[ERROR] $(date): Exit code $exit_code at line $line_number" >> "$LOG_FILE"
    fi
    
    exit $exit_code
}

# Logging functions
init_logging() {
    local log_dir="$ROOT_DIR/logs"
    mkdir -p "$log_dir"
    
    export LOG_FILE="$log_dir/setup-$(date +%Y%m%d-%H%M%S).log"
    echo "=== Automagik Setup Log ===" > "$LOG_FILE"
    echo "Started: $(date)" >> "$LOG_FILE"
    echo "User: $(whoami)" >> "$LOG_FILE"
    echo "Directory: $ROOT_DIR" >> "$LOG_FILE"
    echo "===========================" >> "$LOG_FILE"
}

log() {
    local level="$1"
    shift
    local message="$*"
    
    if [ -n "$LOG_FILE" ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
    fi
    
    case "$level" in
        ERROR) print_error "$message" ;;
        WARN) print_warning "$message" ;;
        INFO) print_info "$message" ;;
        SUCCESS) print_success "$message" ;;
        *) echo "$message" ;;
    esac
}

# Exit handlers
cleanup_on_exit() {
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Setup completed successfully"
    else
        log "ERROR" "Setup failed with exit code $exit_code"
    fi
    
    # Add any cleanup tasks here
    return $exit_code
}

# Version checking
check_version() {
    local current="$1"
    local required="$2"
    
    # Convert versions to comparable format
    local current_comparable=$(echo "$current" | awk -F. '{ printf("%d%03d%03d\n", $1, $2, $3) }')
    local required_comparable=$(echo "$required" | awk -F. '{ printf("%d%03d%03d\n", $1, $2, $3) }')
    
    [ "$current_comparable" -ge "$required_comparable" ]
}

# Export functions for use in other scripts
export -f print_banner print_header print_success print_warning print_error
export -f print_info print_step print_reuse check_command confirm_action
export -f set_error_trap handle_error init_logging log cleanup_on_exit
export -f check_version 