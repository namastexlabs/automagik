"""api_stress_test.py
Comprehensive API stress testing tool for the Automagik Agents API.

This tool extends the basic agent_run_bench.py with:
- Multi-endpoint testing (agents, users, sessions, memories)
- Session queue stress testing with rapid messages to same session
- Authentication testing
- Memory and performance monitoring
- Realistic payload generation
- Error tracking and analysis

Example usage:

    # Basic agent endpoint stress test
    python scripts/benchmarks/api_stress_test.py \
        --base-url http://localhost:8000 \
        --api-key your-api-key \
        --test-type agent_run \
        --concurrency 100 \
        --requests 500

    # Session queue merging test
    python scripts/benchmarks/api_stress_test.py \
        --base-url http://localhost:8000 \
        --api-key your-api-key \
        --test-type session_queue \
        --session-count 10 \
        --messages-per-session 20 \
        --concurrency 50

    # Full API stress test
    python scripts/benchmarks/api_stress_test.py \
        --base-url http://localhost:8000 \
        --api-key your-api-key \
        --test-type full_api \
        --concurrency 200 \
        --requests 1000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import statistics
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import sys
import traceback

import httpx

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor system performance during stress tests."""
    
    def __init__(self):
        self.start_time = None
        self.process = psutil.Process() if HAS_PSUTIL else None
        self.initial_memory = None
        self.peak_memory = 0
        self.samples = []
        self.enabled = HAS_PSUTIL
        
    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        if self.enabled and self.process:
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.initial_memory
        
    def sample(self):
        """Take a performance sample."""
        if not self.enabled or self.start_time is None or not self.process:
            return
            
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)
        
        sample = {
            'timestamp': time.time() - self.start_time,
            'memory_mb': current_memory,
            'cpu_percent': self.process.cpu_percent(),
            'open_files': len(self.process.open_files()),
            'connections': len(self.process.connections()),
        }
        self.samples.append(sample)
        
    def get_summary(self):
        """Get performance summary."""
        if not self.enabled or not self.samples:
            return {}
            
        return {
            'duration_seconds': time.time() - self.start_time if self.start_time else 0,
            'initial_memory_mb': self.initial_memory,
            'peak_memory_mb': self.peak_memory,
            'memory_growth_mb': self.peak_memory - self.initial_memory if self.initial_memory else 0,
            'avg_cpu_percent': sum(s['cpu_percent'] for s in self.samples) / len(self.samples),
            'max_open_files': max(s['open_files'] for s in self.samples),
            'max_connections': max(s['connections'] for s in self.samples),
        }


class PayloadGenerator:
    """Generate realistic payloads for different API endpoints."""
    
    @staticmethod
    def agent_run_payload(agent_name: str = "simple_agent", session_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate agent run payload."""
        messages = [
            "Hello, how are you today?",
            "What products do you have available?",
            "Can you help me find something specific?",
            "I'm looking for gaming accessories",
            "What's your return policy?",
            "Do you have any discounts available?",
            "Can you tell me about your company?",
            "I need technical support",
            "What are your business hours?",
            "How can I track my order?"
        ]
        
        payload = {
            "input_text": random.choice(messages),
            "message_type": "text",
            "preserve_system_prompt": False,
        }
        
        if session_id:
            payload["session_name"] = session_id
            payload["session_origin"] = "stress_test"
        
        # Add some variety to payloads
        if random.random() < 0.3:  # 30% chance
            payload["message_limit"] = random.randint(5, 20)
            
        if random.random() < 0.2:  # 20% chance
            payload["user_id"] = str(random.randint(1, 100))
            
        return payload
    
    @staticmethod
    def user_create_payload() -> Dict[str, Any]:
        """Generate user creation payload."""
        return {
            "email": f"stress_test_{uuid.uuid4().hex[:8]}@example.com",
            "phone_number": f"+1555{random.randint(1000000, 9999999)}",
            "user_data": {
                "source": "stress_test",
                "test_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def memory_create_payload(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate memory creation payload."""
        return {
            "name": f"stress_test_memory_{uuid.uuid4().hex[:8]}",
            "description": "Memory created during stress testing",
            "content": f"This is test content for stress testing: {random.random()}",
            "user_id": user_id or str(uuid.uuid4()),
            "agent_id": random.randint(1, 5),
            "read_mode": random.choice(["auto", "manual"]),
            "access": random.choice(["private", "shared"]),
            "metadata": {
                "test": True,
                "stress_test_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat()
            }
        }


class APIStressTester:
    """Main stress testing class."""
    
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.performance_monitor = PerformanceMonitor()
        self.results = {
            'successful_requests': 0,
            'failed_requests': 0,
            'errors': [],
            'latencies': [],
            'start_time': None,
            'end_time': None,
        }
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with API key."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
    
    async def _make_request(self, client: httpx.AsyncClient, method: str, endpoint: str, 
                           payload: Optional[Dict] = None) -> Tuple[bool, float, Optional[str]]:
        """Make a single API request and track performance."""
        start_time = time.perf_counter()
        error_msg = None
        success = False
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url, json=payload)
            elif method.upper() == "PUT":
                response = await client.put(url, json=payload)
            elif method.upper() == "DELETE":
                response = await client.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status_code in [200, 201, 202]:
                success = True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            error_msg = f"Request error: {str(e)}"
            
        latency = time.perf_counter() - start_time
        return success, latency, error_msg
    
    async def _worker(self, semaphore: asyncio.Semaphore, client: httpx.AsyncClient,
                     method: str, endpoint: str, payload_generator,
                     worker_id: int = 0) -> None:
        """Worker coroutine for making requests."""
        async with semaphore:
            # Generate payload if needed
            payload = payload_generator() if callable(payload_generator) else payload_generator
            
            success, latency, error_msg = await self._make_request(client, method, endpoint, payload)
            
            # Update results
            if success:
                self.results['successful_requests'] += 1
            else:
                self.results['failed_requests'] += 1
                if error_msg:
                    self.results['errors'].append(error_msg)
                    
            self.results['latencies'].append(latency)
            
            # Sample performance periodically
            if worker_id % 10 == 0:  # Every 10th worker
                self.performance_monitor.sample()
    
    async def test_agent_run(self, agent_name: str, concurrency: int, requests: int) -> Dict[str, Any]:
        """Test agent run endpoint."""
        logger.info(f"Testing agent/{agent_name}/run with {requests} requests, concurrency {concurrency}")
        
        endpoint = f"/api/v1/agent/{agent_name}/run"
        semaphore = asyncio.Semaphore(concurrency)
        
        self.performance_monitor.start()
        self.results['start_time'] = time.time()
        
        async with httpx.AsyncClient(headers=self._get_headers(), timeout=self.timeout) as client:
            tasks = [
                asyncio.create_task(
                    self._worker(
                        semaphore, client, "POST", endpoint,
                        lambda: PayloadGenerator.agent_run_payload(agent_name),
                        i
                    )
                )
                for i in range(requests)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self.results['end_time'] = time.time()
        return self._generate_report("Agent Run Test")
    
    async def test_session_queue_merging(self, session_count: int, messages_per_session: int,
                                       concurrency: int, agent_name: str = "simple_agent") -> Dict[str, Any]:
        """Test session queue merging behavior under load."""
        logger.info(f"Testing session queue with {session_count} sessions, "
                   f"{messages_per_session} messages each, concurrency {concurrency}")
        
        endpoint = f"/api/v1/agent/{agent_name}/run"
        semaphore = asyncio.Semaphore(concurrency)
        
        # Generate session IDs
        session_ids = [f"stress_session_{i}" for i in range(session_count)]
        
        self.performance_monitor.start()
        self.results['start_time'] = time.time()
        
        async with httpx.AsyncClient(headers=self._get_headers(), timeout=self.timeout) as client:
            tasks = []
            
            # Create tasks for each session
            for session_id in session_ids:
                for msg_num in range(messages_per_session):
                    task = asyncio.create_task(
                        self._worker(
                            semaphore, client, "POST", endpoint,
                            lambda sid=session_id: PayloadGenerator.agent_run_payload(agent_name, sid),
                            len(tasks)
                        )
                    )
                    tasks.append(task)
                    
                    # Small delay between messages to same session to test merging
                    if msg_num < messages_per_session - 1:
                        await asyncio.sleep(0.001)  # 1ms delay
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self.results['end_time'] = time.time()
        return self._generate_report("Session Queue Merging Test")
    
    async def test_full_api(self, concurrency: int, requests: int) -> Dict[str, Any]:
        """Test multiple API endpoints."""
        logger.info(f"Testing full API with {requests} total requests, concurrency {concurrency}")
        
        # Define endpoint test scenarios
        scenarios = [
            ("GET", "/api/v1/agent/list", lambda: None, 0.1),  # 10% of requests
            ("POST", "/api/v1/agent/simple_agent/run", 
             lambda: PayloadGenerator.agent_run_payload(), 0.6),  # 60% of requests
            ("GET", "/api/v1/sessions", lambda: None, 0.1),  # 10% of requests
            ("POST", "/api/v1/users", lambda: PayloadGenerator.user_create_payload(), 0.1),  # 10% of requests
            ("POST", "/api/v1/memories", lambda: PayloadGenerator.memory_create_payload(), 0.1),  # 10% of requests
        ]
        
        semaphore = asyncio.Semaphore(concurrency)
        
        self.performance_monitor.start()
        self.results['start_time'] = time.time()
        
        async with httpx.AsyncClient(headers=self._get_headers(), timeout=self.timeout) as client:
            tasks = []
            
            for i in range(requests):
                # Choose scenario based on weights
                rand = random.random()
                cumulative = 0
                chosen_scenario = scenarios[0]  # default
                
                for scenario in scenarios:
                    cumulative += scenario[3]
                    if rand <= cumulative:
                        chosen_scenario = scenario
                        break
                
                method, endpoint, payload_gen, _ = chosen_scenario
                task = asyncio.create_task(
                    self._worker(semaphore, client, method, endpoint, payload_gen, i)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self.results['end_time'] = time.time()
        return self._generate_report("Full API Stress Test")
    
    def _generate_report(self, test_name: str) -> Dict[str, Any]:
        """Generate detailed test report."""
        if not self.results['latencies']:
            return {"error": "No successful requests captured"}
        
        latencies = self.results['latencies']
        duration = self.results['end_time'] - self.results['start_time']
        
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Calculate throughput
        total_requests = self.results['successful_requests'] + self.results['failed_requests']
        rps = total_requests / duration if duration > 0 else 0
        
        # Error analysis
        error_rate = self.results['failed_requests'] / total_requests if total_requests > 0 else 0
        
        # Performance summary
        perf_summary = self.performance_monitor.get_summary()
        
        report = {
            "test_name": test_name,
            "summary": {
                "total_requests": total_requests,
                "successful_requests": self.results['successful_requests'],
                "failed_requests": self.results['failed_requests'],
                "error_rate": f"{error_rate:.2%}",
                "duration_seconds": f"{duration:.2f}",
                "requests_per_second": f"{rps:.2f}",
            },
            "latency_stats": {
                "mean_ms": f"{mean_latency * 1000:.2f}",
                "median_ms": f"{median_latency * 1000:.2f}",
                "p95_ms": f"{p95_latency * 1000:.2f}",
                "max_ms": f"{max_latency * 1000:.2f}",
                "min_ms": f"{min_latency * 1000:.2f}",
            },
            "performance": perf_summary,
            "errors": self.results['errors'][:10] if self.results['errors'] else [],  # First 10 errors
        }
        
        return report


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Comprehensive API stress testing tool")
    
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="FastAPI server base URL")
    parser.add_argument("--api-key", required=True,
                       help="API key for authentication")
    parser.add_argument("--test-type", choices=["agent_run", "session_queue", "full_api"], 
                       default="agent_run", help="Type of test to run")
    parser.add_argument("--agent-name", default="simple_agent", 
                       help="Agent name for agent tests")
    parser.add_argument("--concurrency", type=int, default=100, 
                       help="Number of concurrent requests")
    parser.add_argument("--requests", type=int, default=500, 
                       help="Total number of requests")
    parser.add_argument("--session-count", type=int, default=10,
                       help="Number of sessions for session queue test")
    parser.add_argument("--messages-per-session", type=int, default=20,
                       help="Messages per session for session queue test")
    parser.add_argument("--timeout", type=float, default=30.0, 
                       help="Request timeout in seconds")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create stress tester
    tester = APIStressTester(args.base_url, args.api_key, args.timeout)
    
    try:
        # Run appropriate test
        if args.test_type == "agent_run":
            results = await tester.test_agent_run(args.agent_name, args.concurrency, args.requests)
        elif args.test_type == "session_queue":
            results = await tester.test_session_queue_merging(
                args.session_count, args.messages_per_session, args.concurrency, args.agent_name
            )
        elif args.test_type == "full_api":
            results = await tester.test_full_api(args.concurrency, args.requests)
        else:
            raise ValueError(f"Unknown test type: {args.test_type}")
        
        # Print results
        print("\n" + "="*80)
        print(f"STRESS TEST RESULTS: {results['test_name']}")
        print("="*80)
        
        # Summary
        summary = results['summary']
        print(f"\n📊 SUMMARY:")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Successful: {summary['successful_requests']}")
        print(f"  Failed: {summary['failed_requests']}")
        print(f"  Error Rate: {summary['error_rate']}")
        print(f"  Duration: {summary['duration_seconds']} seconds")
        print(f"  Throughput: {summary['requests_per_second']} req/sec")
        
        # Latency stats
        latency = results['latency_stats']
        print(f"\n⏱️  LATENCY STATISTICS:")
        print(f"  Mean: {latency['mean_ms']} ms")
        print(f"  Median: {latency['median_ms']} ms")
        print(f"  95th percentile: {latency['p95_ms']} ms")
        print(f"  Max: {latency['max_ms']} ms")
        print(f"  Min: {latency['min_ms']} ms")
        
        # Performance stats
        perf = results['performance']
        if perf:
            print(f"\n🖥️  PERFORMANCE MONITORING:")
            print(f"  Peak Memory: {perf.get('peak_memory_mb', 0):.1f} MB")
            print(f"  Memory Growth: {perf.get('memory_growth_mb', 0):.1f} MB")
            print(f"  Avg CPU: {perf.get('avg_cpu_percent', 0):.1f}%")
            print(f"  Max Connections: {perf.get('max_connections', 0)}")
            print(f"  Max Open Files: {perf.get('max_open_files', 0)}")
        
        # Errors
        if results['errors']:
            print(f"\n❌ SAMPLE ERRORS ({len(results['errors'])} shown):")
            for i, error in enumerate(results['errors'][:5], 1):
                print(f"  {i}. {error}")
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        logger.error(f"Stress test failed: {str(e)}")
        if args.verbose:
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 