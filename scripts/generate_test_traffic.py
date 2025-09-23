#!/usr/bin/env python3
"""
Script to generate test traffic for SLO alert testing.
"""

import random
import time
import asyncio
import aiohttp
import logging
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class TrafficGenerator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_endpoints = [
            "/api/v1/test/health",
            "/api/v1/test/error",
            "/api/v1/test/error/400",
            "/api/v1/test/error/404",
            "/api/v1/test/error/500",
        ]
        self.latency_endpoint = "/api/v1/test/latency"

    async def start(self):
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession()

    async def stop(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()

    async def make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict:
        """Make an HTTP request and return the status code and response time."""
        if not self.session:
            await self.start()

        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "success": 200 <= response.status < 300,
                }
        except Exception as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            return {
                "status": 0,
                "response_time": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
            }

    async def generate_normal_traffic(self, duration: int = 60, rps: int = 10):
        """Generate normal traffic with low latency and few errors."""
        logger.info(
            f"Generating normal traffic for {duration} seconds at {rps} requests per second"
        )

        end_time = time.time() + duration
        request_count = 0
        success_count = 0
        error_count = 0
        total_latency = 0

        while time.time() < end_time:
            tasks = []
            for _ in range(rps):
                # 90% chance of hitting health endpoint, 10% chance of hitting error endpoint
                if random.random() < 0.9:
                    endpoint = "/api/v1/test/health"
                else:
                    endpoint = random.choice(
                        [
                            "/api/v1/test/error",
                            "/api/v1/test/error/400",
                            "/api/v1/test/error/500",
                        ]
                    )

                tasks.append(self.make_request(endpoint))

            # Execute batch of requests
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Request failed: {str(result)}")
                    error_count += 1
                    continue

                request_count += 1
                if result["success"]:
                    success_count += 1
                    total_latency += result["response_time"]
                else:
                    error_count += 1

                if request_count % 100 == 0:
                    avg_latency = (
                        (total_latency / (success_count or 1))
                        if success_count > 0
                        else 0
                    )
                    logger.info(
                        f"Requests: {request_count}, "
                        f"Success: {success_count} ({success_count / request_count * 100:.1f}%), "
                        f"Avg Latency: {avg_latency:.1f}ms"
                    )

            # Sleep to maintain target RPS
            await asyncio.sleep(1)

        logger.info("Normal traffic generation completed")
        return {
            "total_requests": request_count,
            "successful_requests": success_count,
            "error_requests": error_count,
            "success_rate": success_count / (request_count or 1) * 100,
            "avg_latency_ms": total_latency / (success_count or 1)
            if success_count > 0
            else 0,
        }

    async def generate_high_latency_traffic(self, duration: int = 300, rps: int = 5):
        """Generate traffic with high latency."""
        logger.info(
            f"Generating high latency traffic for {duration} seconds at {rps} requests per second"
        )

        end_time = time.time() + duration
        request_count = 0
        success_count = 0
        error_count = 0

        while time.time() < end_time:
            tasks = []
            for _ in range(rps):
                # Random delay between 1000ms and 3000ms
                delay_ms = random.randint(1000, 3000)
                tasks.append(
                    self.make_request(
                        self.latency_endpoint,
                        method="POST",
                        json={"delay_ms": delay_ms},
                    )
                )

            # Execute batch of requests
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Request failed: {str(result)}")
                    error_count += 1
                    continue

                request_count += 1
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

                if request_count % 10 == 0:
                    logger.info(
                        f"High latency requests: {request_count}, "
                        f"Success: {success_count} ({success_count / request_count * 100:.1f}%)"
                    )

            # Sleep to maintain target RPS
            await asyncio.sleep(1)

        logger.info("High latency traffic generation completed")
        return {
            "total_requests": request_count,
            "successful_requests": success_count,
            "error_requests": error_count,
            "success_rate": success_count / (request_count or 1) * 100,
        }

    async def generate_high_error_traffic(self, duration: int = 300, rps: int = 10):
        """Generate traffic with high error rate."""
        logger.info(
            f"Generating high error traffic for {duration} seconds at {rps} requests per second"
        )

        end_time = time.time() + duration
        request_count = 0
        success_count = 0
        error_count = 0

        while time.time() < end_time:
            tasks = []
            for _ in range(rps):
                # 70% chance of error, 30% chance of success
                if random.random() < 0.7:
                    endpoint = random.choice(
                        [
                            "/api/v1/test/error",
                            "/api/v1/test/error/400",
                            "/api/v1/test/error/404",
                            "/api/v1/test/error/500",
                        ]
                    )
                else:
                    endpoint = "/api/v1/test/health"

                tasks.append(self.make_request(endpoint))

            # Execute batch of requests
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Request failed: {str(result)}")
                    error_count += 1
                    continue

                request_count += 1
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

                if request_count % 50 == 0:
                    logger.info(
                        f"Error test requests: {request_count}, "
                        f"Success: {success_count} ({success_count / request_count * 100:.1f}%)"
                    )

            # Sleep to maintain target RPS
            await asyncio.sleep(1)

        logger.info("High error traffic generation completed")
        return {
            "total_requests": request_count,
            "successful_requests": success_count,
            "error_requests": error_count,
            "success_rate": success_count / (request_count or 1) * 100,
        }


async def main():
    """Main function to run the traffic generator."""
    base_url = "http://localhost:8000"
    traffic_gen = TrafficGenerator(base_url)

    try:
        # Start with normal traffic
        logger.info("=== Starting normal traffic generation ===")
        normal_stats = await traffic_gen.generate_normal_traffic(duration=300, rps=20)
        logger.info(f"Normal traffic stats: {normal_stats}")

        # Generate high latency traffic
        logger.info("\n=== Starting high latency traffic generation ===")
        latency_stats = await traffic_gen.generate_high_latency_traffic(
            duration=300, rps=5
        )
        logger.info(f"High latency traffic stats: {latency_stats}")

        # Generate high error traffic
        logger.info("\n=== Starting high error traffic generation ===")
        error_stats = await traffic_gen.generate_high_error_traffic(
            duration=300, rps=10
        )
        logger.info(f"High error traffic stats: {error_stats}")

    except KeyboardInterrupt:
        logger.info("\nTraffic generation interrupted by user")
    except Exception as e:
        logger.error(f"Error during traffic generation: {str(e)}", exc_info=True)
    finally:
        await traffic_gen.stop()
        logger.info("Traffic generation completed")


if __name__ == "__main__":
    asyncio.run(main())
