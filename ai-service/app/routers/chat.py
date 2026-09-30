import time

from fastapi import APIRouter

from app.core.llm import generate_answer
from app.core.retrieval import hybrid_retrieve
from app.models.schemas import ChatRequest, ChatResponse


router = APIRouter(
    prefix="/internal",
    tags=["chat"]
)


@router.post("/retrieve")
async def retrieve_only(request: ChatRequest):

    total_start = time.perf_counter()

    retrieval_start = time.perf_counter()

    chunks = hybrid_retrieve(
        request.query,
        request.document_ids
    )

    retrieval_ms = int(
        (time.perf_counter() - retrieval_start) * 1000
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
        ],
        "timing": {
            "retrieval_ms": retrieval_ms,
            "total_ms": int(
                (time.perf_counter() - total_start) * 1000
            ),
        },
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    total_start = time.perf_counter()

    # -----------------------------
    # 1. RETRIEVAL TIMING
    # -----------------------------

    retrieval_start = time.perf_counter()

    chunks = hybrid_retrieve(
        request.query,
        request.document_ids
    )

    retrieval_ms = int(
        (time.perf_counter() - retrieval_start) * 1000
    )

    # -----------------------------
    # 2. LLM ANSWER TIMING
    # -----------------------------

    generation_start = time.perf_counter()

    result = generate_answer(
        request.query,
        chunks
    )

    generation_ms = int(
        (time.perf_counter() - generation_start) * 1000
    )

    # -----------------------------
    # 3. TOTAL TIMING
    # -----------------------------

    total_ms = int(
        (time.perf_counter() - total_start) * 1000
    )

    print(
        "\n========== RESEARCHMIND TIMING =========="
    )
    print(
        f"Retrieval:    {retrieval_ms} ms"
    )
    print(
        f"LLM Answer:   {generation_ms} ms"
    )
    print(
        f"Total:        {total_ms} ms"
    )
    print(
        "==========================================\n"
    )

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        grounded=result["grounded"],
        faithfulness_score=None,
        latency_ms=total_ms,
    )