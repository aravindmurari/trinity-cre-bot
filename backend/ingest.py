"""
Run once to chunk knowledge files and load them into Pinecone.
Re-run any time you add or edit knowledge files.

Usage:
    cd backend
    venv/bin/python3 ingest.py
"""
import os
import glob
import time
import voyageai
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 800    # characters per chunk
CHUNK_OVERLAP = 100


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c]


def ingest():
    vo = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index_name = os.environ["PINECONE_INDEX_NAME"]

    # Recreate index with 512 dims (voyage-3-lite)
    existing = [i.name for i in pc.list_indexes()]
    if index_name in existing:
        print(f"Deleting existing index '{index_name}'...")
        pc.delete_index(index_name)
        time.sleep(5)

    print(f"Creating index '{index_name}' (512 dims, cosine)...")
    pc.create_index(
        name=index_name,
        dimension=512,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    time.sleep(5)
    index = pc.Index(index_name)

    # Load and chunk all knowledge files
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    all_chunks = []
    all_meta = []

    for path in sorted(glob.glob(os.path.join(knowledge_dir, "*.md"))):
        filename = os.path.basename(path)
        with open(path) as f:
            text = f.read()
        chunks = chunk_text(text)
        print(f"  {filename}: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_meta.append({"file": filename, "text": chunk})

    # Embed in small batches (free tier = 3 RPM, so pause between batches)
    print(f"\nEmbedding {len(all_chunks)} chunks via Voyage AI...")
    all_embeddings = []
    batch_size = 10
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        result = vo.embed(batch, model="voyage-3-lite", input_type="document")
        all_embeddings.extend(result.embeddings)
        print(f"  Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")
        if i + batch_size < len(all_chunks):
            time.sleep(22)  # stay within 3 RPM free tier limit

    # Upsert to Pinecone in batches of 100
    print("\nUpserting to Pinecone...")
    vectors = [
        {"id": f"chunk-{i}", "values": emb, "metadata": meta}
        for i, (emb, meta) in enumerate(zip(all_embeddings, all_meta))
    ]
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i + 100])

    print(f"\nDone. {len(vectors)} chunks indexed in '{index_name}'.")


if __name__ == "__main__":
    ingest()
