# Claude Code Status API - Enhanced Debug Mode Structure

## Debug Mode Overview

Based on real Claude CLI streaming JSON data, the enhanced debug mode provides comprehensive technical insights for troubleshooting, performance analysis, and workflow optimization. The debug output is structured into logical sections that expose all available data without cluttering the main status response.

## Complete Debug Response Structure

```json
{
  // Simplified main response (same as non-debug)
  "run_id": "run_63655145",
  "status": "completed", 
  "workflow_name": "simple_test",
  "started_at": "2025-06-14T02:55:16Z",
  "completed_at": "2025-06-14T02:55:40Z",
  "execution_time_seconds": 23.8,
  "progress": {
    "turns": 8,
    "max_turns": 30,
    "completion_type": "success",
    "current_phase": "completed"
  },
  "metrics": {
    "cost_usd": 0.154274,
    "tokens": {"total": 100989, "cache_efficiency": 74.2},
    "tools_used": ["Write", "Bash"]
  },
  "result": {
    "success": true,
    "message": "✅ Task completed successfully",
    "final_output": "The script works correctly!..."
  },

  // ===== DEBUG SECTION =====
  "debug": {
    
    // 1. SESSION & ENVIRONMENT INFO
    "session_info": {
      "claude_session_id": "63655145-2fe1-4f64-990b-02b563c5c88b",
      "database_session_id": "12345",
      "container_id": "claude-code-container-abc123",
      "model": "claude-sonnet-4-20250514",
      "permission_mode": "acceptEdits",
      "api_key_source": "none",
      "working_directory": "/home/namastex/workspace/am-agents-labs",
      "claude_cli_version": "1.0.24",
      "exit_code": 0
    },

    // 2. MCP SERVER ECOSYSTEM STATUS
    "mcp_infrastructure": {
      "servers_connected": 6,
      "servers_status": [
        {"name": "git", "status": "connected", "tools_available": 14},
        {"name": "agent-memory", "status": "connected", "tools_available": 8},
        {"name": "mcp-sqlite", "status": "connected", "tools_available": 8},
        {"name": "linear", "status": "connected", "tools_available": 32},
        {"name": "deepwiki", "status": "connected", "tools_available": 3},
        {"name": "automagik-workflows", "status": "connected", "tools_available": 4}
      ],
      "total_tools_available": 90,
      "tools_allowed": ["Task", "Bash", "Glob", "Grep", "LS", "Read", "Edit", "Write", "TodoRead", "TodoWrite"],
      "tools_restricted": ["WebFetch", "MultiEdit", "NotebookRead", "NotebookEdit"]
    },

    // 3. EXECUTION COMMAND & CONFIGURATION
    "execution_context": {
      "original_command": "claude -p --verbose --output-format stream-json --max-turns 30 --model sonnet --mcp-config .mcp.json --allowedTools Task Bash Glob Grep LS Read Edit Write TodoRead TodoWrite --permission-mode acceptEdits",
      "command_parameters": {
        "max_turns": 30,
        "model": "sonnet", 
        "output_format": "stream-json",
        "verbose": true,
        "permission_mode": "acceptEdits",
        "mcp_config": ".mcp.json",
        "allowed_tools": ["Task", "Bash", "Glob", "Grep", "LS", "Read", "Edit", "Write", "TodoRead", "TodoWrite"]
      },
      "environment_variables": {
        "mcp_timeout": 30000,
        "claude_max_memory": "4GB"
      }
    },

    // 4. TURN-BY-TURN EXECUTION BREAKDOWN
    "turn_by_turn_analysis": [
      {
        "turn": 1,
        "timestamp": "2025-06-14T02:55:17Z",
        "duration_estimate_ms": 3000,
        "message_id": "msg_01WLDXh1Uz2gDzMAaYLaPZka",
        "message_type": "assistant",
        "content_type": "text",
        "content_preview": "I'll create a simple test script to check if a file exists...",
        "phase": "planning",
        "tokens": {
          "input": 4,
          "output": 1,
          "cache_creation": 24558,
          "cache_read": 0,
          "total": 24563
        },
        "cost_usd": 0.123456,
        "tools_used": [],
        "stop_reason": null,
        "service_tier": "standard"
      },
      {
        "turn": 2,
        "timestamp": "2025-06-14T02:55:17Z",
        "duration_estimate_ms": 5000,
        "message_id": "msg_01WLDXh1Uz2gDzMAaYLaPZka",
        "message_type": "assistant",
        "content_type": "tool_use",
        "content_preview": "Writing test_file_check.py...",
        "phase": "implementation",
        "tokens": {
          "input": 4,
          "output": 1,
          "cache_creation": 24558,
          "cache_read": 0,
          "total": 24563
        },
        "cost_usd": 0.123456,
        "tools_used": ["Write"],
        "tool_results": [
          {
            "tool": "Write",
            "tool_use_id": "toolu_01Pi4iPtN5h5NCVxLGv164wh",
            "success": true,
            "file_path": "/home/namastex/workspace/am-agents-labs/test_file_check.py",
            "result": "File created successfully"
          }
        ],
        "stop_reason": null,
        "service_tier": "standard"
      },
      {
        "turn": 3,
        "timestamp": "2025-06-14T02:55:22Z",
        "duration_estimate_ms": 8000,
        "message_id": "msg_01KQD8LGK6itAg4kb475Fe3s",
        "message_type": "assistant",
        "content_type": "tool_use",
        "content_preview": "Running python test_file_check.py...",
        "phase": "testing",
        "tokens": {
          "input": 7,
          "output": 97,
          "cache_creation": 601,
          "cache_read": 24558,
          "total": 25263
        },
        "cost_usd": 0.015432,
        "tools_used": ["Bash"],
        "tool_results": [
          {
            "tool": "Bash",
            "tool_use_id": "toolu_01RFVRsAho5BoERdZFxWquiD",
            "success": false,
            "command": "python test_file_check.py",
            "error": "/bin/bash: line 1: python: command not found",
            "exit_code": 127
          }
        ],
        "errors_encountered": 1,
        "stop_reason": null,
        "service_tier": "standard"
      },
      {
        "turn": 4,
        "timestamp": "2025-06-14T02:55:30Z",
        "duration_estimate_ms": 7820,
        "message_id": "msg_01LbbcmRqP1CaFQts8Bmc6tW",
        "message_type": "assistant",
        "content_type": "tool_use",
        "content_preview": "Retrying with python3...",
        "phase": "testing",
        "tokens": {
          "input": 8,
          "output": 41,
          "cache_creation": 113,
          "cache_read": 25159,
          "total": 25321
        },
        "cost_usd": 0.012345,
        "tools_used": ["Bash"],
        "tool_results": [
          {
            "tool": "Bash",
            "tool_use_id": "toolu_012adquUpboLL879UfqbL7ML",
            "success": true,
            "command": "python3 test_file_check.py",
            "output": "File existence check:\\n✓ File 'CLAUDE.md' exists\\n✗ File 'nonexistent_file.txt' does not exist\\n✓ File 'test_file_check.py' exists",
            "exit_code": 0
          }
        ],
        "errors_encountered": 0,
        "stop_reason": null,
        "service_tier": "standard"
      }
    ],

    // 5. WORKFLOW PHASE ANALYSIS
    "workflow_phases": {
      "phases_detected": ["planning", "implementation", "testing", "completion"],
      "phase_breakdown": {
        "planning": {
          "turns": [1],
          "duration_ms": 3000,
          "tools_used": [],
          "primary_activity": "Task understanding and initial response"
        },
        "implementation": {
          "turns": [2],
          "duration_ms": 5000,
          "tools_used": ["Write"],
          "primary_activity": "File creation and code writing",
          "files_created": ["test_file_check.py"]
        },
        "testing": {
          "turns": [3, 4],
          "duration_ms": 15820,
          "tools_used": ["Bash"],
          "primary_activity": "Script execution and debugging",
          "errors_resolved": 1,
          "retry_attempts": 1
        },
        "completion": {
          "turns": [5],
          "duration_ms": 0,
          "tools_used": [],
          "primary_activity": "Final status confirmation"
        }
      },
      "phase_transitions": [
        {"from": "planning", "to": "implementation", "trigger": "task_understood"},
        {"from": "implementation", "to": "testing", "trigger": "file_created"},
        {"from": "testing", "to": "completion", "trigger": "test_successful"}
      ]
    },

    // 6. PERFORMANCE & EFFICIENCY METRICS
    "performance_analysis": {
      "cache_efficiency": {
        "cache_creation_tokens": 25422,
        "cache_read_tokens": 74989,
        "cache_hit_ratio": 74.7,
        "cache_effectiveness": "high"
      },
      "token_efficiency": {
        "total_tokens": 100989,
        "input_tokens": 26,
        "output_tokens": 562,
        "cache_tokens": 100401,
        "input_output_ratio": 21.6,
        "tokens_per_turn": 12623.6
      },
      "cost_efficiency": {
        "total_cost_usd": 0.154274,
        "cost_per_turn": 0.019284,
        "cost_per_token": 0.00000153,
        "cost_breakdown": {
          "input_cost": 0.00013,
          "output_cost": 0.00337,
          "cache_cost": 0.15077
        }
      },
      "execution_efficiency": {
        "total_duration_ms": 23820,
        "api_duration_ms": 43072,
        "overhead_ratio": 81.0,
        "average_turn_duration_ms": 2977.5,
        "tool_success_rate": 75.0
      }
    },

    // 7. TOOL USAGE STATISTICS
    "tool_usage_analysis": {
      "tools_invoked": {
        "Write": {
          "count": 1,
          "success_rate": 100.0,
          "total_duration_ms": 5000,
          "average_duration_ms": 5000,
          "files_affected": ["test_file_check.py"]
        },
        "Bash": {
          "count": 2,
          "success_rate": 50.0,
          "total_duration_ms": 15820,
          "average_duration_ms": 7910,
          "commands_executed": ["python test_file_check.py", "python3 test_file_check.py"],
          "errors_encountered": 1
        }
      },
      "tool_efficiency_ranking": [
        {"tool": "Write", "efficiency_score": 95, "reason": "High success rate, fast execution"},
        {"tool": "Bash", "efficiency_score": 70, "reason": "50% success rate due to python vs python3 issue"}
      ],
      "unused_tools_available": ["Task", "Glob", "Grep", "LS", "Read", "Edit", "TodoRead", "TodoWrite"]
    },

    // 8. ERROR ANALYSIS & RECOVERY
    "error_analysis": {
      "total_errors": 1,
      "error_rate": 12.5,
      "errors_by_type": {
        "command_not_found": 1
      },
      "error_details": [
        {
          "turn": 3,
          "tool": "Bash",
          "error_type": "command_not_found",
          "error_message": "/bin/bash: line 1: python: command not found",
          "resolution": "Retried with python3 in next turn",
          "resolution_success": true,
          "impact": "low"
        }
      ],
      "recovery_patterns": {
        "retry_with_alternative": 1,
        "automatic_correction": 1
      }
    },

    // 9. FILES & SYSTEM CHANGES
    "system_impact": {
      "files_created": [
        {
          "path": "/home/namastex/workspace/am-agents-labs/test_file_check.py",
          "size_bytes": 523,
          "type": "python_script",
          "turn_created": 2
        }
      ],
      "files_modified": [],
      "files_deleted": [],
      "directories_created": [],
      "git_operations": [],
      "database_operations": [],
      "network_requests": 0
    },

    // 10. CONVERSATION FLOW ANALYSIS  
    "conversation_analysis": {
      "message_count": 9,
      "assistant_messages": 5,
      "user_messages": 4,
      "tool_use_messages": 3,
      "text_only_messages": 2,
      "conversation_coherence": "high",
      "task_completion_clarity": "explicit",
      "user_engagement_required": false
    },

    // 11. RAW STREAM EVENTS (LAST 10)
    "raw_stream_sample": [
      {
        "timestamp": "2025-06-14T02:55:40.123Z",
        "event_type": "result",
        "event_data": {
          "type": "result",
          "subtype": "success",
          "is_error": false,
          "duration_ms": 23820,
          "result": "The script works correctly! It checks for three files: CLAUDE.md (exists), nonexistent_file.txt (doesn't exist), and itself (exists)."
        }
      },
      {
        "timestamp": "2025-06-14T02:55:35.456Z", 
        "event_type": "assistant",
        "event_data": {
          "message_id": "msg_01LT99YarQzKt3dWvG8eWkRG",
          "content": "The script works correctly! It checks for three files...",
          "tokens": {"input": 7, "output": 2}
        }
      }
    ],

    // 12. SYSTEM HEALTH & DIAGNOSTICS
    "system_diagnostics": {
      "claude_cli_health": "healthy",
      "mcp_servers_health": "all_connected",
      "memory_usage_estimate": "normal",
      "potential_issues": [],
      "recommendations": [
        "Consider adding python symlink to python3 for smoother execution",
        "Workflow completed efficiently with good cache utilization"
      ]
    }
  }
}
```

## Debug Mode Benefits

### **For Developers & DevOps**
- **Complete execution traceability** with turn-by-turn analysis
- **Performance bottleneck identification** through timing and efficiency metrics
- **Error pattern analysis** for proactive issue prevention
- **Resource utilization monitoring** (tokens, cache, cost)

### **For Workflow Optimization**
- **Phase detection insights** for workflow improvement
- **Tool usage efficiency** ranking for better tool selection
- **Cache utilization analysis** for performance optimization
- **Cost breakdown** for budget planning

### **For Troubleshooting**
- **Raw stream events** for deep debugging
- **MCP server status** for infrastructure issues
- **File system impact** tracking for rollback scenarios
- **Error recovery patterns** for automated fixes

### **For Analytics & Reporting**
- **Conversation flow analysis** for UX insights
- **Tool success rates** for tool reliability metrics
- **Cost efficiency tracking** for financial optimization
- **System health monitoring** for proactive maintenance

## Debug Mode Access Control

```python
@router.get("/run/{run_id}/status")
async def get_enhanced_status(
    run_id: str,
    debug: bool = False,
    debug_level: str = Query("standard", enum=["basic", "standard", "full"]),
    include_raw_stream: bool = Query(False),
    include_conversation: bool = Query(False)
):
    """
    Enhanced status endpoint with granular debug control.
    
    Debug Levels:
    - basic: Essential debug info (session, errors, performance)
    - standard: Full debug without raw streams (default)
    - full: Complete debug including raw stream events
    """
```

## Implementation Strategy

### **Phase 1: Core Debug Structure**
- Implement session info, tool usage, and performance metrics
- Add turn-by-turn analysis with token tracking
- Create workflow phase detection algorithms

### **Phase 2: Advanced Analytics**
- Add error analysis and recovery pattern detection
- Implement cache efficiency and cost breakdown analysis
- Create tool efficiency ranking system

### **Phase 3: Deep Diagnostics**
- Add raw stream event capture and analysis
- Implement system health monitoring
- Create recommendation engine for optimization

This enhanced debug mode transforms the status API from a simple progress checker into a comprehensive workflow analysis and optimization platform while keeping the main response clean and focused for regular monitoring needs.