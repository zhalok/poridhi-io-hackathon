# Performance Testing for Intent-Based Product Search System

This directory contains Locust scripts and resource monitoring tools for comprehensive load testing and performance analysis of the product search system.

## Prerequisites

- Python 3.7+
- Locust (`pip install locust`)
- Matplotlib and pandas for visualization (`pip install matplotlib pandas`)
- Running product search system (all services should be up)

## Using Docker for Performance Testing

The easiest way to run performance tests is using the included Docker container.

1. Start the entire system including the performance testing service:

```bash
docker-compose up -d
```

2. Access the Locust web interface:

   - Open http://localhost:8089 in your browser

3. Run different test types through Docker:

```bash
# Run web UI
docker-compose run performance-tests web

# Run a headless spike test (20 users, 10 spawn rate, 30s duration)
docker-compose run performance-tests headless spike 20 10 30

# Run only resource monitoring
docker-compose run performance-tests monitor

# Run automated test suite
docker-compose run performance-tests run-tests

# Generate report from test results
docker-compose run performance-tests report ./results/YYYYMMDD_HHMMSS

# Show help
docker-compose run performance-tests help
```

## Test Types

The advanced locustfile includes several user types:

1. `MainServiceUser` - Tests only the main query service

   - Simulates users doing product searches
   - Good for baseline performance testing

2. `StorageServiceUser` - Tests only the upload functionality

   - Uploads product data files
   - Good for testing ingestion performance

3. `CompleteSystemUser` - Tests both services with realistic ratios

   - Mix of queries (higher frequency) and occasional uploads (10:1 ratio)
   - More reasonable wait times between actions

4. `SpikeTestUser` - Simulates spike/burst traffic
   - Much higher query rate
   - Shorter wait times
   - Higher concurrency

## Automated Test Suite

For consistent and repeatable testing, use the automated test runner:

```bash
cd performance_tests
./run_tests.sh
```

This script:

1. Creates a timestamped results directory
2. Starts resource monitoring for each Docker container
3. Runs a series of predefined tests (baseline and spike)
4. Collects performance metrics and resource usage data
5. Generates summary files

### Understanding Resource Monitoring

The `monitor_resources.py` script captures:

- CPU usage per container (can exceed 100% on multi-core systems)
- Memory usage
- Network I/O
- Key statistics (min/max/avg)

CPU percentages are relative to a single CPU core, so values like 274% indicate usage of approximately 2.7 CPU cores.

## Manual Test Options

### Start Your System First

Make sure your Docker containers are running:

```bash
docker-compose up -d
```

### Run Individual Tests

```bash
# Basic query test
locust -f advanced_locustfile.py MainServiceUser --host=http://localhost:8000

# Upload test
locust -f advanced_locustfile.py StorageServiceUser --host=http://localhost:8000

# Complete system test
locust -f advanced_locustfile.py CompleteSystemUser --host=http://localhost:8000

# Spike test
locust -f advanced_locustfile.py SpikeTestUser --host=http://localhost:8000
```

### Using Resource Monitoring Separately

You can monitor Docker container resources independently:

```bash
python monitor_resources.py --output ./results/my_test --interval 1
```

## Visualization and Reporting

After running tests, generate visualizations and a comprehensive report:

```bash
python plot_results.py ./results/YYYYMMDD_HHMMSS
```

This produces:

- Response time charts
- Request rate visualizations
- CPU usage per container
- Memory usage per container
- Performance report with recommendations

## Using the Locust Web UI

By default, Locust starts a web UI at http://localhost:8089 where you can:

1. Set the number of users to simulate
2. Set the spawn rate (users started per second)
3. Start/stop the test
4. View real-time metrics
5. Download test results in various formats

## Recommended Test Scenarios

### Baseline Test

- 5-10 users
- Spawn rate: 1-5 users/second
- Duration: 1-5 minutes

### Moderate Load

- 50 users
- Spawn rate: 5 users/second
- Duration: 10 minutes

### Heavy Load

- 200 users
- Spawn rate: 10 users/second
- Duration: 15 minutes

### Spike Test

- 20 users with spawn rate 10 users/second
- Duration: 20-30 seconds
- Monitors system recovery after burst traffic

## Interpreting Results

Key metrics to monitor:

- Response time (p50, p95, p99)
- Requests per second (RPS)
- Failure rate
- CPU utilization per container
- Memory usage patterns
- Network I/O

## Troubleshooting

If your tests show high failure rates or performance issues:

1. Check resource monitoring results for bottlenecks
2. Look for containers with CPU usage consistently above 80%
3. Review memory growth patterns that might indicate leaks
4. Check Docker container logs for errors
5. Consider scaling services that show high CPU utilization
