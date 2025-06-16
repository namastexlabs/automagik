# Timezone Fix Plan - UTC-3 Consistency for Workflow Management

## 🎯 Problem Identified

**3-hour gap between execution and database timestamps** due to timezone inconsistencies:
- **Configuration**: `AM_TIMEZONE=UTC` (default in config.py)
- **System Runtime**: `America/Sao_Paulo` (UTC-3)
- **Workflow Code**: Uses `datetime.utcnow()` (ignores AM_TIMEZONE setting)
- **Database**: Stores UTC timestamps while system expects UTC-3

## 🔍 Root Cause Analysis

### Mixed Timezone Approaches Found:
1. **Config Default**: `AM_TIMEZONE="UTC"` in `src/config.py:169-172`
2. **Hardcoded UTC**: `datetime.utcnow()` in workflow monitoring code
3. **Hardcoded UTC-3**: Some APIs force `America/Sao_Paulo`
4. **Database**: Uses `CURRENT_TIMESTAMP` without timezone specification

### Critical Code Locations:
- `src/mcp/workflow_monitor.py` - Uses `datetime.utcnow()` (lines 291, 436, 487)
- `src/agents/claude_code/cli_executor.py` - Uses `datetime.utcnow()` (lines 141, 1083)  
- `src/db/repository/workflow_process.py` - Uses `datetime.utcnow()` (lines 25, 191, 239, 292)
- `src/db/models.py` - Uses `datetime.utcnow()` in workflow models

## 🔧 Comprehensive Fix Strategy

### Phase 1: Environment Configuration (IMMEDIATE)
```bash
# Set environment variable for UTC-3
export AM_TIMEZONE="America/Sao_Paulo"

# Or add to .env file:
echo "AM_TIMEZONE=America/Sao_Paulo" >> .env
```

### Phase 2: Code Standardization (PRIORITY 1)

#### Create Timezone Utility Function
```python
# src/utils/timezone.py (NEW FILE)
from datetime import datetime
import pytz
from src.config import settings

def get_current_time() -> datetime:
    """Get current time in configured timezone."""
    tz = pytz.timezone(settings.AM_TIMEZONE)
    return datetime.now(tz)

def get_utc_time() -> datetime:
    """Get current time in UTC."""
    return datetime.utcnow()

def convert_to_local(utc_time: datetime) -> datetime:
    """Convert UTC time to local timezone."""
    tz = pytz.timezone(settings.AM_TIMEZONE)
    return utc_time.replace(tzinfo=pytz.UTC).astimezone(tz)
```

#### Fix Workflow Monitor (CRITICAL)
Replace all `datetime.utcnow()` calls in:
- `src/mcp/workflow_monitor.py`
- `src/agents/claude_code/cli_executor.py`
- `src/db/repository/workflow_process.py`

### Phase 3: Database Consistency (PRIORITY 2)

#### Update Migration for Timezone Awareness
```sql
-- Consider updating workflow_processes table
ALTER TABLE workflow_processes 
  ALTER COLUMN started_at TYPE TIMESTAMPTZ,
  ALTER COLUMN last_heartbeat TYPE TIMESTAMPTZ,
  ALTER COLUMN created_at TYPE TIMESTAMPTZ,
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ;
```

### Phase 4: API Standardization (PRIORITY 3)
Remove hardcoded `America/Sao_Paulo` from:
- `src/tools/blackpearl/interface.py:121`
- `src/tools/flashed/interface.py:29`

## 🚀 Implementation Steps

### Step 1: Quick Environment Fix (Test First)
```bash
# Test with environment variable
export AM_TIMEZONE="America/Sao_Paulo"
uv run python -c "
from src.config import settings
print(f'AM_TIMEZONE: {settings.AM_TIMEZONE}')
"
```

### Step 2: Create Timezone Utility
```python
# Add timezone utility to standardize datetime usage
# This ensures all workflow code uses consistent timezone
```

### Step 3: Fix Workflow Monitoring Code
```python
# Replace datetime.utcnow() with timezone-aware calls
# Update workflow_monitor.py, cli_executor.py, workflow_process.py
```

### Step 4: Test Workflow Timeout Detection
```bash
# Test timeout detection with correct timezone
# Verify 3-hour gap is eliminated
```

## 🧪 Testing Plan

### Test 1: Environment Configuration
```bash
export AM_TIMEZONE="America/Sao_Paulo"
# Verify configuration loads correctly
```

### Test 2: Database Timestamp Consistency
```python
# Create workflow process record
# Verify timestamps match local time (UTC-3)
```

### Test 3: Timeout Detection Accuracy
```python
# Test workflow timeout detection
# Verify no false positives from timezone mismatch
```

## 🎯 Expected Results

### Before Fix:
- Database: UTC timestamps
- System: UTC-3 runtime
- Gap: 3-hour difference causing timeout issues

### After Fix:
- Database: UTC-3 timestamps (or timezone-aware)
- System: UTC-3 runtime  
- Result: Consistent timing, accurate timeout detection

## 📋 Implementation Priority

### IMMEDIATE (Testing Phase):
1. Set `AM_TIMEZONE=America/Sao_Paulo` environment variable
2. Test workflow creation and timeout detection
3. Verify 3-hour gap elimination

### SHORT-TERM (Code Fix):
1. Create timezone utility module
2. Fix workflow monitoring datetime usage
3. Update database operations

### LONG-TERM (System Hardening):
1. Database timezone awareness
2. API standardization
3. Comprehensive timezone testing

This fix ensures the entire repository works consistently in UTC-3, eliminating the 3-hour timestamp discrepancy that could cause false timeout triggers and monitoring issues.