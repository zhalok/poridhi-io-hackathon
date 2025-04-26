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
from repositories.qdrant.vectore_store import initiate_vector_store
import services.query as query_service
import os
from services.auth import get_tenant_id_from_token


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
    print("collection name",os.getenv("QDRANT_COLLECTION_NAME"))
    os.makedirs(STATIC_DIR, exist_ok=True)

    print("initializing qdrant ...")
    qdrant_client = initiate_vector_store()
    print("qdrant_client",qdrant_client)
    print("qdrant initialized!!!")


app.add_event_handler("startup", startup_event)



# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/query", response_model=QueryResponse)
async def query_endpoint(query: Optional[str] = Query(default=None)):

    tenant_id = get_tenant_id_from_token("mock-token")

    results = query_service.query(query,tenant_id)
    results = [Result(product_id=result.id, score=result.score,payload=result.payload) for result in results]
    
    return QueryResponse(data=results)