import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException

from app import config
from app.models import ChatRequest, ChatResponse, UploadResponse, SourceChunk
from app.rag import ingest, retriever, llm

app = FastAPI(title="RAG Agent")


@app.on_event("startup")
def startup():
    ingest.load_index()


@app.get("/health")
def health():
    total = 0 if ingest._index is None else ingest._index.ntotal
    return {"status": "ok", "chunks_indexed": total}


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    dest = config.UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    added, total = ingest.ingest_pdf(dest, file.filename)
    return UploadResponse(filename=file.filename, chunks_added=added, total_chunks=total)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    chunks = retriever.search(req.question, req.top_k)
    answer = llm.generate_answer(req.question, chunks)
    sources = [SourceChunk(**c) for c in chunks]
    return ChatResponse(answer=answer, sources=sources)
