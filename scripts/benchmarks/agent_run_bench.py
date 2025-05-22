"""agent_run_bench.py
A micro-benchmark to stress-test the `/agent/{name}/run` endpoint using asyncio & httpx.

Example usage (from repo root):

    python scripts/benchmarks/agent_run_bench.py \
        --base-url http://localhost:8000 \
        --agent-name simple_agent \
        --concurrency 200 \
        --requests 1000

The script prints aggregated latency statistics similar to the `hey` utility but
without requiring an external binary.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import List

import httpx


def parse_args() -> argparse.Namespace:  # noqa: D401
    parser = argparse.ArgumentParser(description="Benchmark /agent/{name}/run throughput")
    parser.add_argument("--base-url", default="http://localhost:8000", help="FastAPI server base URL")
    parser.add_argument("--agent-name", default="simple_agent", help="Agent name to invoke")
    parser.add_argument("--concurrency", type=int, default=100, help="Number of concurrent in-flight requests")
    parser.add_argument("--requests", type=int, default=500, help="Total number of requests to send")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    return parser.parse_args()


async def _worker(
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    latencies: List[float],
) -> None:
    async with semaphore:
        start = time.perf_counter()
        try:
            await client.post(url, json=payload)
        except Exception:
            # For benchmarking we ignore individual errors – they will skew latency
            return
        finally:
            end = time.perf_counter() - start
            latencies.append(end)


async def main() -> None:  # noqa: D401
    args = parse_args()
    url = f"{args.base_url.rstrip('/')}/agent/{args.agent_name}/run"

    # Minimal payload – adjust as needed for your agents
    payload = {"input_text": "benchmark ping"}

    semaphore = asyncio.Semaphore(args.concurrency)
    latencies: List[float] = []

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        tasks = [
            asyncio.create_task(_worker(semaphore, client, url, payload, latencies))
            for _ in range(args.requests)
        ]
        await asyncio.gather(*tasks)

    if not latencies:
        print("No successful responses captured – benchmark aborted")
        return

    # Basic stats
    print("\nBenchmark results:")
    print(f"  Requests: {len(latencies)}")
    print(f"  Concurrency level: {args.concurrency}")
    print(f"  Mean latency: {statistics.mean(latencies)*1000:.2f} ms")
    print(f"  95th percentile: {statistics.quantiles(latencies, n=20)[18]*1000:.2f} ms")
    print(f"  Max latency: {max(latencies)*1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main()) 