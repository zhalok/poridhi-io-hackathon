# the main service should only take care of the query in the vector database, 
# file uploading for insertion and triggering the insertion service after the file upload


# first make the api for query
# then make the api at gateway for the sync pipeline queue trigger 
# then make the file upload api 
# then make the auth api

# main.py
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from services.model import get_model
from repositories.qdrant.vectore_store import initiate_vector_store, create_collection
import services.query as query_service
import os
from services.auth import get_tenant_id_from_token

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# --- Configuration ---
OTEL_EXPORTER_OTLP_ENDPOINT = "http://jaeger:4318/v1/traces"
OTEL_SERVICE_NAME = "main-service"
# OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "service-b")

# --- OpenTelemetry Setup ---
print(f"Initializing OpenTelemetry for service: {OTEL_SERVICE_NAME}")
print(f"OTLP Exporter Endpoint: {OTEL_EXPORTER_OTLP_ENDPOINT}")

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

# Instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

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
    
            
    quadrant_client = None
    
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
    
    results = []
    
    with tracer.start_as_current_span("embedding_model_load") as span:
        tenant_id = get_tenant_id_from_token("mock-token")
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("Query", query)

        results = query_service.query(query,tenant_id)
        
        results = [Result(product_id=result.id, score=result.score,payload=result.payload) for result in results]
        span.set_attribute("results", results)
        
        print(results)          
    
    return QueryResponse(data=results)