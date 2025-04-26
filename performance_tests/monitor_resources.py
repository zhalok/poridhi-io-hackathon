#!/usr/bin/env python3
"""
System resource monitor for performance testing
Tracks CPU, memory, and network usage of Docker containers during tests
"""

import subprocess
import time
import json
import csv
import os
import signal
import argparse
import sys
from datetime import datetime

# Define the containers to monitor - ensure these match your Docker container names exactly
CONTAINERS = [
    "main-service",
    "insertion-service", 
    "storage-service",
    "sync-consumer-service",
    "rabbitmq",
    "qdrant"
]

class DockerMonitor:
    def __init__(self, output_dir="./results", interval=5):
        self.output_dir = output_dir
        self.interval = interval  # seconds between measurements
        self.running = False
        self.results = {}
        self.containers = {}
        self.start_time = None
        self.metrics_data = {}  # Store metrics data for summary
        
        # Create results directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
    def start(self):
        """Start the monitoring process"""
        self.running = True
        self.start_time = datetime.now()
        test_id = self.start_time.strftime("%Y%m%d_%H%M%S")
        
        # First check which containers actually exist
        running_containers = self.get_running_containers()
        print(f"Found running containers: {running_containers}")
        
        # If no containers are found
        if not running_containers:
            print("No matching Docker containers found! Please check container names.")
            print(f"Expected container names: {CONTAINERS}")
            print("Make sure your Docker containers are running with 'docker-compose up -d'")
            self.save_dummy_data(test_id)
            return
        
        # Initialize metrics data structure for each container
        for container in running_containers:
            self.metrics_data[container] = {
                'cpu_percent': [],
                'memory_percent': [],
                'network_rx_mb': [],
                'network_tx_mb': []
            }
            
        # Create CSV files for each container with headers
        for container in running_containers:
            filename = f"{self.output_dir}/{container}_{test_id}.csv"
            self.containers[container] = filename
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "timestamp", 
                    "cpu_percent", 
                    "memory_usage_mb", 
                    "memory_limit_mb", 
                    "memory_percent",
                    "network_rx_mb",
                    "network_tx_mb"
                ])
        
        print(f"Started monitoring containers: {', '.join(running_containers)}")
        print(f"Results will be saved to: {self.output_dir}")
        
        try:
            sample_count = 0
            while self.running and sample_count < 100:  # Safety limit of 100 samples
                self.collect_metrics()
                time.sleep(self.interval)
                sample_count += 1
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        finally:
            self.stop()
    
    def get_running_containers(self):
        """Get a list of running containers that match our target containers"""
        running_containers = []
        try:
            # List all running containers
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error listing Docker containers: {result.stderr}")
                return running_containers
            
            all_containers = result.stdout.strip().split('\n')
            
            # Filter containers based on our target names
            for container in CONTAINERS:
                if container in all_containers:
                    running_containers.append(container)
                    
            return running_containers
        except Exception as e:
            print(f"Error getting container list: {e}")
            return running_containers
    
    def save_dummy_data(self, test_id):
        """Save dummy data when no containers are found"""
        print("Creating placeholder metrics file")
        filename = f"{self.output_dir}/dummy_data_{test_id}.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "timestamp", 
                "container",
                "message"
            ])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "none",
                "No Docker containers were found or accessible"
            ])
            
        # Create the summary file
        summary = {
            "test_start": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": "No Docker containers were found or accessible",
            "containers": {}
        }
        
        summary_file = f"{self.output_dir}/summary_{test_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def collect_metrics(self):
        """Collect metrics from all containers and save to CSV"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        container_list = list(self.containers.keys())
        
        if not container_list:
            print("No containers to monitor!")
            return
        
        # Format for Docker stats command with all containers at once
        try:
            # Run docker stats once with no-stream option
            cmd = ["docker", "stats", "--no-stream", "--format", 
                   "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}"]
            cmd.extend(container_list)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting Docker stats: {result.stderr}")
                return
                
            stats_output = result.stdout.strip().split('\n')
            
            metrics_captured = False
            for line in stats_output:
                if not line.strip():
                    continue
                    
                parts = line.strip().split('\t')
                if len(parts) < 5:
                    continue
                    
                container = parts[0]
                if container not in self.containers:
                    continue
                    
                # Parse values with better error handling
                try:
                    # Remove % character and convert to float
                    cpu_percent = float(parts[1].strip().rstrip('%'))
                except ValueError:
                    cpu_percent = 0.0
                
                # Memory usage parsing
                mem_parts = parts[2].split('/')
                try:
                    mem_usage = self._parse_size(mem_parts[0].strip())
                    mem_limit = self._parse_size(mem_parts[1].strip()) if len(mem_parts) > 1 else 0
                except:
                    mem_usage = 0.0
                    mem_limit = 0.0
                
                # Memory percentage parsing
                try:
                    mem_percent = float(parts[3].strip().rstrip('%'))
                except ValueError:
                    mem_percent = 0.0
                
                # Network IO parsing
                net_parts = parts[4].split('/')
                try:
                    net_rx = self._parse_size(net_parts[0].strip())
                    net_tx = self._parse_size(net_parts[1].strip()) if len(net_parts) > 1 else 0
                except:
                    net_rx = 0.0
                    net_tx = 0.0
                
                # Store metrics in memory for summary generation
                if container in self.metrics_data:
                    self.metrics_data[container]['cpu_percent'].append(cpu_percent)
                    self.metrics_data[container]['memory_percent'].append(mem_percent)
                    self.metrics_data[container]['network_rx_mb'].append(net_rx)
                    self.metrics_data[container]['network_tx_mb'].append(net_tx)
                
                # Write to CSV
                if container in self.containers:
                    with open(self.containers[container], 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([
                            timestamp, 
                            cpu_percent, 
                            mem_usage, 
                            mem_limit, 
                            mem_percent,
                            net_rx,
                            net_tx
                        ])
                    metrics_captured = True
                    print(f"{timestamp} - {container}: CPU: {cpu_percent:.1f}%, Mem: {mem_percent:.1f}%")
            
            if not metrics_captured:
                print(f"{timestamp} - No metrics captured, check container names")
                
        except subprocess.TimeoutExpired:
            print(f"Timeout collecting metrics")
        except Exception as e:
            print(f"Error collecting metrics: {e}")
    
    def _parse_size(self, size_str):
        """Convert size string like '10.5MiB' to MB float value with better error handling"""
        try:
            # Extract the numeric part
            numeric_part = ''.join(c for c in size_str if c.isdigit() or c == '.')
            value = float(numeric_part) if numeric_part else 0
            
            # Convert to MB based on unit
            if 'GiB' in size_str or 'GB' in size_str:
                return value * 1024  # Convert GB to MB
            elif 'KiB' in size_str or 'KB' in size_str:
                return value / 1024  # Convert KB to MB
            elif 'B' in size_str and not ('MB' in size_str or 'MiB' in size_str):
                return value / (1024 * 1024)  # Convert B to MB
            else:
                return value  # Already in MB
        except Exception as e:
            print(f"Error parsing size '{size_str}': {e}")
            return 0
    
    def stop(self):
        """Stop the monitoring process and save final results"""
        self.running = False
        duration = datetime.now() - self.start_time
        print(f"\nMonitoring stopped after {duration.total_seconds():.1f} seconds")
        print(f"Results saved to: {self.output_dir}")
        
        # Generate summary file
        self._generate_summary()
    
    def _generate_summary(self):
        """Generate a summary of the test results"""
        summary = {
            "test_start": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "containers": {}
        }
        
        # Process each container's data to get max/avg/min values
        for container, metrics in self.metrics_data.items():
            container_data = {
                "cpu_percent": {"max": 0, "avg": 0, "min": float('inf')},
                "memory_percent": {"max": 0, "avg": 0, "min": float('inf')},
                "network_rx_mb": {"max": 0, "avg": 0, "min": float('inf')},
                "network_tx_mb": {"max": 0, "avg": 0, "min": float('inf')}
            }
            
            # Calculate stats for each metric
            for metric_name, values in metrics.items():
                if values:
                    container_data[metric_name]["max"] = max(values)
                    container_data[metric_name]["min"] = min(values)
                    container_data[metric_name]["avg"] = sum(values) / len(values)
                else:
                    # Default values if no data
                    container_data[metric_name]["max"] = 0
                    container_data[metric_name]["min"] = 0
                    container_data[metric_name]["avg"] = 0
            
            # Fix min value if no data was collected
            for metric in container_data.values():
                if metric["min"] == float('inf'):
                    metric["min"] = 0
                    
            summary["containers"][container] = container_data
        
        # Save summary as JSON
        summary_file = f"{self.output_dir}/summary_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Summary saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="Monitor Docker container resources during performance tests")
    parser.add_argument("--output", "-o", default="./results", help="Output directory for results")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Interval between measurements in seconds")
    args = parser.parse_args()
    
    monitor = DockerMonitor(output_dir=args.output, interval=args.interval)
    
    # Handle SIGINT gracefully
    def signal_handler(sig, frame):
        print("\nReceived signal to stop monitoring")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring
    monitor.start()


if __name__ == "__main__":
    main() 