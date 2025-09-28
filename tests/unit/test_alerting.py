import logging
import time

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("alerting_test.log"), logging.StreamHandler()],
)


def generate_high_cpu_load(duration=60):
    """Generate high CPU load for testing"""
    logging.info("Starting CPU load test...")
    start_time = time.time()

    # Generate high CPU load
    while time.time() - start_time < duration:
        # Do some CPU-intensive work
        [x**2 for x in range(1000000)]

        # Log current CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        logging.info(f"CPU Usage: {cpu_percent}%")

        time.sleep(1)

    logging.info("CPU load test completed")


def test_disk_usage():
    """Log current disk usage"""
    disk_usage = psutil.disk_usage("/")
    usage_percent = disk_usage.percent
    logging.info(f"Disk Usage: {usage_percent}%")
    assert 0 <= usage_percent <= 100, "Disk usage percentage should be between 0 and 100"


def test_memory_usage():
    """Log current memory usage"""
    memory = psutil.virtual_memory()
    usage_percent = memory.percent
    logging.info(f"Memory Usage: {usage_percent}%")
    assert 0 <= usage_percent <= 100, "Memory usage percentage should be between 0 and 100"


if __name__ == "__main__":
    logging.info("Starting alerting system test")

    try:
        # Test 1: Log current system metrics
        logging.info("\n=== Current System Metrics ===")
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = test_memory_usage()
        disk_usage = test_disk_usage()

        logging.info(f"\nCPU Usage: {cpu_usage}%")
        logging.info(f"Memory Usage: {memory_usage}%")
        logging.info(f"Disk Usage: {disk_usage}%")

        # Test 2: Generate high CPU load to trigger alert
        if input("\nRun high CPU load test? (y/n): ").lower() == "y":
            generate_high_cpu_load(duration=300)  # 5 minutes

        logging.info("\nAlerting system test completed")

    except Exception as e:
        logging.error(f"Error during alerting test: {e!s}", exc_info=True)
