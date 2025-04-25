def get_embeddings(text,model):
    return model.encode([text]).squeeze()