from functools import lru_cache
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.chunking import Chunk

VECTOR_SIZE = 384  # matches all-MiniLM-L6-v2 output dimension


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection() -> None:
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )


def upsert_chunks(document_id: int, chunks: List[Chunk], vectors: List[List[float]], file_name: str) -> None:
    ensure_collection()
    client = get_client()
    points = [
        qmodels.PointStruct(
            id=chunk.chunk_id,
            vector=vector,
            payload={
                "document_id": document_id,
                "file_name": file_name,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "text": chunk.text,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def vector_search(query_vector: List[float], top_k: int, document_ids: Optional[List[int]] = None):
    ensure_collection()
    client = get_client()
    query_filter = None
    if document_ids:
        query_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchAny(any=document_ids))]
        )
    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        query_filter=query_filter,
    )
    return results


def delete_document_vectors(document_id: int) -> None:
    client = get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))]
            )
        ),
    )


def fetch_all_payloads(document_ids: Optional[List[int]] = None):
    """Used by the BM25 index builder to pull all chunk texts + payloads."""
    ensure_collection()
    client = get_client()
    query_filter = None
    if document_ids:
        query_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchAny(any=document_ids))]
        )
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=query_filter,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    return points
