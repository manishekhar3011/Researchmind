import time

from fastapi import APIRouter

from app.core.llm import generate_answer, fact_check
from app.core.retrieval import hybrid_retrieve
from app.models.schemas import EvalRunRequest, EvalRunResponse, EvalResultItem

router = APIRouter(prefix="/internal", tags=["evaluation"])


@router.post("/evaluation/run", response_model=EvalRunResponse)
async def run_evaluation(request: EvalRunRequest):
    """
    Runs each test question through the full pipeline and records retrieval +
    generation metrics. This is intentionally simple (no ground-truth relevance
    judgments yet) — it gives you faithfulness, groundedness rate, and latency
    out of the box; add precision/recall/MRR once you have a labeled chunk set
    per question (see README > Evaluation methodology).
    """
    results = []
    for q in request.questions:
        start = time.time()
        chunks = hybrid_retrieve(q.question, q.document_ids)
        gen = generate_answer(q.question, chunks)
        faithfulness = None
        if gen["grounded"]:
            fc = fact_check(gen["answer"], chunks)
            faithfulness = fc["faithfulness_score"]
        latency_ms = int((time.time() - start) * 1000)

        results.append(
            EvalResultItem(
                question=q.question,
                generated_answer=gen["answer"],
                retrieved_chunk_count=len(chunks),
                top_rerank_score=chunks[0].rerank_score if chunks else None,
                faithfulness_score=faithfulness,
                grounded=gen["grounded"],
                latency_ms=latency_ms,
            )
        )

    faithful_scores = [r.faithfulness_score for r in results if r.faithfulness_score is not None]
    return EvalRunResponse(
        results=results,
        avg_faithfulness=sum(faithful_scores) / len(faithful_scores) if faithful_scores else None,
        avg_latency_ms=sum(r.latency_ms for r in results) / len(results) if results else 0,
        grounded_rate=sum(1 for r in results if r.grounded) / len(results) if results else 0,
    )
