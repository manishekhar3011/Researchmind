from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.embeddings import embed_query
from app.core.vectorstore import vector_search, fetch_all_payloads


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: int
    file_name: str
    page_number: int
    section_title: str
    text: str
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _bm25_search(query: str, document_ids: Optional[List[int]], top_k: int) -> List[RetrievedChunk]:
    points = fetch_all_payloads(document_ids)
    if not points:
        return []
    corpus_tokens = [p.payload["text"].lower().split() for p in points]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(points, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        RetrievedChunk(
            chunk_id=str(p.id),
            document_id=p.payload["document_id"],
            file_name=p.payload["file_name"],
            page_number=p.payload["page_number"],
            section_title=p.payload["section_title"],
            text=p.payload["text"],
            bm25_score=float(score),
        )
        for p, score in ranked
        if score > 0
    ]


def _vector_search(query: str, document_ids: Optional[List[int]], top_k: int) -> List[RetrievedChunk]:
    vector = embed_query(query)
    results = vector_search(vector, top_k, document_ids)
    return [
        RetrievedChunk(
            chunk_id=str(r.id),
            document_id=r.payload["document_id"],
            file_name=r.payload["file_name"],
            page_number=r.payload["page_number"],
            section_title=r.payload["section_title"],
            text=r.payload["text"],
            vector_score=float(r.score),
        )
        for r in results
    ]


def _reciprocal_rank_fusion(vector_results: List[RetrievedChunk], bm25_results: List[RetrievedChunk], k: int = 60) -> List[RetrievedChunk]:
    """Combines two ranked lists into one score per chunk_id (standard RRF, k=60 is the common default)."""
    scores = {}
    merged = {}

    for rank, chunk in enumerate(vector_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        merged[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(bm25_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        if chunk.chunk_id in merged:
            merged[chunk.chunk_id].bm25_score = chunk.bm25_score
        else:
            merged[chunk.chunk_id] = chunk

    fused_order = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [merged[cid] for cid, _ in fused_order]


def _rerank(query: str, candidates: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
    if not candidates:
        return []
    reranker = get_reranker()
    pairs = [(query, c.text) for c in candidates]
    scores = reranker.predict(pairs)
    for c, s in zip(candidates, scores):
        c.rerank_score = float(s)
    ranked = sorted(candidates, key=lambda c: c.rerank_score, reverse=True)
    return ranked[:top_k]


def hybrid_retrieve(query: str, document_ids: Optional[List[int]] = None) -> List[RetrievedChunk]:
    vector_results = _vector_search(query, document_ids, settings.top_k_vector)
    bm25_results = _bm25_search(query, document_ids, settings.top_k_bm25)
    fused = _reciprocal_rank_fusion(vector_results, bm25_results)
    reranked = _rerank(query, fused[: max(settings.top_k_vector, settings.top_k_bm25)], settings.top_k_final)
    # Hallucination-prevention gate: drop weak results rather than passing them to the LLM.
    return [c for c in reranked if c.rerank_score >= settings.min_rerank_score]
