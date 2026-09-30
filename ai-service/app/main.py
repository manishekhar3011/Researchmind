from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ingest, chat, evaluation

app = FastAPI(title="ResearchMind AI Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(evaluation.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-service"}
