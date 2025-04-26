import time
import os
import random
from locust import HttpUser, task, between, events
import csv

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

class ProductSearchUser(HttpUser):
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    # Simulate different query patterns
    @task(10)  # Higher weight for queries as they'll be more common
    def query_products(self):
        query = random.choice(SAMPLE_QUERIES)
        self.client.get(f"/query?query={query}")
    
    # Simulate file uploads (less frequent)
    @task(1)
    def upload_file(self):
        # For testing, we'll create a small CSV file with random product data
        filename = f"test_products_{int(time.time())}.csv"
        self.create_test_csv(filename)
        
        with open(filename, "rb") as file:
            self.client.post(
                "/upload",
                files={"file": (filename, file, "text/csv")}
            )
        
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
                    'title': f'Test Product {i}',
                    'description': f'This is a test product description for product {i}'
                })

class SpikeUser(ProductSearchUser):
    """This user class simulates spike traffic with more aggressive request patterns"""
    wait_time = between(0.1, 1)  # Much shorter wait times
    
    @task(20)  # Even higher weight on queries during spike
    def query_products(self):
        query = random.choice(SAMPLE_QUERIES)
        self.client.get(f"/query?query={query}")
    
    @task(2)  # Also slightly more uploads during spike
    def upload_file(self):
        super().upload_file()

# Add custom test configuration for normal load and spike patterns
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    print("Locust initialized with the following test configuration:")
    print(" - Normal load: ProductSearchUser - Queries:Uploads ratio of 10:1, wait time 1-5s")
    print(" - Spike load: SpikeUser - Queries:Uploads ratio of 20:2, wait time 0.1-1s")
    print("\nRun a normal test with: locust -f locustfile.py ProductSearchUser")
    print("Run a spike test with: locust -f locustfile.py SpikeUser")
    print("Run both together with: locust -f locustfile.py") 