import time
import os
import random
from locust import HttpUser, task, between, events, tag
import csv
import json
from datetime import datetime

# Sample query data for testing
SAMPLE_QUERIES = [
    "smartphone with good camera",
    "wireless headphones",
    "laptop for gaming",
    "kitchen appliances",
    "comfortable office chair",
    "running shoes",
    "winter jacket",
    "smart watch",
    "bluetooth speaker",
    "4k television"
]

# Configuration for services
MAIN_SERVICE_HOST = "http://localhost:8000"
STORAGE_SERVICE_HOST = "http://localhost:8001"

class CompleteSystemUser(HttpUser):
    """User class that tests the complete system using both services"""
    wait_time = between(1, 3)
    
    def on_start(self):
        # No need to store client references
        pass
    
    @tag('query')
    @task(10)
    def query_products(self):
        query = random.choice(SAMPLE_QUERIES)
        with self.client.get(
            f"{MAIN_SERVICE_HOST}/query?query={query}", 
            name="/query",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Failed with status code: {response.status_code}")
    
    @tag('upload')
    @task(1)
    def upload_file(self):
        # Create a small CSV file with random product data
        filename = f"test_products_{int(time.time())}.csv"
        self.create_test_csv(filename)
        
        with open(filename, "rb") as file:
            with self.client.post(
                f"{STORAGE_SERVICE_HOST}/upload",
                files={"file": (filename, file, "text/csv")},
                name="/upload",
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed with status code: {response.status_code}")
        
        # Clean up the test file
        os.remove(filename)
    
    def create_test_csv(self, filename, rows=10):
        """Create a small CSV file with random product data for testing"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['title', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for i in range(rows):
                writer.writerow({
                    'title': f'Test Product {i} - {datetime.now().strftime("%H:%M:%S")}',
                    'description': f'This is a test product description for product {i}'
                })


class MainServiceUser(HttpUser):
    """User class that only tests the main service API"""
    host = MAIN_SERVICE_HOST
    wait_time = between(0.5, 3) 
    
    @tag('query')
    @task
    def query_products(self):
        query = random.choice(SAMPLE_QUERIES)
        with self.client.get(
            f"/query?query={query}", 
            name="/query",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Failed with status code: {response.status_code}")
            else:
                # Analyze response time
                if response.elapsed.total_seconds() > 0.5:  # Set threshold at 500ms
                    response.success()
                    # Log slow responses for analysis
                    print(f"Slow response ({response.elapsed.total_seconds():.2f}s) for query: {query}")


class StorageServiceUser(HttpUser):
    """User class that only tests the storage service API"""
    host = STORAGE_SERVICE_HOST
    wait_time = between(1, 5)  # File uploads are less frequent
    
    @tag('upload')
    @task
    def upload_file(self):
        filename = f"test_products_{int(time.time())}.csv"
        self.create_test_csv(filename)
        
        with open(filename, "rb") as file:
            with self.client.post(
                "/upload",
                files={"file": (filename, file, "text/csv")},
                name="/upload",
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed with status code: {response.status_code}")
        
        # Clean up the test file
        os.remove(filename)
    
    def create_test_csv(self, filename, rows=10):
        """Create a small CSV file with random product data for testing"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['title', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for i in range(rows):
                writer.writerow({
                    'title': f'Test Product {i} - {datetime.now().strftime("%H:%M:%S")}',
                    'description': f'This is a test product description for product {i}'
                })


class SpikeTestUser(CompleteSystemUser):
    """User class for spike testing both services with aggressive patterns"""
    wait_time = between(0.1, 0.5)  # Much shorter wait times during spike
    
    @tag('query')
    @task(20)  # Higher weight on queries during spike
    def query_products(self):
        super().query_products()
    
    @tag('upload')
    @task(2)  # More uploads during spike
    def upload_file(self):
        super().upload_file()


# Custom test configuration
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    print("\n=== Intent-Based Product Search System Load Test ===")
    print("Available user classes:")
    print(" - CompleteSystemUser: Tests both services (query:upload ratio 10:1)")
    print(" - MainServiceUser: Tests only the main service (queries)")
    print(" - StorageServiceUser: Tests only the storage service (uploads)")
    print(" - SpikeTestUser: Simulates spike traffic on both services")
    print("\nExample commands:")
    print(" - Test complete system: locust -f advanced_locustfile.py CompleteSystemUser")
    print(" - Test queries only: locust -f advanced_locustfile.py MainServiceUser")
    print(" - Test uploads only: locust -f advanced_locustfile.py StorageServiceUser")
    print(" - Test spike scenario: locust -f advanced_locustfile.py SpikeTestUser")


# Add custom stats event listener to log detailed metrics
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== Test Results Summary ===")
    stats = environment.stats
    
    # Calculate and print summary statistics
    total_requests = sum(r.num_requests for r in stats.entries.values())
    total_failures = sum(r.num_failures for r in stats.entries.values())
    failure_percent = (total_failures / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total Requests: {total_requests}")
    print(f"Failed Requests: {total_failures} ({failure_percent:.2f}%)")
    
    # Print stats per endpoint
    print("\nEndpoint Statistics:")
    for name, entry in stats.entries.items():
        print(f"  {name}:")
        print(f"    Requests: {entry.num_requests}")
        print(f"    Failures: {entry.num_failures}")
        print(f"    Median Response Time: {entry.median_response_time:.2f}ms")
        print(f"    95% Response Time: {entry.get_response_time_percentile(0.95):.2f}ms")
        print(f"    99% Response Time: {entry.get_response_time_percentile(0.99):.2f}ms")
        print(f"    Max Response Time: {entry.max_response_time:.2f}ms")
        print(f"    RPS: {entry.total_rps:.2f}")
    
    print("\nNote: Save this data for comparison with future tests") 