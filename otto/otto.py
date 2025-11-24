import sys
import argparse

from ollama import Client
from fastmcp import Client as MCPClient

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import format_tools, run_ollama, print_message

#TODO: max tool calls per iter?

config = load_config()
MODEL = config["ollama"]["model"]
CONTEXT_LENGTH = config["ollama"]["context_length"]
MAX_ITERS = config["max_iters"]

#TODO: use as default in config.py
USER_PROMPT = "Execute your given tasks autonomously without any further user input."

def add_message(message, role="user"):
  messages.append({"role": role, "content": message})

def add_tool_message(name, content):
  # messages.append({"role": "tool", "tool_name": name, "content": content})
  messages.append({"role": "tool", "tool_name": name, "content": f"<tool_response name=\"{name}\">\n{content}\n</tool_response>"})

client = Client(host=config["ollama"]["host"])
messages = []

system_prompt = load_system_prompt(config["system_prompts"])
add_message(system_prompt, role="system")

#TODO: avoid `ValueError: No MCP servers defined in the config` if no mcp servers defined
mcp_servers_config = load_mcp_servers(config["mcp_servers"])
#TODO: create dummy client if empty
mcp_client = MCPClient(mcp_servers_config)

async def append_message_and_call_tools(content, tool_calls):
  if content.strip() != "":
    add_message(content, role="assistant")
    print_message(messages[-1])
  
  for tool_call in tool_calls:
    tool_result = await mcp_client.call_tool(tool_call.function.name, tool_call.function.arguments)
    #TODO: check if error
    # print(tool_result)
    add_tool_message(tool_call.function.name, tool_result.data)
    print_message(messages[-1])

async def agent_loop():
  add_message(USER_PROMPT, role="user")

  iters = 0
  tool_calls = []
  
  while True:
    #TODO: catch error
    response = await run_ollama(client, mcp_client, MODEL, CONTEXT_LENGTH, messages)
    #TODO: for future reference
    up_tokens = response.prompt_eval_count
    down_tokens = response.eval_count
    print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    tool_calls = response.message.tool_calls or []
    
    await append_message_and_call_tools(response.message.content, tool_calls)
    iters += 1

    if iters >= MAX_ITERS or len(tool_calls) == 0:
      break

async def main():
  async with mcp_client:
    await agent_loop()
    # print(messages)
