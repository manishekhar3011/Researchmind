from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "researchmind_chunks"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    top_k_vector: int = 20
    top_k_bm25: int = 20
    top_k_final: int = 5
    min_rerank_score: float = 0.15

    ai_service_port: int = 8001

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()