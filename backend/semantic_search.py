# backend/semantic_search.py
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from backend.config import TOP_K
from backend.context_indexer import _get_model

def semantic_search(query: str, index: faiss.Index, metadata: List[dict]) -> List[dict]:
    """
    Retrieve top-k relevant context chunks from the repo's FAISS index.
    The index and metadata are now passed as arguments.
    """
    if index is None or not metadata:
        return []

    model = _get_model()
    q_emb = model.encode([query])[0].astype("float32")
    
    # Use the passed index for searching
    D, I = index.search(np.array([q_emb]), TOP_K)

    results = []
    for idx in I[0]:
        if idx < 0 or idx >= len(metadata):
            continue
        results.append(metadata[idx])
    return results