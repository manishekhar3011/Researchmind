-- ResearchMind database schema
-- Applied automatically by the postgres docker image on first container start
-- (mounted into /docker-entrypoint-initdb.d/). Spring Boot's ddl-auto=update
-- will also reconcile any drift, but this file is the canonical reference.

CREATE TABLE IF NOT EXISTS app_user (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,
    storage_path    VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    chunk_count     INT DEFAULT 0,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_document_user ON document(user_id);
CREATE INDEX IF NOT EXISTS idx_document_status ON document(status);

CREATE TABLE IF NOT EXISTS document_chunk (
    id              BIGSERIAL PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    qdrant_point_id UUID NOT NULL,
    chunk_index     INT NOT NULL,
    page_number     INT,
    section_title   VARCHAR(255),
    content_preview VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunk_document ON document_chunk(document_id);

CREATE TABLE IF NOT EXISTS conversation (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    title           VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversation(user_id);

CREATE TABLE IF NOT EXISTS message (
    id                  BIGSERIAL PRIMARY KEY,
    conversation_id     BIGINT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role                VARCHAR(10) NOT NULL,
    content             TEXT NOT NULL,
    citations           JSONB,
    agent_used          VARCHAR(50),
    latency_ms          INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_message_conversation ON message(conversation_id);

CREATE TABLE IF NOT EXISTS evaluation_result (
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
CREATE INDEX IF NOT EXISTS idx_eval_run_at ON evaluation_result(run_at);
