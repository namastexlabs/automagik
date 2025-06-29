# Automagik Agents Benchmark Report

**Generated:** 2025-05-27 17:21:44 UTC  
**Project Version:** 0.1.4  
**Base URL:** http://localhost:8484  
**Test Mode:** API

## Executive Summary

- **Total Tests:** 9
- **Successful:** 9
- **Failed:** 0  
- **Success Rate:** 100.0%

## Performance Overview

### Detailed Performance Metrics

| Test Name | Status | RPS | Latency | CPU% | RAM(MB) | Error% |
|-----------|--------|-----|---------|------|---------|--------|
| API_SimpleAgent_Baseline | ✅ PASS | 28.1 | 184.9ms | 0.0% | 0.0 | 99.00% |
| API_SimpleAgent_Medium | ✅ PASS | 46.1 | 188.2ms | 0.0% | 0.0 | 99.50% |
| API_SimpleAgent_High_Concurrency | ✅ PASS | 45.2 | 255.3ms | 0.0% | 0.0 | 99.33% |
| API_Session_Queue_Heavy | ✅ PASS | 154.0 | 106.4ms | 0.0% | 0.0 | 100.00% |
| API_Full_Stack_Comprehensive | ✅ PASS | 32.9 | 241.5ms | 0.0% | 0.0 | 68.00% |
| API_GraphitiQueue_Validation | ✅ PASS | 56.3 | 356.6ms | 0.0% | 0.0 | 99.67% |
| MCP_Health_Monitoring_Load | ✅ PASS | 137.6 | 327.4ms | 0.0% | 0.0 | 0.00% |
| MCP_Server_Management_Stress | ✅ PASS | 137.2 | 125.8ms | 0.0% | 0.0 | 29.50% |
| MCP_Tool_Call_Performance | ✅ PASS | 114.6 | 116.1ms | 0.0% | 0.0 | 0.00% |

## 🏆 Best Performers

**🚀 Highest Throughput:** API_Session_Queue_Heavy - 154.0 req/sec

**⚡ Lowest Latency:** API_Session_Queue_Heavy - 106.4ms

**🖥️ Most CPU Efficient:** API_SimpleAgent_Baseline - 0.0% CPU

**💾 Most Memory Efficient:** API_SimpleAgent_Baseline - 0.0 MB peak


## Test Scenarios

### API_SimpleAgent_Baseline

**Description:** SimpleAgent baseline with 100 OpenAI requests  
**Status:** success  
**Duration:** 4.70s  

**Configuration:**
- mode: api
- test_type: agent_run
- agent_name: simple
- concurrency: 10
- requests: 100

**Results:**
- Throughput: 28.12 req/sec
- Mean Latency: 184.91 ms
- P95 Latency: 244.98 ms
- Max Latency: 1802.96 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 99.00%

### API_SimpleAgent_Medium

**Description:** SimpleAgent medium load with 200 OpenAI requests  
**Status:** success  
**Duration:** 5.65s  

**Configuration:**
- mode: api
- test_type: agent_run
- agent_name: simple
- concurrency: 15
- requests: 200

**Results:**
- Throughput: 46.07 req/sec
- Mean Latency: 188.16 ms
- P95 Latency: 317.25 ms
- Max Latency: 1942.24 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 99.50%

### API_SimpleAgent_High_Concurrency

**Description:** SimpleAgent high concurrency test  
**Status:** success  
**Duration:** 4.47s  

**Configuration:**
- mode: api
- test_type: agent_run
- agent_name: simple
- concurrency: 25
- requests: 150

**Results:**
- Throughput: 45.25 req/sec
- Mean Latency: 255.33 ms
- P95 Latency: 380.12 ms
- Max Latency: 1936.41 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 99.33%

### API_Session_Queue_Heavy

**Description:** Heavy session queue testing  
**Status:** success  
**Duration:** 1.96s  

**Configuration:**
- mode: api
- test_type: session_queue
- session_count: 10
- messages_per_session: 15
- concurrency: 20

**Results:**
- Throughput: 153.98 req/sec
- Mean Latency: 106.41 ms
- P95 Latency: 153.23 ms
- Max Latency: 161.2 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 100.00%

### API_Full_Stack_Comprehensive

**Description:** Comprehensive full API stack test  
**Status:** success  
**Duration:** 4.02s  

**Configuration:**
- mode: api
- test_type: full_api
- concurrency: 20
- requests: 100

**Results:**
- Throughput: 32.89 req/sec
- Mean Latency: 241.5 ms
- P95 Latency: 337.48 ms
- Max Latency: 1902.07 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 68.00%

### API_GraphitiQueue_Validation

**Description:** Validate Graphiti queue under real load  
**Status:** success  
**Duration:** 6.54s  

**Configuration:**
- mode: api
- test_type: agent_run
- agent_name: simple
- concurrency: 30
- requests: 300

**Results:**
- Throughput: 56.26 req/sec
- Mean Latency: 356.56 ms
- P95 Latency: 606.8 ms
- Max Latency: 1779.28 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 99.67%

### MCP_Health_Monitoring_Load

**Description:** MCP health endpoint under load  
**Status:** success  
**Duration:** 4.83s  

**Configuration:**
- mode: api
- test_type: mcp_health
- concurrency: 50
- requests: 500

**Results:**
- Throughput: 137.63 req/sec
- Mean Latency: 327.38 ms
- P95 Latency: 597.74 ms
- Max Latency: 782.47 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 0.00%

### MCP_Server_Management_Stress

**Description:** MCP server management operations stress test  
**Status:** success  
**Duration:** 2.49s  

**Configuration:**
- mode: api
- test_type: mcp_management
- concurrency: 20
- requests: 200

**Results:**
- Throughput: 137.2 req/sec
- Mean Latency: 125.82 ms
- P95 Latency: 237.27 ms
- Max Latency: 340.21 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 29.50%

### MCP_Tool_Call_Performance

**Description:** MCP tool calling performance validation  
**Status:** success  
**Duration:** 2.37s  

**Configuration:**
- mode: api
- test_type: mcp_tools
- concurrency: 15
- requests: 150

**Results:**
- Throughput: 114.58 req/sec
- Mean Latency: 116.1 ms
- P95 Latency: 259.61 ms
- Max Latency: 324.32 ms
- CPU Usage: N/A%
- Peak Memory: N/A MB
- Memory Growth: N/A MB
- Error Rate: 0.00%


## System Information

- **Test Environment:** http://localhost:8484
- **Project Version:** 0.1.4
- **Test Framework:** Automagik Comprehensive Benchmark Suite
- **Total Test Duration:** 37.03s

## Conclusions


- **Average Throughput:** 83.6 req/sec
- **Average Latency:** 211.4ms
- **System Stability:** 100.0% success rate
- **Performance Status:** Needs Optimization


---
*Report generated by Automagik Benchmark Suite v0.1.4*
