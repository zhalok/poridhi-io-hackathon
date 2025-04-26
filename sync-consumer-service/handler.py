from preprocessor import preprocess
from model import get_model
from embedder import get_embeddings
from vector_store import prepare_qdrant_point_from_embedding,store_in_vector_store
import uuid

def handle(event, context):
    ""
    model = context["model"]
    collection_name = context["collection_name"]
    vstore_client = context["client"]

    json_payload = event["payload"]
    tenant_id = json_payload["tenant_id"]
    
    normalized_text = preprocess(json_payload)
    embeddings = get_embeddings(normalized_text,model)
    qdrant_point = prepare_qdrant_point_from_embedding(embeddings,{
        "id":json_payload["id"],
        "title":json_payload["title"],
        "tenant_id":tenant_id,
        "text":normalized_text
    })
    operation_response = store_in_vector_store(vstore_client,collection_name=collection_name,qdrant_points=[qdrant_point])
    return operation_response

