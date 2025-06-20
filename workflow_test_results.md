
7. Testing Kill Workflow on stuck workflows:
{
  "success": false,
  "run_id": "9daf1c45-f64b-4f57-9b9f-c11828ac6c01",
  "workflow_name": "surgeon",
  "killed_at": "2025-06-20T19:12:32.309435",
  "kill_method": "graceful",
  "kill_duration_ms": 3,
  "cleanup_status": {
    "session_updated": true,
    "audit_logged": true,
    "process_terminated": false
  },
  "message": "Workflow surgeon (gracefully terminated) in 0.00s"
}

8. Running another test workflow with git branch:
{
  "run_id": "a5e3c632-9dbc-40d0-9c58-3c4ffdeb17ef",
  "status": "pending",
  "message": "Started builder workflow. Use the status endpoint to track progress.",
  "session_id": "6b4a9984-deec-4e83-8bef-36880ab3d806",
  "workflow_name": "builder",
  "started_at": "2025-06-20T19:12:39.609895",
  "auto_commit_sha": null,
  "pr_url": null,
  "merge_sha": null
}

9. Check status of second test workflow:
{
  "run_id": "a5e3c632-9dbc-40d0-9c58-3c4ffdeb17ef",
  "status": "completed",
  "workflow_name": "builder",
  "started_at": "2025-06-20T19:12:39",
  "completed_at": "2025-06-20T19:12:55.915993",
  "execution_time_seconds": 16.0,
  "progress": {
    "turns": 0,
    "max_turns": 5,
    "completion_percentage": 100.0,
    "current_phase": "failed",
    "phases_completed": [
      "initializing"
    ],
    "is_running": false,
    "estimated_completion": null
  },
  "metrics": {
    "cost_usd": 0.1201079,
    "tokens": {
      "total": 77951,
      "input": 19,
      "output": 262,
      "cache_created": 0,
      "cache_read": 0,
      "cache_efficiency": 0.0
    },
    "tools_used": [],
    "api_duration_ms": 0,
    "performance_score": 60.0
  },
  "result": {
    "success": false,
    "completion_type": "unknown",
    "message": "⚠️ Workflow status unclear - check logs for details",
    "final_output": null,
    "files_created": [],
    "git_commits": [],
    "files_changed": []
  }
}
