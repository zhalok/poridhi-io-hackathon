#!/bin/bash

# Performance test suite runner for intent-based product search system
# This script will run multiple tests with different configurations
# Short version for quick testing

# Create results directory
RESULTS_DIR="./results/$(date +%Y%m%d_%H%M%S)"
mkdir -p $RESULTS_DIR

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "Locust not found. Please install with: pip install locust"
    exit 1
fi

# Make sure Docker is running and services are up
echo "Checking if Docker services are running..."
if [ "$(docker ps | grep main-service)" == "" ]; then
    echo "Main service container not found. Make sure your services are running with: docker-compose up -d"
    exit 1
fi

echo "Services are running!"

# Function to run a test
run_test() {
    local test_name=$1
    local user_class=$2
    local host=$3
    local users=$4
    local spawn_rate=$5
    local runtime=$6
    
    echo "=============================================="
    echo "Running test: $test_name"
    echo "UserClass: $user_class, Host: $host"
    echo "Users: $users, Spawn Rate: $spawn_rate, Runtime: ${runtime}s"
    echo "=============================================="
    
    # Start resource monitoring in the background
    python monitor_resources.py --output "$RESULTS_DIR/$test_name" --interval 1 &
    MONITOR_PID=$!
    
    # Run the locust test in headless mode
    locust -f advanced_locustfile.py $user_class \
        --host=$host \
        --headless \
        --users $users \
        --spawn-rate $spawn_rate \
        --run-time ${runtime}s \
        --csv="$RESULTS_DIR/$test_name/locust"
    
    # Give the monitor a few seconds to complete its final measurement
    echo "Completing resource monitoring..."
    sleep 3
    
    # Send SIGINT to the monitor process to trigger summary generation
    kill -SIGINT $MONITOR_PID
    
    # Wait for the monitor to exit properly
    wait $MONITOR_PID 2>/dev/null
    
    echo "Test '$test_name' completed. Results saved to: $RESULTS_DIR/$test_name"
    echo ""
    # Wait just a short time between tests
    sleep 3
}

echo "Starting performance tests..."
echo "Results will be saved to: $RESULTS_DIR"

# Just run 2 quick tests for query API only
# Test 1: Basic query test (15 seconds)
run_test "01_baseline_query" "MainServiceUser" "http://localhost:8000" 5 5 15

# Test 2: Mini spike test (20 seconds)
run_test "02_spike_test" "SpikeTestUser" "http://localhost:8000" 20 10 20

echo "All tests completed!"
echo "Results are saved in: $RESULTS_DIR"
echo ""
echo "To generate visualization and report, run:"
echo "cd performance_tests && python plot_results.py $RESULTS_DIR" 