# Task: Fix API Concurrent 500 Errors

**Created:** Thu May 22 22:52:37 UTC 2025  
**Priority:** HIGH  
**Status:** IN PROGRESS  
**Estimated Time:** 4-6 hours  

## Problem Summary

The Automagik API is experiencing significant 500 errors under concurrent load, with approximately **80% failure rate** when processing 5 concurrent requests. Single requests work perfectly (~1.1s response time), but concurrent requests fail at the FastAPI/Uvicorn level **before reaching application code**.

## Current Status

### ✅ **FIXED Issues (Phase 1 Complete)**
1. **Foreign Key Constraint Violations**: Fixed `MessageHistory` to use `no_auto_create=True` for temporary sessions
2. **Graphiti Queue Freezing**: Fixed health endpoint and queue initialization when disabled
3. **Database Session Creation**: Fixed agent controller to create in-memory sessions for better performance
4. **Basic Logging**: Added file logging capability for debugging (`AM_LOG_TO_FILE=true`)

### 🔄 **CURRENT Problem (Phase 2 Required)**
- **80% of concurrent requests return HTTP 500** at FastAPI level
- **Errors don't appear in application logs** - happening before our code executes
- **Only 1 out of 5 concurrent requests succeeds consistently**
- **Perfect success rate with sequential requests**

## Root Cause Analysis

The 500 errors occur **before** reaching application code, indicating issues at:

1. **FastAPI/Uvicorn Request Processing Level**
   - Internal request handling limits
   - Request parsing/validation failures
   - Middleware errors (auth, CORS, etc.)

2. **Resource Exhaustion**
   - Database connection pool limits (despite increases)
   - Thread pool saturation
   - Memory allocation issues

3. **Synchronization Issues**
   - Race conditions in request initialization
   - Lock contention in agent factory or database layer
   - Shared resource conflicts

## Detailed Fix Instructions

### Phase 2A: Capture FastAPI-Level Errors (1-2 hours)

**WHY:** We need to see the actual 500 error details since they're not reaching our application logs.

#### Step 1: Add FastAPI Error Middleware
```python
# Add to src/main.py before other middleware

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def catch_all_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"❌ Unhandled exception in request {request.url}: {str(exc)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(exc)}"}
        )
```

#### Step 2: Enable FastAPI Debug Mode
```python
# In src/main.py, modify app creation:
app = FastAPI(
    title="Automagik Agents API",
    debug=True,  # Add this
    # ... rest of config
)
```

#### Step 3: Add Uvicorn Request Logging
```bash
# In .env add:
AM_LOG_LEVEL=DEBUG
AM_VERBOSE_LOGGING=true
```

### Phase 2B: Fix Resource Limits (2-3 hours)

**WHY:** Even with increased DB pool, we may be hitting other resource limits.

#### Step 4: Increase All Resource Limits
```bash
# Add to .env:
POSTGRES_POOL_MIN=15
POSTGRES_POOL_MAX=50
LLM_MAX_CONCURRENT_REQUESTS=20
LLM_RETRY_ATTEMPTS=3

# FastAPI/Uvicorn limits:
UVICORN_LIMIT_CONCURRENCY=100
UVICORN_LIMIT_MAX_REQUESTS=1000
```

#### Step 5: Add Request-Level Semaphore
```python
# Add to src/main.py before routes:

import asyncio
_request_semaphore = asyncio.BoundedSemaphore(10)

@app.middleware("http")
async def limit_concurrent_requests(request: Request, call_next):
    async with _request_semaphore:
        response = await call_next(request)
        return response
```

#### Step 6: Fix Database Connection Management
```python
# Modify src/db/connection.py to ensure proper cleanup:

@asynccontextmanager
async def get_db_connection():
    """Context manager for database connections with guaranteed cleanup."""
    conn = None
    try:
        conn = await get_connection()
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            await conn.close()
```

### Phase 2C: Fix Agent Factory Race Conditions (1-2 hours)

**WHY:** Multiple concurrent requests may be racing to initialize the same agent instance.

#### Step 7: Add Agent Instance Caching with Locks
```python
# Modify src/agents/models/agent_factory.py:

import asyncio
from typing import Dict

class AgentFactory:
    def __init__(self):
        # ... existing code ...
        self._agent_locks: Dict[str, asyncio.Lock] = {}
        self._lock_creation_lock = asyncio.Lock()
    
    async def _get_agent_lock(self, agent_name: str) -> asyncio.Lock:
        """Get or create a lock for the specific agent."""
        async with self._lock_creation_lock:
            if agent_name not in self._agent_locks:
                self._agent_locks[agent_name] = asyncio.Lock()
            return self._agent_locks[agent_name]
    
    async def get_agent(self, agent_type: str):
        """Thread-safe agent retrieval with locking."""
        agent_lock = await self._get_agent_lock(agent_type)
        async with agent_lock:
            # Existing agent creation logic here
            return self._get_or_create_agent(agent_type)
```

### Phase 2D: Add Request Timeouts (30 minutes)

**WHY:** Long-running requests may be blocking others.

#### Step 8: Add Request Timeouts
```python
# Add to src/main.py:

from fastapi import BackgroundTasks
import asyncio

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"Request timeout: {request.url}")
        return JSONResponse(
            status_code=408,
            content={"detail": "Request timeout"}
        )
```

## Testing Instructions

### Phase 2E: Validation Testing (1 hour)

#### Test 1: Baseline Concurrent Test
```bash
# Should improve from 20% to 80%+ success rate
python scripts/benchmarks/api_stress_test.py --base-url http://localhost:8881 --test-type agent_run --concurrency 5 --requests 15 --api-key am_xxxxx
```

#### Test 2: High Concurrency Test
```bash
# Should handle higher loads
python scripts/benchmarks/api_stress_test.py --base-url http://localhost:8881 --test-type agent_run --concurrency 10 --requests 25 --api-key am_xxxxx
```

#### Test 3: Error Log Verification
```bash
# Check that errors are now captured
tail -f api_debug.log | grep -i "error\|exception"
```

## Success Criteria

1. **Concurrent Success Rate**: ≥85% success with 5 concurrent requests
2. **High Load Handling**: ≥70% success with 10 concurrent requests  
3. **Error Visibility**: All 500 errors captured in logs with details
4. **Response Time**: Average response time <3s under load
5. **Stability**: No crashes or freezes under sustained load

## Why This Matters

1. **Production Readiness**: APIs must handle concurrent load in real-world usage
2. **User Experience**: Failed requests mean failed user interactions
3. **System Reliability**: Concurrent failures indicate fundamental stability issues
4. **Scalability**: Current issues prevent horizontal scaling
5. **Debugging**: Invisible errors make production issues impossible to diagnose

## Dependencies

- Database pool configuration changes require API restart
- FastAPI middleware changes require code reload
- Testing requires the stress test script (`scripts/benchmarks/api_stress_test.py`)
- Agent factory changes may affect existing agent instances

## Notes

- **Current improvement**: 15% → 20% success rate (Phase 1)
- **Target improvement**: 20% → 85% success rate (Phase 2)
- **Critical insight**: Errors occur before application code, indicating infrastructure-level issues
- **Key principle**: Fix visibility first (error capture), then fix root causes

## Follow-up Tasks

- [ ] Performance optimization for memory usage under load
- [ ] Add circuit breaker pattern for LLM calls
- [ ] Implement request queuing for overflow scenarios
- [ ] Add comprehensive load testing to CI/CD pipeline 