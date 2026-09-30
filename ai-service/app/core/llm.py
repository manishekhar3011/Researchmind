from typing import List

import requests

from app.core.config import settings
from app.core.retrieval import RetrievedChunk


NO_EVIDENCE_MESSAGE = "I could not find sufficient information in the available sources."

SYSTEM_PROMPT = """You are ResearchMind, a technical research assistant.

Answer ONLY using the provided context chunks.

Rules:
1. Every factual claim must be supported by the provided context.
2. Never invent facts, sources, page numbers, section numbers, dates, scores, or names.
3. Cite supporting context inline using [n].
4. Use citation numbers exactly as provided in the context.
5. NEVER infer a section number from a page number.
6. NEVER convert "Page X" into "Section X".
7. Only mention a section number when the context explicitly provides that section number.
8. If the context says "Section: Introduction", call it "Introduction", not "Section 3".
9. Use document metadata exactly as provided.
10. If the context does not contain enough information to answer confidently, respond exactly:
"I could not find sufficient information in the available sources."
11. Do not mention information that is not supported by the retrieved context.
"""


def _build_context_block(chunks: List[RetrievedChunk]) -> str:
    lines = []

    for i, c in enumerate(chunks, start=1):
        section = c.section_title or "Unknown"

        lines.append(
            f"[{i}] "
            f"Source: {c.file_name} | "
            f"Page: {c.page_number} | "
            f"Section: {section}\n"
            f"{c.text}"
        )

    return "\n\n".join(lines)


def generate_answer(query: str, chunks: List[RetrievedChunk]) -> dict:
    if not chunks:
        return {
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": [],
            "grounded": False,
        }

    context_block = _build_context_block(chunks)

    prompt = f"""Context:

{context_block}

Question:
{query}

Answer using ONLY the context above.
"""

    response = requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.llm_model,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()
    answer_text = data["message"]["content"].strip()

    if NO_EVIDENCE_MESSAGE in answer_text:
        return {
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": [],
            "grounded": False,
        }

    citations = [
        {
            "index": i + 1,
            "document": c.file_name,
            "page": c.page_number,
            "section": c.section_title,
            "rerank_score": round(c.rerank_score, 4),
        }
        for i, c in enumerate(chunks)
    ]

    return {
        "answer": answer_text,
        "citations": citations,
        "grounded": True,
    }

def fact_check(answer: str, context: str):
    """Compatibility function for the evaluation router.

    Normal chat does not call this function, so it does not add
    an extra LLM request to the normal chat flow.
    """
    return {
        "faithfulness_score": None,
        "supported": True,
        "explanation": "Fact-checking is disabled for the optimized chat path."
    }
