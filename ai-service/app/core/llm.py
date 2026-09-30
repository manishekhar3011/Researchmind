from typing import List
import json
import re
import requests

from app.core.config import settings
from app.core.retrieval import RetrievedChunk


NO_EVIDENCE_MESSAGE = (
    "I could not find sufficient information in the available sources."
)


SYSTEM_PROMPT = """You are ResearchMind, a technical research assistant.

Answer ONLY using the provided context chunks.

Rules:
1. Every factual claim must be supported by the provided context.
2. Never invent facts, sources, page numbers, or sections.
3. When you use information from a chunk, cite it inline as [n].
4. If the context does not contain enough information to answer confidently,
respond with exactly:
"I could not find sufficient information in the available sources."
5. Keep the answer clear and useful.
"""


def _build_context_block(chunks: List[RetrievedChunk]) -> str:
    lines = []

    for i, c in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] (Source: {c.file_name}, "
            f"Page {c.page_number}, "
            f"Section: {c.section_title})\n"
            f"{c.text}"
        )

    return "\n\n".join(lines)


def _ollama_generate(
    prompt: str,
    system: str = "",
    max_tokens: int = 800,
) -> str:

    payload = {
        "model": settings.llm_model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "num_predict": max_tokens
        },
    }

    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("response", "").strip()


def generate_answer(query: str, chunks: List[RetrievedChunk]) -> dict:

    if not chunks:
        return {
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": [],
            "grounded": False,
        }

    context_block = _build_context_block(chunks)

    user_prompt = (
        f"Context:\n\n"
        f"{context_block}\n\n"
        f"Question:\n{query}\n\n"
        f"Answer using ONLY the context above."
    )

    answer_text = _ollama_generate(
        prompt=user_prompt,
        system=SYSTEM_PROMPT,
        max_tokens=800,
    )

    if not answer_text:
        answer_text = NO_EVIDENCE_MESSAGE

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

    is_grounded = (
        answer_text.strip() != NO_EVIDENCE_MESSAGE
        and len(answer_text.strip()) > 0
    )

    return {
        "answer": answer_text,
        "citations": citations if is_grounded else [],
        "grounded": is_grounded,
    }


def fact_check(answer: str, chunks: List[RetrievedChunk]) -> dict:
    """
    Check whether the generated answer is supported by the retrieved
    source context.

    Returns:
        faithfulness_score:
            Float between 0.0 and 1.0 if the judge successfully responds.

            None if the judge fails or returns invalid JSON.

        verdict:
            Short explanation returned by the judge.
    """

    if not chunks:
        return {
            "faithfulness_score": None,
            "verdict": "no evidence provided",
        }

    context_block = _build_context_block(chunks)

    judge_prompt = f"""
Evaluate whether the candidate answer is supported by the source context.

IMPORTANT RULES:
- Use ONLY the SOURCE CONTEXT.
- Do not use outside knowledge.
- Check every factual claim in the candidate answer.
- A claim is supported if it is directly stated or clearly supported
  by the source context.
- 1.0 means fully supported.
- 0.0 means completely unsupported.
- Return a score between 0.0 and 1.0.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add text before or after the JSON.

Return exactly this structure:

{{"score": 0.0, "verdict": "short explanation"}}

SOURCE CONTEXT:
{context_block}

CANDIDATE ANSWER:
{answer}
"""

    try:
        raw = _ollama_generate(
            prompt=judge_prompt,
            system=(
                "You are a strict research fact-checking system. "
                "Return ONLY valid JSON."
            ),
            max_tokens=150,
        )

        raw = raw.strip()

        # Remove accidental Markdown code fences.
        if raw.startswith("```"):
            raw = re.sub(
                r"^```(?:json)?\s*",
                "",
                raw,
                flags=re.IGNORECASE,
            )

            raw = re.sub(
                r"\s*```$",
                "",
                raw,
            )

            raw = raw.strip()

        # Try to extract a JSON object if the model added extra text.
        if not raw.startswith("{"):
            match = re.search(r"\{.*\}", raw, re.DOTALL)

            if match:
                raw = match.group(0)

        parsed = json.loads(raw)

        score = parsed.get("score")

        if score is None:
            return {
                "faithfulness_score": None,
                "verdict": "judge did not return a score",
            }

        score = float(score)

        # Keep score safely inside 0-1.
        score = max(0.0, min(1.0, score))

        verdict = str(
            parsed.get(
                "verdict",
                "answer evaluated against retrieved context",
            )
        )

        return {
            "faithfulness_score": score,
            "verdict": verdict,
        }

    except json.JSONDecodeError:
        return {
            "faithfulness_score": None,
            "verdict": "judge returned invalid JSON",
        }

    except requests.RequestException as exc:
        return {
            "faithfulness_score": None,
            "verdict": f"judge request failed: {type(exc).__name__}",
        }

    except Exception as exc:
        return {
            "faithfulness_score": None,
            "verdict": f"judge failed: {type(exc).__name__}",
        }