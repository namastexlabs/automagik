#!/bin/bash
#===========================================
# Automagik Configuration Management Library
#===========================================
# Functions for environment file creation, configuration validation, and template processing

# Source common utilities if not already loaded
if [ -z "$COMMON_LOADED" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
    COMMON_LOADED=true
fi

# Configuration variables
export ENV_FILE="$ROOT_DIR/.env"
export ENV_EXAMPLE="$ROOT_DIR/.env.example"
export ENV_BACKUP_DIR="$ROOT_DIR/.env-backups"

# Setup environment file
setup_environment_file() {
    local force_recreate="${1:-false}"
    
    print_header "Setting up environment configuration"
    
    # Create backup directory
    mkdir -p "$ENV_BACKUP_DIR"
    
    # Check if .env file already exists
    if [ -f "$ENV_FILE" ] && [ -s "$ENV_FILE" ]; then
        if [ "$force_recreate" = false ] && [ "$NON_INTERACTIVE" != "true" ]; then
            log "SUCCESS" ".env file already exists"
            echo
            echo -e "${YELLOW}What would you like to do with the existing .env file?${NC}"
            echo "1) Keep existing .env file (recommended for existing setups)"
            echo "2) Backup current .env and create new one from template"
            echo "3) Overwrite current .env file (will lose current settings)"
            read -p "Choose option (1-3): " env_choice
            
            case $env_choice in
                1)
                    log "SUCCESS" "Keeping existing .env file"
                    return 0
                    ;;
                2)
                    local backup_file="$ROOT_DIR/.env.bkp"
                    log "INFO" "Backing up current .env to .env.bkp"
                    cp "$ENV_FILE" "$backup_file"
                    log "SUCCESS" "Original .env backed up to .env.bkp"
                    ;;
                3)
                    log "INFO" "Overwriting current .env file"
                    ;;
                *)
                    log "SUCCESS" "Invalid choice. Keeping existing .env file"
                    return 0
                    ;;
            esac
        else
            # Backup the existing file in force mode or non-interactive mode
            local backup_file="$ROOT_DIR/.env.bkp"
            log "INFO" "$([ "$NON_INTERACTIVE" = "true" ] && echo "Non-interactive mode:" || echo "Force rebuild mode:") backing up current .env to .env.bkp"
            cp "$ENV_FILE" "$backup_file"
        fi
    fi
    
    # Create .env from .env.example if it exists
    if [ -f "$ENV_EXAMPLE" ]; then
        log "INFO" "Creating new .env file from .env.example template"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log "SUCCESS" ".env file created from .env.example template"
        log "INFO" "All configuration parameters loaded from template"
        
        # Mark that we created a new file for later processing
        export NEW_ENV_CREATED=true
    else
        log "ERROR" ".env.example file not found at $ENV_EXAMPLE"
        return 1
    fi
    
    return 0
}

# Configure essential settings interactively
configure_essential_settings() {
    log "INFO" "Configuring essential settings..."
    
    echo
    echo -e "${YELLOW}🔑 Essential Configuration Required:${NC}"
    echo -e "${CYAN}Please provide the following required settings for a working installation:${NC}"
    echo
    
    # OpenAI API Key (Required)
    local openai_key=""
    while [ -z "$openai_key" ]; do
        echo -e "${BLUE}OpenAI API Key (Required for AI functionality)${NC}"
        echo -e "${GRAY}Get one at: https://platform.openai.com/api-keys${NC}"
        read -p "Enter OPENAI_API_KEY: " openai_key
        if [ -z "$openai_key" ]; then
            echo -e "${RED}⚠️  OpenAI API key is required for agent functionality${NC}"
            echo
        fi
    done
    update_env_value "OPENAI_API_KEY" "$openai_key"
    
    # Discord Bot Token (Required)
    local discord_token=""
    while [ -z "$discord_token" ]; do
        echo
        echo -e "${BLUE}Discord Bot Token (Required for Discord functionality)${NC}"
        echo -e "${GRAY}Create bot at: https://discord.com/developers/applications${NC}"
        read -p "Enter DISCORD_BOT_TOKEN: " discord_token
        if [ -z "$discord_token" ]; then
            echo -e "${RED}⚠️  Discord bot token is required for Discord functionality${NC}"
            echo
        fi
    done
    update_env_value "DISCORD_BOT_TOKEN" "$discord_token"
    
    # Generate API key if not set
    local current_api_key=$(get_env_value "AM_API_KEY")
    if [ -z "$current_api_key" ] || [ "$current_api_key" = "your_api_key_here" ]; then
        local new_api_key=$(generate_api_key)
        update_env_value "AM_API_KEY" "$new_api_key"
        log "SUCCESS" "Generated secure API key for automagik-agents authentication"
    fi
    
    echo
    log "SUCCESS" "Essential settings configured"
    
    # Show optional integrations prompt
    echo
    echo -e "${YELLOW}Optional Integrations:${NC}"
    echo -e "${GRAY}You can add these later by editing .env file:${NC}"
    echo -e "${GRAY}• Notion (NOTION_TOKEN)${NC}"
    echo -e "${GRAY}• Airtable (AIRTABLE_TOKEN)${NC}"
    echo -e "${GRAY}• Neo4j/Graphiti (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)${NC}"
    echo -e "${GRAY}• Evolution API for WhatsApp (EVOLUTION_API_KEY, EVOLUTION_API_URL)${NC}"
}

# Configure essential settings non-interactively (for CI/automated installs)
configure_essential_settings_non_interactive() {
    log "INFO" "Configuring essential settings for non-interactive installation..."
    
    # Use provided OpenAI API key or warn about missing it
    if [ -n "$OPENAI_API_KEY_PARAM" ]; then
        update_env_value "OPENAI_API_KEY" "$OPENAI_API_KEY_PARAM"
        log "SUCCESS" "Configured OpenAI API key from command line parameter"
    else
        log "WARN" "No OpenAI API key provided via --openai-key parameter"
    fi
    
    # Use provided Discord bot token or warn about missing it
    if [ -n "$DISCORD_BOT_TOKEN_PARAM" ]; then
        update_env_value "DISCORD_BOT_TOKEN" "$DISCORD_BOT_TOKEN_PARAM"
        log "SUCCESS" "Configured Discord bot token from command line parameter"
    else
        log "WARN" "No Discord bot token provided via --discord-token parameter"
    fi
    
    # Generate or use provided AM_API_KEY
    if [ -n "$AM_API_KEY_PARAM" ]; then
        update_env_value "AM_API_KEY" "$AM_API_KEY_PARAM"
        log "SUCCESS" "Using provided AM_API_KEY from command line parameter"
    else
        local current_api_key=$(get_env_value "AM_API_KEY")
        if [ -z "$current_api_key" ]; then
            local new_api_key=$(generate_api_key)
            update_env_value "AM_API_KEY" "$new_api_key"
            log "SUCCESS" "Generated secure API key for automagik-agents authentication"
        else
            log "SUCCESS" "Using existing AM_API_KEY"
        fi
    fi
    
    # Show configuration guidance if API keys are missing
    if [ -z "$OPENAI_API_KEY_PARAM" ] || [ -z "$DISCORD_BOT_TOKEN_PARAM" ]; then
        echo
        log "INFO" "💡 For a fully working installation, add API keys:"
        if [ -z "$OPENAI_API_KEY_PARAM" ]; then
            log "INFO" "  --openai-key sk-your-openai-key-here"
            log "INFO" "  Get OpenAI key: https://platform.openai.com/api-keys"
        fi
        if [ -z "$DISCORD_BOT_TOKEN_PARAM" ]; then
            log "INFO" "  --discord-token your-discord-token-here"
            log "INFO" "  Create Discord bot: https://discord.com/developers/applications"
        fi
        echo
        log "INFO" "Or edit .env file manually after installation"
    fi
}

# Update environment value
update_env_value() {
    local key="$1"
    local value="$2"
    local env_file="${3:-$ENV_FILE}"
    
    if [ -z "$key" ] || [ -z "$value" ]; then
        log "ERROR" "Key and value are required for update_env_value"
        return 1
    fi
    
    # Escape special characters in value for sed
    local escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|\/]/\\&/g')
    
    # Check if key exists in file
    if grep -q "^${key}=" "$env_file" 2>/dev/null; then
        # Update existing value using a different delimiter to avoid conflicts
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed
            sed -i '' "s|^${key}=.*|${key}=${escaped_value}|" "$env_file"
        else
            # Linux sed
            sed -i "s|^${key}=.*|${key}=${escaped_value}|" "$env_file"
        fi
        log "INFO" "Updated $key in $env_file"
    else
        # Add new key-value pair
        echo "${key}=${value}" >> "$env_file"
        log "INFO" "Added $key to $env_file"
    fi
}

# Get environment value
get_env_value() {
    local key="$1"
    local env_file="${2:-$ENV_FILE}"
    
    if [ ! -f "$env_file" ]; then
        return 1
    fi
    
    grep "^${key}=" "$env_file" 2>/dev/null | cut -d'=' -f2- | sed 's/#.*//' | sed 's/^[ \t]*//;s/[ \t]*$//' | sed 's/^[\"'\'']//' | sed 's/[\"'\'']$//'
}

# Validate environment configuration
validate_environment() {
    local env_file="${1:-$ENV_FILE}"
    
    log "INFO" "Validating environment configuration..."
    
    if [ ! -f "$env_file" ]; then
        log "ERROR" "Environment file not found: $env_file"
        return 1
    fi
    
    local critical_issues=()
    local warnings=()
    
    # Check absolutely required variables for basic functionality
    local required_vars=("DATABASE_URL")
    for var in "${required_vars[@]}"; do
        local value=$(get_env_value "$var" "$env_file")
        if [ -z "$value" ]; then
            critical_issues+=("Missing required variable: $var")
        fi
    done
    
    # Check AM_API_KEY specifically (should be auto-generated)
    local am_api_key=$(get_env_value "AM_API_KEY" "$env_file")
    if [ -z "$am_api_key" ]; then
        critical_issues+=("Missing required variable: AM_API_KEY")
    fi
    
    # Check important variables for AI functionality
    local ai_vars=("OPENAI_API_KEY" "DISCORD_BOT_TOKEN")
    for var in "${ai_vars[@]}"; do
        local value=$(get_env_value "$var" "$env_file")
        if [ -z "$value" ]; then
            warnings+=("Missing API key for full functionality: $var")
        fi
    done
    
    # Report critical issues
    if [ ${#critical_issues[@]} -gt 0 ]; then
        log "ERROR" "Environment validation failed with critical issues:"
        for issue in "${critical_issues[@]}"; do
            log "ERROR" "  ❌ $issue"
        done
        return 1
    fi
    
    # Report warnings
    if [ ${#warnings[@]} -gt 0 ]; then
        for warning in "${warnings[@]}"; do
            log "WARN" "⚠️  $warning"
        done
    fi
    
    log "SUCCESS" "Environment configuration is valid"
    return 0
}

# Show environment file location and next steps
show_config_info() {
    echo
    echo -e "${CYAN}📋 Configuration Information:${NC}"
    echo -e "  Environment file: ${GREEN}$ENV_FILE${NC}"
    
    if [ -d "$ENV_BACKUP_DIR" ] && [ "$(ls -A "$ENV_BACKUP_DIR" 2>/dev/null)" ]; then
        echo -e "  Backups available in: ${BLUE}$ENV_BACKUP_DIR${NC}"
    fi
    
    echo
    echo -e "${YELLOW}📝 To modify configuration later:${NC}"
    echo -e "  Edit: ${GREEN}nano $ENV_FILE${NC}"
    echo -e "  Or:   ${GREEN}vim $ENV_FILE${NC}"
    echo
    
    echo -e "${YELLOW}🔑 Important environment variables:${NC}"
    echo -e "  ${BLUE}AM_API_KEY${NC}        - Required for authentication"
    echo -e "  ${BLUE}OPENAI_API_KEY${NC}    - Required for AI functionality"
    echo -e "  ${BLUE}DISCORD_BOT_TOKEN${NC} - Required for Discord integration"
    echo -e "  ${BLUE}DATABASE_URL${NC}      - Database connection string"
    echo
}

# Set default database URL for local installation
set_local_database_url() {
    local use_docker_db="${1:-true}"
    
    if [ "$use_docker_db" = true ]; then
        local db_url="postgresql://postgres:postgres@localhost:5432/automagik"
        update_env_value "DATABASE_URL" "$db_url"
        log "INFO" "Set DATABASE_URL for Docker PostgreSQL"
    else
        log "INFO" "Using existing DATABASE_URL or manual configuration required"
    fi
}

# Generate secure API key
generate_api_key() {
    # Generate a secure random API key
    if check_command openssl; then
        openssl rand -hex 32
    elif check_command python3; then
        command python3 -c 'import secrets; print(secrets.token_hex(32))'
    else
        # Fallback to a simple random string
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1
    fi
}

# Setup configuration with options
setup_configuration() {
    local interactive="${1:-true}"
    local use_docker_db="${2:-true}"
    local force_recreate="${3:-false}"
    
    # Setup environment file
    if ! setup_environment_file "$force_recreate"; then
        log "ERROR" "Failed to setup environment file"
        return 1
    fi
    
    # Set database URL for local installation
    set_local_database_url "$use_docker_db"
    
    # Configure essential settings if we created a new .env file
    if [ "$NEW_ENV_CREATED" = "true" ]; then
        if [ "$interactive" = "true" ] && [ "$NON_INTERACTIVE" != "true" ]; then
            echo
            if confirm_action "Would you like to configure essential settings now?" "y"; then
                configure_essential_settings
            else
                configure_essential_settings_non_interactive
                log "INFO" "You can configure API keys later by editing .env file"
            fi
        else
            configure_essential_settings_non_interactive
        fi
    fi
    
    # Validate configuration
    if ! validate_environment; then
        log "WARN" "Environment validation had issues, but continuing installation..."
        log "INFO" "You may need to configure API keys in .env for full functionality"
    fi
    
    log "SUCCESS" "Configuration setup completed"
    return 0
}

# Export functions
export -f setup_environment_file configure_essential_settings update_env_value
export -f get_env_value validate_environment show_config_info
export -f set_local_database_url generate_api_key setup_configuration 