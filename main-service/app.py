# main.py
from fastapi import FastAPI, Query, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from services.model import get_model
from repositories.qdrant.vectore_store import initiate_vector_store, create_collection
import services.query as query_service
import os
from services.auth import get_tenant_id_from_token
from fastapi.responses import JSONResponse

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
import logging
import asyncio
import psutil
from prometheus_client import Gauge, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from logging_conf import setup_logger
from utils import do_some_heavy_task
import time
from fastapi.responses import Response

# --- Configuration ---
OTEL_EXPORTER_OTLP_ENDPOINT = "http://jaeger:4318/v1/traces"
OTEL_SERVICE_NAME = "main-service"

# --- OpenTelemetry Setup ---
print(f"Initializing OpenTelemetry for service: {OTEL_SERVICE_NAME}")
print(f"OTLP Exporter Endpoint: {OTEL_EXPORTER_OTLP_ENDPOINT}")

resource = Resource(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
trace_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(otlp_exporter)
trace_provider.add_span_processor(span_processor)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Loki Logging Setup
log_dir = "/var/log/fastapi"
log_file = os.path.join(log_dir, "app.log")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fastapi-app")

# --- Models ---
class Result(BaseModel):
    product_id: str
    score: float
    payload: dict

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    data: List[Result]

# --- Constants ---
STATIC_DIR = "uploaded_data_csv_files"

# --- Prometheus Metrics ---
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
CPU_USAGE = Gauge("app_cpu_usage_percent", "Process CPU usage percent")
MEMORY_USAGE = Gauge("app_memory_usage_bytes", "Process memory usage in bytes")

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    # Load environment variables
    load_dotenv()
    os.makedirs(STATIC_DIR, exist_ok=True)
    get_model(model_name=os.getenv("MODEL_NAME"))

    # Initialize Qdrant
    collection_name = os.getenv("COLLECTION_NAME")
    print("initializing qdrant ...")
    qdrant_client = initiate_vector_store()
    print("qdrant_client", qdrant_client)
    print("qdrant initialized!!!")

    if not qdrant_client.collection_exists(collection_name=collection_name):
        create_collection(client=qdrant_client, collection_name=collection_name)
    else:
        print("collection already exists!!!")

        
    # Start metrics collector
    async def collect_metrics():
        while True:
            CPU_USAGE.set(psutil.cpu_percent(interval=None))
            MEMORY_USAGE.set(psutil.Process().memory_info().rss)
            await asyncio.sleep(5)

    asyncio.create_task(collect_metrics())

# --- Middleware ---
@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    resp_time = time.time() - start_time

    # Global request metrics
    REQUEST_COUNT.inc()
    REQ_RES_TIME.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=response.status_code,
    ).observe(resp_time)

    # /query specific metrics
    if request.url.path == "/query":
        QUERY_COUNT.inc()
        QUERY_LATENCY.observe(resp_time)

    return response

app.add_event_handler("startup", startup_event)

@app.get("/healthcheck", tags=["Health"])
async def healthcheck():
    return JSONResponse(status_code=200, content={"status": "ok"})


# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

# --- Endpoints ---
@app.get("/")
async def read_root():
    logger.info("Request to root path")
    return {"message": "Hello from FastAPI!"}

@app.get("/query", response_model=QueryResponse)
async def query_endpoint(query: Optional[str] = Query(default=None)):
    results = []
    with tracer.start_as_current_span("embedding_model_load") as span:
        tenant_id = get_tenant_id_from_token("mock-token")
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("Query", query)

        results = query_service.query(query, tenant_id, tracer)
        results = [Result(product_id=result.id, score=result.score, payload=result.payload) for result in results]

        span.set_attribute("results", results)
        print(results)

    return QueryResponse(data=results)

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
