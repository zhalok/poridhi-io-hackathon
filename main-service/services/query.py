from repositories.qdrant.vectore_store import get_client
from services.model import get_model
from services.embedding import get_embeddings
import os

collection_name = os.getenv("QDRANT_COLLECTION_NAME")
print("collection name",collection_name)
def query(query_text):
    client = get_client()
    model = get_model(model_name=os.getenv("MODEL_NAME"))

    query_embeddings = get_embeddings(text=query_text,model=model)

    search_result = client.query_points(
    collection_name=collection_name,
    query=query_embeddings,
    with_payload=True,
    with_vectors=False,
    limit=3,
    score_threshold=0.4
    ).points

    return search_result
