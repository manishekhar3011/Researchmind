from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.chunking import chunk_pages
from app.core.embeddings import embed_texts
from app.core.parsing import parse_document
from app.core.vectorstore import upsert_chunks, delete_document_vectors
from app.models.schemas import IngestResponse

router = APIRouter(prefix="/internal", tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    document_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Called by the Spring Boot backend AFTER it has created the Document row
    in Postgres and knows the document_id. This keeps Postgres as the source
    of truth for the id, while ai-service owns everything downstream of it.
    """
    file_type = file.filename.split(".")[-1].lower()
    if file_type not in ("pdf", "docx", "txt"):
        raise HTTPException(400, f"Unsupported file type: {file_type}")

    file_bytes = await file.read()

    try:
        pages = parse_document(file_bytes, file_type)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse document: {e}")

    if not pages:
        raise HTTPException(400, "No extractable text found in document")

    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(400, "Chunking produced no chunks")

    vectors = embed_texts([c.text for c in chunks])
    upsert_chunks(document_id, chunks, vectors, file.filename)

    return IngestResponse(
        document_id=document_id,
        file_name=file.filename,
        chunk_count=len(chunks),
        status="READY",
    )


@router.delete("/ingest/{document_id}")
async def delete_document(document_id: int):
    delete_document_vectors(document_id)
    return {"status": "deleted", "document_id": document_id}
