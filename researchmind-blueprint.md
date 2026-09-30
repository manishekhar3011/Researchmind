# ResearchMind — Architecture, DB Schema & API Design Blueprint

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                             │
│                    React + Tailwind (SPA, JWT stored in memory)       │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ REST/JSON + SSE (streaming)
┌───────────────────────────────▼─────────────────────────────────────┐
│                      BACKEND (Spring Boot) — Orchestration Layer      │
│  - Auth (JWT), User/Doc/Conversation CRUD, Postgres persistence       │
│  - Delegates all AI work to ai-service over internal REST             │
│  - Owns "source of truth" for users, documents, chat history, evals   │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ Internal REST (service-to-service)
┌───────────────────────────────▼─────────────────────────────────────┐
│                    AI-SERVICE (FastAPI) — RAG + Agent Layer           │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐     │
│  │  Ingestion  │ │   Retrieval   │ │   Agents   │ │  Evaluation │     │
│  │  Pipeline   │ │  (Hybrid+     │ │  (Router,  │ │   Harness   │     │
│  │             │ │   Reranker)   │ │  Research, │ │             │     │
│  │             │ │               │ │  WebSearch,│ │             │     │
│  │             │ │               │ │  Summarize,│ │             │     │
│  │             │ │               │ │  FactCheck,│ │             │     │
│  │             │ │               │ │  Citation) │ │             │     │
│  └─────────────┘ └──────────────┘ └────────────┘ └─────────────┘     │
└──────┬───────────────────┬─────────────────┬───────────────┬────────┘
       │                   │                 │               │
┌──────▼──────┐    ┌───────▼──────┐   ┌──────▼─────┐  ┌──────▼──────┐
│  PostgreSQL │    │    Qdrant     │   │  LLM API   │  │  Web Search │
│ (users,docs,│    │ (chunk vectors│   │ (generation│  │  API (agent │
│  chat, eval)│    │  + metadata)  │   │ + judge)   │  │  fallback)  │
└─────────────┘    └──────────────┘   └────────────┘  └─────────────┘
```

**Why split Spring Boot / FastAPI this way:**
- Spring Boot = durable state, auth, multi-tenancy, transactional integrity (things the JVM ecosystem is strong at)
- FastAPI = ML/AI orchestration, async I/O to LLM + vector DB, where the Python ecosystem (LangChain/LlamaIndex, Sentence Transformers) lives
- Spring Boot never talks to Qdrant or the LLM directly — it always proxies through ai-service. This keeps AI logic swappable/testable independently and mirrors real org boundaries (platform team vs. ML team).

---

## 2. RAG Pipeline Design (ai-service internals)

```
Upload → Parse → Clean → Chunk (metadata-aware) → Embed → Upsert to Qdrant
                                                              │
User Query → Query Router ─────────────────────────────┬─────┘
                 │                                      │
        ┌────────┴─────────┐                    Hybrid Retrieval
        │                  │                (BM25 + vector, RRF fusion)
   [Research Agent]   [WebSearch Agent]                 │
   (internal KB)      (KB insufficient)            Reranker (cross-encoder)
        │                  │                              │
        └────────┬─────────┘                      Context Builder
                 │                                        │
          Context Validator ◄───────────────────────────┘
          (min score threshold; if fails → "insufficient evidence")
                 │
          LLM Generation (streaming)
                 │
          Fact-Checking Agent (entailment check vs. retrieved chunks)
                 │
          Citation Agent (attach doc/page/section)
                 │
          Final Answer + Citations → Backend → Client (SSE stream)
```

**Query Router logic (rule-based + LLM fallback, keep it simple to start):**
1. Is this a summarization request? → Summarization Agent
2. Else: retrieve from KB → if top reranked score < threshold → WebSearch Agent → merge/flag as external source
3. Else: Research Agent (standard RAG path)

This router is intentionally simple at v1 — it's the most defensible "agentic" claim if you can clearly explain the decision logic and show it branching in a demo/eval.

---

## 3. Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE app_user (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documents
CREATE TABLE document (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,          -- PDF, DOCX, TXT, URL
    storage_path    VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, READY, FAILED
    chunk_count     INT DEFAULT 0,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_document_user ON document(user_id);
CREATE INDEX idx_document_status ON document(status);

-- Document Chunks (metadata lives here; vectors live in Qdrant, linked by chunk_id)
CREATE TABLE document_chunk (
    id              BIGSERIAL PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    qdrant_point_id UUID NOT NULL,                 -- points to vector in Qdrant
    chunk_index     INT NOT NULL,
    page_number     INT,
    section_title   VARCHAR(255),
    content_preview VARCHAR(500),                  -- first N chars, for admin UI
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chunk_document ON document_chunk(document_id);

-- Conversations
CREATE TABLE conversation (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    title           VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_conversation_user ON conversation(user_id);

-- Messages
CREATE TABLE message (
    id                  BIGSERIAL PRIMARY KEY,
    conversation_id     BIGINT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role                VARCHAR(10) NOT NULL,       -- USER, ASSISTANT
    content             TEXT NOT NULL,
    citations           JSONB,                       -- [{document, page, section, score}]
    agent_used          VARCHAR(50),                 -- RESEARCH, WEB_SEARCH, SUMMARY
    latency_ms          INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_message_conversation ON message(conversation_id);

-- Evaluation Results
CREATE TABLE evaluation_result (
    id                  BIGSERIAL PRIMARY KEY,
    test_question       TEXT NOT NULL,
    expected_answer     TEXT,
    generated_answer    TEXT,
    retrieval_precision NUMERIC(5,4),
    retrieval_recall    NUMERIC(5,4),
    mrr                 NUMERIC(5,4),
    context_relevance   NUMERIC(5,4),
    faithfulness        NUMERIC(5,4),
    citation_accuracy   NUMERIC(5,4),
    response_time_ms    INT,
    run_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_eval_run_at ON evaluation_result(run_at);
```

**Design notes:**
- Vectors stay in Qdrant, not Postgres — `qdrant_point_id` is the bridge. Never duplicate embeddings in relational storage.
- `citations` and per-message `agent_used`/`latency_ms` are what let your evaluation dashboard and resume-bullet metrics actually be computed from real logged data, not hand-waved.
- `evaluation_result` is append-only — you build a history of runs, so you can show "faithfulness improved from run N to run N+10 after adding reranker."

---

## 4. API Design

### Auth (Spring Boot)
```
POST /api/auth/register        { email, password, displayName } → 201
POST /api/auth/login           { email, password } → { token, expiresAt }
POST /api/auth/logout          (invalidate/blacklist token if using a denylist)
```

### Documents (Spring Boot → proxies ingestion to ai-service)
```
POST   /api/documents/upload         multipart file → { documentId, status: PENDING }
GET    /api/documents                ?status=&type=&search= → paginated list
GET    /api/documents/{id}           → document detail incl. chunkCount, status
DELETE /api/documents/{id}           → 204 (cascades chunks + Qdrant points)
```

### Chat (Spring Boot → ai-service, SSE passthrough)
```
POST /api/chat                       { conversationId?, message, documentIds? }
                                      → SSE stream: token chunks, then final
                                        { answer, citations[], agentUsed, latencyMs }
GET  /api/conversations              → list, paginated
GET  /api/conversations/{id}         → full message history
DELETE /api/conversations/{id}       → clear conversation
```

### Research / Agents (ai-service, exposed via backend)
```
POST /api/research                   { query, documentIds? } → agent-routed answer
POST /api/research/summarize         { documentId } → summary
```

### Evaluation (ai-service, exposed via backend, admin-only)
```
POST /api/evaluation/run             { testSetId? } → triggers batch eval run
GET  /api/evaluation/results         ?from=&to= → aggregated metrics + history
GET  /api/evaluation/results/{runId} → per-question breakdown
```

**Internal-only (ai-service, not exposed to frontend directly):**
```
POST /internal/ingest                Spring Boot → ai-service, on upload
POST /internal/retrieve              query → hybrid+reranked chunks (used by /chat, /research)
POST /internal/embed                 batch embedding generation
```

All public endpoints require `Authorization: Bearer <jwt>` except `/api/auth/*`. Document- and conversation-scoped endpoints enforce `user_id` ownership at the Spring Boot repository layer (never trust a client-supplied user id).

---

## 5. Suggested Build Order (module-by-module)

1. **Postgres schema + Spring Boot entities/repositories** (fast, mechanical, unblocks everything else)
2. **Auth (JWT register/login)**
3. **Ingestion pipeline in ai-service**: parse → chunk → embed → Qdrant upsert (the highest-value module to get right)
4. **Hybrid retrieval + reranker** — this is what your "precision@k / recall@k" resume metrics come from
5. **Query router + Research Agent** (basic version first, WebSearch/Summarize/FactCheck/Citation agents layered in after)
6. **Chat endpoint with streaming + citations**
7. **Evaluation harness** (build this early against a small hand-labeled test set — even 15-20 Q&A pairs — so every later change has a before/after number)
8. **React chat UI**, then **document management UI**, then **evaluation dashboard UI**
9. **Docker Compose** wiring it all together — last, once each service runs standalone

Next natural step is #3 — the ingestion pipeline — since it's the foundation everything else depends on and it's where "metadata-aware chunking" (a specific claim in your resume bullet) actually gets implemented.
