#!/bin/bash
# Test all Claude Code workflows

API_KEY="namastex888"
BASE_URL="http://localhost:28881/api/v1"

echo "🧪 Testing All Claude Code Workflows"
echo "===================================="
echo

# Array of workflows to test
declare -A WORKFLOWS=(
    ["test"]="Hello! List your top 3 tools with examples of how to use them."
    ["architect"]="Design a simple REST API architecture for a todo list application with user authentication."
    ["implement"]="Create a simple Python function that validates email addresses using regex."
    ["fix"]="Analyze this code and suggest fixes: def divide(a, b): return a/b"
    ["refactor"]="Suggest how to refactor this: x = []; for i in range(10): if i % 2 == 0: x.append(i)"
    ["review"]="Review this approach: Using global variables to store application state in a web server."
    ["document"]="Write documentation for a function called calculate_discount(price, percentage) that returns the discounted price."
    ["pr"]="Prepare a summary of changes for a pull request that adds user authentication to an API."
)

# Store run IDs
declare -A RUN_IDS

# Function to start a workflow
start_workflow() {
    local workflow=$1
    local message=$2
    
    echo "🚀 Starting $workflow workflow..."
    
    response=$(curl -s -X POST "$BASE_URL/agent/claude-code/run" \
        -H "x-api-key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"workflow_name\": \"$workflow\",
            \"message\": \"$message\",
            \"max_turns\": 1
        }")
    
    run_id=$(echo "$response" | grep -o '"run_id":"[^"]*' | cut -d'"' -f4)
    status=$(echo "$response" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$run_id" ]; then
        RUN_IDS[$workflow]=$run_id
        echo "✅ Started: $run_id (status: $status)"
    else
        echo "❌ Failed to start workflow"
        echo "Response: $response"
    fi
    echo
}

# Function to check workflow status
check_status() {
    local workflow=$1
    local run_id=$2
    
    echo "📊 Checking $workflow status (run_id: $run_id)..."
    
    response=$(curl -s -X GET "$BASE_URL/run/$run_id/status" \
        -H "x-api-key: $API_KEY")
    
    status=$(echo "$response" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    execution_time=$(echo "$response" | grep -o '"execution_time":[0-9.]*' | cut -d':' -f2)
    
    echo "Status: $status"
    if [ -n "$execution_time" ]; then
        echo "Execution time: ${execution_time}s"
    fi
    
    # Extract key log entries
    echo "Key log entries:"
    echo "$response" | grep -o '"logs":"[^"]*' | cut -d'"' -f4 | sed 's/\\n/\n/g' | grep -E "(session_confirmed|error|ERROR|completed|failed)" | head -5
    
    # Check for result
    if echo "$response" | grep -q '"result":'; then
        echo "✅ Has result"
        # Show first 200 chars of result
        result=$(echo "$response" | grep -o '"result":"[^"]*' | cut -d'"' -f4)
        echo "Result preview: ${result:0:200}..."
    else
        echo "⚠️  No result found"
    fi
    
    # Check for errors
    if echo "$response" | grep -q '"error":'; then
        error=$(echo "$response" | grep -o '"error":"[^"]*' | cut -d'"' -f4)
        if [ "$error" != "null" ]; then
            echo "❌ Error: $error"
        fi
    fi
    
    echo
}

# 1. Start all workflows
echo "=== PHASE 1: Starting All Workflows ==="
echo
for workflow in "${!WORKFLOWS[@]}"; do
    start_workflow "$workflow" "${WORKFLOWS[$workflow]}"
    sleep 1  # Small delay between starts
done

# 2. Wait for execution
echo "=== PHASE 2: Waiting for Execution ==="
echo "Waiting 30 seconds for workflows to complete..."
sleep 30

# 3. Check all statuses
echo
echo "=== PHASE 3: Checking Results ==="
echo
for workflow in "${!WORKFLOWS[@]}"; do
    if [ -n "${RUN_IDS[$workflow]}" ]; then
        check_status "$workflow" "${RUN_IDS[$workflow]}"
    fi
done

# 4. Detailed log analysis for failed workflows
echo "=== PHASE 4: Analyzing Issues ==="
echo
for workflow in "${!WORKFLOWS[@]}"; do
    if [ -n "${RUN_IDS[$workflow]}" ]; then
        run_id="${RUN_IDS[$workflow]}"
        
        # Check if workflow completed successfully
        response=$(curl -s -X GET "$BASE_URL/run/$run_id/status" -H "x-api-key: $API_KEY")
        status=$(echo "$response" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        
        if [ "$status" != "completed" ]; then
            echo "⚠️  $workflow workflow did not complete successfully (status: $status)"
            
            # Try to get more detailed logs
            if [ -f "/home/namastex/workspace/am-agents-labs/logs/run_${run_id}.log" ]; then
                echo "Checking log file for errors..."
                grep -i "error\|exception\|failed" "/home/namastex/workspace/am-agents-labs/logs/run_${run_id}.log" | tail -5
            fi
            echo
        fi
    fi
done

# 5. Summary
echo "=== SUMMARY ==="
echo
completed=0
failed=0
for workflow in "${!WORKFLOWS[@]}"; do
    if [ -n "${RUN_IDS[$workflow]}" ]; then
        response=$(curl -s -X GET "$BASE_URL/run/${RUN_IDS[$workflow]}/status" -H "x-api-key: $API_KEY")
        status=$(echo "$response" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        
        if [ "$status" = "completed" ]; then
            echo "✅ $workflow: COMPLETED"
            ((completed++))
        else
            echo "❌ $workflow: $status"
            ((failed++))
        fi
    else
        echo "❌ $workflow: FAILED TO START"
        ((failed++))
    fi
done

echo
echo "Total: $((completed + failed)) workflows"
echo "Completed: $completed"
echo "Failed/Other: $failed"
echo
echo "✅ Test complete!"