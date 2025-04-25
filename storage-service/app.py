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

load_dotenv()

app = FastAPI()



STATIC_DIR = "files"
UPLOAD_DIR = "files"
def startup_event():
    os.makedirs(STATIC_DIR, exist_ok=True)




app.add_event_handler("startup", startup_event)



# Mount the static files directory
app.mount("/files", StaticFiles(directory=STATIC_DIR), name="static")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    message = json.dumps({

    "payload":{
    "file_path":f"http://localhost:8001/{UPLOAD_DIR}/{file.filename}",

    }})
    
    publish_to_mq(message)
    

    return JSONResponse(content={"filename": file.filename, "message": "File uploaded successfully"})