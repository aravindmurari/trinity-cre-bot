import os
import anthropic
import voyageai
from pinecone import Pinecone
from dotenv import load_dotenv
from config import MODEL, TOP_K, SYSTEM_PROMPT

load_dotenv()

_client: anthropic.Anthropic | None = None
_voyage: voyageai.Client | None = None
_pinecone_index = None


def _get_voyage() -> voyageai.Client:
    global _voyage
    if _voyage is None:
        _voyage = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _voyage


def _get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        _pinecone_index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    return _pinecone_index


def _retrieve_context(message: str) -> str:
    result = _get_voyage().embed([message], model="voyage-3-lite", input_type="query")
    query_embedding = result.embeddings[0]
    matches = _get_pinecone_index().query(
        vector=query_embedding, top_k=TOP_K, include_metadata=True
    ).matches
    chunks = [m.metadata["text"] for m in matches if m.metadata.get("text")]
    return "\n\n---\n\n".join(chunks)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _build_messages(message: str, context: str, history: list) -> list:
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({
        "role": "user",
        "content": f"Relevant context:\n{context}\n\nUser message: {message}",
    })
    return messages


def query(message: str, history: list = None) -> dict:
    context = _retrieve_context(message)
    messages = _build_messages(message, context, history or [])
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return {"response": response.content[0].text, "sources": []}


def query_stream(message: str, history: list = None):
    context = _retrieve_context(message)
    messages = _build_messages(message, context, history or [])
    with _get_client().messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for token in stream.text_stream:
            yield token
