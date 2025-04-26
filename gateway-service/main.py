import os
import requests
import logging
from fastapi import FastAPI, File, UploadFile

from typing import List, Optional
from fastapi import  Query
from pydantic import BaseModel

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# --- Configuration ---
# MAIN_SERVICE_URL=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://main-service:8000")
MAIN_SERVICE_URL="http://main-service:8000"
STORAGE_SERVICE_URL="http://storage-service:8001"
OTEL_EXPORTER_OTLP_ENDPOINT = "http://jaeger:4318/v1/traces"
OTEL_SERVICE_NAME = "gateway-service"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- OpenTelemetry Setup ---
logger.info(f"Initializing OpenTelemetry for service: {OTEL_SERVICE_NAME}")
logger.info(f"OTLP Exporter Endpoint: {OTEL_EXPORTER_OTLP_ENDPOINT}")

# Set service name attribute
resource = Resource(attributes={
    SERVICE_NAME: OTEL_SERVICE_NAME
})

# Set up OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)

# Set up trace provider and processor
trace_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(otlp_exporter)
trace_provider.add_span_processor(span_processor)

# Set the global tracer provider
trace.set_tracer_provider(trace_provider)

# Get a tracer
tracer = trace.get_tracer(__name__)

# Instrument FastAPI and Requests
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument() # Instrument the requests library


# --- API Endpoints ---
@app.get("/")
def read_root():
    logger.info("GATEWAY-SERVICE: Received request for /")
    return {"service": OTEL_SERVICE_NAME, "status": "OK"}

class Result(BaseModel):
    product_id: str
    score: float
    payload: dict

class QueryResponse(BaseModel):
    data: List[Result]

@app.get("/query")
async def query_endpoint(query: Optional[str] = Query(default=None)):
    logger.info(f"GATEWAY-SERVICE: Received request for /query, calling {MAIN_SERVICE_URL}")
    try:
        # The RequestsInstrumentor automatically adds trace context headers
        url = MAIN_SERVICE_URL + "/query?query=" + query
        logger.info(f"GATEWAY-SERVICE: Calling main service: {url}")
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        logger.info(f"GATEWAY-SERVICE: Received response from main service: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"GATEWAY-SERVICE: Error calling Service B: {e}")
        # You might want to create a span manually here to record the error,
        # though the instrumentor might already capture the failed request.
        with tracer.start_as_current_span("main_service_error") as span:
            span.set_attribute("error", True)
            span.record_exception(e)
        return {"error from main service": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"GATEWAY-SERVICE: Received request for /upload, calling {STORAGE_SERVICE_URL}")
    try:
        # The RequestsInstrumentor automatically adds trace context headers        
        url = STORAGE_SERVICE_URL + "/upload"
        logger.info(f"GATEWAY-SERVICE: Calling STORAGE_SERVICE_URL service: {url}")
        files = {'file': file.file}
        response = requests.post(url, files=files)
        response.raise_for_status() # Raise an exception for bad status codes
        logger.info(f"GATEWAY-SERVICE: Received response from main service: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"GATEWAY-SERVICE: Error calling Service B: {e}")
        # You might want to create a span manually here to record the error,
        # though the instrumentor might already capture the failed request.
        with tracer.start_as_current_span("storage_service_error") as span:
            span.set_attribute("error", True)
            span.record_exception(e)
        return {"error from main service": str(e)}
    
    
if __name__ == "__main__":
    import uvicorn
    # Uvicorn will be run by Docker, but this allows local running if needed
    uvicorn.run(app, host="0.0.0.0", port=8002)