from sentence_transformers import SentenceTransformer


model = None

def get_model(model_name):
    ""
    global model
    
    if model != None:
        return model
    
    model = SentenceTransformer(model_name)

    
    return model