from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_model: str = "gpt-oss:120b"
    ollama_base_url: str = "https://ollama.com"
    ollama_api_key: str = ""

    # Qdrant Cloud
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # Local Qdrant fallback
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Collection
    qdrant_collection: str = "researchmind_chunks"

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Retrieval
    top_k_vector: int = 10
    top_k_bm25: int = 10
    top_k_final: int = 5
    min_rerank_score: float = 0.15

    # Service
    ai_service_port: int = 8001

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()