"""
Automatic Safety Trigger System for MCP Migration - NMSTX-257

Provides automated safety mechanisms including data integrity validation,
performance regression detection, and emergency rollback capabilities
for the NMSTX-253 MCP System Refactor.

This module implements the critical safety triggers that protect production
deployments and ensure zero data loss during migration.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from ..config.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of safety triggers."""
    DATA_INTEGRITY = "data_integrity"
    PERFORMANCE_REGRESSION = "performance_regression"
    ZERO_DATA_LOSS = "zero_data_loss"
    SYSTEM_HEALTH = "system_health"
    THRESHOLD_BREACH = "threshold_breach"
    MANUAL_TRIGGER = "manual_trigger"


class TriggerSeverity(Enum):
    """Severity levels for safety triggers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyTriggerEvent:
    """Safety trigger event data."""
    trigger_id: str
    trigger_type: TriggerType
    severity: TriggerSeverity
    timestamp: datetime
    message: str
    context: Dict[str, Any]
    validation_data: Optional[Dict[str, Any]] = None
    rollback_required: bool = False
    auto_rollback_triggered: bool = False


@dataclass
class DataIntegrityResult:
    """Result of data integrity validation."""
    passed: bool
    total_records_checked: int
    discrepancies_found: int
    missing_records: List[str]
    corrupted_records: List[str]
    validation_details: Dict[str, Any]
    check_duration_seconds: float


@dataclass
class PerformanceComparisonResult:
    """Result of performance comparison."""
    passed: bool
    baseline_response_time_ms: float
    current_response_time_ms: float
    regression_percentage: float
    threshold_percentage: float
    affected_operations: List[str]
    check_duration_seconds: float


class SafetyTriggerSystem:
    """
    Automated safety trigger system for migration protection.
    
    Provides comprehensive safety mechanisms including:
    - Data integrity validation with zero-loss verification
    - Performance regression detection with automatic rollback
    - System health monitoring with threshold-based triggers
    - Emergency rollback capabilities with cause tracking
    - Configurable safety thresholds and response actions
    
    Features:
    - Real-time validation of data integrity
    - Automated detection of performance regression
    - Zero data loss verification with detailed reporting
    - Configurable rollback triggers and thresholds
    - Integration with feature flag system
    - Comprehensive logging and audit trail
    """
    
    def __init__(self):
        """Initialize the safety trigger system."""
        self.feature_flags = get_feature_flags()
        
        # Trigger state
        self.active_triggers: Dict[str, SafetyTriggerEvent] = {}
        self.trigger_history: List[SafetyTriggerEvent] = []
        self.rollback_handlers: List[Callable[[SafetyTriggerEvent], None]] = []
        
        # Safety thresholds (configurable)
        self.data_integrity_threshold = 0.0  # 0% data loss tolerance
        self.performance_regression_threshold = 0.2  # 20% performance degradation
        self.response_time_threshold_ms = 5000  # 5 second response time limit
        self.error_rate_threshold = 0.1  # 10% error rate limit
        
        # Baseline data for comparisons
        self.baseline_performance: Optional[Dict[str, float]] = None
        self.baseline_data_counts: Optional[Dict[str, int]] = None
        
        # Internal state
        self.is_active = False
        self.last_validation_time: Optional[datetime] = None
        
        logger.info("🛡️ Safety trigger system initialized")
    
    def add_rollback_handler(self, handler: Callable[[SafetyTriggerEvent], None]) -> None:
        """
        Add a rollback handler function.
        
        Args:
            handler: Function to call when rollback is triggered
        """
        self.rollback_handlers.append(handler)
        logger.debug(f"Added rollback handler: {handler.__name__}")
    
    def activate(self) -> None:
        """Activate the safety trigger system."""
        if not self.feature_flags.is_enabled("MCP_SAFETY_CHECKS"):
            logger.info("Safety checks disabled by feature flag")
            return
        
        self.is_active = True
        logger.info("🛡️ Safety trigger system activated")
    
    def deactivate(self) -> None:
        """Deactivate the safety trigger system."""
        self.is_active = False
        logger.info("🛡️ Safety trigger system deactivated")
    
    async def capture_baseline_metrics(self) -> Dict[str, Any]:
        """
        Capture baseline metrics for comparison.
        
        Returns:
            Baseline metrics data
        """
        logger.info("📊 Capturing baseline metrics for safety validation")
        
        try:
            # Capture performance baseline
            start_time = time.time()
            self.baseline_performance = await self._measure_system_performance()
            
            # Capture data count baseline
            self.baseline_data_counts = await self._count_database_records()
            
            duration = time.time() - start_time
            
            baseline_data = {
                "timestamp": datetime.now().isoformat(),
                "performance": self.baseline_performance,
                "data_counts": self.baseline_data_counts,
                "capture_duration_seconds": duration
            }
            
            logger.info(f"✅ Baseline metrics captured in {duration:.2f}s")
            return baseline_data
            
        except Exception as e:
            logger.error(f"❌ Failed to capture baseline metrics: {e}")
            raise
    
    async def validate_zero_data_loss(self) -> DataIntegrityResult:
        """
        Validate that no data has been lost during migration.
        
        Returns:
            Data integrity validation result
        """
        if not self.is_active:
            return DataIntegrityResult(
                passed=True, total_records_checked=0, discrepancies_found=0,
                missing_records=[], corrupted_records=[], validation_details={},
                check_duration_seconds=0.0
            )
        
        logger.info("🔍 Validating zero data loss...")
        start_time = time.time()
        
        try:
            # Get current data counts
            current_counts = await self._count_database_records()
            
            # Compare with baseline
            missing_records = []
            discrepancies = 0
            total_checked = 0
            
            if self.baseline_data_counts:
                for table, baseline_count in self.baseline_data_counts.items():
                    current_count = current_counts.get(table, 0)
                    total_checked += baseline_count
                    
                    if current_count < baseline_count:
                        missing_count = baseline_count - current_count
                        missing_records.append(f"{table}: {missing_count} records missing")
                        discrepancies += missing_count
                        logger.error(f"❌ Data loss detected in {table}: {missing_count} records missing")
            
            # Additional integrity checks
            corrupted_records = await self._check_data_corruption()
            
            check_duration = time.time() - start_time
            
            result = DataIntegrityResult(
                passed=(discrepancies == 0 and len(corrupted_records) == 0),
                total_records_checked=total_checked,
                discrepancies_found=discrepancies,
                missing_records=missing_records,
                corrupted_records=corrupted_records,
                validation_details={
                    "baseline_counts": self.baseline_data_counts,
                    "current_counts": current_counts,
                    "tables_checked": list(current_counts.keys())
                },
                check_duration_seconds=check_duration
            )
            
            # Trigger safety mechanism if data loss detected
            if not result.passed:
                await self._trigger_safety_event(
                    TriggerType.ZERO_DATA_LOSS,
                    TriggerSeverity.CRITICAL,
                    f"Data loss detected: {discrepancies} discrepancies, {len(corrupted_records)} corrupted",
                    {
                        "discrepancies": discrepancies,
                        "missing_records": missing_records,
                        "corrupted_records": corrupted_records,
                        "total_checked": total_checked
                    },
                    rollback_required=True
                )
            else:
                logger.info(f"✅ Zero data loss validation passed ({total_checked} records checked)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Data integrity validation failed: {e}")
            
            # Trigger critical safety event on validation failure
            await self._trigger_safety_event(
                TriggerType.DATA_INTEGRITY,
                TriggerSeverity.CRITICAL,
                f"Data integrity validation failed: {str(e)}",
                {"error": str(e), "check_duration": time.time() - start_time},
                rollback_required=True
            )
            
            raise
    
    async def check_performance_regression(self) -> PerformanceComparisonResult:
        """
        Check for performance regression compared to baseline.
        
        Returns:
            Performance comparison result
        """
        if not self.is_active:
            return PerformanceComparisonResult(
                passed=True, baseline_response_time_ms=0.0, current_response_time_ms=0.0,
                regression_percentage=0.0, threshold_percentage=self.performance_regression_threshold,
                affected_operations=[], check_duration_seconds=0.0
            )
        
        logger.info("📈 Checking for performance regression...")
        start_time = time.time()
        
        try:
            # Measure current performance
            current_performance = await self._measure_system_performance()
            
            if not self.baseline_performance:
                logger.warning("No baseline performance data available")
                return PerformanceComparisonResult(
                    passed=True, baseline_response_time_ms=0.0,
                    current_response_time_ms=current_performance.get("avg_response_time_ms", 0.0),
                    regression_percentage=0.0, threshold_percentage=self.performance_regression_threshold,
                    affected_operations=[], check_duration_seconds=time.time() - start_time
                )
            
            # Calculate regression
            baseline_response_time = self.baseline_performance.get("avg_response_time_ms", 0.0)
            current_response_time = current_performance.get("avg_response_time_ms", 0.0)
            
            if baseline_response_time > 0:
                regression_percentage = (current_response_time - baseline_response_time) / baseline_response_time
            else:
                regression_percentage = 0.0
            
            # Check if regression exceeds threshold
            regression_detected = regression_percentage > self.performance_regression_threshold
            
            # Identify affected operations
            affected_operations = []
            if regression_detected:
                for operation, current_time in current_performance.items():
                    if operation.endswith("_ms") and operation in self.baseline_performance:
                        baseline_time = self.baseline_performance[operation]
                        if baseline_time > 0:
                            op_regression = (current_time - baseline_time) / baseline_time
                            if op_regression > self.performance_regression_threshold:
                                affected_operations.append(operation.replace("_ms", ""))
            
            check_duration = time.time() - start_time
            
            result = PerformanceComparisonResult(
                passed=not regression_detected,
                baseline_response_time_ms=baseline_response_time,
                current_response_time_ms=current_response_time,
                regression_percentage=regression_percentage,
                threshold_percentage=self.performance_regression_threshold,
                affected_operations=affected_operations,
                check_duration_seconds=check_duration
            )
            
            # Trigger safety mechanism if significant regression detected
            if regression_detected:
                severity = TriggerSeverity.HIGH if regression_percentage > 0.5 else TriggerSeverity.MEDIUM
                
                await self._trigger_safety_event(
                    TriggerType.PERFORMANCE_REGRESSION,
                    severity,
                    f"Performance regression detected: {regression_percentage:.1%} degradation",
                    {
                        "regression_percentage": regression_percentage,
                        "threshold": self.performance_regression_threshold,
                        "baseline_ms": baseline_response_time,
                        "current_ms": current_response_time,
                        "affected_operations": affected_operations
                    },
                    rollback_required=(severity == TriggerSeverity.HIGH)
                )
            else:
                logger.info(f"✅ Performance check passed (regression: {regression_percentage:.1%})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Performance regression check failed: {e}")
            
            await self._trigger_safety_event(
                TriggerType.PERFORMANCE_REGRESSION,
                TriggerSeverity.HIGH,
                f"Performance check failed: {str(e)}",
                {"error": str(e), "check_duration": time.time() - start_time},
                rollback_required=False
            )
            
            raise
    
    async def execute_emergency_rollback(self, reason: str, context: Dict[str, Any] = None) -> bool:
        """
        Execute emergency rollback procedures.
        
        Args:
            reason: Reason for emergency rollback
            context: Additional context data
            
        Returns:
            True if rollback executed successfully
        """
        logger.critical(f"🚨 EXECUTING EMERGENCY ROLLBACK: {reason}")
        
        try:
            # Create rollback trigger event
            trigger_event = SafetyTriggerEvent(
                trigger_id=f"emergency_rollback_{int(time.time())}",
                trigger_type=TriggerType.MANUAL_TRIGGER,
                severity=TriggerSeverity.CRITICAL,
                timestamp=datetime.now(),
                message=f"Emergency rollback: {reason}",
                context=context or {},
                rollback_required=True,
                auto_rollback_triggered=True
            )
            
            # Add to history
            self.trigger_history.append(trigger_event)
            
            # Enable emergency rollback mode in feature flags
            self.feature_flags.emergency_rollback_mode()
            
            # Execute rollback handlers
            rollback_success = True
            for handler in self.rollback_handlers:
                try:
                    handler(trigger_event)
                except Exception as e:
                    logger.error(f"❌ Rollback handler failed: {e}")
                    rollback_success = False
            
            if rollback_success:
                logger.critical("✅ Emergency rollback completed successfully")
            else:
                logger.critical("❌ Emergency rollback completed with errors")
            
            return rollback_success
            
        except Exception as e:
            logger.critical(f"💥 Emergency rollback failed: {e}")
            return False
    
    async def validate_system_health(self) -> Dict[str, Any]:
        """
        Comprehensive system health validation.
        
        Returns:
            System health report
        """
        logger.info("🏥 Validating system health...")
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_healthy": True,
            "checks": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Database connectivity check
            db_health = await self._check_database_health()
            health_report["checks"]["database"] = db_health
            if not db_health["healthy"]:
                health_report["overall_healthy"] = False
                health_report["issues"].append("Database connectivity issues detected")
            
            # Response time check
            response_check = await self._check_response_times()
            health_report["checks"]["response_times"] = response_check
            if not response_check["healthy"]:
                health_report["overall_healthy"] = False
                health_report["issues"].append("Response time threshold exceeded")
            
            # Memory usage check
            memory_check = await self._check_memory_usage()
            health_report["checks"]["memory"] = memory_check
            if not memory_check["healthy"]:
                health_report["overall_healthy"] = False
                health_report["issues"].append("High memory usage detected")
            
            # Feature flag validation
            flag_check = self._check_feature_flag_consistency()
            health_report["checks"]["feature_flags"] = flag_check
            if not flag_check["healthy"]:
                health_report["overall_healthy"] = False
                health_report["issues"].append("Feature flag configuration issues")
            
            # Generate recommendations
            if health_report["issues"]:
                health_report["recommendations"].extend([
                    "Consider enabling emergency rollback mode",
                    "Monitor system resources closely",
                    "Verify all safety mechanisms are active"
                ])
            
            # Trigger safety event if unhealthy
            if not health_report["overall_healthy"]:
                await self._trigger_safety_event(
                    TriggerType.SYSTEM_HEALTH,
                    TriggerSeverity.HIGH,
                    f"System health issues detected: {len(health_report['issues'])} problems",
                    {"health_report": health_report},
                    rollback_required=False
                )
            
            return health_report
            
        except Exception as e:
            logger.error(f"❌ System health validation failed: {e}")
            health_report["overall_healthy"] = False
            health_report["issues"].append(f"Health check failed: {str(e)}")
            return health_report
    
    async def _trigger_safety_event(self, trigger_type: TriggerType, severity: TriggerSeverity,
                                   message: str, context: Dict[str, Any],
                                   rollback_required: bool = False) -> None:
        """Trigger a safety event and handle rollback if needed."""
        trigger_id = f"{trigger_type.value}_{int(time.time())}"
        
        event = SafetyTriggerEvent(
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            severity=severity,
            timestamp=datetime.now(),
            message=message,
            context=context,
            rollback_required=rollback_required,
            auto_rollback_triggered=False
        )
        
        # Add to active triggers and history
        self.active_triggers[trigger_id] = event
        self.trigger_history.append(event)
        
        logger.warning(f"🚨 Safety trigger: {severity.value.upper()} - {message}")
        
        # Execute automatic rollback if required and enabled
        if (rollback_required and 
            self.feature_flags.is_enabled("MCP_ENABLE_AUTO_ROLLBACK") and
            severity in [TriggerSeverity.HIGH, TriggerSeverity.CRITICAL]):
            
            event.auto_rollback_triggered = True
            
            for handler in self.rollback_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"❌ Rollback handler failed: {e}")
    
    async def _measure_system_performance(self) -> Dict[str, float]:
        """Measure current system performance metrics."""
        try:
            from src.db.connection import execute_query
            
            performance_metrics = {}
            
            # Database response time
            start = time.time()
            execute_query("SELECT 1", fetch=True)
            performance_metrics["db_response_time_ms"] = (time.time() - start) * 1000
            
            # Complex query performance
            start = time.time()
            execute_query("SELECT COUNT(*) FROM mcp_configs", fetch=True)
            performance_metrics["query_response_time_ms"] = (time.time() - start) * 1000
            
            # Average response time
            response_times = [v for k, v in performance_metrics.items() if k.endswith("_ms")]
            performance_metrics["avg_response_time_ms"] = sum(response_times) / len(response_times) if response_times else 0.0
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Performance measurement failed: {e}")
            return {"avg_response_time_ms": float('inf')}
    
    async def _count_database_records(self) -> Dict[str, int]:
        """Count records in key database tables."""
        try:
            from src.db.connection import execute_query
            
            tables_to_check = [
                "mcp_configs",
                "agents", 
                "sessions",
                "messages"
            ]
            
            counts = {}
            for table in tables_to_check:
                try:
                    result = execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                    counts[table] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.warning(f"Could not count {table}: {e}")
                    counts[table] = 0
            
            return counts
            
        except Exception as e:
            logger.error(f"Database record counting failed: {e}")
            return {}
    
    async def _check_data_corruption(self) -> List[str]:
        """Check for data corruption in key tables."""
        corrupted_records = []
        
        try:
            from src.db.connection import execute_query
            
            # Check for NULL values in required fields
            checks = [
                ("mcp_configs", "name IS NULL OR config IS NULL"),
                ("agents", "name IS NULL OR id IS NULL"),
                ("sessions", "id IS NULL")
            ]
            
            for table, condition in checks:
                try:
                    result = execute_query(f"SELECT COUNT(*) as count FROM {table} WHERE {condition}", fetch=True)
                    count = result[0]["count"] if result else 0
                    if count > 0:
                        corrupted_records.append(f"{table}: {count} records with NULL required fields")
                except Exception as e:
                    logger.warning(f"Corruption check failed for {table}: {e}")
            
        except Exception as e:
            logger.error(f"Data corruption check failed: {e}")
        
        return corrupted_records
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            from src.db.connection import execute_query
            
            start_time = time.time()
            execute_query("SELECT 1", fetch=True)
            response_time = (time.time() - start_time) * 1000
            
            return {
                "healthy": response_time < self.response_time_threshold_ms,
                "response_time_ms": response_time,
                "threshold_ms": self.response_time_threshold_ms
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time_ms": float('inf')
            }
    
    async def _check_response_times(self) -> Dict[str, Any]:
        """Check system response times."""
        performance = await self._measure_system_performance()
        avg_response = performance.get("avg_response_time_ms", float('inf'))
        
        return {
            "healthy": avg_response < self.response_time_threshold_ms,
            "avg_response_time_ms": avg_response,
            "threshold_ms": self.response_time_threshold_ms
        }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            return {
                "healthy": memory_percent < 80.0,  # 80% threshold
                "memory_usage_mb": memory_mb,
                "memory_usage_percent": memory_percent,
                "threshold_percent": 80.0
            }
            
        except ImportError:
            return {"healthy": True, "note": "psutil not available"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _check_feature_flag_consistency(self) -> Dict[str, Any]:
        """Check feature flag configuration consistency."""
        flags = self.feature_flags.get_all_flags()
        issues = []
        
        # Check for dangerous combinations
        if flags.get("MCP_USE_NEW_SYSTEM") and not flags.get("MCP_SAFETY_CHECKS"):
            issues.append("New system enabled without safety checks")
        
        if flags.get("MCP_USE_NEW_SYSTEM") and not flags.get("MCP_MONITORING_ENABLED"):
            issues.append("New system enabled without monitoring")
        
        if not flags.get("MCP_ENABLE_AUTO_ROLLBACK") and flags.get("MCP_USE_NEW_SYSTEM"):
            issues.append("Auto-rollback disabled while using new system")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "flags_checked": len(flags)
        }
    
    def get_trigger_summary(self) -> Dict[str, Any]:
        """Get summary of all safety triggers."""
        active_count = len(self.active_triggers)
        total_count = len(self.trigger_history)
        
        # Count by severity
        severity_counts = {severity.value: 0 for severity in TriggerSeverity}
        for trigger in self.trigger_history:
            severity_counts[trigger.severity.value] += 1
        
        # Count by type
        type_counts = {trigger_type.value: 0 for trigger_type in TriggerType}
        for trigger in self.trigger_history:
            type_counts[trigger.trigger_type.value] += 1
        
        return {
            "active_triggers": active_count,
            "total_triggers": total_count,
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts,
            "rollbacks_triggered": len([t for t in self.trigger_history if t.auto_rollback_triggered]),
            "system_active": self.is_active,
            "last_validation": self.last_validation_time.isoformat() if self.last_validation_time else None
        }