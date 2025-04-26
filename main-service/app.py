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
from fastapi.responses import JSONResponse


app = FastAPI()

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

@app.get("/healthcheck", tags=["Health"])
async def healthcheck():
    return JSONResponse(status_code=200, content={"status": "ok"})


# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/query", response_model=QueryResponse)
async def query_endpoint(query: Optional[str] = Query(default=None)):

    tenant_id = get_tenant_id_from_token("mock-token")

    results = query_service.query(query,tenant_id)
    
    results = [Result(product_id=result.id, score=result.score,payload=result.payload) for result in results]
    print(results)  
    
    return QueryResponse(data=results)