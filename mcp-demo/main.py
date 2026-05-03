import os

from langchain_anthropic import ChatAnthropic
import json
import os

def setup_key():
    with open("config.json", "r") as read_file:
        config = json.load(read_file)
        key=config['claude_key']
    os.environ["ANTHROPIC_API_KEY"] = key


def query_claude(query):
    llm = ChatAnthropic(model="claude-opus-4-5")
    response = llm.invoke(query)
    print(response.content)


if __name__ == '__main__':
    setup_key()
    query_claude('what is the capital of China?')

