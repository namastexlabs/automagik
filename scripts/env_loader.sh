#!/bin/bash

# Environment Detection and Loading System for Automagik Agents
# Part of NMSTX-108: Environment file detection and loading implementation

# Colors (Purple theme matching epic design)
PURPLE='\033[0;35m'
BOLD_PURPLE='\033[1;35m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Default environment files
ENV_FILE=".env"
PROD_ENV_FILE=".env.prod"
EXAMPLE_ENV_FILE=".env.example"

# Environment detection function
detect_environment_mode() {
    local mode="development"
    
    # Check if production environment indicators exist
    if [[ -f "$PROD_ENV_FILE" ]]; then
        # Check if we're in production mode based on:
        # 1. AM_ENV=production in current env
        # 2. Production ports in use
        # 3. Production containers running
        
        local current_env=$(grep "^AM_ENV=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' "'"'" | tr '[:upper:]' '[:lower:]')
        local prod_env=$(grep "^AM_ENV=" "$PROD_ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' "'"'" | tr '[:upper:]' '[:lower:]')
        local prod_port=$(grep "^AM_PORT=" "$PROD_ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d ' "'"'")
        
        # Check if production containers are running
        if docker ps | grep -q "automagik-agents-prod\|automagik_agent.*:${prod_port:-18881}"; then
            mode="production"
        # Check if environment is explicitly set to production
        elif [[ "$current_env" == "production" || "$prod_env" == "production" ]]; then
            mode="production"
        fi
    fi
    
    echo "$mode"
}

# Get the appropriate environment file based on mode
get_env_file() {
    local mode=$(detect_environment_mode)
    
    if [[ "$mode" == "production" && -f "$PROD_ENV_FILE" ]]; then
        echo "$PROD_ENV_FILE"
    elif [[ -f "$ENV_FILE" ]]; then
        echo "$ENV_FILE"
    else
        echo ""
    fi
}

# Load environment variables from specified file
load_env_file() {
    local env_file=${1:-$(get_env_file)}
    
    if [[ -z "$env_file" || ! -f "$env_file" ]]; then
        echo -e "${RED}❌ Environment file not found: ${env_file:-"none detected"}${NC}" >&2
        return 1
    fi
    
    # Export variables, handling comments and special characters
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Handle lines with = (environment variables)
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*) ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            
            # Remove quotes if present
            var_value=$(echo "$var_value" | sed 's/^["'"'"']\(.*\)["'"'"']$/\1/')
            
            # Remove inline comments
            var_value=$(echo "$var_value" | sed 's/[[:space:]]*#.*$//')
            
            # Export the variable
            export "$var_name"="$var_value"
        fi
    done < "$env_file"
    
    echo -e "${GREEN}✅ Environment loaded from: ${env_file}${NC}" >&2
    return 0
}

# Validate required environment variables
validate_env() {
    local env_file=${1:-$(get_env_file)}
    local errors=0
    
    if [[ -z "$env_file" || ! -f "$env_file" ]]; then
        echo -e "${RED}❌ Cannot validate: environment file not found${NC}" >&2
        return 1
    fi
    
    echo -e "${PURPLE}🔍 Validating environment variables...${NC}" >&2
    
    # Core required variables
    local required_vars=(
        "AM_API_KEY"
        "AM_PORT"
        "DATABASE_URL"
    )
    
    # Check each required variable
    for var in "${required_vars[@]}"; do
        local value=$(get_env_var "$var" "$env_file")
        if [[ -z "$value" || "$value" == "am-xxxxx" || "$value" == "your-key-here" ]]; then
            echo -e "  ${RED}✗ $var: missing or placeholder value${NC}" >&2
            ((errors++))
        else
            echo -e "  ${GREEN}✓ $var: configured${NC}" >&2
        fi
    done
    
    # Optional but important variables
    local optional_vars=(
        "OPENAI_API_KEY"
        "POSTGRES_HOST"
        "POSTGRES_PORT"
    )
    
    for var in "${optional_vars[@]}"; do
        local value=$(get_env_var "$var" "$env_file")
        if [[ -z "$value" ]]; then
            echo -e "  ${YELLOW}⚠ $var: not set (optional)${NC}" >&2
        else
            echo -e "  ${GREEN}✓ $var: configured${NC}" >&2
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        echo -e "${GREEN}✅ Environment validation passed${NC}" >&2
        return 0
    else
        echo -e "${RED}❌ Environment validation failed with $errors error(s)${NC}" >&2
        return $errors
    fi
}

# Get a specific environment variable from file
get_env_var() {
    local var_name="$1"
    local env_file="${2:-$(get_env_file)}"
    
    if [[ -z "$env_file" || ! -f "$env_file" ]]; then
        return 1
    fi
    
    grep "^${var_name}=" "$env_file" 2>/dev/null | head -1 | cut -d'=' -f2- | sed 's/^["'"'"']\(.*\)["'"'"']$/\1/' | sed 's/[[:space:]]*#.*$//'
}

# Get port from environment (with fallback)
get_port() {
    local var_name="${1:-AM_PORT}"
    local default_port="${2:-8881}"
    local env_file="${3:-$(get_env_file)}"
    
    local port=$(get_env_var "$var_name" "$env_file")
    echo "${port:-$default_port}"
}

# Environment information display
show_env_info() {
    local env_file=$(get_env_file)
    local mode=$(detect_environment_mode)
    
    echo -e "${BOLD_PURPLE}💜 Environment Information${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "${PURPLE}🎯 Detection Results:${NC}"
    echo "  Mode: $mode"
    echo "  Environment file: ${env_file:-"❌ not found"}"
    echo "  Files present:"
    [[ -f "$ENV_FILE" ]] && echo "    ✅ .env" || echo "    ❌ .env"
    [[ -f "$PROD_ENV_FILE" ]] && echo "    ✅ .env.prod" || echo "    ❌ .env.prod"
    [[ -f "$EXAMPLE_ENV_FILE" ]] && echo "    ✅ .env.example" || echo "    ❌ .env.example"
    
    if [[ -n "$env_file" && -f "$env_file" ]]; then
        echo ""
        echo -e "${PURPLE}🔧 Key Variables:${NC}"
        local am_port=$(get_env_var "AM_PORT" "$env_file")
        local am_env=$(get_env_var "AM_ENV" "$env_file")
        local db_host=$(get_env_var "POSTGRES_HOST" "$env_file")
        local db_port=$(get_env_var "POSTGRES_PORT" "$env_file")
        
        echo "  AM_PORT: ${am_port:-"not set"}"
        echo "  AM_ENV: ${am_env:-"not set"}"
        echo "  POSTGRES_HOST: ${db_host:-"not set"}"
        echo "  POSTGRES_PORT: ${db_port:-"not set"}"
    fi
}

# Check if environment supports a feature
env_supports_feature() {
    local feature="$1"
    local env_file="${2:-$(get_env_file)}"
    
    case "$feature" in
        "neo4j")
            local neo4j_uri=$(get_env_var "NEO4J_URI" "$env_file")
            [[ -n "$neo4j_uri" && "$neo4j_uri" != "bolt://neo4j:7687" ]]
            ;;
        "graphiti")
            local graphiti_enabled=$(get_env_var "GRAPHITI_QUEUE_ENABLED" "$env_file")
            [[ "$graphiti_enabled" == "true" ]]
            ;;
        "discord")
            local discord_token=$(get_env_var "DISCORD_BOT_TOKEN" "$env_file")
            [[ -n "$discord_token" && "$discord_token" != "your-token-here" ]]
            ;;
        "notion")
            local notion_token=$(get_env_var "NOTION_TOKEN" "$env_file")
            [[ -n "$notion_token" && "$notion_token" != "your-token-here" ]]
            ;;
        *)
            return 1
            ;;
    esac
}

# Create environment from template
create_env_from_template() {
    local target_file="${1:-$ENV_FILE}"
    
    if [[ ! -f "$EXAMPLE_ENV_FILE" ]]; then
        echo -e "${RED}❌ Template file not found: $EXAMPLE_ENV_FILE${NC}" >&2
        return 1
    fi
    
    if [[ -f "$target_file" ]]; then
        echo -e "${YELLOW}⚠️  File already exists: $target_file${NC}" >&2
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            return 1
        fi
    fi
    
    cp "$EXAMPLE_ENV_FILE" "$target_file"
    echo -e "${GREEN}✅ Environment file created: $target_file${NC}"
    echo -e "${YELLOW}⚠️  Please edit $target_file and set your actual values${NC}"
    return 0
}

# Main function to handle command line arguments
main() {
    case "${1:-}" in
        "load")
            load_env_file "$2"
            ;;
        "validate")
            validate_env "$2"
            ;;
        "info"|"show")
            show_env_info
            ;;
        "detect")
            detect_environment_mode
            ;;
        "get-env-file")
            get_env_file
            ;;
        "get-port")
            get_port "$2" "$3" "$4"
            ;;
        "get-var")
            if [[ -z "$2" ]]; then
                echo "Usage: $0 get-var VARIABLE_NAME [env_file]" >&2
                exit 1
            fi
            get_env_var "$2" "$3"
            ;;
        "supports")
            if [[ -z "$2" ]]; then
                echo "Usage: $0 supports FEATURE [env_file]" >&2
                echo "Features: neo4j, graphiti, discord, notion" >&2
                exit 1
            fi
            env_supports_feature "$2" "$3" && echo "yes" || echo "no"
            ;;
        "create")
            create_env_from_template "$2"
            ;;
        "help"|"-h"|"--help")
            echo "Automagik Agents Environment Loader"
            echo ""
            echo "Usage: $0 COMMAND [OPTIONS]"
            echo ""
            echo "Commands:"
            echo "  load [file]           Load environment variables from file"
            echo "  validate [file]       Validate required environment variables"
            echo "  info                  Show environment information"
            echo "  detect                Detect environment mode (development/production)"
            echo "  get-env-file          Get the appropriate environment file path"
            echo "  get-port [var] [def]  Get port from environment (default: AM_PORT, 8881)"
            echo "  get-var VAR [file]    Get specific environment variable"
            echo "  supports FEATURE      Check if environment supports feature"
            echo "  create [file]         Create environment file from template"
            echo "  help                  Show this help"
            echo ""
            echo "Features for 'supports': neo4j, graphiti, discord, notion"
            echo ""
            echo "Examples:"
            echo "  $0 load                    # Load environment"
            echo "  $0 validate                # Validate environment"
            echo "  $0 get-port                # Get AM_PORT"
            echo "  $0 get-port POSTGRES_PORT 5432  # Get POSTGRES_PORT with default"
            echo "  $0 get-var DATABASE_URL    # Get DATABASE_URL"
            echo "  $0 supports graphiti       # Check if Graphiti is enabled"
            echo "  $0 create .env.local       # Create new env file from template"
            ;;
        "")
            echo "Usage: $0 COMMAND [OPTIONS]"
            echo "Run '$0 help' for available commands"
            ;;
        *)
            echo "Unknown command: $1" >&2
            echo "Run '$0 help' for available commands" >&2
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 