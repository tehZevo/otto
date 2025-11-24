import sys
import asyncio

from ollama import Client
from fastmcp import Client as MCPClient, FastMCP

def format_tools(tools):
  return [{
    'type': 'function',
    'function': {
      'name': tool.name,
      'description': tool.description,
      'parameters': tool.inputSchema
    }
  } for tool in tools]

async def run_ollama(client, mcp_client, model, num_ctx, messages):
  tools = await mcp_client.list_tools()
  tools = format_tools(tools)
  #TODO: make ollama call async?
  return client.chat(
    model=model,
    messages=messages,
    tools=tools,
    stream=False,
    options={
      "num_ctx": num_ctx
    }
  )

def print_message(message):
  if message['role'] == 'system':
    print(f"⚙ {message['content']}")
  elif message['role'] == 'user':
    print(f"👤 {message['content']}")
  elif message['role'] == 'assistant':
    print(f"💬 {message['content']}")
  elif message['role'] == 'tool':
    # print(f"🔧 {message['tool_name']}: {message['content']}")
    print(f"🔧 {message['tool_name']}")
