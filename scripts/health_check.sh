#!/bin/bash

# Unified Health Check System for Automagik Agents
# Part of NMSTX-105: Health check system implementation

# Colors (Purple theme matching status display)
PURPLE='\033[0;35m'
BOLD_PURPLE='\033[1;35m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Health indicators
HEALTHY="●"
WARNING="⚠"
DOWN="✗"
OPTIONAL="○"

# Default timeouts
TIMEOUT=${TIMEOUT:-5}
DEFAULT_PORT=${AUTOMAGIK_API_PORT:-8881}

# Function to check if a service is responding on a port
check_port() {
    local host=${1:-localhost}
    local port=$2
    local timeout=${3:-$TIMEOUT}
    
    if [ -z "$port" ]; then
        return 1
    fi
    
    timeout "$timeout" bash -c "</dev/tcp/$host/$port" >/dev/null 2>&1
}

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local timeout=${2:-$TIMEOUT}
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --max-time "$timeout" --fail "$url" >/dev/null 2>&1
    else
        # Fallback using nc if curl not available
        local host=$(echo "$url" | sed -n 's|http://\([^:/]*\).*|\1|p')
        local port=$(echo "$url" | sed -n 's|http://[^:]*:\([0-9]*\).*|\1|p')
        [ -z "$port" ] && port=80
        check_port "$host" "$port" "$timeout"
    fi
}

# Function to get port from environment
get_port_from_env() {
    local var_name=$1
    local default_port=$2
    local env_file=${3:-.env}
    
    if [ -f "$env_file" ]; then
        local port=$(grep "^${var_name}=" "$env_file" 2>/dev/null | cut -d'=' -f2 | tr -d ' "')
        echo "${port:-$default_port}"
    else
        echo "$default_port"
    fi
}

# Check Automagik Agents API
check_agents_api() {
    local port=$(get_port_from_env "AUTOMAGIK_API_PORT" "$DEFAULT_PORT")
    local health_url="http://localhost:${port}/health"
    
    echo -n "  💜 Automagik Agents API    "
    
    if check_http "$health_url"; then
        echo -e "${GREEN}${HEALTHY} healthy${NC}"
        return 0
    else
        # Try to detect if the service is running but not responding
        if check_port "localhost" "$port" 2; then
            echo -e "${YELLOW}${WARNING} responding but unhealthy${NC}"
            return 1
        else
            echo -e "${RED}${DOWN} down${NC}"
            return 1
        fi
    fi
}

# Check PostgreSQL Database
check_postgres() {
    echo -n "  🐘 PostgreSQL Database     "
    
    # First try with standardized Docker container
    if docker exec automagik-agents-db pg_isready >/dev/null 2>&1; then
        echo -e "${GREEN}${HEALTHY} healthy${NC}"
        return 0
    # Fallback to old naming
    elif docker exec automagik_agents_db pg_isready >/dev/null 2>&1; then
        echo -e "${GREEN}${HEALTHY} healthy${NC}"
        return 0
    # Try direct connection if not using Docker
    elif command -v pg_isready >/dev/null 2>&1; then
        local db_host=$(get_port_from_env "POSTGRES_HOST" "localhost")
        local db_port=$(get_port_from_env "POSTGRES_PORT" "5432")
        
        if pg_isready -h "$db_host" -p "$db_port" >/dev/null 2>&1; then
            echo -e "${GREEN}${HEALTHY} healthy${NC}"
            return 0
        else
            echo -e "${RED}${DOWN} down${NC}"
            return 1
        fi
    else
        echo -e "${RED}${DOWN} not found${NC}"
        return 1
    fi
}

# Check Neo4j Graph Database
check_neo4j() {
    echo -n "  🔷 Neo4j Graph Database    "
    
    # Check if Neo4j is required (graphiti profile)
    local neo4j_required=false
    if grep -q "NEO4J" .env 2>/dev/null || docker ps | grep -q "neo4j"; then
        neo4j_required=true
    fi
    
    local neo4j_port=$(get_port_from_env "NEO4J_PORT" "7474")
    
    if check_http "http://localhost:${neo4j_port}"; then
        echo -e "${GREEN}${HEALTHY} healthy${NC}"
        return 0
    elif $neo4j_required; then
        echo -e "${RED}${DOWN} required but down${NC}"
        return 1
    else
        echo -e "${GRAY}${OPTIONAL} not required${NC}"
        return 0
    fi
}

# Check Graphiti Service
check_graphiti() {
    echo -n "  📊 Graphiti Service        "
    
    # Check for Docker containers
    local graphiti_running=false
    if docker ps | grep -q "automagik-agents-graphiti"; then
        graphiti_running=true
    elif docker ps | grep -q "automagik_graphiti"; then
        graphiti_running=true
    fi
    
    if $graphiti_running; then
        # Try standard healthcheck endpoint
        if check_http "http://localhost:8000/healthcheck" || check_http "http://localhost:18000/healthcheck"; then
            echo -e "${GREEN}${HEALTHY} healthy${NC}"
            return 0
        else
            echo -e "${YELLOW}${WARNING} running but not responding${NC}"
            return 1
        fi
    else
        echo -e "${GRAY}${OPTIONAL} not running${NC}"
        return 0
    fi
}

# Check specific service
check_service() {
    local service=$1
    case "$service" in
        "api"|"agents")
            check_agents_api
            ;;
        "postgres"|"postgresql"|"db")
            check_postgres
            ;;
        "neo4j"|"graph")
            check_neo4j
            ;;
        "graphiti")
            check_graphiti
            ;;
        *)
            echo "Unknown service: $service"
            echo "Available services: api, postgres, neo4j, graphiti"
            return 1
            ;;
    esac
}

# Main health check function
run_health_check() {
    echo -e "${BOLD_PURPLE}💜 Automagik Health Check${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local failed_services=0
    local total_services=0
    
    # Check all services
    services=("agents_api" "postgres" "neo4j" "graphiti")
    
    for service in "${services[@]}"; do
        case "$service" in
            "agents_api")
                check_agents_api || ((failed_services++))
                ;;
            "postgres")
                check_postgres || ((failed_services++))
                ;;
            "neo4j")
                check_neo4j || ((failed_services++))
                ;;
            "graphiti")
                check_graphiti || ((failed_services++))
                ;;
        esac
        ((total_services++))
    done
    
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Overall status
    if [ $failed_services -eq 0 ]; then
        echo -e "Overall Status: ${GREEN}✅ All systems operational${NC}"
        return 0
    elif [ $failed_services -lt $total_services ]; then
        echo -e "Overall Status: ${YELLOW}⚠️  ${failed_services} service(s) down${NC}"
        return 1
    else
        echo -e "Overall Status: ${RED}❌ Critical systems down${NC}"
        return 2
    fi
}

# Quick health check (just status codes)
quick_health_check() {
    local failed=0
    
    # Check critical services only
    check_agents_api >/dev/null || ((failed++))
    check_postgres >/dev/null || ((failed++))
    
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}${HEALTHY} All critical services healthy${NC}"
        return 0
    else
        echo -e "${RED}${DOWN} ${failed} critical service(s) down${NC}"
        return $failed
    fi
}

# Detailed health information
detailed_health_info() {
    echo -e "${BOLD_PURPLE}💜 Detailed Health Information${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo ""
    echo -e "${PURPLE}🔍 Environment Information:${NC}"
    local am_port=$(get_port_from_env "AUTOMAGIK_API_PORT" "$DEFAULT_PORT")
    echo "  AUTOMAGIK_API_PORT: $am_port"
    echo "  Environment file: $([[ -f .env ]] && echo "✅ .env found" || echo "❌ .env missing")"
    echo "  Production file: $([[ -f .env.prod ]] && echo "✅ .env.prod found" || echo "❌ .env.prod missing")"
    
    echo ""
    echo -e "${PURPLE}🐳 Docker Information:${NC}"
    local docker_containers=$(docker ps --filter "name=automagik-agents-" --format "{{.Names}}" | wc -l)
    echo "  Automagik containers running: $docker_containers"
    if [ "$docker_containers" -gt 0 ]; then
        docker ps --filter "name=automagik-agents-" --format "  - {{.Names}} ({{.Status}})"
    fi
    
    echo ""
    echo -e "${PURPLE}📡 Network Connectivity:${NC}"
    local am_port=$(get_port_from_env "AUTOMAGIK_API_PORT" "$DEFAULT_PORT")
    local postgres_port=$(get_port_from_env "POSTGRES_PORT" "5432")
    local neo4j_port=$(get_port_from_env "NEO4J_PORT" "7474")
    
    echo -n "  Port $am_port (API): "
    if check_port "localhost" "$am_port" 2; then
        echo -e "${GREEN}open${NC}"
    else
        echo -e "${RED}closed${NC}"
    fi
    
    echo -n "  Port $postgres_port (PostgreSQL): "
    if check_port "localhost" "$postgres_port" 2; then
        echo -e "${GREEN}open${NC}"
    else
        echo -e "${RED}closed${NC}"
    fi
    
    echo -n "  Port $neo4j_port (Neo4j): "
    if check_port "localhost" "$neo4j_port" 2; then
        echo -e "${GREEN}open${NC}"
    else
        echo -e "${GRAY}closed${NC}"
    fi
}

# Handle command line arguments
case "${1:-}" in
    "-q"|"--quick")
        quick_health_check
        ;;
    "-d"|"--detailed")
        run_health_check
        echo ""
        detailed_health_info
        ;;
    "-s"|"--service")
        if [ -n "$2" ]; then
            check_service "$2"
        else
            echo "Usage: $0 --service <service_name>"
            echo "Available services: api, postgres, neo4j, graphiti"
            exit 1
        fi
        ;;
    "-h"|"--help")
        echo "Automagik Agents Health Check System"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no options)        Run full health check"
        echo "  -q, --quick         Quick health check (critical services only)"
        echo "  -d, --detailed      Detailed health check with system info"
        echo "  -s, --service NAME  Check specific service"
        echo "  -h, --help          Show this help"
        echo ""
        echo "Environment variables:"
        echo "  TIMEOUT=N           Set connection timeout (default: 5 seconds)"
        echo ""
        echo "Examples:"
        echo "  $0                  # Full health check"
        echo "  $0 --quick          # Quick check"
        echo "  $0 --service api    # Check API only"
        echo "  TIMEOUT=10 $0       # Use 10s timeout"
        ;;
    "")
        run_health_check
        ;;
    *)
        echo "Unknown option: $1"
        echo "Run '$0 --help' for usage information"
        exit 1
        ;;
esac 