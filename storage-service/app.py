# the main service should only take care of the query in the vector database, 
# file uploading for insertion and triggering the insertion service after the file upload


# first make the api for query
# then make the api at gateway for the sync pipeline queue trigger 
# then make the file upload api 
# then make the auth api

# main.py
from fastapi import FastAPI,  File, UploadFile
from fastapi.responses import JSONResponse
import shutil
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import uuid
from publisher import publish_to_mq
import json
from auth import get_tenant_id_from_token
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

load_dotenv()

OTEL_EXPORTER_OTLP_ENDPOINT = "http://jaeger:4318/v1/traces"
OTEL_SERVICE_NAME = "storage-service"

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


STATIC_DIR = "files"
UPLOAD_DIR = "files"
def startup_event():
    os.makedirs(STATIC_DIR, exist_ok=True)




app.add_event_handler("startup", startup_event)



# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/healthcheck", tags=["Health"])
async def healthcheck():
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    with tracer.start_as_current_span("embedding_model_load") as span:
        tenant_id = get_tenant_id_from_token("mock-token")
        
        file_location = f"{UPLOAD_DIR}/{file.filename}"
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("file_name", file.filename)
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        message = json.dumps({

        "payload":{
        "file_path":f"http://storage-service:8001/{UPLOAD_DIR}/{file.filename}",
        "tenant_id":tenant_id

        }})
        
        publish_to_mq(message)
    

    return JSONResponse(content={"filename": file.filename, "message": "File uploaded successfully"})