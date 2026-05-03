import os
import json
import asyncio
import anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

# load api key
with open("config.json", "r") as f:
    config = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = config["claude_key"]

# anthropic client
claude = anthropic.Anthropic()

# tell the mcp client how to start the server
server_params = StdioServerParameters(
    command="python",
    args=["server.py"]
)


async def ask(question):
    print("Question: " + question)
    print("-" * 50)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # step 1 - connect and discover tools from server
            await session.initialize()
            tools_result = await session.list_tools()

            # convert mcp tool format to anthropic tool format
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })

            print("tools discovered: " + str([t["name"] for t in tools]))

            # step 2 - send question + tools to claude
            messages = [{"role": "user", "content": question}]

            response = claude.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                tools=tools,
                messages=messages
            )

            # step 3 - agentic loop
            while response.stop_reason == "tool_use":

                # collect ALL tool calls claude made in this response
                tool_use_blocks = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_use_blocks.append(block)

                # add claude's full response to messages
                messages.append({"role": "assistant", "content": response.content})

                # execute every tool call and collect all results
                tool_results = []
                for tool_use_block in tool_use_blocks:
                    tool_name = tool_use_block.name
                    tool_input = tool_use_block.input

                    print("claude wants to call: " + tool_name)
                    print("with input: " + str(tool_input))

                    tool_result = await session.call_tool(tool_name, tool_input)
                    result_text = tool_result.content[0].text

                    print("tool result: " + result_text[:120])

                    # one result per tool call, matched by id
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": result_text
                    })

                # send ALL tool results back together in one message
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # ask claude again with all results
                response = claude.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=1024,
                    tools=tools,
                    messages=messages
                )

            # step 4 - print final answer
            for block in response.content:
                if hasattr(block, "text"):
                    print("answer: " + block.text)
                    print()


async def main():
    await ask("How many sick days do I get per year?")
    await ask("What is the hotel limit for business travel?")
    await ask("Do I need VPN to work remotely?")


if __name__ == "__main__":
    asyncio.run(main())