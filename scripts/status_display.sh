#!/bin/bash

# PM2-Style Status Display for Automagik Agents
# Part of NMSTX-101: Status display implementation

# Colors (Purple theme)
PURPLE='\033[0;35m'
BOLD_PURPLE='\033[1;35m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Unicode characters for status
ONLINE="●"
STOPPED="○"
WARNING="⚠"

# Function to get running time from a timestamp
get_uptime() {
    local start_time="$1"
    if [ -z "$start_time" ] || [ "$start_time" = "-" ]; then
        echo "-"
        return
    fi
    
    local current_time=$(date +%s)
    local diff=$((current_time - start_time))
    
    if [ $diff -lt 60 ]; then
        echo "${diff}s"
    elif [ $diff -lt 3600 ]; then
        echo "$((diff/60))m"
    elif [ $diff -lt 86400 ]; then
        echo "$((diff/3600))h $((diff%3600/60))m"
    else
        echo "$((diff/86400))d $((diff%86400/3600))h"
    fi
}

# Function to detect Docker containers
detect_docker_containers() {
    # Get all automagik-agents containers
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            local name=$(echo "$line" | awk '{print $1}')
            local state=$(echo "$line" | awk '{print $2}')
            local ports=$(echo "$line" | awk '{$1=$2=""; print $0}' | sed 's/^ *//')
            
            # Extract port number
            local port=$(echo "$ports" | grep -o '[0-9]\{4,5\}' | head -1)
            [ -z "$port" ] && port="-"
            
            # Get container ID and start time
            local container_id=$(docker ps -a --filter "name=$name" --format "{{.ID}}" | cut -c1-6)
            local start_time=""
            if [ "$state" = "running" ]; then
                start_time=$(docker inspect "$name" --format='{{.State.StartedAt}}' 2>/dev/null)
                if [ -n "$start_time" ]; then
                    start_time=$(date -d "$start_time" +%s 2>/dev/null || echo "-")
                fi
            fi
            
            # Determine instance type from name
            local instance_type="docker"
            local instance_name="$name"
            if [[ "$name" == *"-dev" ]]; then
                instance_name="agents-dev"
            elif [[ "$name" == *"-prod" ]]; then
                instance_name="agents-prod"
            elif [[ "$name" == *"-db" ]]; then
                instance_name="postgres-db"
            elif [[ "$name" == *"-graphiti"* ]]; then
                instance_name="graphiti"
            fi
            
            # Format status
            local status_text=""
            if [ "$state" = "running" ]; then
                status_text="${GREEN}$ONLINE online${NC}"
            else
                status_text="${GRAY}$STOPPED stopped${NC}"
            fi
            
            local uptime=$(get_uptime "$start_time")
            
            echo "$instance_name|$instance_type|$port|$container_id|$uptime|$status_text"
        fi
    done < <(docker ps -a --filter "name=automagik-agents-" --format "{{.Names}} {{.State}} {{.Ports}}" 2>/dev/null)
}

# Function to detect systemd service
detect_systemd_service() {
    if command -v systemctl >/dev/null 2>&1; then
        local status=$(systemctl is-active automagik-agents 2>/dev/null || echo "inactive")
        local pid=""
        local port=""
        local uptime=""
        
        if [ "$status" = "active" ]; then
            pid=$(systemctl show automagik-agents --property=MainPID --value 2>/dev/null)
            # Try to get port from environment or process
            port=$(ps aux | grep "$pid" | grep -o 'AM_PORT[=:][0-9]*' | cut -d'=' -f2 | cut -d':' -f2 | head -1)
            [ -z "$port" ] && port="8881"  # default
            
            # Get service start time
            local start_time=$(systemctl show automagik-agents --property=ActiveEnterTimestamp --value 2>/dev/null)
            if [ -n "$start_time" ]; then
                start_time=$(date -d "$start_time" +%s 2>/dev/null || echo "-")
            fi
            uptime=$(get_uptime "$start_time")
            
            echo "automagik|service|$port|$pid|$uptime|${GREEN}$ONLINE online${NC}"
        else
            echo "automagik|service|-|-|-|${GRAY}$STOPPED stopped${NC}"
        fi
    fi
}

# Function to detect development processes
detect_dev_processes() {
    # Look for python processes running automagik agents
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            local pid=$(echo "$line" | awk '{print $2}')
            local port=$(echo "$line" | grep -o 'AM_PORT[=:][0-9]*' | cut -d'=' -f2 | cut -d':' -f2 | head -1)
            [ -z "$port" ] && port="8881"  # default
            
            # Get process start time
            local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null)
            if [ -n "$start_time" ]; then
                start_time=$(date -d "$start_time" +%s 2>/dev/null || echo "-")
            fi
            local uptime=$(get_uptime "$start_time")
            
            echo "agents-dev|process|$port|$pid|$uptime|${GREEN}$ONLINE online${NC}"
        fi
    done < <(ps aux | grep -E "(python.*src|uvicorn.*src)" | grep -v grep | grep -v docker)
}

# Main status display function
show_status() {
    echo -e "${BOLD_PURPLE}💜 Automagik Agents Status${NC}"
    echo -e "${PURPLE}┌─────────────────┬──────────┬───────┬────────┬─────────┬──────────┐${NC}"
    echo -e "${PURPLE}│ Instance        │ Mode     │ Port  │ PID    │ Uptime  │ Status   │${NC}"
    echo -e "${PURPLE}├─────────────────┼──────────┼───────┼────────┼─────────┼──────────┤${NC}"
    
    # Collect all instances
    local instances=()
    
    # Add systemd service
    local service_data=$(detect_systemd_service)
    if [ -n "$service_data" ] && [ "$service_data" != "" ]; then
        instances+=("$service_data")
    fi
    
    # Add docker containers
    local docker_data=$(detect_docker_containers)
    if [ -n "$docker_data" ] && [ "$docker_data" != "" ]; then
        while IFS= read -r line; do
            if [ -n "$line" ]; then
                instances+=("$line")
            fi
        done <<< "$docker_data"
    fi
    
    # Add development processes
    local dev_data=$(detect_dev_processes)
    if [ -n "$dev_data" ] && [ "$dev_data" != "" ]; then
        while IFS= read -r line; do
            if [ -n "$line" ]; then
                instances+=("$line")
            fi
        done <<< "$dev_data"
    fi
    
    # Display instances or show empty state
    if [ ${#instances[@]} -gt 0 ]; then
        for instance_data in "${instances[@]}"; do
            # Remove leading/trailing |
            instance_data=$(echo "$instance_data" | sed 's/^|//;s/|$//')
            
            if [ -n "$instance_data" ]; then
                IFS='|' read -r instance mode port pid uptime status <<< "$instance_data"
                
                # Use echo to properly interpret color codes, then format with printf
                local clean_status=$(echo -e "$status")
                
                printf "${PURPLE}│${NC} %-15s ${PURPLE}│${NC} %-8s ${PURPLE}│${NC} %-5s ${PURPLE}│${NC} %-6s ${PURPLE}│${NC} %-7s ${PURPLE}│${NC} %s ${PURPLE}│${NC}\n" \
                    "$instance" "$mode" "$port" "$pid" "$uptime" "$clean_status"
            fi
        done
    else
        printf "${PURPLE}│${NC} %-15s ${PURPLE}│${NC} %-8s ${PURPLE}│${NC} %-5s ${PURPLE}│${NC} %-6s ${PURPLE}│${NC} %-7s ${PURPLE}│${NC} %-17s ${PURPLE}│${NC}\n" \
            "No instances" "-" "-" "-" "-" "${GRAY}$STOPPED stopped${NC}"
    fi
    
    echo -e "${PURPLE}└─────────────────┴──────────┴───────┴────────┴─────────┴──────────┘${NC}"
    
    # Summary
    local total_running=0
    local total_stopped=0
    
    for instance_data in "${instances[@]}"; do
        if [[ "$instance_data" == *"online"* ]]; then
            ((total_running++))
        elif [[ "$instance_data" == *"stopped"* ]]; then
            ((total_stopped++))
        fi
    done
    
    echo ""
    if [ "$total_running" -gt 0 ]; then
        echo -e "${GREEN}● ${total_running} running${NC} • ${GRAY}○ ${total_stopped} stopped${NC}"
    else
        echo -e "${GRAY}○ All instances stopped${NC}"
    fi
}

# Handle command line arguments
case "${1:-}" in
    "-v"|"--verbose")
        echo "Verbose mode - showing detailed information"
        show_status
        echo ""
        echo -e "${PURPLE}🔍 Detection Details:${NC}"
        echo "Docker containers:"
        docker ps -a --filter "name=automagik-agents-" --format "table {{.Names}}\t{{.State}}\t{{.Ports}}" 2>/dev/null || echo "  No Docker containers found"
        echo ""
        echo "System service:"
        systemctl is-active automagik-agents 2>/dev/null || echo "  Service not installed"
        echo ""
        echo "Development processes:"
        ps aux | grep -E "(python.*src|uvicorn.*src)" | grep -v grep | grep -v docker || echo "  No development processes found"
        ;;
    *)
        show_status
        ;;
esac 