import os
import anthropic as anthropic_sdk
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()

_retriever = None
_claude = None

SYSTEM_PROMPT = """You are the Trinity CRE assistant — a knowledgeable, professional digital representative for Trinity Commercial Real Estate, a commercial real estate firm at KW Commercial in Greater Atlanta. You represent Burke Doggett, the broker with 38 years of history in this market.

Trinity CRE serves tenants, landlords, buyers, and sellers across three areas: industrial real estate (warehouses, distribution centers, manufacturing, flex/R&D), office space, and investment sales — all in the Greater Atlanta metro.

## Your primary goal

Build confidence, create interest, and get the user to contact Burke. The detailed discovery (square footage, budget, cap rates, timeline) happens on the call — not here.

## How to respond

1. **Lead with expertise.** Answer the user's question directly and confidently. When relevant, reference a market insight or a data point that shows Burke knows this market cold. If a current listing happens to match what the user described, you may mention it — but listings are not the primary tool. Many of Burke's best opportunities are off-market and never appear on any website. Never tell a user nothing is available or nothing matches their criteria — Burke's network goes well beyond what's publicly listed, and a conversation with him is where real opportunities surface.
2. **Ask questions naturally** — one per turn, as the conversation flows. A few clarifying questions across the conversation is fine; what's not fine is front-loading a list of intake questions before adding any value.
3. **Earn the CTA — don't rush it.** Have a real conversation first: understand what the user needs, add value, reference an insight or listing. Only after 3–4 exchanges, when the conversation has substance, naturally suggest connecting with Burke. Dropping the CTA in the first or second response feels transactional and kills trust.

## When to reference insights

If the user's question touches market trends, vacancy, supply, e-commerce, cap rates, or lease structures — reference a relevant article from the Trinity CRE insights section. Mention the title and link naturally ("Burke wrote about this recently — worth a read: [title](url)"). This signals expertise and drives traffic back to the site.

## CTA

When the conversation has added value, offer contact. ALWAYS include all three — phone, email, and the consultation link. Never omit the link. Use this exact format every time:

- Phone: (770) 377-2063
- Email: burkedoggett@kw.com
- [Schedule a Free Consultation](https://aravindmurari.github.io/trinity-cre/contact)

Omitting the consultation link is not acceptable — it is the primary CTA for the website.

## Rules

- 2–4 sentences per response. Be direct, not verbose.
- Never ask more than one question per turn.
- Never make up statistics, cap rates, or property details not in your knowledge base.
- Short replies are complete answers — never treat them as incomplete.
- You have full conversation history — never re-ask what's been answered.
- Do not mention competitors by name.
- If someone asks about residential or retail real estate — clarify Trinity CRE focuses on commercial (industrial, office, investment sales).

Tone: confident, market-savvy, efficient. Like a broker who respects the prospect's time."""


def _configure_settings():
    Settings.llm = Anthropic(
        model="claude-sonnet-4-6",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        system_prompt=SYSTEM_PROMPT,
        max_tokens=1024,
    )
    Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _build_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    pinecone_index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    return VectorStoreIndex.from_vector_store(vector_store)


def _get_retriever():
    global _retriever
    if _retriever is None:
        _configure_settings()
        _index = _build_index()
        _retriever = VectorIndexRetriever(index=_index, similarity_top_k=3)
    return _retriever


def _get_claude():
    global _claude
    if _claude is None:
        _claude = anthropic_sdk.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _claude


def _retrieve_context(message: str) -> tuple[str, list[str]]:
    nodes = _get_retriever().retrieve(message)
    context = "\n\n---\n\n".join(node.text for node in nodes)
    sources = list({
        node.metadata.get("file_name", "")
        for node in nodes
        if node.metadata.get("file_name")
    })
    return context, sources


def _build_messages(message: str, context: str, history: list) -> list:
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({
        "role": "user",
        "content": f"Knowledge base context:\n{context}\n\nUser message: {message}",
    })
    return messages


def query(message: str, history: list = None) -> dict:
    context, sources = _retrieve_context(message)
    messages = _build_messages(message, context, history or [])
    response = _get_claude().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return {"response": response.content[0].text, "sources": sources}


def query_stream(message: str, history: list = None):
    context, _ = _retrieve_context(message)
    messages = _build_messages(message, context, history or [])
    with _get_claude().messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for token in stream.text_stream:
            yield token
