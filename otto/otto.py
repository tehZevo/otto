import sys
import argparse

from ollama import Client
from fastmcp import Client as MCPClient

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import run_ollama, print_message, format_tools

config = load_config()
MODEL = config["ollama"]["model"]
CONTEXT_LENGTH = config["ollama"]["context_length"]
MAX_ITERS = config["max_iters"]
MAX_TOOLS_PER_ITER = config["max_tools_per_iter"]

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

# Global variable to store pre-loaded tools
tools = []

async def append_message_and_call_tools(content, tool_calls):
  if content.strip() != "":
    add_message(content, role="assistant")
    print_message(messages[-1])
  
  # Limit the number of tools executed per iteration
  tools_to_execute = tool_calls[:MAX_TOOLS_PER_ITER]
  
  if len(tool_calls) > MAX_TOOLS_PER_ITER:
    print(f"⚠ Limiting tool execution to {MAX_TOOLS_PER_ITER} of {len(tool_calls)} requested tools")
  
  for tool_call in tools_to_execute:
    print(f"🔧 Calling tool: {tool_call.function.name}")
    print(f"   Arguments: {tool_call.function.arguments}")
    
    tool_result = await mcp_client.call_tool(tool_call.function.name, tool_call.function.arguments)
    #TODO: check if error
    #TODO: best way to parse result?
    add_tool_message(tool_call.function.name, str(tool_result.content))
    print_message(messages[-1])

async def agent_loop():
  add_message(USER_PROMPT, role="user")
  print(f"🚀 Starting agent loop (max iterations: {MAX_ITERS})")

  iters = 0
  tool_calls = []
  retried_no_tools = False
  
  while True:
    print(f"\n🔄 Iteration {iters + 1}/{MAX_ITERS}")

    response = await run_ollama(client, MODEL, CONTEXT_LENGTH, messages, tools)
    
    #TODO: for future reference
    up_tokens = response.prompt_eval_count
    down_tokens = response.eval_count
    print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    tool_calls = response.message.tool_calls or []
    
    if len(tool_calls) > 0:
      print(f"🎯 Agent requested {len(tool_calls)} tool(s)")
      retried_no_tools = False  # Reset retry flag when tools are called
    else:
      print(f"✅ Agent completed (no more tools requested)")
    
    await append_message_and_call_tools(response.message.content, tool_calls)
    iters += 1

    if iters >= MAX_ITERS:
      print(f"\n⏹ Stopped: Reached max iterations ({MAX_ITERS})")
      break
    if len(tool_calls) == 0:
      if not retried_no_tools:
        print(f"🔄 No tool calls detected. Retrying once with appended message...")
        add_message("You did not call any tools. If you have completed your task(s), state that you have completed your task(s). Otherwise, call the appropriate tool(s).", role="user")
        retried_no_tools = True
        continue
      else:
        print(f"\n⏹ Stopped: Agent finished (no more tools after retry)")
        break

async def main():
  global tools
  
  print("🔌 Initializing MCP client...")
  async with mcp_client:
    print("✅ MCP client initialized")
    
    # Load tools once at initialization
    print(f"📋 Fetching available tools from MCP servers...")
    raw_tools = await mcp_client.list_tools()
    tools = format_tools(raw_tools)
    print(f"✅ Found {len(tools)} tools available")
    
    await agent_loop()
    print("\n✅ Agent loop completed")
