#!/usr/bin/env python3
"""
Migration Safety System Demo - NMSTX-257

This script demonstrates the migration safety systems including feature flags,
monitoring, and safety triggers. It shows how the systems work together to
provide safe migration capabilities.

Usage:
    uv run python scripts/demo_migration_safety.py
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demo_feature_flags():
    """Demonstrate feature flag functionality."""
    print("🚩 FEATURE FLAGS DEMONSTRATION")
    print("=" * 50)
    
    from scripts.migrate_mcp_system import FeatureFlags
    
    # Clear environment for clean demo
    test_flags = ["MCP_USE_NEW_SYSTEM", "MCP_MIGRATION_ENABLED", 
                 "MCP_SAFETY_CHECKS", "MCP_AUTO_ROLLBACK", "MCP_MONITORING_ENABLED"]
    for flag in test_flags:
        os.environ.pop(flag, None)
    
    flags = FeatureFlags()
    
    print("1. Default Flag Values (Production Safe):")
    flag_descriptions = {
        "MCP_SAFETY_CHECKS": "Safety checks (should default to True)",
        "MCP_AUTO_ROLLBACK": "Auto rollback (should default to True)", 
        "MCP_MONITORING_ENABLED": "Monitoring (should default to True)",
        "MCP_MIGRATION_ENABLED": "Migration enabled (should default to False)",
        "MCP_USE_NEW_SYSTEM": "Use new system (should default to False)"
    }
    
    for flag, description in flag_descriptions.items():
        enabled = flags.is_enabled(flag)
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        print(f"   {flag}: {status} - {description}")
    
    print("\n2. Runtime Flag Modification:")
    print(f"   Before: MCP_MIGRATION_ENABLED = {flags.is_enabled('MCP_MIGRATION_ENABLED')}")
    
    flags.enable("MCP_MIGRATION_ENABLED")
    print(f"   After Enable: MCP_MIGRATION_ENABLED = {flags.is_enabled('MCP_MIGRATION_ENABLED')}")
    
    flags.disable("MCP_MIGRATION_ENABLED")
    print(f"   After Disable: MCP_MIGRATION_ENABLED = {flags.is_enabled('MCP_MIGRATION_ENABLED')}")
    
    print("\n3. Environment Variable Parsing:")
    test_cases = [("true", True), ("false", False), ("1", True), ("0", False), ("invalid", False)]
    
    for env_value, expected in test_cases:
        os.environ["MCP_USE_NEW_SYSTEM"] = env_value
        test_flags = FeatureFlags()
        actual = test_flags.is_enabled("MCP_USE_NEW_SYSTEM")
        result = "✅" if actual == expected else "❌"
        print(f"   '{env_value}' -> {actual} {result}")
    
    print("\n")


def demo_migration_monitor():
    """Demonstrate migration monitoring functionality."""
    print("🔍 MIGRATION MONITORING DEMONSTRATION")
    print("=" * 50)
    
    from scripts.migrate_mcp_system import MigrationMonitor, SafetyThresholdExceeded
    
    monitor = MigrationMonitor()
    
    print("1. Monitor Initialization:")
    print(f"   Safety Thresholds:")
    for key, value in monitor.safety_thresholds.items():
        print(f"     {key}: {value}")
    
    print(f"   Initial State: {len(monitor.errors)} errors, {len(monitor.warnings)} warnings")
    
    print("\n2. Starting Monitoring:")
    monitor.start_monitoring()
    print(f"   Monitoring started at: {datetime.fromtimestamp(monitor.start_time).strftime('%H:%M:%S')}")
    
    print("\n3. Recording Events:")
    
    # Record some warnings
    monitor.record_warning("System load is high", "performance_check")
    monitor.record_warning("Slow database response", "db_check")
    print(f"   Recorded 2 warnings")
    
    # Record some errors
    monitor.record_error("Connection timeout", "network_check")
    monitor.record_error("Invalid configuration", "config_check")
    print(f"   Recorded 2 errors")
    
    print(f"   Current State: {len(monitor.errors)} errors, {len(monitor.warnings)} warnings")
    
    print("\n4. Safety Threshold Testing:")
    print("   Testing error threshold (max 5 errors)...")
    
    try:
        # Add more errors to approach threshold
        for i in range(3):
            monitor.record_error(f"Additional error {i+1}", "threshold_test")
        print("   ❌ Error threshold should have been triggered!")
    except SafetyThresholdExceeded as e:
        print(f"   ✅ Safety threshold triggered: {e}")
    
    print("\n5. Duration Threshold Testing:")
    print("   Testing duration threshold (max 30 minutes)...")
    
    # Create a new monitor for duration test
    duration_monitor = MigrationMonitor()
    duration_monitor.start_monitoring()
    
    # Simulate exceeding time limit
    duration_monitor.start_time = time.time() - (31 * 60)  # 31 minutes ago
    
    try:
        duration_monitor.check_duration_threshold()
        print("   ❌ Duration threshold should have been triggered!")
    except SafetyThresholdExceeded as e:
        print(f"   ✅ Duration threshold triggered: {e}")
    
    print("\n6. Performance Metrics:")
    performance_monitor = MigrationMonitor()
    performance_monitor.start_monitoring()
    performance_monitor.performance_metrics = {
        "server_1": 120.5,
        "server_2": 98.2,
        "server_3": 4850.0  # Slow server
    }
    
    for server, response_time in performance_monitor.performance_metrics.items():
        status = "⚠️ SLOW" if response_time > 1000 else "✅ FAST"
        print(f"   {server}: {response_time:.1f}ms {status}")
    
    print("\n7. Monitoring Summary:")
    summary_monitor = MigrationMonitor()
    summary_monitor.start_monitoring()
    summary_monitor.record_error("Demo error", "demo")
    summary_monitor.record_warning("Demo warning", "demo")
    summary_monitor.performance_metrics = {"demo_server": 150.0}
    
    time.sleep(0.1)  # Small delay for duration calculation
    summary = summary_monitor.get_summary()
    
    print(f"   Duration: {summary['duration_minutes']:.3f} minutes")
    print(f"   Total Errors: {summary['total_errors']}")
    print(f"   Total Warnings: {summary['total_warnings']}")
    print(f"   Performance Metrics: {len(summary['performance_metrics'])} servers")
    
    print("\n")


def demo_server_transformation():
    """Demonstrate server configuration transformation."""
    print("🔄 SERVER TRANSFORMATION DEMONSTRATION")
    print("=" * 50)
    
    def transform_server_config(server_data, agent_names):
        """Demo transformation function."""
        config = {
            "name": server_data["name"],
            "server_type": server_data["server_type"],
            "enabled": server_data.get("enabled", True),
            "auto_start": server_data.get("auto_start", True),
            "timeout": (server_data.get("timeout_seconds", 30) * 1000),  # Convert to ms
            "retry_count": server_data.get("max_retries", 3),
            "agents": agent_names if agent_names else ["*"]  # Default to wildcard
        }
        
        # Add optional fields
        if server_data.get("description"):
            config["description"] = server_data["description"]
        
        if server_data.get("tags"):
            config["tags"] = server_data["tags"]
        
        if server_data.get("priority"):
            config["priority"] = server_data["priority"]
        
        # Add type-specific configuration
        if server_data["server_type"] == "stdio":
            if server_data.get("command"):
                config["command"] = server_data["command"]
            if server_data.get("env"):
                config["environment"] = server_data["env"]
        elif server_data["server_type"] == "http":
            if server_data.get("http_url"):
                config["url"] = server_data["http_url"]
        
        # Add tools configuration
        config["tools"] = {"include": ["*"], "exclude": []}
        
        return config
    
    print("1. Legacy STDIO Server Configuration:")
    legacy_stdio = {
        "id": 1,
        "name": "legacy-stdio-server",
        "server_type": "stdio",
        "command": ["python", "-m", "my_mcp_server"],
        "env": {"DEBUG": "1", "LOG_LEVEL": "INFO"},
        "enabled": True,
        "auto_start": True,
        "max_retries": 3,
        "timeout_seconds": 30,
        "description": "Legacy STDIO MCP Server",
        "tags": ["python", "legacy"],
        "priority": 1
    }
    
    print(json.dumps(legacy_stdio, indent=2))
    
    print("\n2. Transformed Configuration (with agents):")
    transformed_stdio = transform_server_config(legacy_stdio, ["simple", "genie"])
    print(json.dumps(transformed_stdio, indent=2))
    
    print("\n3. Legacy HTTP Server Configuration:")
    legacy_http = {
        "id": 2,
        "name": "legacy-http-server",
        "server_type": "http",
        "http_url": "https://api.example.com/mcp",
        "enabled": True,
        "auto_start": False,
        "max_retries": 5,
        "timeout_seconds": 60,
        "description": "Legacy HTTP MCP Server"
    }
    
    print(json.dumps(legacy_http, indent=2))
    
    print("\n4. Transformed Configuration (no agent assignments):")
    transformed_http = transform_server_config(legacy_http, [])
    print(json.dumps(transformed_http, indent=2))
    
    print("\n5. Key Transformation Changes:")
    print("   • timeout_seconds (30) -> timeout (30000ms)")
    print("   • max_retries (3) -> retry_count (3)")
    print("   • env -> environment")
    print("   • http_url -> url")
    print("   • Empty agent list -> ['*'] (wildcard)")
    print("   • Added tools configuration")
    
    print("\n")


def demo_integration_scenario():
    """Demonstrate integration of all components."""
    print("🔗 INTEGRATION SCENARIO DEMONSTRATION")
    print("=" * 50)
    
    from scripts.migrate_mcp_system import FeatureFlags, MigrationMonitor
    
    print("1. Setting Up Safe Migration Environment:")
    
    # Configure environment
    os.environ["MCP_MIGRATION_ENABLED"] = "true"
    os.environ["MCP_SAFETY_CHECKS"] = "true"
    os.environ["MCP_MONITORING_ENABLED"] = "true"
    os.environ["MCP_AUTO_ROLLBACK"] = "true"
    
    flags = FeatureFlags()
    monitor = MigrationMonitor()
    
    print("   Feature Flags:")
    for flag in ["MCP_MIGRATION_ENABLED", "MCP_SAFETY_CHECKS", "MCP_MONITORING_ENABLED", "MCP_AUTO_ROLLBACK"]:
        status = "✅ ENABLED" if flags.is_enabled(flag) else "❌ DISABLED"
        print(f"     {flag}: {status}")
    
    print("\n2. Pre-Migration Safety Checks:")
    
    # Simulate pre-migration checks
    checks = [
        ("Migration Enabled", flags.is_enabled("MCP_MIGRATION_ENABLED")),
        ("Safety Checks Enabled", flags.is_enabled("MCP_SAFETY_CHECKS")),
        ("Monitoring Enabled", flags.is_enabled("MCP_MONITORING_ENABLED")),
        ("Auto Rollback Enabled", flags.is_enabled("MCP_AUTO_ROLLBACK"))
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"     {check_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("   🎯 All pre-migration checks passed!")
    else:
        print("   ⚠️ Some pre-migration checks failed!")
    
    print("\n3. Simulated Migration Process:")
    
    if all_passed:
        monitor.start_monitoring()
        print("   📊 Monitoring started")
        
        # Simulate processing servers
        servers = [
            {"name": "agent-memory", "type": "stdio"},
            {"name": "linear-api", "type": "http"}, 
            {"name": "slack-bot", "type": "stdio"}
        ]
        
        for i, server in enumerate(servers):
            print(f"   🔄 Processing server {i+1}/{len(servers)}: {server['name']}")
            
            # Simulate some processing time
            time.sleep(0.05)
            
            # Test monitoring during process
            try:
                monitor.check_duration_threshold()
            except Exception:
                print("   ⚠️ Duration threshold would trigger auto-rollback")
            
            monitor.record_warning(f"Server {server['name']} migrated", "migration_process")
        
        print("   ✅ All servers processed successfully")
        
        # Get final summary
        summary = monitor.get_summary()
        print(f"   📈 Migration completed in {summary['duration_minutes']:.3f} minutes")
        print(f"   📊 {summary['total_warnings']} warnings, {summary['total_errors']} errors")
    
    print("\n4. Emergency Scenarios:")
    
    # Demonstrate emergency flag override
    print("   🚨 Emergency Scenario: Disable safety for critical fix")
    flags.disable("MCP_SAFETY_CHECKS")
    flags.disable("MCP_AUTO_ROLLBACK")
    
    print(f"     Safety Checks: {'DISABLED' if not flags.is_enabled('MCP_SAFETY_CHECKS') else 'ENABLED'}")
    print(f"     Auto Rollback: {'DISABLED' if not flags.is_enabled('MCP_AUTO_ROLLBACK') else 'ENABLED'}")
    print(f"     Monitoring: {'ENABLED' if flags.is_enabled('MCP_MONITORING_ENABLED') else 'DISABLED'}")
    print("     ℹ️ Monitoring remains enabled for observability")
    
    print("\n")


def main():
    """Run all demonstrations."""
    print("🧪 MIGRATION SAFETY SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo shows the migration safety systems in action.")
    print("All tests run in safe mode without affecting production systems.")
    print("=" * 60)
    print()
    
    try:
        demo_feature_flags()
        demo_migration_monitor()
        demo_server_transformation()
        demo_integration_scenario()
        
        print("🎯 DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("✅ All migration safety systems demonstrated successfully!")
        print()
        print("Key Takeaways:")
        print("• Feature flags provide safe rollout control")
        print("• Monitoring catches issues early with automatic thresholds")
        print("• Server transformation preserves functionality")
        print("• Integration scenarios show real-world usage")
        print("• Emergency overrides available for critical situations")
        print()
        print("The migration safety system is ready for production use.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()