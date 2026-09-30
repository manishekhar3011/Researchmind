from typing import List, Optional

from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: int
    file_name: str
    chunk_count: int
    status: str


class ChatRequest(BaseModel):
    query: str
    document_ids: Optional[List[int]] = None


class Citation(BaseModel):
    index: int
    document: str
    page: int
    section: str
    rerank_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    grounded: bool
    faithfulness_score: Optional[float] = None
    latency_ms: int


class EvalQuestion(BaseModel):
    question: str
    expected_answer: Optional[str] = None
    document_ids: Optional[List[int]] = None


class EvalRunRequest(BaseModel):
    questions: List[EvalQuestion]


class EvalResultItem(BaseModel):
    question: str
    generated_answer: str
    retrieved_chunk_count: int
    top_rerank_score: Optional[float]
    faithfulness_score: Optional[float]
    grounded: bool
    latency_ms: int


class EvalRunResponse(BaseModel):
    results: List[EvalResultItem]
    avg_faithfulness: Optional[float]
    avg_latency_ms: float
    grounded_rate: float
