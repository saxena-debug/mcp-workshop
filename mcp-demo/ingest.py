import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

# ── Load API key ──────────────────────────────────────────────
with open("config.json", "r") as f:
    config = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = config["claude_key"]

# ── Setup ─────────────────────────────────────────────────────
DOCS_FOLDER = "docs"
CHROMA_PATH = "chroma_db"

# Load embedding model (runs locally, no API needed)
print("Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Setup ChromaDB (local vector store saved to disk)
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Delete collection if it already exists (clean re-run)
try:
    client.delete_collection("company_docs")
except:
    pass

collection = client.create_collection("company_docs")

# ── Read + Chunk + Embed ──────────────────────────────────────
print("Reading documents...")

for filename in os.listdir(DOCS_FOLDER):
    if filename.endswith(".txt"):
        filepath = os.path.join(DOCS_FOLDER, filename)

        with open(filepath, "r") as f:
            content = f.read()

        # Split into chunks by line (simple chunking strategy)
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        for i, chunk in enumerate(lines):
            embedding = embedder.encode(chunk).tolist()
            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"source": filename, "chunk_id": i}],
                ids=[f"{filename}_{i}"]
            )
            print(f"Indexed: [{filename}] chunk {i} → '{chunk[:50]}...'")

print(f"\nDone! {collection.count()} chunks stored in ChromaDB")