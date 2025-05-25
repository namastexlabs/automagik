# API Benchmark Quick Reference Guide

## Prerequisites
```bash
# Activate virtual environment
source .venv/bin/activate

# Ensure API server is running
curl -s http://localhost:8881/health
```

## Common Benchmark Commands

### 🎯 **Full API Benchmark (Recommended Starting Point)**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type full_api \
  --concurrency 50 \
  --requests 1000 \
  --timeout 60 \
  --output full_api_results.json \
  --verbose
```

### 🤖 **Agent-Only Benchmark**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type agent_run \
  --concurrency 25 \
  --requests 500 \
  --output agent_only_results.json
```

### 🔄 **Session Queue Testing**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type session_queue \
  --session-count 10 \
  --messages-per-session 20 \
  --concurrency 50 \
  --output session_queue_results.json
```

### 🎭 **Mock Agent Testing (No API Calls)**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode mock \
  --mock-type test \
  --concurrency 100 \
  --requests 1000 \
  --output mock_results.json
```

## Progressive Load Testing

### **Concurrency Scaling Test**
```bash
#!/bin/bash
for concurrency in 10 25 50 100 200; do
  echo "Testing concurrency: $concurrency"
  python scripts/benchmarks/api_stress_test.py \
    --mode api \
    --base-url http://localhost:8881 \
    --api-key am_xxxxx \
    --test-type full_api \
    --concurrency $concurrency \
    --requests 500 \
    --output "load_test_c${concurrency}.json"
  sleep 30  # Cool down between tests
done
```

### **Volume Scaling Test**
```bash
#!/bin/bash
for requests in 100 500 1000 2000 5000; do
  echo "Testing volume: $requests requests"
  python scripts/benchmarks/api_stress_test.py \
    --mode api \
    --base-url http://localhost:8881 \
    --api-key am_xxxxx \
    --test-type agent_run \
    --concurrency 25 \
    --requests $requests \
    --output "volume_test_r${requests}.json"
  sleep 60  # Longer cool down for larger tests
done
```

## Performance Baseline Testing

### **Optimal Performance Test (Low Load)**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type agent_run \
  --concurrency 5 \
  --requests 100 \
  --output baseline_low_load.json
```

### **Breaking Point Test (High Load)**
```bash
python scripts/benchmarks/api_stress_test.py \
  --mode api \
  --base-url http://localhost:8881 \
  --api-key am_xxxxx \
  --test-type full_api \
  --concurrency 200 \
  --requests 5000 \
  --timeout 120 \
  --output breaking_point_test.json
```

## Interpreting Results

### **Good Performance Indicators**
```yaml
Throughput: >50 req/sec
Error Rate: <5%
Mean Latency: <1000ms
95th Percentile: <3000ms
Memory Growth: <20MB
```

### **Warning Signs**
```yaml
Throughput: 20-50 req/sec
Error Rate: 5-20%
Mean Latency: 1000-3000ms
95th Percentile: 3000-10000ms
Memory Growth: 20-50MB
```

### **Critical Issues**
```yaml
Throughput: <20 req/sec
Error Rate: >20%
Mean Latency: >3000ms
95th Percentile: >10000ms
Memory Growth: >50MB
```

## Common Error Patterns

### **Memory Creation Failures**
```
Error: "Error creating memory: 500: Failed to create memory"
Cause: Database constraint violations, foreign key issues
Solution: Check database logs, validate user_id format
```

### **Agent Run Timeouts**
```
Error: "HTTP 500: Internal Server Error"
Cause: Graphiti operations blocking responses
Solution: Disable Graphiti during load testing
```

### **Connection Pool Exhaustion**
```
Error: Connection timeouts, pool exhaustion
Cause: Too many concurrent requests for pool size
Solution: Increase POSTGRES_POOL_MAX setting
```

## Environment Optimizations

### **For Load Testing**
```bash
# Disable expensive operations
export GRAPHITI_ENABLED=false
export AM_LOG_LEVEL=WARNING

# Increase connection limits
export POSTGRES_POOL_MAX=50
export POSTGRES_POOL_MIN=5
```

### **For Development**
```bash
# Enable detailed logging
export AM_LOG_LEVEL=DEBUG
export AM_VERBOSE_LOGGING=true

# Enable all features
export GRAPHITI_ENABLED=true
```

## Monitoring During Tests

### **Watch Server Logs**
```bash
tail -f server.log | grep -E "(ERROR|WARN|episode|memory)"
```

### **Monitor System Resources**
```bash
# CPU and Memory
top -p $(pgrep -f uvicorn)

# Database Connections
ps aux | grep postgres | wc -l

# Open Files
lsof -p $(pgrep -f uvicorn) | wc -l
```

### **Database Monitoring**
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Long running queries  
SELECT pid, query, state, query_start 
FROM pg_stat_activity 
WHERE state = 'active' 
AND query_start < now() - interval '30 seconds';
```

## Results Analysis

### **Key Metrics to Track**
1. **Throughput Trend**: Should remain stable or increase with optimizations
2. **Error Rate Pattern**: Should decrease over time  
3. **Latency Distribution**: P95 should be predictable
4. **Resource Usage**: Memory/CPU should be bounded

### **Comparison Baseline**
Current Performance (May 22, 2025):
```
Throughput: 22.36 req/sec
Error Rate: 64.90%
Mean Latency: 1,952ms
P95 Latency: 5,829ms
```

### **Target Performance Goals**
```
Throughput: 200+ req/sec (9x improvement)
Error Rate: <5% (13x improvement)  
Mean Latency: <500ms (4x improvement)
P95 Latency: <2,000ms (3x improvement)
```

## Quick Troubleshooting

### **High Error Rates**
1. Check server logs for specific errors
2. Verify API key is correct
3. Ensure all required services are running
4. Test with lower concurrency first

### **High Latency**  
1. Check if Graphiti is enabled (major bottleneck)
2. Monitor database connection pool usage
3. Look for memory leaks or resource exhaustion
4. Test individual endpoints in isolation

### **Low Throughput**
1. Increase concurrency gradually
2. Check system resource limits
3. Verify network connectivity
4. Profile server-side bottlenecks

---

*For detailed analysis of current performance issues, see [FULL_API_BENCHMARK_SUMMARY.md](FULL_API_BENCHMARK_SUMMARY.md)* 