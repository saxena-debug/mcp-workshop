import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# ── Load API key ──────────────────────────────────────────────
with open("config.json", "r") as f:
    config = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = config["claude_key"]

# ── Load embedding model + ChromaDB ──────────────────────────
embedder = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("company_docs")

# ── RAG Search (hardcoded directly here) ─────────────────────
def search_docs(query, n_results=3):
    query_embedding = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    return chunks, sources

# ── Ask Claude ────────────────────────────────────────────────
def ask(query):
    print(f"\n Question: {query}")
    print("-" * 50)

    # Step 1: Search docs
    chunks, sources = search_docs(query)
    context = "\n".join(chunks)

    print(f"Retrieved chunks from: {set(sources)}")
    print(f"Context:\n{context}\n")

    # Step 2: Send to Claude with context
    llm = ChatAnthropic(model="claude-opus-4-5")
    messages = [
        SystemMessage(content="You are a helpful HR assistant. Answer questions using only the context provided."),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
    ]

    response = llm.invoke(messages)
    print(f"Answer: {response.content}")

# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    ask("How many sick days do I get?")
    ask("What is the hotel limit for business travel?")
    ask("Do I need VPN to work remotely?")