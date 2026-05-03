import os
import json
import asyncio
import chromadb
from sentence_transformers import SentenceTransformer
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from pydantic import BaseModel

# load api key
with open("config.json", "r") as f:
    config = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = config["claude_key"]

# load embedder and chromadb
embedder = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("company_docs")

# create mcp server
server = Server("rag-server")


# pydantic models for tool inputs
class SearchInput(BaseModel):
    query: str
    n_results: int = 3


class GetDocInput(BaseModel):
    filename: str


# define tools
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_documents",
            description="List all available documents in the knowledge base",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="search_docs",
            description="Search the knowledge base using a query string",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "n_results": {"type": "integer"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_document",
            description="Get full content of a document by its filename",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string"}
                },
                "required": ["filename"]
            }
        )
    ]


# handle tool calls
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    if name == "list_documents":
        results = collection.get(include=["metadatas"])
        sources = list(set(m["source"] for m in results["metadatas"]))
        text = "Available documents: " + ", ".join(sources)
        return [types.TextContent(type="text", text=text)]

    if name == "search_docs":
        inp = SearchInput(**arguments)
        query_embedding = embedder.encode(inp.query).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=inp.n_results
        )
        chunks = results["documents"][0]
        sources = [m["source"] for m in results["metadatas"][0]]
        text = ""
        for chunk, source in zip(chunks, sources):
            text = text + "[" + source + "]: " + chunk + "\n\n"
        return [types.TextContent(type="text", text=text)]

    if name == "get_document":
        inp = GetDocInput(**arguments)
        filepath = os.path.join("docs", inp.filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                content = f.read()
            return [types.TextContent(type="text", text=content)]
        else:
            return [types.TextContent(type="text", text="File not found: " + inp.filename)]


# run the server
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())