import os
import json
import asyncio
import sys
import anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

with open("config.json", "r") as f:
    config = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = config["claude_key"]

claude = anthropic.Anthropic()

SERVER_PATH = "/Users/ys/Downloads/Projects/mcp-demo2/server.py"


server_params = StdioServerParameters(
    command="/Users/ys/Downloads/Projects/mcp-demo2/.venv/bin/python3",
    args=["/Users/ys/Downloads/Projects/mcp-demo2/server.py"],
    env={"PYTHONPATH": "/Users/ys/Downloads/Projects/mcp-demo2"},
    cwd="/Users/ys/Downloads/Projects/mcp-demo2"
)


async def ask(question):
    print("QUESTION|" + question, flush=True)

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                await session.initialize()
                tools_result = await session.list_tools()

                tools = []
                for tool in tools_result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })

                print("STEP|User|client.py|question received", flush=True)
                print("STEP|client.py|server.py|list_tools request", flush=True)
                print("STEP|server.py|client.py|" + str(len(tools)) + " tools returned", flush=True)
                print("STEP|client.py|Claude|question + tools list", flush=True)

                messages = [{"role": "user", "content": question}]
                response = claude.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=1024,
                    tools=tools,
                    messages=messages
                )

                while response.stop_reason == "tool_use":
                    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for tb in tool_use_blocks:
                        print("STEP|Claude|client.py|call " + tb.name, flush=True)
                        print("STEP|client.py|server.py|call_tool: " + tb.name, flush=True)

                        result = await session.call_tool(tb.name, tb.input)
                        result_text = result.content[0].text

                        if tb.name == "search_docs":
                            print("STEP|server.py|ChromaDB|vector search", flush=True)
                            print("STEP|ChromaDB|server.py|chunks returned", flush=True)

                        print("STEP|server.py|client.py|tool result ready", flush=True)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tb.id,
                            "content": result_text
                        })

                    messages.append({"role": "user", "content": tool_results})
                    print("STEP|client.py|Claude|tool_result sent", flush=True)

                    response = claude.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=1024,
                        tools=tools,
                        messages=messages
                    )

                for block in response.content:
                    if hasattr(block, "text"):
                        print("STEP|Claude|client.py|final answer ready", flush=True)
                        print("STEP|client.py|User|answer delivered", flush=True)
                        print("ANSWER|" + block.text, flush=True)

    except Exception as e:
        print("ERROR|" + str(e), flush=True)


async def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "How many sick days do I get?"
    await ask(question)

if __name__ == "__main__":
    asyncio.run(main())