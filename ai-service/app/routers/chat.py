import time

from fastapi import APIRouter

from app.core.llm import generate_answer
from app.core.retrieval import hybrid_retrieve
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/internal", tags=["chat"])


@router.post("/retrieve")
async def retrieve_only(request: ChatRequest):
    """Exposed separately so the evaluation harness can score retrieval alone."""

    chunks = hybrid_retrieve(
        request.query,
        request.document_ids,
    )

    return {
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "document": c.file_name,
                "page": c.page_number,
                "section": c.section_title,
                "text": c.text,
                "vector_score": c.vector_score,
                "bm25_score": c.bm25_score,
                "rerank_score": c.rerank_score,
            }
            for c in chunks
        ]
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start = time.time()

    chunks = hybrid_retrieve(
        request.query,
        request.document_ids,
    )

    result = generate_answer(
        request.query,
        chunks,
    )

    latency_ms = int(
        (time.time() - start) * 1000
    )

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        grounded=result["grounded"],
        # Fact-check is intentionally not executed on every chat request.
        # This avoids a second LLM call and significantly reduces latency.
        faithfulness_score=None,
        latency_ms=latency_ms,
    )
