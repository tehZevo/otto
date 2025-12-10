import sys
import os
import argparse
import json
import time

from fastmcp import Client as MCPClient
from fastmcp.exceptions import ToolError
import openai

from .config import load_system_prompt, load_mcp_servers, load_config
from .utils import run_model, print_message, format_tools, print_tools, extract_tool_results, format_builtin_tools, get_openai_client
from .builtin_tools import BUILTIN_TOOLS, sleep


parser = argparse.ArgumentParser(description="Otto Agent")
parser.add_argument("--config", default="otto.yaml", help="Path to config file")
parser.add_argument("--loop", "-l", action="store_true", help="Loop indefinitely")
parser.add_argument("--sleep", "-s", type=int, default=60, help="Sleep time in seconds between loops (default: 60)")
args = parser.parse_args()

config = load_config(args.config)
config_dir = config.get("_config_dir", ".")
MODEL = config["client"]["model"]
OPENAI_API_KEY = config["client"]["api_key"]
OPENAI_BASE_URL = config["client"]["base_url"]
CONTEXT_LENGTH = config["client"]["context_length"]
#TODO: add NUM_PREDICT to config
MAX_ITERS = config["max_iters"]
MAX_TOOLS_PER_ITER = config["max_tools_per_iter"]
NUM_RETRIES = config.get("num_retries", 10)

#TODO: use as default in config.py
USER_PROMPT = "Execute your given tasks autonomously without any further user input. Use the built-in task completion tool when you are finished."

def add_message(message, role="user"):
  messages.append({"role": role, "content": message})

def add_tool_message(name, content):
  messages.append({"role": "tool", "tool_name": name, "content": f"<tool_response name=\"{name}\">\n{content}\n"})

messages = []
client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

system_prompt = load_system_prompt(config["system_prompts"], config_dir)
add_message(system_prompt, role="system")

#TODO: avoid `ValueError: No MCP servers defined in the config` if no mcp servers defined
mcp_servers_config = load_mcp_servers(config["mcp_servers"], config_dir)
#TODO: create dummy client if empty
mcp_client = MCPClient(mcp_servers_config)

#TODO: make non global
tools = []

async def get_tool_call():
  """Get tool calls from the model, retrying if necessary."""
  retry_count = 0
  while retry_count <= NUM_RETRIES:
    response = await run_model(client, MODEL, CONTEXT_LENGTH, messages, tools, num_predict=256)
    
    up_tokens = response.prompt_eval_count
    down_tokens = response.eval_count
    # print(f"⇄ API Request [⬆ {up_tokens} / ⬇ {down_tokens}]")
    tool_calls = response.message.tool_calls or []
    
    if len(tool_calls) > 0:
      # print(f"🎯 Agent requested {len(tool_calls)} tool(s)")
      return response.message.content, tool_calls
    
    # No tools called - retry or exit
    if retry_count < NUM_RETRIES:
      retry_count += 1
      print(f"🔄 No tool calls detected. Retry {retry_count}/{NUM_RETRIES}...")
      add_message("No tool call detected. Please ensure that your message contains a tool call and is properly formatted.")
      # print_message(messages[-1])
    else:
      # Exhausted retries
      print(f"✅ Agent completed (no more tools requested)")
      print(f"\n⏹ Stopped: Agent finished (no more tools after {NUM_RETRIES} retries)")
      return None, None

async def append_message_and_call_tools(content, tool_calls):
  if content.strip() != "":
    add_message(content, role="assistant")
    print_message(messages[-1])
  
  # Limit the number of tools executed per iteration
  tools_to_execute = tool_calls[:MAX_TOOLS_PER_ITER]
  
  if len(tool_calls) > MAX_TOOLS_PER_ITER:
    print(f"⚠ Limiting tool execution to {MAX_TOOLS_PER_ITER} of {len(tool_calls)} requested tools")
  
  # Check for built-in tools first (like complete_task)
  built_in_tool_calls = []
  mcp_tool_calls = []
  
  for tool_call in tools_to_execute:
    if tool_call.function.name in BUILTIN_TOOLS:
      built_in_tool_calls.append(tool_call)
    else:
      mcp_tool_calls.append(tool_call)
  
  # Handle built-in tools first
  for tool_call in built_in_tool_calls:
    print(f"🔧 [Built-in]: {tool_call.function.name}")
    # print(f"   Arguments: {tool_call.function.arguments}")
    
    try:
      # For built-in tools, we call the function directly
      tool_result = BUILTIN_TOOLS[tool_call.function.name]()
      result_content = json.dumps(tool_result, indent=2)
    except Exception as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ {tool_call.function.name}")
    
    add_tool_message(tool_call.function.name, result_content)
  
  # Handle MCP tools
  for tool_call in mcp_tool_calls:
    print(f"🔧 [MCP] {tool_call.function.name}")
    
    try:
      tool_result = await mcp_client.call_tool(tool_call.function.name, tool_call.function.arguments)
      # Extract content from result objects - only TextContent is allowed
      result_content = extract_tool_results(tool_result)
    except (ToolError, ValueError) as e:
      result_content = f"ToolError: {str(e)}"
      print(f"❌ Tool error: {e}")
    
    add_tool_message(tool_call.function.name, result_content)
    # print_message(messages[-1])

async def agent_loop():
  add_message(USER_PROMPT, role="user")
  print(f"🚀 Starting agent loop (max steps: {MAX_ITERS}, max retries: {NUM_RETRIES})")

  steps = 0
  
  while True:
    content, tool_calls = await get_tool_call()
    
    if tool_calls is None:
      return
    
    await append_message_and_call_tools(content, tool_calls)
    steps += 1

    if any(tool_call.function.name == "sleep" for tool_call in tool_calls):
      print(f"✅ Agent completed (sleep called)")
      break

    if steps >= MAX_ITERS:
      print(f"\n⏹ Stopped: Reached max steps ({MAX_ITERS})")
      break

def setup_tools(mcp_tools):
  mcp_tools = format_tools(mcp_tools)
  builtin_tools = format_builtin_tools(BUILTIN_TOOLS)
  
  available_mcp_tool_names = {tool["function"]["name"] for tool in mcp_tools}
  allowed_mcp_tool_names = config.get("tools", []) or [] #handle cases where it's just `tools:`
  total_mcp_tool_count = len(mcp_tools)
  
  # allowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] in allowed_tool_names]
  allowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] in allowed_mcp_tool_names]
  disallowed_mcp_tools = [tool for tool in mcp_tools if tool["function"]["name"] not in allowed_mcp_tool_names]
  allowed_mcp_tool_count = len(allowed_mcp_tools)

  missing_tools = set(allowed_mcp_tool_names) - available_mcp_tool_names

  if missing_tools:
    print(f"❌ Error: The following tools in config were not found: {', '.join(missing_tools)}")
    print("Exiting due to invalid tool references in otto.yaml")
    sys.exit(1)
  
  print(f"🔒 Allowing {allowed_mcp_tool_count} of {total_mcp_tool_count} tools:")
  print_tools(allowed_mcp_tools, disallowed_mcp_tools)

  return allowed_mcp_tools + builtin_tools

async def main():
  global tools
  
  print("🔌 Initializing MCP client...")
  async with mcp_client:
    print(f"📋 Fetching available tools from MCP servers...")
    mcp_tools = await mcp_client.list_tools()
    tools = setup_tools(mcp_tools)

    while True:
      await agent_loop()
      if not args.loop:
        break
      print(f"💤 Sleeping for {args.sleep} seconds before next loop...")
      time.sleep(args.sleep)
      # Reset messages for next loop
      messages.clear()
      # Re-add system prompt for next loop
      add_message(system_prompt, role="system")
