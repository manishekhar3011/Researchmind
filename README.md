# ResearchMind — Agentic RAG-Based Technical Research Assistant

An AI research assistant that answers questions over your own technical documents (PDF/DOCX/TXT) using **Retrieval-Augmented Generation** — hybrid search, reranking, source citations, and hallucination-resistant generation — instead of relying on the LLM's memorized knowledge.

> **Read this first:** this repo is a working **core MVP**, not the full 8-agent, full-dashboard system described in an original spec. What's here is real and runs end-to-end: ingestion, hybrid retrieval, reranking, grounded generation with citations, a fact-check pass, basic auth, chat, and a batch evaluation endpoint. See **"What's simplified"** near the bottom before you present this as a finished product — and treat that section as your actual next milestones.

---

## 1. Problem Statement

Plain LLM chat answers technical questions from memory, which means it can be outdated, generic, or simply wrong for a specific corpus (your company's docs, a set of papers, internal specs). ResearchMind grounds every answer in retrieved passages from documents you control, tells you the exact page/section it came from, and explicitly says "I don't know" rather than inventing an answer when evidence is weak.

## 2. Features

- Upload PDF / DOCX / TXT documents
- Metadata-aware chunking (paragraph-boundary aware, tracks page number + detected section heading per chunk)
- Hybrid retrieval: BM25 (keyword) + dense vector search, fused with Reciprocal Rank Fusion
- Cross-encoder reranking before any chunk reaches the LLM
- Minimum-score gate: if nothing clears the bar, the system says so instead of guessing
- Source-grounded generation with inline citations (`[1]`, `[2]`, ...) mapped to document/page/section
- A second-pass LLM-as-judge fact-check that scores faithfulness of the generated answer against retrieved context
- JWT auth, per-user document/conversation isolation
- Chat UI with conversation history, streaming-ready backend contract
- Batch evaluation endpoint: run a set of test questions through the full pipeline and get faithfulness/groundedness/latency back

## 3. Architecture

See `researchmind-blueprint.md` (shared earlier in this conversation) for the full architecture diagram, RAG pipeline flow, DB schema and API design. Summary:

```
React (frontend) → Spring Boot (backend: auth, persistence, orchestration)
                        → FastAPI (ai-service: parsing, chunking, embeddings,
                                    hybrid retrieval, reranking, generation, eval)
                              → Qdrant (vectors)     → PostgreSQL (users, docs, chat, eval)
                              → Ollama (local LLM)
```

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Tailwind CSS, Vite |
| Backend | Java 25, Spring Boot 3, Spring Security (JWT), Spring Data JPA |
| AI Service | Python 3.11, FastAPI, Sentence-Transformers, rank-bm25, Qdrant client, Ollama |
| Databases | PostgreSQL 16 (relational), Qdrant (vectors) |
| Deployment | Docker, Docker Compose |

---

## 5. Running it in VS Code

You have two options. **Option A (Docker Compose)** is the fastest path to "it just works." **Option B (run each service natively)** is better while you're actively developing/debugging one service, since you get hot-reload and real breakpoints in VS Code.

### Option A — Docker Compose (recommended first run)

**Prerequisites:** Docker Desktop installed and running.

```bash
# from the researchmind/ root
cp .env.example .env
# make sure Ollama is running with llama3.2:3b

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend Swagger docs: http://localhost:8080/swagger-ui.html
- ai-service docs: http://localhost:8001/docs
- Qdrant dashboard: http://localhost:6333/dashboard

First build downloads the embedding + reranker models (~200-300MB) inside the ai-service container, so the first `docker compose up` will take a few minutes longer than subsequent ones.

### Option B — Run natively in VS Code (for active development)

**1. Start just the data layer with Docker:**
```bash
docker compose up postgres qdrant
```

**2. ai-service** (VS Code: open `ai-service/` folder, use the Python extension)
```bash
cd ai-service
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env             # configure Ollama settings
uvicorn app.main:app --reload --port 8001
```

**3. backend** (VS Code: open `backend/` folder, use the Java Extension Pack / Spring Boot Extension Pack)
```bash
cd backend
export DB_HOST=localhost AI_SERVICE_URL=http://localhost:8001 JWT_SECRET=your-long-random-secret
mvn spring-boot:run
```
Or just hit **Run** on `BackendApplication.java` from VS Code once the extensions are installed — set the same env vars in a `.vscode/launch.json` env block.

**4. frontend**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

---

## 6. Environment Variables

**`ai-service/.env`**
```
LLM_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=researchmind_chunks
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOP_K_VECTOR=20
TOP_K_BM25=20
TOP_K_FINAL=5
MIN_RERANK_SCORE=0.15
```

**`backend` (env vars, e.g. via `.env` + `mvn spring-boot:run` or your run config)**
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=researchmind
DB_USER=researchmind
DB_PASSWORD=change-this-password
JWT_SECRET=change-this-to-a-long-random-secret-in-production-min-32-chars
AI_SERVICE_URL=http://localhost:8001
```

**`frontend/.env`**
```
VITE_API_BASE_URL=http://localhost:8080
```

---

## 7. API Reference

Full request/response shapes are in `researchmind-blueprint.md`. Quick reference:

```
POST /api/auth/register        { email, password, displayName } → { token, userId, ... }
POST /api/auth/login           { email, password } → { token, userId, ... }

POST /api/documents/upload     multipart file → DocumentResponse
GET  /api/documents            → DocumentResponse[]
DELETE /api/documents/{id}

POST /api/chat                 { message, conversationId?, documentIds? } → ChatResponse (answer + citations)
GET  /api/conversations
GET  /api/conversations/{id}
```

Swagger UI (once backend is running): `http://localhost:8080/swagger-ui.html`
FastAPI interactive docs (ai-service): `http://localhost:8001/docs`

---

## 8. Evaluation Methodology

`POST /internal/evaluation/run` on ai-service (call it directly, or wire a backend/admin route to it) takes a list of `{question, documentIds?}` and returns, per question:

- **Groundedness** — did the system answer at all, or correctly say "insufficient information"?
- **Faithfulness score** (0-1) — an LLM-as-judge pass checks whether the generated answer's claims are actually supported by the retrieved chunks
- **Top rerank score** — signal for retrieval quality on that query
- **Latency (ms)**

**What's NOT included yet, and is your natural next step:** true retrieval precision/recall/MRR require a hand-labeled set of "which chunk IDs are actually relevant" per test question. Build a 15-20 question test set once you have real documents loaded, label the correct chunk(s) for each by hand, and extend `evaluation.py` to compute precision@k/recall@k/MRR against those labels. That's what turns "we have an eval framework" into "we measured X% retrieval precision," which is the number your resume bullet needs.

### Sample test questions (swap in your own once real docs are loaded)
```
"What is the main contribution of this paper?"
"What dataset was used for evaluation?"
"What are the reported latency numbers?"
"How does this approach compare to the previous version?"
"What are the stated limitations of this method?"
```

---

## 9. What's Simplified (be upfront about this in interviews)

- **Agent architecture**: the spec called for 5 separate agents (Research, WebSearch, Summarization, FactChecking, Citation). This build has a real fact-check pass and citation logic, but the "router" is a straight retrieval pipeline — there's no WebSearch fallback or Summarization agent yet, and no branching logic beyond the retrieval-confidence gate. Adding a real router (e.g., an LLM call that picks a tool given the query + retrieval confidence) is the highest-value next addition if you want to defend the word "agentic" under questioning.
- **Evaluation dashboard**: the backend/AI-service expose the metrics; there's no dedicated React admin dashboard page yet rendering charts over time — `/internal/evaluation/run` returns the data, but you'd add a `EvaluationDashboard.jsx` page to visualize it.
- **Streaming**: the backend contract is streaming-ready (SSE was in the original design) but the current `/api/chat` implementation returns a single JSON response rather than token-by-token SSE. Swapping to `StreamingResponseBody` in Spring Boot + `text/event-stream` in FastAPI is a contained follow-up.
- **Tests**: no automated test suite yet (unit/integration/e2e). Given how the modules are separated (parsing, chunking, retrieval, generation are all pure-ish functions), they're straightforward to unit test — that's a good next task.

---

## 10. Resume Bullet Points (once you've run real evals and have real numbers)

> Replace the bracketed placeholders with your own measured numbers from `/internal/evaluation/run` before using these.

- Built ResearchMind, an agentic RAG platform combining hybrid retrieval (BM25 + dense vectors, RRF fusion), cross-encoder reranking, and source-grounded generation, using hybrid retrieval, cross-encoder reranking, and source-grounded generation for technical Q&A.
- Designed a metadata-aware ingestion pipeline (PDF/DOCX/TXT) with paragraph-boundary chunking and section-aware metadata, storing embeddings in Qdrant and reducing unsupported/hallucinated answers via a minimum-confidence retrieval gate.
- Implemented a full-stack architecture (React, Spring Boot, FastAPI) with JWT authentication, per-user data isolation, and Docker Compose deployment across 5 services (frontend, backend, AI service, PostgreSQL, Qdrant).
- Built an automated RAG evaluation harness measuring answer faithfulness, groundedness rate, and end-to-end latency, enabling before/after comparison across retrieval configuration changes.

## 11. 10 Likely Interview Questions (with how to answer them from this codebase)

1. **"Walk me through what happens when a user asks a question."**
   Query → `hybrid_retrieve()` runs BM25 + vector search in parallel → RRF fusion merges the two ranked lists → cross-encoder reranks the fused candidates → chunks below `MIN_RERANK_SCORE` are dropped → remaining chunks go into the LLM prompt with a strict "answer only from context" system prompt → a second LLM call fact-checks the answer against the same chunks → citations are attached from chunk metadata.

2. **"Why hybrid retrieval instead of just vector search?"**
   Dense vectors are great at semantic similarity but weak on exact terms (model names, version numbers, acronyms) that BM25 catches directly. RRF fusion lets you get both without needing to tune a single blended score.

3. **"How do you prevent hallucination?"**
   Two layers: (1) a retrieval-confidence gate — if nothing clears `MIN_RERANK_SCORE`, the system returns "insufficient information" instead of generating; (2) a fact-check pass — after generation, a second LLM call scores whether the answer's claims are entailed by the retrieved chunks (`faithfulness_score`). Be honest that this fact-check is currently LLM-as-judge, not a dedicated NLI model — name that as a known limitation and the natural upgrade path.

4. **"Is this actually 'agentic'? What decisions does the agent make?"**
   Right now: an implicit decision at the retrieval-confidence gate (answer vs. decline). Be upfront that the multi-agent router (WebSearch fallback, Summarization agent) described in the original spec isn't built yet — this is the honest answer and the strongest thing to say you'd build next.

5. **"How would you evaluate retrieval quality specifically, separate from generation quality?"**
   Precision@k / Recall@k / MRR against a hand-labeled "relevant chunk IDs per question" set — explain why you need ground truth for that (see Evaluation Methodology section) and that the current harness only measures faithfulness/groundedness/latency, not retrieval precision, until that labeled set exists.

6. **"Why split Spring Boot and FastAPI instead of one service?"**
   Separation of concerns: Spring Boot owns durable state, auth and multi-tenancy (JVM ecosystem strength); FastAPI owns ML orchestration (Python ecosystem for embeddings/rerankers/LangChain-style tooling). It also mirrors how many real orgs split platform vs. ML teams, and lets you scale/deploy the AI service independently (e.g., on GPU nodes) from the stateless API layer.

7. **"How do you handle a user querying documents that aren't theirs?"**
   Every document/conversation query goes through `findByIdAndUserId` at the repository layer — ownership is enforced in the query itself, not just in a controller-level check, so there's no path that returns another user's row.

8. **"What happens if the LLM API call fails or times out?"**
   Currently a `ResponseStatusException` (502) bubbles up in `DocumentService`/`ChatService` — mention this as a real weakness (no retry/backoff yet) and that you'd add exponential backoff + a circuit breaker (Resilience4j is the natural Spring Boot fit) as a production hardening step.

9. **"Why chunk on paragraph boundaries instead of fixed token windows?"**
   Fixed-size slicing can cut a sentence or table row in half, which both hurts embedding quality and produces citations that point to a fragment instead of a coherent passage. Paragraph-aware chunking with overlap keeps chunks semantically coherent at a small cost in exact size control — a reasonable trade-off to name explicitly.

10. **"How would this scale to millions of documents?"**
    Qdrant shards natively; the bottleneck would more likely be the BM25 step, since the current implementation rebuilds a `BM25Okapi` index from a full `scroll()` of all matching chunks on every query — fine for a demo, but you'd want a persistent BM25/inverted index (e.g., Elasticsearch/OpenSearch) or a precomputed sparse index at real scale. Naming this limitation directly is a strong answer.

---

## 12. Future Improvements

- Real multi-agent router (WebSearch fallback, Summarization agent) with an LLM-driven tool-selection step
- Retrieval precision/recall/MRR against a labeled test set
- Streaming responses (SSE end-to-end)
- Persistent BM25 index instead of per-query rebuild
- Automated test suite (unit + integration + e2e)
- Evaluation dashboard UI with historical trend charts
- Retry/backoff + circuit breaker around all ai-service calls









