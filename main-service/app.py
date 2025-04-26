# the main service should only take care of the query in the vector database, 
# file uploading for insertion and triggering the insertion service after the file upload


# first make the api for query
# then make the api at gateway for the sync pipeline queue trigger 
# then make the file upload api 
# then make the auth api

# main.py
from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from services.model import get_model
from repositories.qdrant.vectore_store import initiate_vector_store, create_collection
import services.query as query_service
import os
from services.auth import get_tenant_id_from_token

# monitoring and tracing
import asyncio
import psutil 
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from logging_conf import setup_logger
from utils import do_some_heavy_task
import time
from fastapi.responses import Response
import logging


app = FastAPI()

# loki configuration
log_dir = "/var/log/fastapi"
log_file = os.path.join(log_dir, "app.log")

os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename="/var/log/fastapi/app.log",  # Match Promtail config
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("fastapi-app")

class Result(BaseModel):
    product_id: str
    score: float
    payload: dict

class QueryRequest(BaseModel):
    query: str
    

class QueryResponse(BaseModel):
    data: List[Result]

STATIC_DIR = "uploaded_data_csv_files"

def startup_event():
    load_dotenv()

    os.makedirs(STATIC_DIR, exist_ok=True)

    get_model(model_name=os.getenv("MODEL_NAME"))
    
    collection_name = os.getenv("COLLECTION_NAME")
    
    

    print("initializing qdrant ...")
    qdrant_client = initiate_vector_store()

    print("qdrant_client",qdrant_client)
    print("qdrant initialized!!!")
    result = qdrant_client.collection_exists(collection_name=collection_name)
    if result == False:
        create_collection(client=qdrant_client,collection_name=collection_name)
    else:
        print("collection already exists!!!")


app.add_event_handler("startup", startup_event)



# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/query", response_model=QueryResponse)
async def query_endpoint(query: Optional[str] = Query(default=None)):
    tenant_id = get_tenant_id_from_token("mock-token")
    results = query_service.query(query, tenant_id)
    return QueryResponse(
        data=[
            Result(product_id=r.id, score=r.score, payload=r.payload)
            for r in results
        ]
    )


# Metrics
REQUEST_COUNT = Counter("total_req", "Total number of requests")
REQ_RES_TIME = Histogram(
    "http_fastapi_req_res_time",
    "Request/response latency",
    ["method", "endpoint", "http_status"],
    buckets=[0.001, 0.05, 0.1, 0.2, 0.5, 1, 2.5]
)

QUERY_COUNT = Counter(
    "query_requests_total",
    "Total number of /query requests received",
)
QUERY_LATENCY = Histogram(
    "query_request_duration_seconds",
    "Latency of /query handler",
    buckets=[0.001, 0.01, 0.05, 0.1, 0.2, 0.5, 1, 2.5],
)

CPU_USAGE    = Gauge("app_cpu_usage_percent",   "Process CPU usage percent")
MEMORY_USAGE = Gauge("app_memory_usage_bytes",   "Process memory usage in bytes")

@app.on_event("startup")
async def start_background_metrics_collector():
    """
    Every 5 seconds, poll psutil for CPU & memory usage and set the Gauges.
    """
    async def collect():
        while True:
            CPU_USAGE.set(psutil.cpu_percent(interval=None))
            MEMORY_USAGE.set(psutil.Process().memory_info().rss)
            await asyncio.sleep(5)

    asyncio.create_task(collect())


@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    resp_time = time.time() - start_time

    # global metrics
    REQUEST_COUNT.inc()
    REQ_RES_TIME.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=response.status_code,
    ).observe(resp_time)

    # query-only metrics
    if request.url.path == "/query":
        QUERY_COUNT.inc()
        QUERY_LATENCY.observe(resp_time)

    return response


@app.get("/")
async def read_root():
    logger.info("Request to root path")
    return {"message": "Hello from FastAPI!"}


@app.get("/slow")
async def slow_task():
    try:
        logger.info("Request to /slow path")
        time_taken = await do_some_heavy_task()
        return {
            "status": "Success",
            "message": f"Heavy task completed in {time_taken}ms"
        }
    except Exception as e:
        logger.error(f"Error in /slow: {str(e)}")
        return {"status": "Error", "error": str(e)}




@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)