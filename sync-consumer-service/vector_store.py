from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import PointStruct
import uuid


vector_client = None

def initiate_vector_store():
    ""
    global vector_client
    vector_client = QdrantClient(url="http://localhost:6333")

    return vector_client

def create_collection(client,collection_name):

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.DOT),
    )

    return get_collection(client=client,collection_name=collection_name)

def get_collection(client, collection_name):
    try:
        collection = client.get_collection(collection_name)
        return collection
    except:
        return None

def get_client():
    global vector_client
    if vector_client != None:
        return vector_client
    
    new_client = initiate_vector_store()
    vector_client = new_client
    return vector_client


def prepare_qdrant_point_from_payload_descriptions(model,payloads,get_embeddings_func):
    ""
    points = []
    for payload in payloads:
        text_for_embeddings = payload["text"]
        embeddings = get_embeddings_func(text_for_embeddings,model)
        point = PointStruct(id=payload["id"], vector=embeddings, payload=payload)
        points.append(point)
    
    return points

def prepare_qdrant_point_from_embedding(embedding,payload):
    id = uuid.uuid4()
    point = PointStruct(id=str(id), vector=embedding, payload=payload)
    return point
        


def store_in_vector_store(client,collection_name,qdrant_points):
    ""
    operation_info = client.upsert(
        collection_name=collection_name,
        wait=True,
        points=qdrant_points,
    )

    return operation_info


