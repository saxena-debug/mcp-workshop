# MCP Demo — RAG over Internal Docs

A minimal implementation of Model Context Protocol (MCP) showing how to build
a RAG system where tools are decoupled from the LLM using a standalone MCP server.

## What this project demonstrates

- The difference between a tightly coupled AI app and an MCP-based one
- How an MCP server exposes tools, independently of any LLM
- How a Claude-powered client discovers and calls those tools dynamically
- How to test MCP tools without any LLM using the MCP Inspector

## Project structure

    mcp-demo2/
    ├── config.json           ← your API key (never commit this)
    ├── config.example.json   ← template for config.json
    ├── docs/                 ← company policy documents
    │   ├── hr_policy.txt
    │   ├── it_policy.txt
    │   └── expense_policy.txt
    ├── ingest.py             ← chunk, embed and store docs in ChromaDB
    ├── without_mcp.py        ← baseline — LLM + search in one file
    ├── server.py             ← MCP server exposing 3 tools
    └── client.py             ← MCP client with Claude agentic loop


## Setup

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/mcp-demo2.git
cd mcp-demo2
```

**2. Create and activate a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your Anthropic API key**
```bash
cp config.example.json config.json
```
Open `config.json` and replace the placeholder with your actual key.

**5. Add your documents**

Place `.txt` files inside the `docs/` folder. Three sample company policy
documents are included by default.

## Run order

**Step 1 — ingest documents into ChromaDB (run once)**
```bash
python ingest.py
```

**Step 2 — run the baseline version (no MCP)**
```bash
python without_mcp.py
```

**Step 3 — test the MCP server with the Inspector (no LLM needed)**
```bash
npx @modelcontextprotocol/inspector python server.py
```
Open the browser UI, connect, and call tools directly.

**Step 4 — run the full MCP client**
```bash
python client.py
```

## MCP tools exposed by server.py

| Tool | Input | What it does |
|------|-------|--------------|
| `list_documents` | none | returns all available documents |
| `search_docs` | query (string) | vector search, returns top 3 chunks |
| `get_document` | filename (string) | returns full document content |

## Key concept

    without_mcp.py          server.py + client.py
    ─────────────────       ─────────────────────────
    LLM + search            LLM lives in client.py
    in one file             Tools live in server.py
    tightly coupled         fully decoupled
    copy to reuse           point to server to reuse