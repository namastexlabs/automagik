#!/usr/bin/env python3
"""
Comprehensive Benchmark Suite for Automagik Agents

Runs multiple benchmark scenarios to validate:
- Graphiti queue performance
- System scaling behavior  
- Performance regression testing
- Mock vs Real API comparison

Usage:
    python scripts/benchmarks/comprehensive_benchmark.py --mode mock
    python scripts/benchmarks/comprehensive_benchmark.py --mode api --api-key your-key
    python scripts/benchmarks/comprehensive_benchmark.py --mode both --api-key your-key
"""

import asyncio
import json
import time
import argparse
import subprocess
import sys
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

class ComprehensiveBenchmark:
    """Comprehensive benchmark suite for Automagik agents."""
    
    def __init__(self, base_url: str = "http://localhost:8881", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.results = []
        self.project_version = self.get_project_version()
        
    def get_project_version(self) -> str:
        """Get project version from src/version.py."""
        try:
            version_path = Path("src/version.py")
            if version_path.exists():
                # Read the version file and extract __version__
                with open(version_path, "r") as f:
                    content = f.read()
                    # Look for __version__ = "x.y.z" pattern
                    for line in content.split('\n'):
                        if line.strip().startswith('__version__'):
                            # Extract version string
                            version = line.split('=')[1].strip().strip('"').strip("'")
                            return version
            return "unknown"
        except Exception:
            return "unknown"
        
    async def run_single_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single benchmark test configuration."""
        
        cmd = [
            "python", "tests/perf/benchmarks/api_stress_test.py",
            "--base-url", self.base_url,
        ]
        
        # Add test-specific parameters
        for key, value in test_config.items():
            if key != "name" and key != "description":
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        # Add API key if provided and in API mode
        if self.api_key and test_config.get("mode") == "api":
            cmd.extend(["--api-key", self.api_key])
        
        print(f"\n🧪 Running: {test_config['name']}")
        print(f"📝 {test_config['description']}")
        print(f"⚡ Command: {' '.join(cmd)}")
        
        start_time = time.time()
        
        try:
            # Run the test
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # Parse output for key metrics
                output = result.stdout
                
                # Extract key metrics from output
                metrics = self.parse_test_output(output)
                
                return {
                    "name": test_config["name"],
                    "description": test_config["description"],
                    "status": "success",
                    "duration": duration,
                    "config": test_config,
                    "metrics": metrics,
                    "output": output
                }
            else:
                return {
                    "name": test_config["name"],
                    "description": test_config["description"],
                    "status": "failed",
                    "duration": duration,
                    "config": test_config,
                    "error": result.stderr,
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "name": test_config["name"],
                "description": test_config["description"],
                "status": "timeout",
                "duration": 300,
                "config": test_config,
                "error": "Test timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "name": test_config["name"],
                "description": test_config["description"],
                "status": "error",
                "duration": time.time() - start_time,
                "config": test_config,
                "error": str(e)
            }
    
    def parse_test_output(self, output: str) -> Dict[str, Any]:
        """Parse test output to extract key metrics."""
        metrics = {}
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Extract key performance metrics
            if "Total Requests:" in line:
                metrics["total_requests"] = int(line.split(":")[1].strip())
            elif "Successful:" in line:
                metrics["successful_requests"] = int(line.split(":")[1].strip())
            elif "Failed:" in line:
                metrics["failed_requests"] = int(line.split(":")[1].strip())
            elif "Error Rate:" in line:
                metrics["error_rate"] = line.split(":")[1].strip()
            elif "Throughput:" in line:
                metrics["throughput_rps"] = float(line.split(":")[1].strip().replace(" req/sec", ""))
            elif "Mean:" in line and "ms" in line:
                metrics["mean_latency_ms"] = float(line.split(":")[1].strip().replace(" ms", ""))
            elif "95th percentile:" in line:
                metrics["p95_latency_ms"] = float(line.split(":")[1].strip().replace(" ms", ""))
            elif "Max:" in line and "ms" in line:
                metrics["max_latency_ms"] = float(line.split(":")[1].strip().replace(" ms", ""))
            
            # Extract system performance metrics
            elif "Peak Memory:" in line:
                memory_str = line.split(":")[1].strip().replace(" MB", "")
                metrics["peak_memory_mb"] = float(memory_str)
            elif "Memory Growth:" in line:
                growth_str = line.split(":")[1].strip().replace(" MB", "")
                metrics["memory_growth_mb"] = float(growth_str)
            elif "Avg CPU:" in line:
                cpu_str = line.split(":")[1].strip().replace("%", "")
                metrics["avg_cpu_percent"] = float(cpu_str)
            elif "Max Connections:" in line:
                metrics["max_connections"] = int(line.split(":")[1].strip())
            elif "Max Open Files:" in line:
                metrics["max_open_files"] = int(line.split(":")[1].strip())
        
        return metrics
    
    def get_test_scenarios(self, mode: str) -> List[Dict[str, Any]]:
        """Get test scenarios based on mode."""
        
        scenarios = []
        
        if mode in ["mock", "both"]:
            # Mock mode tests - focus on infrastructure performance
            scenarios.extend([
                {
                    "name": "Mock_Infrastructure_Baseline",
                    "description": "Infrastructure baseline with mock agents",
                    "mode": "mock",
                    "mock_type": "test",
                    "concurrency": 20,
                    "requests": 100
                },
                {
                    "name": "Mock_Medium_Load",
                    "description": "Medium infrastructure load test",
                    "mode": "mock",
                    "mock_type": "test",
                    "concurrency": 50,
                    "requests": 500
                },
                {
                    "name": "Mock_High_Concurrency",
                    "description": "High concurrency infrastructure test",
                    "mode": "mock",
                    "mock_type": "test",
                    "concurrency": 100,
                    "requests": 1000
                },
                {
                    "name": "Mock_Extreme_Load",
                    "description": "Extreme load infrastructure test",
                    "mode": "mock",
                    "mock_type": "test",
                    "concurrency": 200,
                    "requests": 2000
                },
                {
                    "name": "Mock_Stress_Test",
                    "description": "Maximum stress test for infrastructure",
                    "mode": "mock",
                    "mock_type": "test",
                    "concurrency": 500,
                    "requests": 5000
                },
                {
                    "name": "Mock_Function_Model_Realistic",
                    "description": "Realistic responses with function model",
                    "mode": "mock",
                    "mock_type": "function",
                    "concurrency": 100,
                    "requests": 1000
                }
            ])
        
        if mode in ["api", "both"]:
            # Real API tests - focus on end-to-end performance with OpenAI
            scenarios.extend([
                {
                    "name": "API_SimpleAgent_Baseline",
                    "description": "SimpleAgent baseline with 100 OpenAI requests",
                    "mode": "api",
                    "test_type": "agent_run",
                    "agent_name": "simple",
                    "concurrency": 10,
                    "requests": 100
                },
                {
                    "name": "API_SimpleAgent_Medium",
                    "description": "SimpleAgent medium load with 200 OpenAI requests",
                    "mode": "api",
                    "test_type": "agent_run",
                    "agent_name": "simple",
                    "concurrency": 15,
                    "requests": 200
                },
                {
                    "name": "API_SimpleAgent_High_Concurrency",
                    "description": "SimpleAgent high concurrency test",
                    "mode": "api",
                    "test_type": "agent_run",
                    "agent_name": "simple",
                    "concurrency": 25,
                    "requests": 150
                },
                {
                    "name": "API_Session_Queue_Heavy",
                    "description": "Heavy session queue testing",
                    "mode": "api",
                    "test_type": "session_queue",
                    "session_count": 10,
                    "messages_per_session": 15,
                    "concurrency": 20
                },
                {
                    "name": "API_Full_Stack_Comprehensive",
                    "description": "Comprehensive full API stack test",
                    "mode": "api",
                    "test_type": "full_api",
                    "concurrency": 20,
                    "requests": 100
                },
                {
                    "name": "API_GraphitiQueue_Validation",
                    "description": "Validate Graphiti queue under real load",
                    "mode": "api",
                    "test_type": "agent_run",
                    "agent_name": "simple",
                    "concurrency": 30,
                    "requests": 300
                }
            ])
        
        return scenarios
    
    async def run_comprehensive_benchmark(self, mode: str) -> None:
        """Run comprehensive benchmark suite."""
        
        print("=" * 80)
        print("🚀 COMPREHENSIVE AUTOMAGIK BENCHMARK SUITE")
        print("=" * 80)
        print(f"📊 Mode: {mode.upper()}")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"🔑 API Key: {'Provided' if self.api_key else 'Not provided'}")
        print("=" * 80)
        
        scenarios = self.get_test_scenarios(mode)
        
        print(f"\n📋 Running {len(scenarios)} test scenarios...")
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*20} Test {i}/{len(scenarios)} {'='*20}")
            
            result = await self.run_single_test(scenario)
            self.results.append(result)
            
            # Print immediate results
            if result["status"] == "success":
                metrics = result.get("metrics", {})
                print(f"✅ {result['name']}: SUCCESS")
                print(f"   📈 Throughput: {metrics.get('throughput_rps', 'N/A')} req/sec")
                print(f"   ⏱️  Mean Latency: {metrics.get('mean_latency_ms', 'N/A')} ms")
                print(f"   🎯 Error Rate: {metrics.get('error_rate', 'N/A')}")
                print(f"   🖥️  CPU Usage: {metrics.get('avg_cpu_percent', 'N/A')}%")
                print(f"   💾 Peak Memory: {metrics.get('peak_memory_mb', 'N/A')} MB")
                print(f"   📊 Memory Growth: {metrics.get('memory_growth_mb', 'N/A')} MB")
            else:
                print(f"❌ {result['name']}: {result['status'].upper()}")
                if result.get("error"):
                    print(f"   💥 Error: {result['error'][:100]}...")
        
        # Generate final report
        self.generate_console_report()
        self.save_markdown_report()
    
    def generate_console_report(self) -> None:
        """Generate console output for immediate feedback."""
        
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE BENCHMARK RESULTS")
        print("="*80)
        
        # Summary statistics
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r["status"] == "success"])
        failed_tests = total_tests - successful_tests
        
        print("\n📋 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {successful_tests/total_tests*100:.1f}%")
        
        # Performance metrics table
        print("\n📈 PERFORMANCE METRICS:")
        print(f"{'Test Name':<25} {'Status':<10} {'RPS':<10} {'Latency':<12} {'CPU%':<8} {'RAM(MB)':<10} {'Error%':<10}")
        print("-" * 95)
        
        for result in self.results:
            name = result["name"][:24]
            status = "✅ PASS" if result["status"] == "success" else "❌ FAIL"
            
            if result["status"] == "success":
                metrics = result.get("metrics", {})
                rps = f"{metrics.get('throughput_rps', 0):.1f}"
                latency = f"{metrics.get('mean_latency_ms', 0):.1f}ms"
                cpu_usage = f"{metrics.get('avg_cpu_percent', 0):.1f}"
                peak_memory = f"{metrics.get('peak_memory_mb', 0):.1f}"
                error_rate = metrics.get('error_rate', 'N/A')
            else:
                rps = "N/A"
                latency = "N/A"
                cpu_usage = "N/A"
                peak_memory = "N/A"
                error_rate = "N/A"
            
            print(f"{name:<25} {status:<10} {rps:<10} {latency:<12} {cpu_usage:<8} {peak_memory:<10} {error_rate:<10}")
        
        # Best performers
        successful_results = [r for r in self.results if r["status"] == "success"]
        
        if successful_results:
            print("\n🏆 BEST PERFORMERS:")
            
            # Highest throughput
            best_rps = max(successful_results, 
                          key=lambda x: x.get("metrics", {}).get("throughput_rps", 0))
            print(f"   🚀 Highest Throughput: {best_rps['name']} - "
                  f"{best_rps['metrics'].get('throughput_rps', 0):.1f} req/sec")
            
            # Lowest latency
            best_latency = min(successful_results,
                              key=lambda x: x.get("metrics", {}).get("mean_latency_ms", float('inf')))
            print(f"   ⚡ Lowest Latency: {best_latency['name']} - "
                  f"{best_latency['metrics'].get('mean_latency_ms', 0):.1f}ms")
            
            # Most CPU efficient
            cpu_efficient = min(successful_results,
                               key=lambda x: x.get("metrics", {}).get("avg_cpu_percent", float('inf')))
            print(f"   🖥️  Most CPU Efficient: {cpu_efficient['name']} - "
                  f"{cpu_efficient['metrics'].get('avg_cpu_percent', 0):.1f}% CPU")
            
            # Most memory efficient
            memory_efficient = min(successful_results,
                                  key=lambda x: x.get("metrics", {}).get("peak_memory_mb", float('inf')))
            print(f"   💾 Most Memory Efficient: {memory_efficient['name']} - "
                  f"{memory_efficient['metrics'].get('peak_memory_mb', 0):.1f} MB peak")
        
        print("="*80)
    
    def save_markdown_report(self) -> None:
        """Save comprehensive benchmark results as markdown report."""
        
        # Create benchmark directory if it doesn't exist
        benchmark_dir = Path("tests/perf/benchmarks/benchmark")
        benchmark_dir.mkdir(exist_ok=True)
        
        # Generate filename with date and version
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_report_v{self.project_version}_{date_str}.md"
        filepath = benchmark_dir / filename
        
        # Calculate summary statistics
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r["status"] == "success"])
        failed_tests = total_tests - successful_tests
        
        # Generate markdown content
        markdown_content = f"""# Automagik Agents Benchmark Report

**Generated:** {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}  
**Project Version:** {self.project_version}  
**Base URL:** {self.base_url}  
**Test Mode:** {self.results[0]['config'].get('mode', 'unknown').upper() if self.results else 'unknown'}

## Executive Summary

- **Total Tests:** {total_tests}
- **Successful:** {successful_tests}
- **Failed:** {failed_tests}  
- **Success Rate:** {successful_tests/total_tests*100:.1f}%

## Performance Overview

"""
        
        # Add performance metrics table
        markdown_content += """### Detailed Performance Metrics

| Test Name | Status | RPS | Latency | CPU% | RAM(MB) | Error% |
|-----------|--------|-----|---------|------|---------|--------|
"""
        
        for result in self.results:
            name = result["name"]
            status = "✅ PASS" if result["status"] == "success" else "❌ FAIL"
            
            if result["status"] == "success":
                metrics = result.get("metrics", {})
                rps = f"{metrics.get('throughput_rps', 0):.1f}"
                latency = f"{metrics.get('mean_latency_ms', 0):.1f}ms"
                cpu_usage = f"{metrics.get('avg_cpu_percent', 0):.1f}%"
                peak_memory = f"{metrics.get('peak_memory_mb', 0):.1f}"
                error_rate = metrics.get('error_rate', 'N/A')
            else:
                rps = "N/A"
                latency = "N/A"
                cpu_usage = "N/A"
                peak_memory = "N/A"
                error_rate = "N/A"
            
            markdown_content += f"| {name} | {status} | {rps} | {latency} | {cpu_usage} | {peak_memory} | {error_rate} |\n"
        
        # Add best performers section
        successful_results = [r for r in self.results if r["status"] == "success"]
        
        if successful_results:
            markdown_content += """
## 🏆 Best Performers

"""
            
            # Highest throughput
            best_rps = max(successful_results, 
                          key=lambda x: x.get("metrics", {}).get("throughput_rps", 0))
            markdown_content += f"**🚀 Highest Throughput:** {best_rps['name']} - {best_rps['metrics'].get('throughput_rps', 0):.1f} req/sec\n\n"
            
            # Lowest latency
            best_latency = min(successful_results,
                              key=lambda x: x.get("metrics", {}).get("mean_latency_ms", float('inf')))
            markdown_content += f"**⚡ Lowest Latency:** {best_latency['name']} - {best_latency['metrics'].get('mean_latency_ms', 0):.1f}ms\n\n"
            
            # Most CPU efficient
            cpu_efficient = min(successful_results,
                               key=lambda x: x.get("metrics", {}).get("avg_cpu_percent", float('inf')))
            markdown_content += f"**🖥️ Most CPU Efficient:** {cpu_efficient['name']} - {cpu_efficient['metrics'].get('avg_cpu_percent', 0):.1f}% CPU\n\n"
            
            # Most memory efficient
            memory_efficient = min(successful_results,
                                  key=lambda x: x.get("metrics", {}).get("peak_memory_mb", float('inf')))
            markdown_content += f"**💾 Most Memory Efficient:** {memory_efficient['name']} - {memory_efficient['metrics'].get('peak_memory_mb', 0):.1f} MB peak\n\n"
        
        # Add detailed test descriptions
        markdown_content += """
## Test Scenarios

"""
        
        for result in self.results:
            markdown_content += f"""### {result['name']}

**Description:** {result['description']}  
**Status:** {result['status']}  
**Duration:** {result['duration']:.2f}s  

**Configuration:**
"""
            for key, value in result['config'].items():
                if key not in ['name', 'description']:
                    markdown_content += f"- {key}: {value}\n"
            
            if result['status'] == 'success':
                metrics = result.get('metrics', {})
                markdown_content += f"""
**Results:**
- Throughput: {metrics.get('throughput_rps', 'N/A')} req/sec
- Mean Latency: {metrics.get('mean_latency_ms', 'N/A')} ms
- P95 Latency: {metrics.get('p95_latency_ms', 'N/A')} ms
- Max Latency: {metrics.get('max_latency_ms', 'N/A')} ms
- CPU Usage: {metrics.get('avg_cpu_percent', 'N/A')}%
- Peak Memory: {metrics.get('peak_memory_mb', 'N/A')} MB
- Memory Growth: {metrics.get('memory_growth_mb', 'N/A')} MB
- Error Rate: {metrics.get('error_rate', 'N/A')}

"""
            else:
                markdown_content += f"""
**Error:** {result.get('error', 'Unknown error')}

"""
        
        # Add system information and conclusions
        markdown_content += f"""
## System Information

- **Test Environment:** {self.base_url}
- **Project Version:** {self.project_version}
- **Test Framework:** Automagik Comprehensive Benchmark Suite
- **Total Test Duration:** {sum(r['duration'] for r in self.results):.2f}s

## Conclusions

"""
        
        if successful_results:
            avg_rps = sum(r.get('metrics', {}).get('throughput_rps', 0) for r in successful_results) / len(successful_results)
            avg_latency = sum(r.get('metrics', {}).get('mean_latency_ms', 0) for r in successful_results) / len(successful_results)
            
            markdown_content += f"""
- **Average Throughput:** {avg_rps:.1f} req/sec
- **Average Latency:** {avg_latency:.1f}ms
- **System Stability:** {successful_tests/total_tests*100:.1f}% success rate
- **Performance Status:** {'Excellent' if avg_rps > 400 else 'Good' if avg_rps > 100 else 'Needs Optimization'}

"""
        
        markdown_content += f"""
---
*Report generated by Automagik Benchmark Suite v{self.project_version}*
"""
        
        # Write markdown file
        with open(filepath, 'w') as f:
            f.write(markdown_content)
        
        print(f"\n📄 Markdown report saved to: {filepath}")
        
        # Also save JSON for programmatic access
        json_filename = f"benchmark_data_v{self.project_version}_{date_str}.json"
        json_filepath = benchmark_dir / json_filename
        
        with open(json_filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp.isoformat(),
                "project_version": self.project_version,
                "base_url": self.base_url,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "results": self.results
            }, f, indent=2)
        
        print(f"📊 Raw data saved to: {json_filepath}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive Automagik benchmark suite")
    
    parser.add_argument("--mode", choices=["mock", "api", "both"], default="mock",
                       help="Benchmark mode: mock (fast), api (real), or both")
    parser.add_argument("--base-url", default="http://localhost:8881",
                       help="API server base URL")
    parser.add_argument("--api-key", help="API key for real API tests")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode in ["api", "both"] and not args.api_key:
        print("❌ Error: --api-key is required for API mode tests")
        sys.exit(1)
    
    # Run benchmark
    benchmark = ComprehensiveBenchmark(args.base_url, args.api_key)
    asyncio.run(benchmark.run_comprehensive_benchmark(args.mode))


if __name__ == "__main__":
    main() 