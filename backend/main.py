import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import rag
import logger

app = FastAPI(title="Trinity CRE Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    history = [h.model_dump() for h in request.history]
    result = rag.query(request.message, history=history)
    logger.log(request.session_id, "user", request.message)
    logger.log(request.session_id, "assistant", result["response"])
    return ChatResponse(**result)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    history = [h.model_dump() for h in request.history]

    def generate():
        logger.log(request.session_id, "user", request.message)
        full_text = ""
        for token in rag.query_stream(request.message, history=history):
            full_text += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        logger.log(request.session_id, "assistant", full_text)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}
