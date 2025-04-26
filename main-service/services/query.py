from repositories.qdrant.vectore_store import get_client
from services.model import get_model
from services.embedding import get_embeddings
import os
from qdrant_client import models
from qdrant_client.models import Filter, FieldCondition, MatchValue
from services.llm import redefine_query
from services.openai_llm import standardize_query,guardrail
from fastapi import HTTPException



def query(query_text,tenant_id):


    client = get_client()
    model = get_model(model_name=os.getenv("MODEL_NAME"))

    is_safe = guardrail(query=query_text)
    if is_safe == False:
        raise HTTPException(status_code=400, detail="Query is not safe")

    refined_query = standardize_query(query=query_text)



    query_embeddings = get_embeddings(text=refined_query,model=model)
    collection_name = os.getenv("COLLECTION_NAME")
    search_result = client.query_points(
    collection_name=collection_name,
    query=query_embeddings,
    with_payload=True,
    with_vectors=False,
    query_filter=models.Filter(
    should=[
        models.FieldCondition(
            key="tenant_id",
            match=models.MatchValue(
                value=tenant_id,
            ),
        ),
        # models.FieldCondition(
        #     key="text",         # payload field name
        #     match=models.MatchValue(value=refined_query)
        # )
    ]
    ),
    limit=100,
    score_threshold=0.3
    ).points

    return search_result
